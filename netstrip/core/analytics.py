"""
NetStrip Anonymous Analytics Module

Collects minimal, non-identifying usage statistics to help the developer
improve NetStrip. This module is OFF by default and requires explicit
opt-in by the user via Settings > Analytics.

What is collected (when enabled):
  - NetStrip version
  - OS type (Windows/Linux/macOS) and architecture
  - Active mode (Normal/Paranoid/Loose)
  - Aggregate counts: total blocked, total allowed (24h)
  - Number of active user rules
  - Number of custom blocklist sources
  - Uptime (hours)
  - Whether headless mode is active

What is NEVER collected:
  - IP addresses (local or public)
  - Domain names or DNS queries
  - Process names or file paths
  - Connection logs or traffic content
  - Any personally identifiable information
"""

import logging
import threading
import time
import platform
import uuid
import json
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netstrip.core.engine import CrippleEngine

logger = logging.getLogger(__name__)

# Analytics endpoint — receives anonymous JSON payloads via HTTPS POST
ANALYTICS_ENDPOINT = "https://analytics.netstrip.io/v1/report"

# How often to send analytics (in seconds) — once every 24 hours
REPORT_INTERVAL = 86400

# Database setting key — must always default to 'false'
SETTING_KEY = "analytics_opt_in"


class AnalyticsReporter:
    """
    Collects and periodically sends anonymous usage statistics.
    
    This reporter is strictly opt-in. It will NOT send any data unless
    the user has explicitly enabled the 'analytics_opt_in' setting.
    The setting defaults to 'false' in all code paths.
    """

    def __init__(self, engine: 'CrippleEngine'):
        self.engine = engine
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._installation_id: Optional[str] = None

    def start(self):
        """Start the background analytics thread. Only sends if opt-in is enabled."""
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="AnalyticsReporter")
        self._thread.start()
        logger.info("Analytics reporter initialized (will only send if user has opted in)")

    def stop(self):
        """Stop the analytics reporter."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def is_enabled(self) -> bool:
        """Check if the user has opted in to analytics. Always defaults to False."""
        try:
            val = self.engine.db.get_setting(SETTING_KEY, "false")
            return str(val).lower() == "true"
        except Exception:
            return False

    def _get_installation_id(self) -> str:
        """
        Get or create a random installation ID. This is a random UUID
        with no correlation to any hardware, user, or network identifier.
        It exists solely to deduplicate reports from the same installation.
        """
        if self._installation_id:
            return self._installation_id

        try:
            stored = self.engine.db.get_setting("analytics_installation_id", "")
            if stored:
                self._installation_id = stored
            else:
                self._installation_id = str(uuid.uuid4())
                self.engine.db.set_setting("analytics_installation_id", self._installation_id)
        except Exception:
            self._installation_id = str(uuid.uuid4())

        return self._installation_id

    def _collect_payload(self) -> dict:
        """
        Build the anonymous analytics payload. Contains only aggregate
        counts and system type info — never any identifying data.
        """
        from netstrip import __version__

        payload = {
            "id": self._get_installation_id(),
            "version": __version__,
            "os": platform.system(),
            "arch": platform.machine(),
            "python": platform.python_version(),
            "ts": int(time.time()),
        }

        try:
            payload["mode"] = self.engine.classifier.mode.name if hasattr(self.engine, 'classifier') else "unknown"
        except Exception:
            payload["mode"] = "unknown"

        try:
            stats = self.engine.db.get_24h_statistics()
            payload["blocked_24h"] = stats.get("total_blocked", 0)
            payload["allowed_24h"] = stats.get("total_allowed", 0)
        except Exception:
            payload["blocked_24h"] = 0
            payload["allowed_24h"] = 0

        try:
            rules = self.engine.db.get_user_rules()
            payload["rule_count"] = len(rules) if rules else 0
        except Exception:
            payload["rule_count"] = 0

        try:
            payload["blocklist_domains"] = self.engine.blocklist.total_count if hasattr(self.engine, 'blocklist') else 0
        except Exception:
            payload["blocklist_domains"] = 0

        try:
            payload["headless"] = self.engine.is_headless
        except Exception:
            payload["headless"] = False

        try:
            if hasattr(self.engine, '_start_time'):
                payload["uptime_hours"] = round((time.time() - self.engine._start_time) / 3600, 1)
            else:
                payload["uptime_hours"] = 0
        except Exception:
            payload["uptime_hours"] = 0

        return payload

    def _send_report(self, payload: dict) -> bool:
        """Send the analytics payload. Tries HTTPS endpoint first, then email fallback."""
        sent = False
        
        # Channel 1: HTTPS POST to analytics endpoint
        try:
            import urllib.request
            import ssl

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                ANALYTICS_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                if resp.status == 200:
                    sent = True
        except Exception as e:
            logger.debug(f"HTTPS analytics delivery failed (non-critical): {e}")
        
        # Channel 2: Email fallback to developer
        if not sent:
            try:
                from email.mime.text import MIMEText
                import smtplib

                body = "NetStrip Anonymous Analytics Report\n"
                body += "=" * 50 + "\n\n"
                for k, v in payload.items():
                    body += f"  {k}: {v}\n"
                body += "\n" + "=" * 50 + "\n"

                msg = MIMEText(body, "plain", "utf-8")
                msg["From"] = "analytics@netstrip.local"
                msg["To"] = "cripple@frenzypenguin.media"
                msg["Subject"] = f"[NetStrip Analytics] v{payload.get('version', '?')} on {payload.get('os', '?')} — {payload.get('id', '?')[:8]}"

                # Try direct MX delivery
                try:
                    import dns.resolver  # type: ignore
                    mx_records = dns.resolver.resolve("frenzypenguin.media", "MX")
                    mx_host = str(sorted(mx_records, key=lambda r: r.preference)[0].exchange).rstrip(".")
                    with smtplib.SMTP(mx_host, 25, timeout=15) as smtp:
                        smtp.ehlo("netstrip.local")
                        smtp.sendmail("analytics@netstrip.local", "cripple@frenzypenguin.media", msg.as_string())
                    sent = True
                    logger.debug("Analytics sent via MX email delivery")
                except Exception:
                    pass
                
                # Try local MTA
                if not sent:
                    try:
                        with smtplib.SMTP("localhost", 25, timeout=5) as smtp:
                            smtp.sendmail("analytics@netstrip.local", "cripple@frenzypenguin.media", msg.as_string())
                        sent = True
                        logger.debug("Analytics sent via local MTA")
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"Email analytics delivery failed (non-critical): {e}")
        
        return sent

    def _run_loop(self):
        """
        Background loop that checks opt-in status and sends reports.
        Runs every REPORT_INTERVAL seconds. If the user disables analytics
        mid-session, reporting stops immediately on the next cycle.
        """
        # Initial delay: wait 60 seconds after engine startup before first check
        self._stop_event.wait(60)

        while not self._stop_event.is_set():
            try:
                if self.is_enabled():
                    payload = self._collect_payload()
                    success = self._send_report(payload)
                    if success:
                        logger.debug("Analytics report sent successfully")
                    else:
                        logger.debug("Analytics report could not be delivered")
                else:
                    logger.debug("Analytics is disabled, skipping report")
            except Exception as e:
                logger.debug(f"Analytics loop error (non-critical): {e}")

            # Wait for the next interval, or until stopped
            self._stop_event.wait(REPORT_INTERVAL)
