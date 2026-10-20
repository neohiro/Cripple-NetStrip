"""
Tests for the notification digest system.
Verifies buffering, aggregation, flush-on-stop, and lock safety.
"""

import builtins
import os
import threading

import pytest

from netstrip.core.engine import NetStripEngine

_HERE = os.path.dirname(__file__)


def _read_source(*parts: str) -> str:
    """Read a source file from the package via a context manager.

    Test-only helper for the wiring assertions below: they grep the real
    source to confirm a call site exists, and must not leak the file handle.
    """
    path = os.path.join(_HERE, "..", "netstrip", *parts)
    with open(path, encoding="utf-8") as fh:
        return fh.read()


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
        # Capture the real __import__ *before* patching builtins. Calling
        # __import__ from inside the replacement looks up the name again and
        # finds the replacement, so it recursed until Python raised
        # RecursionError - which pytest then turned into a hard INTERNALERROR
        # that aborted the entire test run (not just this file).
        real_import = builtins.__import__

        def fake_import(name, *a, **kw):
            if name == "plyer":
                return type("M", (), {"notification": type("N", (), {
                    "notify": staticmethod(lambda **kw2: toasted.append(kw2))
                })()})
            return real_import(name, *a, **kw)

        monkeypatch.setattr(builtins, "__import__", fake_import)
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
        assert "_note_blocked_for_digest" in _read_source("core", "dns_proxy.py"), \
            "dns_proxy.py does not feed the notification digest"

    def test_digest_is_flushed_by_runtime_loop(self):
        """The digest must actually be drained at runtime, not only in tests.

        Defining _flush_notification_digest() (or feeding the buffer) is not
        enough: if nothing periodic calls it, blocked events accumulate for the
        process lifetime and no aggregate toast is ever shown. Pin the wiring.
        """
        assert "_flush_notification_digest()" in _read_source("core", "engine.py"), \
            "engine.py defines the digest flush but never calls it from a loop"
