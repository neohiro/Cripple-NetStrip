"""
GitHub Telemetry Delivery for NetStrip

Sends analytics, error, and crash reports to the private
neohiro/Cripple-Telemetry repository as GitHub Issues,
categorized by label.

The token is read from (in priority order):
  1. Environment variable NETSTRIP_TELEMETRY_TOKEN
  2. Database setting 'telemetry_github_token'
  3. Encrypted fallback (enabled via NETSTRIP_TELEMETRY_ENCRYPTED_FALLBACK=true)

Each report becomes a GitHub Issue with the appropriate label:
  - 'analytics' for opt-in usage stats
  - 'error' for non-fatal exceptions
  - 'crash' for unhandled crashes / watchdog events
"""

import json
import logging
import os
import urllib.request
import ssl
import base64
from typing import Optional

# Encrypted fallback token (AES-GCM encrypted with machine-derived key)
# To generate: use scripts/generate_telemetry_token.py during build
# Only used if NETSTRIP_TELEMETRY_ENCRYPTED_FALLBACK=true
ENCRYPTED_TELEMETRY_FALLBACK = (
    "gAAAAABl...(truncated-for-security)...placeholder"
)

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
TELEMETRY_REPO = "neohiro/Cripple-Telemetry"
ISSUES_ENDPOINT = f"{GITHUB_API_BASE}/repos/{TELEMETRY_REPO}/issues"


def _decrypt_telemetry_token(encrypted_token: str) -> Optional[str]:
    """Decrypt the telemetry fallback token using AES-GCM with machine-derived key.

    Only returns a result if NETSTRIP_TELEMETRY_ENCRYPTED_FALLBACK=true is set.
    The key is derived from machine hardware characteristics for bind-security.
    """
    if os.environ.get("NETSTRIP_TELEMETRY_ENCRYPTED_FALLBACK", "").lower() != "true":
        return None

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        import socket

        # Derive key from machine-specific data
        machine_id = socket.gethostname().encode() + socket.gethostbyname(socket.gethostname()).encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=machine_id,
            iterations=100000,
        )
        key = kdf.derive(b"NetStrip-Telemetry-Fallback")

        # Decode and decrypt
        data = base64.b64decode(encrypted_token)
        nonce = data[:12]
        ciphertext = data[12:]
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        logger.debug(f"Failed to decrypt telemetry fallback token: {e}")
        return None


def _get_token() -> Optional[str]:
    """
    Retrieve the GitHub PAT for telemetry submission.
    Checks environment variable first, then token file, then database,
    then encrypted fallback (opt-in) last.
    """
    # 1. Environment variable (highest priority)
    token = os.environ.get("NETSTRIP_TELEMETRY_TOKEN")
    if token:
        return token

    # 2. Token file (~/.netstrip/telemetry_token)
    try:
        from pathlib import Path
        token_file = Path.home() / ".netstrip" / "telemetry_token"
        if token_file.exists():
            token = token_file.read_text(encoding="utf-8").strip()
            if token:
                return token
    except Exception:
        pass

    # 3. Database setting
    try:
        from netstrip.data.database import Database
        from pathlib import Path
        db_path = Path.home() / ".netstrip" / "netstrip.db"
        if db_path.exists():
            db = Database(str(db_path))
            token = db.get_setting("telemetry_github_token", "")
            db.stop()
            if token:
                return token
    except Exception:
        pass

    # 4. Encrypted fallback (opt-in via NETSTRIP_TELEMETRY_ENCRYPTED_FALLBACK=true)
    if os.environ.get("NETSTRIP_TELEMETRY_ENCRYPTED_FALLBACK", "").lower() == "true":
        try:
            encrypted_token = base64.b64decode(
                ENCRYPTED_TELEMETRY_FALLBACK
            ).decode("utf-8")
            token = _decrypt_telemetry_token(encrypted_token)
            if token:
                return token
        except Exception as e:
            logger.debug(f"Encrypted telemetry fallback failed: {e}")

    # 5. No token available
    return None



def submit_issue(title: str, body: str, label: str) -> bool:
    """
    Create a GitHub Issue on the Cripple-Telemetry repo.

    Args:
        title: Issue title (e.g., "[Crash] TypeError")
        body:  Issue body (full report text, will be wrapped in a code block)
        label: One of 'analytics', 'error', 'crash'

    Returns:
        True if the issue was created successfully, False otherwise.
    """
    import platform
    import sys
    
    token = _get_token()
    if not token:
        logger.debug("No telemetry token configured, skipping GitHub delivery")
        return False
        
    os_name = "windows"
    if hasattr(sys, 'getandroidapilevel') or os.environ.get('NETSTRIP_ANDROID') == '1':
        os_name = "android"
    else:
        os_name = platform.system().lower()
        
    os_label = f"os-{os_name}"
    os_title_prefix = f"[{os_name.capitalize()}] "
    
    if not title.startswith(os_title_prefix):
        title = f"{os_title_prefix}{title}"

    try:
        payload = json.dumps({
            "title": title,
            "body": body,
            "labels": [label, os_label],
        }).encode("utf-8")

        req = urllib.request.Request(
            ISSUES_ENDPOINT,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "NetStrip-Telemetry/1.0",
            },
            method="POST",
        )

        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            if resp.status == 201:
                logger.debug(f"Telemetry issue created on GitHub ({label}, {os_label})")
                return True
            else:
                logger.debug(f"GitHub API returned status {resp.status}")
                return False

    except Exception as e:
        logger.debug(f"GitHub telemetry delivery failed: {e}")
        return False


def submit_analytics(payload: dict) -> bool:
    """Submit an analytics report as a GitHub Issue."""
    from netstrip import __version__

    safe_payload = dict(payload)
    safe_payload.pop('id', None)

    title = f"[Analytics] v{safe_payload.get('version', '?')} — {safe_payload.get('os', '?')}"

    lines = [
        "## NetStrip Analytics Report",
        "",
        f"**Version:** {safe_payload.get('version', '?')}",
        f"**OS:** {safe_payload.get('os', '?')} ({safe_payload.get('arch', '?')})",
        f"**Python:** {safe_payload.get('python', '?')}",
        f"**Mode:** {safe_payload.get('mode', '?')}",
        f"**Uptime:** {safe_payload.get('uptime_hours', 0)} hours",
        f"**Headless:** {safe_payload.get('headless', False)}",
        "",
        "### 24h Statistics",
        f"- Blocked: {safe_payload.get('blocked_24h', 0)}",
        f"- Allowed: {safe_payload.get('allowed_24h', 0)}",
        f"- User rules: {safe_payload.get('rule_count', 0)}",
        f"- Blocklist domains: {safe_payload.get('blocklist_domains', 0)}",
        "",
        "### Raw Payload",
        "```json",
        json.dumps(safe_payload, indent=2),
        "```",
    ]

    return submit_issue(title, "\n".join(lines), "analytics")


def submit_crash(subject: str, report: str) -> bool:
    """Submit a crash report as a GitHub Issue."""
    body = f"## Crash Report\n\n```\n{report}\n```"
    return submit_issue(subject, body, "crash")


def submit_error(subject: str, report: str) -> bool:
    """Submit a non-fatal error report as a GitHub Issue."""
    body = f"## Error Report\n\n```\n{report}\n```"
    return submit_issue(subject, body, "error")
