"""
Tests for the verified self-update pipeline — no network required.

The GitHub I/O boundary (http_download / latest_release) is monkeypatched;
everything else (manifest parsing, hash verification, asset selection,
mismatch abort semantics) runs for real.
"""

import hashlib
import json

import pytest

from netstrip.core.self_update import (
    SelfUpdateError,
    SelfUpdater,
    parse_sha256sums,
    pick_assets,
    sha256_of_file,
    verify_file_hash,
)

API_URL = "https://api.github.com/repos/neohiro/Cripple-NetStrip/releases/latest"
SETUP_NAME = "NetStrip-Setup-v9.9.9.exe"          # THE single Windows artifact
LEGACY_ZIP_NAME = "netstrip-v9.9.9-windows.zip"   # old portable fallback
ZIP_NAME = LEGACY_ZIP_NAME                        # manifest lists lowercase
ZIP_BYTES = b"PK\x03\x04 fake-but-deterministic zip payload \x00\x01\x02"
GOOD_HASH = hashlib.sha256(ZIP_BYTES).hexdigest()


def make_manifest():
    return (
        f"# SHA256SUMS for v9.9.9\n"
        f"{GOOD_HASH}  {SETUP_NAME.lower()}\n"
        f"{'a'*64}  netstrip-v9.9.9-linux.zip\n"
    )


class FakeResp:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.headers = {"Content-Length": str(len(payload))}

    def read(self, n=None):
        if n is None or n < 0:
            out, self.payload = self.payload, b""
        else:
            out, self.payload = self.payload[:n], self.payload[n:]
        return out

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _asset(name, size=10):
    return {"name": name, "browser_download_url": f"https://example/{name}", "size": size}


def build_release(include_legacy_zip=False):
    assets = [_asset(SETUP_NAME, len(ZIP_BYTES))]
    if include_legacy_zip:
        assets.append(_asset(LEGACY_ZIP_NAME.capitalize(), len(ZIP_BYTES)))
    assets.append(_asset("SHA256SUMS.txt", 200))
    return {"tag_name": "v9.9.9", "assets": assets}


def fake_transport(monkeypatch, *, zip_bytes=ZIP_BYTES, sums_text=None):
    """Install a fully in-memory GitHub transport. Returns the payloads dict so
    tests can assert on requested URLs."""
    release = build_release()
    payloads = {
        API_URL: json.dumps(release).encode(),
        f"https://example/SHA256SUMS.txt":
            (sums_text if sums_text is not None else make_manifest()).encode(),
        f"https://example/{SETUP_NAME}": zip_bytes,
        f"https://example/{LEGACY_ZIP_NAME.capitalize()}": zip_bytes,
    }

    def fake_urlopen(req, timeout=None, context=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        assert url in payloads, f"unexpected URL requested: {url}"
        return FakeResp(payloads[url])

    # Tests must be host-OS independent: always exercise the Windows asset path
    monkeypatch.setattr("netstrip.core.self_update.platform_token",
                        lambda platform=None: "Windows")
    monkeypatch.setattr("netstrip.core.self_update.urllib.request.urlopen", fake_urlopen)
    return payloads


# ---------------------------------------------------------------------------
# Pure helpers


def test_parse_sha256sums_standard_and_bsd_variants():
    text = (
        "# comment line\n"
        f"{GOOD_HASH}  {ZIP_NAME}\n"
        f"{'b' * 64} *binary-mode.zip\r\n"
        "not-a-hash short.txt\n"
        "garbage-line-without-spaces\n"
    )
    out = parse_sha256sums(text)
    assert out[ZIP_NAME] == GOOD_HASH
    assert out["binary-mode.zip"] == "b" * 64
    assert "short.txt" not in out


def test_parse_sha256sums_windows_escaped_spaces():
    out = parse_sha256sums(f"{GOOD_HASH}  my\\ file.zip")
    assert out["my file.zip"] == GOOD_HASH


def test_verify_file_hash(tmp_path):
    p = tmp_path / ZIP_NAME
    p.write_bytes(ZIP_BYTES)
    assert verify_file_hash(p, GOOD_HASH) is True
    assert verify_file_hash(p, "0" * 64) is False


def test_sha256_of_file_streams(tmp_path):
    import hashlib as _h
    p = tmp_path / "big.bin"
    p.write_bytes(b"x" * 3_000_000)
    assert sha256_of_file(p) == _h.sha256(b"x" * 3_000_000).hexdigest()


# ---------------------------------------------------------------------------
# Asset selection


def test_pick_assets_prefers_installer_over_legacy_zip():
    assets = [
        _asset("NetStrip-v9.9.9-Linux.zip"),
        _asset(SETUP_NAME),
        _asset(LEGACY_ZIP_NAME.capitalize()),
        _asset("SHA256SUMS.txt"),
    ]
    z, s = pick_assets(assets, platform="win32")
    assert z["name"] == SETUP_NAME            # installer wins
    assert s["name"] == "SHA256SUMS.txt"


def test_pick_assets_legacy_zip_fallback():
    assets = [
        _asset(LEGACY_ZIP_NAME.capitalize()),
        _asset("SHA256SUMS.txt"),
    ]
    z, _s = pick_assets(assets, platform="win32")
    assert z["name"].lower() == LEGACY_ZIP_NAME


def test_pick_assets_missing_sums_detected():
    z, s = pick_assets([_asset(SETUP_NAME)], platform="win32")
    assert z is not None and s is None  # caller must refuse to update


# ---------------------------------------------------------------------------
# Full verified-download flow (network mocked)


def test_download_verified_happy_path(tmp_path, monkeypatch):
    fake_transport(monkeypatch)
    dest = tmp_path / "updates"

    got = SelfUpdater().download_verified(dest)

    assert got.exists()
    assert got.name == SETUP_NAME
    assert got.read_bytes() == ZIP_BYTES
    assert verify_file_hash(got, GOOD_HASH)


def test_download_aborts_on_hash_mismatch(tmp_path, monkeypatch):
    fake_transport(monkeypatch, zip_bytes=b"TAMPERED")
    dest = tmp_path / "updates"

    with pytest.raises(SelfUpdateError, match="SHA-256 mismatch"):
        SelfUpdater().download_verified(dest)

    # The tampered file must be deleted, never left for the user to run
    assert not (dest / SETUP_NAME).exists()


def test_download_refuses_when_manifest_missing_entry(tmp_path, monkeypatch):
    bogus_sums = f"{'c'*64}  some-other-file.zip\n"
    fake_transport(monkeypatch, sums_text=bogus_sums)
    dest = tmp_path / "updates"

    with pytest.raises(SelfUpdateError, match="absent from"):
        SelfUpdater().download_verified(dest)


def test_download_refuses_when_no_platform_asset(tmp_path, monkeypatch):
    release = {"tag_name": "v9.9.9", "assets": [_asset("SHA256SUMS.txt", 10)]}
    payloads = {API_URL: json.dumps(release).encode()}
    monkeypatch.setattr(
        "netstrip.core.self_update.urllib.request.urlopen",
        lambda req, timeout=None, context=None: FakeResp(payloads[req.full_url]),
    )
    with pytest.raises(SelfUpdateError, match="no update zip"):
        SelfUpdater().download_verified(tmp_path)
