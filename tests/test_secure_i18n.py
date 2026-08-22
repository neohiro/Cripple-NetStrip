"""
Tests for the secure local secret store and the i18n layer.
Both run fully offline with a mocked home directory.
"""

import os

import pytest

REAL_EXPANDUSER = os.path.expanduser


@pytest.fixture()
def fake_home(tmp_path, monkeypatch):
    monkeypatch.setattr(os.path, "expanduser", lambda p: str(tmp_path) if p == "~" else REAL_EXPANDUSER(p))
    return tmp_path


# ---------------------------------------------------------------------------
# secure_store


def test_psk_roundtrip_windows_dpapi(fake_home):
    """On Windows the keyfile must contain DPAPI-wrapped bytes, never plaintext."""
    from netstrip.core.secure_store import store_psk, load_psk, _keyfile_path

    class FakeDB:
        def get_setting(self, k, d=None):
            return d

        def set_setting(self, k, v):
            self.saved = (k, v)

    db = FakeDB()
    store_psk(db, "PAIRING-KEY-123")
    raw = _keyfile_path().read_bytes()
    if os.name == "nt":
        assert raw.startswith(b"DPAPI:") and b"PAIRING" not in raw
    else:
        assert raw.startswith(b"RAW:")
    assert load_psk(db) == "PAIRING-KEY-123"


def test_legacy_db_plaintext_migrates_to_keyfile_and_is_scrubbed(fake_home):
    from netstrip.core.secure_store import store_psk, load_psk, _keyfile_path
    import tempfile

    from netstrip.data.database import Database
    db_path = os.path.join(tempfile.mkdtemp(), "m.db")
    db = Database(db_path=db_path)
    try:
        db.set_setting("lan_shield_psk", "LEGACY-PLAIN")
        assert load_psk(db) == "LEGACY-PLAIN"          # triggers migration
        assert db.get_setting("lan_shield_psk") == "KEYFILE"
        assert _keyfile_path().exists()
        # Subsequent stores still work
        store_psk(db, "NEW-VALUE")
        assert load_psk(db) == "NEW-VALUE"
    finally:
        db.stop()


# ---------------------------------------------------------------------------
# i18n


def test_i18n_fallback_returns_english_source():
    from netstrip.i18n import set_language, t

    set_language("en")
    assert t("modal.killswitch.engage") == "ENGAGE KILLSWITCH"


def test_i18n_spanish_catalog_applies():
    from netstrip.i18n import set_language, t

    set_language("es")
    assert t("modal.killswitch.engage") == "ACTIVAR KILLSWITCH"
    set_language("en")


def test_i18n_unknown_language_falls_back_to_english():
    from netstrip.i18n import set_language, t, get_language

    set_language("xx")   # no catalog
    assert get_language() == "en"
    assert t("modal.recovery.restore") == "RESTORE NETWORK"


def test_i18n_available_languages_lists_installed():
    from netstrip.i18n import available_languages

    langs = available_languages()
    for expected in ("en", "es", "de"):
        assert expected in langs
