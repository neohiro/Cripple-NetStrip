import logging
import subprocess
import threading
import time
from typing import Callable
from netstrip.core.interceptor.base import PacketInterceptor

logger = logging.getLogger("NetStrip.MacOSPF")

class MacOSPFInterceptor(PacketInterceptor):
    """
    MacOS Packet Filter (pf) interceptor.
    Since inline user-space queuing (like NFQueue/WinDivert) is not natively available on macOS 
    without Network Extensions, this falls back to dynamically managing a pf anchor blocklist.
    """
    def __init__(self, callback: Callable[[str, int, str, int, str], bool], engine=None):
        super().__init__(callback)
        self.engine = engine
        self._blocked_ips = set()
        self._anchor_file = "/etc/pf.anchors/com.netstrip.block"
        self._sync_thread = None

    def start(self):
        if self.is_running:
            return
            
        try:
            # Create anchor file
            subprocess.run(["sudo", "touch", self._anchor_file], check=True, capture_output=True)
            # Ensure pf is enabled
            subprocess.run(["sudo", "pfctl", "-E"], capture_output=True)
            logger.info("MacOS PF packet interception started (Anchor mode).")
        except Exception as e:
            logger.error(f"Failed to initialize macOS pfctl: {e}")
            return

        self.is_running = True
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()

    def block_ip(self, ip: str):
        if ip not in self._blocked_ips:
            self._blocked_ips.add(ip)
            self._update_pf_rules()

    def _sync_loop(self):
        # Periodically flush expired IPs if we were to implement TTLs
        while self.is_running:
            time.sleep(10)

    def _update_pf_rules(self):
        if not self._blocked_ips:
            rules = ""
        else:
            rules = "\n".join([f"block drop out proto tcp to {ip}" for ip in self._blocked_ips]) + "\n"
            
        try:
            # Write rules to anchor
            echo = subprocess.Popen(['echo', rules], stdout=subprocess.PIPE)
            subprocess.run(["sudo", "tee", self._anchor_file], stdin=echo.stdout, capture_output=True)
            echo.stdout.close()
            
            # Load anchor
            subprocess.run(["sudo", "pfctl", "-a", "com.netstrip.block", "-f", self._anchor_file], capture_output=True)
        except Exception as e:
            logger.error(f"Failed to update pf rules: {e}")

    def stop(self):
        if not self.is_running:
            return
            
        self.is_running = False
        try:
            # Clear anchor
            echo = subprocess.Popen(['echo', ''], stdout=subprocess.PIPE)
            subprocess.run(["sudo", "tee", self._anchor_file], stdin=echo.stdout, capture_output=True)
            echo.stdout.close()
            subprocess.run(["sudo", "pfctl", "-a", "com.netstrip.block", "-f", self._anchor_file], capture_output=True)
        except Exception as e:
            logger.error(f"Failed to clear pf rules: {e}")
            
        logger.info("MacOS PF packet interception stopped.")
