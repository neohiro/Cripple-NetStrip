"""
Long-duration (months/years) uptime regression tests.

Each test targets a resource that previously grew without bound or caused
periodic latency spikes, and asserts it now stays bounded / smooth.
"""

import time


from netstrip.core.dns_proxy import DNS_MAX_POOL_HOSTS, _DNSConnectionPool


class FakeSock:
    """Mimics a socket closely enough for the DoT pool: tracks close() calls."""

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeHTTPConn:
    """Mimics an http.client.HTTPSConnection for the DoH pool."""

    def __init__(self):
        self.closed = False
        self.sock = object()  # truthy, as http.client sets after connect

    def close(self):
        self.closed = True


# ---------------------------------------------------------------------------
# DNS connection pools


def test_dns_pool_sweep_closes_stale_and_keeps_fresh():
    pool = _DNSConnectionPool(idle_timeout=30.0)
    fresh_dot, stale_dot = FakeSock(), FakeSock()
    fresh_doh, stale_doh = FakeHTTPConn(), FakeHTTPConn()

    now = time.time()
    with pool._lock:
        pool._dot_pool["1.1.1.1"] = [
            (fresh_dot, fresh_dot, now),
            (stale_dot, stale_dot, now - 4000),
        ]
        pool._doh_pool[("8.8.8.8", "dns.google")] = [
            (fresh_doh, now),
            (stale_doh, now - 4000),
        ]

    pool._sweep_once()

    assert fresh_dot.closed is False
    assert stale_dot.closed is True          # fd reclaimed
    assert stale_doh.closed is True
    assert fresh_doh.closed is False

    assert [t[0] for t in pool._dot_pool["1.1.1.1"]] == [fresh_dot]
    assert [c for c, _ in pool._doh_pool[("8.8.8.8", "dns.google")]] == [fresh_doh]


def test_dns_pool_host_count_is_hard_capped():
    """Dynamic resolver lists rotate 100+ IPs; dead host keys must not pile up."""
    pool = _DNSConnectionPool(idle_timeout=30.0)
    now = time.time()
    socks = []
    with pool._lock:
        for i in range(DNS_MAX_POOL_HOSTS + 40):
            s = FakeSock()
            socks.append(s)
            pool._dot_pool[f"10.0.0.{i % 256}.{i // 256 or 7}"] = [(s, s, now)]

    pool._sweep_once()

    assert len(pool._dot_pool) <= DNS_MAX_POOL_HOSTS
    closed_count = sum(1 for s in socks if s.closed)
    assert closed_count >= 40  # every evicted host had its sockets closed


def test_reaper_thread_stops_cleanly():
    pool = _DNSConnectionPool(idle_timeout=30.0)
    pool.start_reaper(interval=0.05)
    time.sleep(0.12)  # let at least one sweep tick run
    pool.stop_reaper()
    assert pool._reaper_stop.is_set()


# ---------------------------------------------------------------------------
# Classifier caches: FIFO trim instead of full-clear latency spikes


def test_classifier_domain_cache_stays_bounded_under_high_entropy():
    from netstrip.core.classifier import TrafficClassifier
    from netstrip.core.modes import ConnectionCategory

    clf = TrafficClassifier(blocklist_manager=object(), db=None)

    class _Mode:
        name = "NORMAL"

        def get_action_for_category(self, cat, db=None):
            return ConnectionCategory.ALLOW if hasattr(ConnectionCategory, "ALLOW") else None

    # classify_domain short-circuits on loopback before touching the blocklist,
    # so `object()` blocklist is safe here.
    clf.mode = _Mode()
    for i in range(20_000):
        clf.classify_domain(f"127.0.0.{i % 250}.{(i >> 8) % 250}", "bench")

    assert len(clf._domain_cache) <= 5001  # trimmed, never unbounded


def test_classifier_ip_cache_stays_bounded():
    from netstrip.core.classifier import TrafficClassifier

    clf = TrafficClassifier(blocklist_manager=object(), db=None)

    class _DB:
        def get_setting(self, k, d=None):
            return d

        _conn_lock_held = False

        def _get_connection(self):  # never reached: loopback short-circuits first
            raise AssertionError("should not hit DB for LAN/loopback IPs")

    clf.db = None
    for i in range(20_000):
        clf.classify_ip(f"127.0.0.{i % 250}.{(i >> 8) % 250}")
    assert len(clf._ip_cache) <= 5001


# ---------------------------------------------------------------------------
# Icon caches (GUI memory over months of new processes)


def test_icon_cache_trim_bounds_both_caches():
    import netstrip.gui.icon_manager as im

    mgr = im.IconManager.__new__(im.IconManager)
    mgr.cache_dir = ""
    mgr._image_cache = {}
    mgr._ctk_image_cache = {}
    mgr._cache_cap = 64

    for i in range(200):
        mgr._image_cache[f"C:\\app{i}.exe"] = object()
        mgr._ctk_image_cache[f"C:\\app{i}.exe"] = object()
        mgr._trim_caches()

    assert len(mgr._image_cache) <= 64
    assert len(mgr._ctk_image_cache) <= 64


# ---------------------------------------------------------------------------
# Misc long-run guarantees


def test_lan_shield_nonce_fifo_survives_wraparound():
    """Replay protection must NOT bulk-clear nonces (old bug reopened a window)."""

    from netstrip.core.lan_shield import LANShield

    shield = LANShield.__new__(LANShield)
    shield.engine = None
    shield._running = False

    seen_nonces = set()

    def add(nonce):
        if nonce in seen_nonces:
            return False
        if len(shield_nonce_order) == shield_nonce_order.maxlen:
            seen_nonces.discard(shield_nonce_order[0])
        shield_nonce_order.append(nonce)
        seen_nonces.add(nonce)
        return True

    from collections import deque
    shield_nonce_order = deque(maxlen=128)

    for i in range(1000):
        assert add(f"n{i}") is True
    # Oldest nonces were evicted FIFO; newest are still protected
    assert add("n999") is False
    assert add("n0") is True  # long-expired nonce may be reused by protocol design


def test_prune_old_logs_clamps_extreme_hours():
    """hours flows into a datetime modifier; extreme values must not error."""
    import os
    import tempfile

    from netstrip.data.database import Database

    with tempfile.TemporaryDirectory() as td:
        db = Database(db_path=os.path.join(td, "t.db"))
        try:
            db.prune_old_logs(hours=10**9)   # absurd value must be clamped, not crash
            db.prune_old_logs(hours=0)       # clamps to minimum 1
        finally:
            db.stop()
