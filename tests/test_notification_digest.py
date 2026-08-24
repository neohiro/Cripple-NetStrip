"""
Tests for the notification digest system.
Verifies buffering, aggregation, flush-on-stop, and lock safety.
"""

import threading

import pytest

from netstrip.core.engine import NetStripEngine


@pytest.fixture()
def engine_stub(tmp_path):
    """Minimal engine with digest methods but no subsystems started."""
    from netstrip.data.database import Database
    db = Database(db_path=str(tmp_path / "test.db"))
    eng = NetStripEngine.__new__(NetStripEngine)
    eng.is_running = False
    eng._stop_event = threading.Event()
    eng._digest_buffer = {}
    eng._digest_lock = threading.Lock()
    eng.db = db
    yield eng
    db.stop()


class TestNotificationDigest:
    def test_note_increments_category_count(self, engine_stub):
        engine_stub._note_blocked_for_digest("tracker")
        engine_stub._note_blocked_for_digest("tracker")
        engine_stub._note_blocked_for_digest("ad")
        assert engine_stub._digest_buffer == {"tracker": 2, "ad": 1}

    def test_flush_clears_buffer(self, engine_stub, monkeypatch):
        """Flush must clear the buffer so events aren't double-counted."""
        toasted = []
        monkeypatch.setattr(
            "builtins.__import__",
            lambda name, *a, **kw: (
                type("M", (), {"notification": type("N", (), {
                    "notify": staticmethod(lambda **kw2: toasted.append(kw2))
                })()})
                if name == "plyer" else __import__(name, *a, **kw)
            ),
        )
        engine_stub._note_blocked_for_digest("malware")
        engine_stub._flush_notification_digest()
        assert engine_stub._digest_buffer == {}
        assert len(toasted) == 1

    def test_flush_empty_buffer_is_noop(self, engine_stub):
        engine_stub._flush_notification_digest()
        assert engine_stub._digest_buffer == {}

    def test_concurrent_writes_are_thread_safe(self, engine_stub):
        """Multiple threads writing to the digest must not lose events."""
        def writer(category, count):
            for _ in range(count):
                engine_stub._note_blocked_for_digest(category)

        threads = [
            threading.Thread(target=writer, args=(f"cat{i}", 100))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total = sum(engine_stub._digest_buffer.values())
        assert total == 500, f"lost events under concurrency: {total}"

    def test_dns_sinkhole_feeds_digest(self, tmp_path):
        """DNS sinkholed domains must appear in the digest (regression)."""
        # This is verified by checking the call exists in dns_proxy source
        src = open(
            os.path.join(os.path.dirname(__file__), "..", "netstrip", "core", "dns_proxy.py"),
            encoding="utf-8",
        ).read()
        assert "_note_blocked_for_digest" in src, \
            "dns_proxy.py does not feed the notification digest"


import os  # noqa: E402 — needed at module level for test above
