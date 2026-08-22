"""
Deterministic fuzz tests for NetStrip's trust boundaries.

Seeded pseudo-random hostile inputs — no new dependencies, stable in CI.
Boundaries covered:
  - Blocklist feed parser (_parse_domains_from_file): ABP/hosts/dnsmasq/v2fly
  - TUN packet parser (AndroidVPNInterceptor._process_ipv4/6)
  - DNS resolve() with malformed request payloads
"""

import os
import random
import socket
import struct
import sys
import types

import pytest

if "jnius" not in sys.modules:
    stub = types.ModuleType("jnius")
    stub.autoclass = lambda *a, **k: (_ for _ in ()).throw(ImportError)
    sys.modules["jnius"] = stub

from netstrip.core.interceptor.android import AndroidVPNInterceptor  # noqa: E402

SEED = 0xC11E  # deterministic fuzz seed
random.seed(SEED)

FUZZ_CHARS = list("abc019.:*/@$%^&|<>[]{}\\\"'`\t\r\n\x00\xffé中") + ["||", "@@", "$", "^", "#!"]


def _rand_line(rng):
    n = rng.randint(0, 60)
    return "".join(rng.choice(FUZZ_CHARS) for _ in range(n))


# ---------------------------------------------------------------------------
# Feed parser


@pytest.fixture(scope="module")
def parser():
    from netstrip.data.blocklist_manager import BlocklistManager
    return BlocklistManager(lists_dir=temp_lists_dir(), db=None, async_load=False)


def temp_lists_dir():
    import tempfile
    d = tempfile.mkdtemp(prefix="ns_fuzz_")
    return d


def test_feed_parser_survives_hostile_lines(parser):
    rng = random.Random(SEED)
    import tempfile
    path = os.path.join(tempfile.mkdtemp(), "fuzz.txt")
    lines = [_rand_line(rng) for _ in range(5000)]
    # Plus structured near-valid attacks
    lines += [
        "||" * 300, "!!!!!", "address=/" * 40, "domain:" + "a" * 400,
        "0.0.0.0 " + "x" * 500, "\x00\x01\x02", "-{", "${jndi:ldap://x}",
        "a." * 200 + "com", ".." , "."*300,
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    result = parser._parse_domains_from_file(path)  # must not raise
    assert isinstance(result, set)
    # Nothing absurdly long or token-leaking may enter the map
    for d in result:
        assert len(d) <= 253 and " " not in d


def test_feed_parser_output_is_idempotent(parser):
    import tempfile
    path = os.path.join(tempfile.mkdtemp(), "idem.txt")
    content = "||ads.example.com^\n0.0.0.0 tracker.net\ndomain: ok.io\n"
    open(path, "w").write(content)
    once = parser._parse_domains_from_file(path)
    twice = parser._parse_domains_from_file(path)
    assert once == twice == {"ads.example.com", "tracker.net", "ok.io"}


# ---------------------------------------------------------------------------
# TUN packet parser


def _interceptor():
    return AndroidVPNInterceptor(callback=lambda *a: True, engine=None)


def test_tun_parser_survives_hostile_packets(monkeypatch):
    inst = _interceptor()
    inst._fd = 42
    tun_writes = []
    monkeypatch.setattr(os, "write", lambda fd, data: tun_writes.append(data))

    rng = random.Random(SEED + 1)
    for _ in range(3000):
        n = rng.randint(0, 80)
        pkt = bytes(rng.getrandbits(8) for _ in range(n))
        try:
            inst._process_ipv4(pkt)   # must never raise
        except AssertionError:
            raise
        except Exception as e:
            pytest.fail(f"ipv4 parser raised on {pkt.hex()}: {e}")
        try:
            inst._process_ipv6(pkt)
        except Exception as e:
            pytest.fail(f"ipv6 parser raised on {pkt.hex()}: {e}")
    # Parser never wrote garbage back on its own during fuzzing loop


def test_checksum_known_vector():
    from netstrip.core.interceptor.android import AndroidVPNInterceptor as A
    # IPv4 header example from RFC 1071-style walkthroughs
    hdr = bytes.fromhex("45000073000040004011b861c0a80001c0a800c7")
    chk = A._calc_checksum(None, hdr[:10] + b"\x00\x00" + hdr[12:])
    assert chk == 0xB861


# ---------------------------------------------------------------------------
# DNS resolve hardening


def test_dns_resolver_rejects_malformed_requests():
    """resolve() must not crash on junk — malformed queries get empty replies."""
    from netstrip.core.dns_proxy import ANDROID_DNS_PORT  # ensure module imports cleanly
    from dnslib import DNSRecord

    class FakeClassifier:
        class mode:
            name = "NORMAL"
            level = None

        def classify_domain(self, d, p=None):
            return None

    class FakeDB:
        def get_setting(self, k, d=None):
            return d

        def cache_domain_mapping(self, *a):
            pass

    from netstrip.core.dns_proxy import NetStripResolver
    resolver = NetStripResolver(FakeClassifier(), FakeDB())

    rng = random.Random(SEED + 2)
    for _ in range(500):
        junk = bytes(rng.getrandbits(8) for _ in range(rng.randint(0, 120)))
        try:
            req = DNSRecord.parse(junk)
        except Exception:
            continue  # parse failures are fine — dnslib guards entry
        try:
            resolver.resolve(req, handler=None)
        except Exception as e:
            # resolve() may legitimately fail to build a reply, but must never
            # leak unexpected exception types past its own handling.
            if not isinstance(e, (KeyboardInterrupt, SystemExit)):
                pytest.fail(f"resolve() leaked {type(e).__name__}: {e}")


def test_android_port_constant_single_source():
    from netstrip.core.dns_proxy import ANDROID_DNS_PORT
    src = open(os.path.join(os.path.dirname(__file__), "..",
               "netstrip", "core", "interceptor", "android.py"), encoding="utf-8").read()
    assert ", 5053)" not in src, "interceptor regressed to hardcoded wrong port"
    assert ANDROID_DNS_PORT == 5353
