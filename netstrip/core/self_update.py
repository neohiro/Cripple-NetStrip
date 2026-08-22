"""
Verified self-update for NetStrip.

Flow (Settings → Updates → "Download & Verify Update"):
  1. GET https://api.github.com/repos/neohiro/Cripple-NetStrip/releases/latest
  2. Pick this platform's zip asset + the published SHA256SUMS.txt manifest
  3. Stream both into the destination directory
  4. Recompute SHA-256 of the zip and compare against the manifest entry
     (case-insensitive). Any mismatch aborts before the file is ever executed.

Trust anchor: the manifest is fetched over TLS from the same release object.
An optional ed25519 detached signature is honored when the environment variable
NETSTRIP_UPDATE_PUBKEY (base64, 32-byte key) and a `<asset>.sig` are present —
enabling out-of-band signing later without another format change.
"""

import base64
import hashlib
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

REPO_API_LATEST = "https://api.github.com/repos/neohiro/Cripple-NetStrip/releases/latest"
USER_AGENT = "NetStrip-SelfUpdate/1.0"


class SelfUpdateError(Exception):
    """Raised when an update cannot be retrieved or fails verification."""


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested)


def parse_sha256sums(text: str) -> Dict[str, str]:
    """Parse `sha256sum` output into {lowercased_filename: lowercase_hex}.

    Tolerates: leading '# ' comments, CRLF, extra whitespace, BSD-style
    '<hash> *<name>' binary markers. Malformed lines are ignored.
    """
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        digest, name = parts[0].strip(), parts[1].strip()
        digest = digest.lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            continue
        if name.startswith("*"):       # BSD binary-mode marker
            name = name[1:]
        name = name.lstrip("*").strip()
        if "\\" in name and "/" not in name:
            # Windows sha256sum may escape spaces as '\ '; unescape common case
            name = name.replace("\\ ", " ")
        result[name.lower()] = digest
    return result


def sha256_of_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def verify_file_hash(path: Path, expected_hex: str) -> bool:
    actual = sha256_of_file(path)
    ok = actual.lower() == expected_hex.strip().lower()
    if not ok:
        logger.error(f"hash mismatch for {path.name}: got {actual} want {expected_hex}")
    return ok


def platform_token(platform: str = None) -> str:
    platform = platform or sys.platform
    if platform.startswith("win"):
        return "Windows"
    if platform == "darwin":
        return "macOS"
    return "Linux"


def pick_assets(assets, platform: str = None):
    """Return (zip_asset, sums_asset) from a release-assets JSON list.

    Matching is prefix-based on our published naming scheme
    (NetStrip-vX.Y.Z-<Platform>.zip) so version bumps never break selection.
    """
    want = platform_token(platform)
    zip_asset = sums_asset = None
    for a in assets or []:
        name = (a.get("name") or "").lower()
        if name.endswith("sha256sums.txt"):
            sums_asset = a
        elif name.startswith("netstrip-") and name.endswith(".zip") and want.lower() in name:
            zip_asset = a
    return zip_asset, sums_asset


def _tls_context():
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()  # fail closed: still verified TLS


def http_download(url: str, dest: Path, progress: Optional[Callable[[int, int], None]] = None):
    """Stream url→dest over verified TLS. Returns dest."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = _tls_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx if url.startswith("https") else None) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        with open(dest, "wb") as f:
            while True:
                block = resp.read(1024 * 256)
                if not block:
                    break
                f.write(block)
                done += len(block)
                if progress and total:
                    try:
                        progress(done, total)
                    except Exception:
                        pass
    return dest


# ---------------------------------------------------------------------------
# Orchestration


class SelfUpdater:
    def __init__(self, engine=None, repo_api: str = REPO_API_LATEST):
        self.engine = engine
        self.repo_api = repo_api

    def latest_release(self) -> dict:
        req = urllib.request.Request(self.repo_api, headers={"User-Agent": USER_AGENT})
        ctx = _tls_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def download_verified(self, dest_dir: Path, tag_hint: str = "",
                          progress: Optional[Callable[[str, int, int], None]] = None) -> Path:
        """
        Download this platform's update zip and its SHA256SUMS manifest,
        then verify. Returns the verified zip path.

        Raises SelfUpdateError on: missing assets, network failure, or — most
        importantly — ANY hash mismatch. The verified file is never left in
        place when verification fails.
        """
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        def prog(stage, done=0, total=0):
            if progress:
                try:
                    progress(stage, done, total)
                except Exception:
                    pass

        release = self.latest_release()
        zip_a, sums_a = pick_assets(release.get("assets"))
        if not zip_a:
            raise SelfUpdateError(f"no update zip for {platform_token()} in latest release")
        if not sums_a:
            raise SelfUpdateError("release is missing SHA256SUMS.txt — refusing to update")

        zip_path = dest_dir / zip_a["name"]
        sums_path = dest_dir / sums_a["name"]

        prog("manifest")
        http_download(sums_a["browser_download_url"], sums_path)
        expected = parse_sha256sums(sums_path.read_text(encoding="utf-8", errors="ignore")).get(
            zip_a["name"].lower()
        )
        if not expected:
            raise SelfUpdateError(f"{zip_a['name']} absent from SHA256SUMS.txt")

        prog("download", 0, int(zip_a.get("size") or 0))
        http_download(zip_a["browser_download_url"], zip_path,
                      progress=lambda d, t: prog("download", d, t))

        if not verify_file_hash(zip_path, expected):
            try:
                zip_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise SelfUpdateError(
                "SHA-256 mismatch — the downloaded update does not match the "
                "published manifest and was deleted."
            )

        self._verify_optional_signature(zip_path)

        logger.info(f"Self-update verified: {zip_path}")
        prog("done")
        return zip_path

    def _verify_optional_signature(self, path: Path):
        """ed25519 detached signature check when both pubkey env and .sig exist."""
        pub_b64 = os.environ.get("NETSTRIP_UPDATE_PUBKEY")
        sig_path = path.with_name(path.name + ".sig")
        if not pub_b64 or not sig_path.exists():
            return
        try:
            from cryptography.hazmat.primitives.asymmetric import ed25519
            pub = ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(pub_b64))
            pub.verify(sig_path.read_bytes(), path.read_bytes())
            logger.info("update signature OK (ed25519)")
        except Exception as e:
            raise SelfUpdateError(f"signature verification failed: {e}") from e


def launch_installer_or_explorer(verified_zip: Path):
    """Best-effort handoff to the user after a verified download."""
    target = verified_zip.parent
    try:
        if sys.platform.startswith("win"):
            os.startfile(target)  # noqa: S606 - opens Explorer at the verified file
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            import subprocess
            subprocess.Popen([opener, str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logger.debug(f"could not open {target}: {e}")
