import os
import time
import logging
import threading
import subprocess
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class AnomalyScanner:
    """
    Constantly checks for software or hardware that could bypass standard network filters,
    such as raw socket hooks (Npcap/WinPcap), active VPNs, and newly plugged-in network adapters.
    """
    def __init__(self, engine=None):
        self.engine = engine
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.callback: Optional[Callable[[dict], None]] = None
        
        self.known_adapters = set()
        self.first_run = True

    def set_callback(self, cb: Callable[[dict], None]):
        self.callback = cb

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._scan_loop, daemon=True, name="AnomalyScanner")
        self.thread.start()
        logger.info("Kernel Anomaly & Rogue Network Scanner started.")

    def stop(self):
        self.is_running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info("Anomaly Scanner stopped.")

    def _get_active_adapters(self) -> set:
        import psutil
        try:
            stats = psutil.net_if_stats()
            return set(iface for iface, stat in stats.items() if stat.isup)
        except Exception:
            return set()

    def _check_vpn_and_pcap(self) -> list:
        anomalies = []
        if os.name == 'nt': # Windows
            # Check for Npcap / WinPcap services running
            try:
                res = subprocess.run(["sc", "query", "npcap"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if "RUNNING" in res.stdout:
                    anomalies.append("Npcap Packet Sniffer/Injector Driver is ACTIVE.")
                    
                res = subprocess.run(["sc", "query", "npf"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if "RUNNING" in res.stdout:
                    anomalies.append("WinPcap Driver is ACTIVE.")
            except: pass
            
        elif os.uname().sysname == 'Linux':
            # Check for raw sockets
            try:
                with open("/proc/net/packet", "r") as f:
                    lines = f.readlines()
                    if len(lines) > 1: # Header + entries
                        anomalies.append(f"Raw AF_PACKET sockets detected ({len(lines)-1} open).")
            except: pass
            
        return anomalies

    def _scan_loop(self):
        while self.is_running:
            if self.engine and self.engine.db.get_setting("kernel_anomaly_scanner", "false") == "true":
                try:
                    # 1. Check Adapters
                    current_adapters = self._get_active_adapters()
                    if self.first_run:
                        self.known_adapters = current_adapters
                        self.first_run = False
                    else:
                        new_adapters = current_adapters - self.known_adapters
                        if new_adapters:
                            for adp in new_adapters:
                                # Flag suspicious virtual adapters
                                is_vpn = any(v in adp.lower() for v in ["tap", "tun", "wireguard", "wg", "vpn", "tailscale", "zerotier"])
                                
                                msg = f"New network adapter detected: {adp}"
                                if is_vpn:
                                    msg = f"Rogue VPN / Virtual Adapter detected: {adp}. This bypasses standard routing!"
                                
                                if self.callback:
                                    self.callback({
                                        'type': 'new_adapter',
                                        'message': msg,
                                        'adapter': adp,
                                        'is_vpn': is_vpn
                                    })
                            self.known_adapters = current_adapters
                            
                    # 2. Check for Pcap/Raw sockets
                    software_anomalies = self._check_vpn_and_pcap()
                    for sa in software_anomalies:
                        if self.callback:
                            self.callback({
                                'type': 'software_anomaly',
                                'message': f"Anomaly Detected: {sa} This software operates BELOW the firewall and can leak data.",
                            })
                            
                except Exception as e:
                    logger.debug(f"Anomaly scanner error: {e}")
                    
            self._stop_event.wait(15) # Scan every 15 seconds
