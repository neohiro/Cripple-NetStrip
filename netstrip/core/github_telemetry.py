"""
GitHub Telemetry Delivery for NetStrip

Sends analytics, error, and crash reports to the private
neohiro/Cripple-Telemetry repository as GitHub Issues,
categorized by label.

The token is read from (in priority order):
  1. Environment variable NETSTRIP_TELEMETRY_TOKEN
  2. Database setting 'telemetry_github_token'
  3. Hardcoded fallback (set during build)

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
from typing import Optional

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
TELEMETRY_REPO = "neohiro/Cripple-Telemetry"
ISSUES_ENDPOINT = f"{GITHUB_API_BASE}/repos/{TELEMETRY_REPO}/issues"


def _get_token() -> Optional[str]:
    """
    Retrieve the GitHub PAT for telemetry submission.
    Checks environment variable first, then database, then fallback.
    """
    # 1. Environment variable (highest priority)
    token = os.environ.get("NETSTRIP_TELEMETRY_TOKEN")
    if token:
        return token

    # 2. Database setting
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

    # 3. No token available
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

    title = f"[Analytics] v{payload.get('version', '?')} — {payload.get('os', '?')} — {payload.get('id', '?')[:8]}"

    lines = [
        "## NetStrip Analytics Report",
        "",
        f"**Installation ID:** `{payload.get('id', '?')}`",
        f"**Version:** {payload.get('version', '?')}",
        f"**OS:** {payload.get('os', '?')} ({payload.get('arch', '?')})",
        f"**Python:** {payload.get('python', '?')}",
        f"**Mode:** {payload.get('mode', '?')}",
        f"**Uptime:** {payload.get('uptime_hours', 0)} hours",
        f"**Headless:** {payload.get('headless', False)}",
        "",
        "### 24h Statistics",
        f"- Blocked: {payload.get('blocked_24h', 0)}",
        f"- Allowed: {payload.get('allowed_24h', 0)}",
        f"- User rules: {payload.get('rule_count', 0)}",
        f"- Blocklist domains: {payload.get('blocklist_domains', 0)}",
        "",
        "### Raw Payload",
        "```json",
        json.dumps(payload, indent=2),
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
