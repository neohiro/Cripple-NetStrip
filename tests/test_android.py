"""
Android-specific regression tests.

These run on any OS (no device / jnius / kivy required) and gate the CI
Android pipeline. They cover:
  - TUN packet parsing / response synthesis in the VPN interceptor
  - The Android DNS forwarding port contract (interceptor <-> engine)
  - platform/android.py behavior with mocked JNI objects
"""

import os
import socket
import struct
import sys
import types

import pytest

# ---------------------------------------------------------------------------
# Stubs: the interceptor imports pyjnius at import time; provide a fake module
# so tests run on desktop CI machines.
if "jnius" not in sys.modules:
    jnius_stub = types.ModuleType("jnius")

    def _autoclass(*_a, **_k):
        raise ImportError("pyjnius unavailable on desktop CI")

    jnius_stub.autoclass = _autoclass
    sys.modules["jnius"] = jnius_stub

from netstrip.core.interceptor.android import (  # noqa: E402
    PROTO_TCP,
    PROTO_UDP,
    AndroidVPNInterceptor,
)
from netstrip.core.dns_proxy import ANDROID_DNS_PORT  # noqa: E402


# ---------------------------------------------------------------------------
# Packet builders


def build_ipv4_udp_packet(src_ip, dst_ip, src_port, dst_port, payload, ttl=64):
    """Build a minimal IPv4+UDP packet exactly as a TUN device would emit."""
    udp_len = 8 + len(payload)
    udp_header = struct.pack("!HHHH", src_port, dst_port, udp_len, 0) + payload

    total_len = 20 + len(udp_header)
    header = bytearray(struct.pack(
        "!BBHHHBBH4s4s",
        0x45, 0x00, total_len, 0x1234, 0x4000, ttl, PROTO_UDP, 0,
        socket.inet_aton(src_ip), socket.inet_aton(dst_ip),
    ))
    chk = AndroidVPNInterceptor._calc_checksum(None, bytes(header))
    header[10:12] = struct.pack("!H", chk)
    return bytes(header) + udp_header


class FakeTun:
    """Stands in for os.read/os.write on the VPN fd."""

    def __init__(self, packets):
        self._packets = list(packets)
        self.written = []

    def read(self, fd, n):
        if not self._packets:
            raise BlockingIOError
        return self._packets.pop(0)

    def write(self, fd, data):
        self.written.append(data)
        return len(data)


@pytest.fixture()
def interceptor(monkeypatch):
    """An interceptor whose DNS forwarding returns a canned answer and whose
    os.write calls are captured."""

    class _Instance:
        def getVpnFd(self):
            return 42

        def isFullMode(self):
            return True

    inst = AndroidVPNInterceptor(callback=lambda *a, **kw: True, engine=None)
    inst.NetStripVpnService = types.SimpleNamespace(getInstance=lambda: _Instance())
    inst._fd = 42

    tun = FakeTun([])
    monkeypatch.setattr(os, "write", lambda fd, data: tun.write(fd, data))
    inst._tun = tun
    inst._process_dns = lambda payload: b"\x00resp"  # canned upstream answer
    return inst, tun


# ---------------------------------------------------------------------------
# Tests


def test_android_dns_port_contract():
    """The interceptor MUST forward to the port the engine binds on Android.

    Regression: it historically hardcoded 5053 while the engine bound 5353 —
    every intercepted DNS query silently timed out on-device.
    """
    assert ANDROID_DNS_PORT == 5353


def test_ipv4_dns_query_gets_synthesized_response(interceptor, monkeypatch):
    inst, tun = interceptor
    query = build_ipv4_udp_packet("10.8.0.2", "10.8.0.1", 44444, 53, b"q" * 12)
    tun._packets.append(query)

    inst._process_ipv4(query)

    assert len(tun.written) == 1
    resp = tun.written[0]

    # Header sanity
    assert resp[0] >> 4 == 4
    total_len = struct.unpack("!H", resp[2:4])[0]
    assert total_len == len(resp)

    # Addresses swapped: response comes FROM the resolver TO the client
    assert socket.inet_ntoa(resp[12:16]) == "10.8.0.1"
    assert socket.inet_ntoa(resp[16:20]) == "10.8.0.2"

    # UDP ports swapped and payload length correct
    sport, dport, ulen, _ = struct.unpack("!HHHH", resp[20:28])
    assert (sport, dport) == (53, 44444)
    assert ulen == 8 + len(b"\x00resp")
    assert resp[28:] == b"\x00resp"

    # IP checksum must validate (recompute over header with field zeroed)
    hdr = bytearray(resp[:20])
    hdr[10:12] = b"\x00\x00"
    assert AndroidVPNInterceptor._calc_checksum(None, bytes(hdr)) == struct.unpack("!H", resp[10:12])[0]


def test_full_mode_blocked_packet_is_dropped():
    dropped_target = "93.184.216.34"

    inst = AndroidVPNInterceptor(callback=lambda s, sp, d, dp, proto, **kw: d != dropped_target, engine=None)
    inst._fd = 42
    tun = FakeTun([])
    inst._tun = tun

    import netstrip.core.interceptor.android as mod
    orig_write = os.write
    writes = []
    mod.os.write = lambda fd, data: writes.append(data)  # patch module ref used by interceptor

    try:
        blocked = build_ipv4_udp_packet("10.8.0.2", dropped_target, 5555, 443, b"x" * 8)
        inst._process_ipv4(blocked)
        allowed = build_ipv4_udp_packet("10.8.0.2", "1.1.1.1", 5556, 443, b"y" * 8)
        inst._process_ipv4(allowed)
    finally:
        mod.os.write = orig_write

    assert len(writes) == 1
    assert socket.inet_ntoa(writes[0][16:20]) == "1.1.1.1"


def test_dns_only_mode_passes_non_dns_traffic_through(monkeypatch):
    inst = AndroidVPNInterceptor(callback=lambda *a, **kw: pytest.fail("callback must not run in DNS_ONLY"), engine=None)
    inst._fd = 42
    inst._is_full_mode = False
    tun = FakeTun([])
    monkeypatch.setattr(os, "write", lambda fd, data: tun.write(fd, data))

    passthrough = build_ipv4_udp_packet("10.8.0.2", "1.1.1.1", 9999, 443, b"z" * 8)
    inst._process_ipv4(passthrough)
    assert tun.written == [passthrough]  # byte-identical passthrough


def test_callback_exception_fails_open(interceptor):
    """Fail-open contract: a classifier crash must never blackhole the user."""
    inst, tun = interceptor

    def boom(*a):
        raise RuntimeError("classifier down")

    inst.callback = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError('classifier down'))
    pkt = build_ipv4_udp_packet("10.8.0.2", "1.1.1.1", 7000, 443, b"p" * 8)
    inst._process_ipv4(pkt)
    assert len(tun.written) == 1


def test_tcp_packets_reach_the_classifier(interceptor):
    inst, tun = interceptor
    seen = []
    inst.callback = lambda s, sp, d, dp, proto, **kw: (seen.append((d, dp, proto)) or True)

    ihl = 20
    tcp = bytearray(build_ipv4_udp_packet("10.8.0.2", "1.2.3.4", 1234, 5678, b""))[:ihl]
    # Rewrite protocol to TCP + rebuild ports area manually
    tcp[9] = PROTO_TCP
    tcp[ihl:ihl + 4] = struct.pack("!HH", 1234, 5678)
    tcp += b"\x00" * 4

    inst._process_ipv4(bytes(tcp))
    assert seen == [("1.2.3.4", 5678, "tcp")]


def test_platform_android_set_dns_with_mocked_jni(monkeypatch):
    """platform/android.set_system_dns succeeds when a VpnService handle exists."""
    from netstrip.platform.android import AndroidPlatform

    plat = AndroidPlatform.__new__(AndroidPlatform)  # skip __init__ JNI probing
    plat.VpnService = object()  # truthy handle

    assert plat.set_system_dns("wlan0", "127.0.0.1") is True

    plat.VpnService = None
    assert plat.set_system_dns("wlan0", "127.0.0.1") is False
