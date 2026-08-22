"""
Secure local secret store for NetStrip (PSK and similar device-local secrets).

Design:
  - The secret lives in a dedicated keyfile (~/.NetStrip/psk.key), NOT in the
    SQLite settings table (which is world-readable to any process the user
    runs, gets exported by --export-profile, and shows up in DB dumps).
  - On Windows the contents are DPAPI-wrapped (machine+user bound, no plaintext
    on disk). On macOS/Linux the file is chmod 0600.
  - Legacy migration: a plaintext `lan_shield_psk` row in the DB is moved into
    the keyfile automatically on first use; the DB keeps only a marker.

Trust model note: possession of the PSK *is* the LAN pairing link — this store
protects it at rest from other local users/processes reading the profile, not
from an attacker who already controls the account.
"""

import base64
import logging
import os
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

KEYFILE_NAME = "psk.key"
DB_MARKER = "KEYFILE"
_PREFIX_DPAPI = b"DPAPI:"
_PREFIX_RAW = b"RAW:"


def _keyfile_path() -> Path:
    return Path.home() / ".NetStrip" / KEYFILE_NAME


def _dpapi_protect(data: bytes) -> bytes:
    """Windows DPAPI (CryptProtectData) — user+machine bound, no extra deps."""
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def blob(raw: bytes) -> DATA_BLOB:
        buf = ctypes.create_string_buffer(raw, len(raw))
        return DATA_BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))

    in_blob = blob(data)
    out_blob = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    )
    if not ok:
        raise OSError("CryptProtectData failed")
    try:
        wrapped = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)
    return _PREFIX_DPAPI + base64.b64encode(wrapped)


def _dpapi_unprotect(blob: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    payload = base64.b64decode(blob[len(_PREFIX_DPAPI):])
    in_blob = DATA_BLOB(len(payload), ctypes.cast(
        ctypes.create_string_buffer(payload, len(payload)), ctypes.POINTER(ctypes.c_char)))
    out_blob = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    )
    if not ok:
        raise OSError("CryptUnprotectData failed")
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _write_keyfile(content: bytes):
    path = _keyfile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        f.write(content)
    try:
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)  # 0600 on POSIX (no-op on Windows)
    except Exception:
        pass
    os.replace(tmp, path)


def _read_keyfile() -> bytes | None:
    path = _keyfile_path()
    if not path.exists():
        return None
    raw = path.read_bytes().strip()
    if not raw:
        return None
    if raw.startswith(_PREFIX_DPAPI):
        try:
            return _dpapi_unprotect(raw)
        except Exception as e:
            logger.error(f"DPAPI unprotect failed (moved machine? deleted user key?): {e}")
            return None
    if raw.startswith(_PREFIX_RAW):
        return base64.b64decode(raw[len(_PREFIX_RAW):])
    # Very old layout: bare base64 PSK — accept and let caller re-store securely
    return raw


def store_psk(db, psk_str: str):
    """Persist the PSK into the protected keyfile; scrub any legacy DB copy."""
    psk_bytes = psk_str.encode("utf-8") if isinstance(psk_str, str) else psk_str
    content = _dpapi_protect(psk_bytes) if os.name == "nt" else (
        _PREFIX_RAW + base64.b64encode(psk_bytes))
    _write_keyfile(content)
    try:
        if db is not None and db.get_setting("lan_shield_psk", "") != DB_MARKER:
            db.set_setting("lan_shield_psk", DB_MARKER)
    except Exception:
        pass


def load_psk(db) -> str | None:
    """Load the PSK from the keyfile; migrates a legacy plaintext DB row once."""
    raw = _read_keyfile()
    if raw:
        return raw.decode("utf-8")

    # Migration path: plaintext PSK sitting in the settings table
    if db is not None:
        legacy = db.get_setting("lan_shield_psk", "")
        if legacy and legacy != DB_MARKER:
            store_psk(db, legacy)
            logger.info("Migrated LAN Shield PSK from database to protected keyfile.")
            return legacy
    return None
