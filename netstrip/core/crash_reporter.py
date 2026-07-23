"""
NetStrip Crash Reporter

Sends crash reports and watchdog-gathered diagnostic information via email
to the developer when the application encounters an unrecoverable error.
This runs independently of the analytics opt-in — crash reports are only
sent when a genuine crash occurs, and they contain system/diagnostic info
(never user traffic, domains, or IPs).

Target: cripple@frenzypenguin.media
"""

import logging
import platform
import time
import traceback
import json
import os
import sys
import threading
from pathlib import Path
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

CRASH_EMAIL = "cripple@frenzypenguin.media"
CRASH_REPORT_DIR = Path.home() / ".netstrip" / "crash_reports"

# GitHub Issues API for crash reports (public repo)
GITHUB_CRASH_ENDPOINT = "https://api.github.com/repos/neohiro/Cripple-NetStrip/issues"


def _get_system_info() -> dict:
    """Collect non-identifying system diagnostic information."""
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "timestamp_local": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    try:
        import psutil
        mem = psutil.virtual_memory()
        info["ram_total_gb"] = round(mem.total / (1024**3), 1)
        info["ram_used_pct"] = mem.percent
        info["cpu_count"] = psutil.cpu_count()
        info["cpu_pct"] = psutil.cpu_percent(interval=0.5)
    except Exception:
        pass
    
    try:
        from netstrip import __version__
        info["netstrip_version"] = __version__
    except Exception:
        info["netstrip_version"] = "unknown"
    
    return info


def _get_engine_state() -> dict:
    """Attempt to capture engine state from the database (read-only, no PII)."""
    state = {}
    try:
        import sqlite3
        db_path = Path.home() / ".netstrip" / "netstrip.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path), timeout=2)
            c = conn.cursor()
            
            # Get current mode
            c.execute("SELECT value FROM settings WHERE key='mode'")
            row = c.fetchone()
            state["mode"] = row[0] if row else "unknown"
            
            # Get 24h stats (aggregate counts only, no domains/IPs)
            c.execute("SELECT SUM(total_blocked), SUM(total_allowed) FROM statistics WHERE date >= date('now', '-1 day')")
            row = c.fetchone()
            if row:
                state["blocked_24h"] = row[0] or 0
                state["allowed_24h"] = row[1] or 0
            
            # Get number of user rules
            c.execute("SELECT COUNT(*) FROM user_rules")
            row = c.fetchone()
            state["rule_count"] = row[0] if row else 0
            
            # Check key settings
            for key in ("smart_paranoid_mode", "autostart", "run_as_service", "linux_ebpf_mode"):
                c.execute("SELECT value FROM settings WHERE key=?", (key,))
                row = c.fetchone()
                state[f"setting_{key}"] = row[0] if row else "unset"
            
            conn.close()
    except Exception as e:
        state["db_error"] = str(e)
    
    return state


def _save_crash_report_locally(report: str, crash_id: str) -> Optional[Path]:
    """Save crash report to local disk as a fallback."""
    try:
        CRASH_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        filepath = CRASH_REPORT_DIR / f"crash_{crash_id}.txt"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"Crash report saved locally: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to save crash report locally: {e}")
        return None


def _send_email(subject: str, body: str) -> bool:
    """
    Send crash report via email using SMTP.
    Attempts multiple free SMTP relay strategies:
    1. Direct MX delivery to the recipient's mail server
    """
    try:
        import smtplib
        import dns.resolver  # type: ignore
        
        # Resolve MX record for frenzypenguin.media
        mx_records = dns.resolver.resolve("frenzypenguin.media", "MX")
        mx_host = str(sorted(mx_records, key=lambda r: r.preference)[0].exchange).rstrip(".")
        
        msg = MIMEMultipart()
        msg["From"] = "crashreporter@netstrip.local"
        msg["To"] = CRASH_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        with smtplib.SMTP(mx_host, 25, timeout=15) as smtp:
            smtp.ehlo("netstrip.local")
            smtp.sendmail("crashreporter@netstrip.local", CRASH_EMAIL, msg.as_string())
        
        logger.info("Crash report sent via direct MX delivery")
        return True
    except ImportError:
        logger.debug("dnspython not available, skipping MX delivery")
    except Exception as e:
        logger.debug(f"MX delivery failed: {e}")
    
    # Fallback: Try using localhost SMTP (if a local MTA is running)
    try:
        import smtplib
        msg = MIMEMultipart()
        msg["From"] = "crashreporter@netstrip.local"
        msg["To"] = CRASH_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        with smtplib.SMTP("localhost", 25, timeout=5) as smtp:
            smtp.sendmail("crashreporter@netstrip.local", CRASH_EMAIL, msg.as_string())
        
        logger.info("Crash report sent via local MTA")
        return True
    except Exception as e:
        logger.debug(f"Local MTA delivery failed: {e}")
    
    return False


def _send_via_https(subject: str, body: str) -> bool:
    """
    Send crash report via HTTPS POST to a crash collection endpoint.
    Falls back to creating a GitHub issue if the primary endpoint fails.
    """
    try:
        import urllib.request
        import ssl
        
        payload = json.dumps({
            "title": subject,
            "body": f"```\n{body}\n```",
            "labels": ["crash-report", "automated"]
        }).encode("utf-8")
        
        # Primary: NetStrip crash endpoint
        try:
            req = urllib.request.Request(
                "https://crash.netstrip.io/v1/report",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                if resp.status == 200:
                    logger.info("Crash report sent via HTTPS endpoint")
                    return True
        except Exception:
            pass
        
        return False
    except Exception as e:
        logger.debug(f"HTTPS crash report failed: {e}")
        return False


def send_crash_report(
    exception: Optional[BaseException] = None,
    tb_string: Optional[str] = None,
    context: str = "runtime",
    extra_info: Optional[dict] = None,
):
    """
    Build and send a comprehensive crash report.
    
    Args:
        exception: The exception that caused the crash (if available)
        tb_string: Pre-formatted traceback string (if exception not available)
        context: Where the crash occurred ("runtime", "watchdog", "gui", "engine")
        extra_info: Additional diagnostic key-value pairs
    """
    crash_id = f"{int(time.time())}_{os.getpid()}"
    
    # Build the traceback
    if exception:
        tb = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
    elif tb_string:
        tb = tb_string
    else:
        tb = traceback.format_exc()
    
    # Collect system info
    sys_info = _get_system_info()
    engine_state = _get_engine_state()
    
    # Build the report
    lines = [
        "=" * 70,
        f"  NETSTRIP CRASH REPORT — {crash_id}",
        "=" * 70,
        "",
        f"Context:   {context}",
        f"Version:   {sys_info.get('netstrip_version', 'unknown')}",
        f"Timestamp: {sys_info.get('timestamp', 'unknown')}",
        f"Local:     {sys_info.get('timestamp_local', 'unknown')}",
        "",
        "--- SYSTEM INFO ---",
        f"OS:        {sys_info.get('os', '?')} {sys_info.get('os_release', '')} ({sys_info.get('os_version', '')})",
        f"Arch:      {sys_info.get('arch', '?')}",
        f"Python:    {sys_info.get('python', '?')}",
        f"CPUs:      {sys_info.get('cpu_count', '?')}",
        f"RAM:       {sys_info.get('ram_total_gb', '?')} GB ({sys_info.get('ram_used_pct', '?')}% used)",
        f"CPU Load:  {sys_info.get('cpu_pct', '?')}%",
        "",
        "--- ENGINE STATE ---",
        f"Mode:      {engine_state.get('mode', 'unknown')}",
        f"Blocked:   {engine_state.get('blocked_24h', '?')} (24h)",
        f"Allowed:   {engine_state.get('allowed_24h', '?')} (24h)",
        f"Rules:     {engine_state.get('rule_count', '?')}",
    ]
    
    # Add settings state
    for key in ("smart_paranoid_mode", "autostart", "run_as_service", "linux_ebpf_mode"):
        val = engine_state.get(f"setting_{key}", "unset")
        lines.append(f"  {key}: {val}")
    
    if engine_state.get("db_error"):
        lines.append(f"  DB Error: {engine_state['db_error']}")
    
    # Add extra info
    if extra_info:
        lines.append("")
        lines.append("--- EXTRA CONTEXT ---")
        for k, v in extra_info.items():
            lines.append(f"  {k}: {v}")
    
    # Add traceback
    lines.extend([
        "",
        "--- TRACEBACK ---",
        tb,
        "=" * 70,
    ])
    
    report = "\n".join(lines)
    
    # Subject line for email
    exc_type = type(exception).__name__ if exception else "CrashReport"
    subject = f"[NetStrip Crash] {exc_type} in {context} — v{sys_info.get('netstrip_version', '?')} on {sys_info.get('os', '?')}"
    
    # Always save locally first
    _save_crash_report_locally(report, crash_id)
    
    # Attempt to send via available channels (non-blocking)
    def _send():
        sent = False
        
        # Try HTTPS endpoint first
        if _send_via_https(subject, report):
            sent = True
        
        # Try email delivery
        if _send_email(subject, report):
            sent = True
        
        if sent:
            logger.info(f"Crash report {crash_id} delivered successfully")
        else:
            logger.warning(f"Crash report {crash_id} saved locally only (delivery failed)")
    
    # Send in background to avoid blocking shutdown
    try:
        t = threading.Thread(target=_send, daemon=True)
        t.start()
        # Give it a few seconds to send before the process potentially exits
        t.join(timeout=10)
    except Exception:
        pass


def install_global_exception_hook():
    """
    Install a global unhandled exception hook that automatically
    sends crash reports for any uncaught exceptions.
    """
    original_hook = sys.excepthook
    
    def crash_hook(exc_type, exc_value, exc_tb):
        # Don't report KeyboardInterrupt or SystemExit
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            original_hook(exc_type, exc_value, exc_tb)
            return
        
        logger.critical(f"Unhandled exception: {exc_type.__name__}: {exc_value}")
        
        try:
            send_crash_report(
                exception=exc_value,
                context="unhandled_exception",
            )
        except Exception:
            pass
        
        # Call the original hook
        original_hook(exc_type, exc_value, exc_tb)
    
    sys.excepthook = crash_hook
    logger.info("Global crash reporter hook installed")
