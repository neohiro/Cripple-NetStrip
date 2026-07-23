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

    def _neutralize_adapter(self, adapter_name: str):
        """Forcefully disable a rogue virtual network adapter at the OS level."""
        try:
            if os.name == 'nt':
                subprocess.run(["netsh", "interface", "set", "interface", adapter_name, "admin=disable"], creationflags=subprocess.CREATE_NO_WINDOW)
                logger.warning(f"Force disabled rogue VPN adapter: {adapter_name}")
            elif os.uname().sysname == 'Linux':
                subprocess.run(["ip", "link", "set", "dev", adapter_name, "down"])
                logger.warning(f"Force disabled rogue VPN adapter: {adapter_name}")
            elif os.uname().sysname == 'Darwin':
                subprocess.run(["ifconfig", adapter_name, "down"])
        except Exception as e:
            logger.debug(f"Failed to neutralize adapter {adapter_name}: {e}")

    def _neutralize_pcap(self):
        """Forcefully stop Pcap kernel drivers and raw socket handles."""
        try:
            if os.name == 'nt':
                subprocess.run(["sc", "stop", "npcap"], creationflags=subprocess.CREATE_NO_WINDOW)
                subprocess.run(["sc", "stop", "npf"], creationflags=subprocess.CREATE_NO_WINDOW)
                logger.warning("Force stopped Npcap/WinPcap kernel services.")
        except Exception as e:
            logger.debug(f"Failed to neutralize pcap: {e}")

    def _check_vpn_and_pcap(self) -> list:
        anomalies = []
        if os.name == 'nt': # Windows
            try:
                res = subprocess.run(["sc", "query", "npcap"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if "RUNNING" in res.stdout:
                    anomalies.append("Npcap Packet Sniffer/Injector Driver is ACTIVE.")
                    self._neutralize_pcap()
                    
                res = subprocess.run(["sc", "query", "npf"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if "RUNNING" in res.stdout:
                    anomalies.append("WinPcap Driver is ACTIVE.")
                    self._neutralize_pcap()
            except: pass
            
        elif os.uname().sysname == 'Linux':
            try:
                with open("/proc/net/packet", "r") as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        anomalies.append(f"Raw AF_PACKET sockets detected ({len(lines)-1} open). Dropping via eBPF.")
            except: pass
            
        return anomalies

    def _scan_loop(self):
        while self.is_running:
            if self.engine and self.engine.db.get_setting("kernel_anomaly_scanner", "true") == "true":
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
                                is_vpn = any(v in adp.lower() for v in ["tap", "tun", "wireguard", "wg", "vpn", "tailscale", "zerotier"])
                                
                                msg = f"New network adapter detected: {adp}"
                                if is_vpn:
                                    msg = f"Rogue VPN / Virtual Adapter detected: {adp}. Successfully neutralized."
                                    self._neutralize_adapter(adp)
                                
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
                                'message': f"Anomaly Neutralized: {sa}",
                            })
                            
                except Exception as e:
                    logger.debug(f"Anomaly scanner error: {e}")
                    
            self._stop_event.wait(15)
