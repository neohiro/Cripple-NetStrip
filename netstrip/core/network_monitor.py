"""
Network Monitor for NetStrip
Polls low-level network state (ARP table for Default Gateway, active interface) 
to detect potential network intrusion/spoofing (Man-in-the-Middle).
"""

import subprocess
import platform
import logging
import threading
import time
import re
from typing import Callable, Optional, Dict
from netstrip.platform.base import get_platform

logger = logging.getLogger(__name__)

class NetworkMonitor:
    def __init__(self, callback: Callable = None, engine=None):
        self.callback = callback
        self.engine = engine
        self.platform = get_platform()
        self.is_running = False
        self.thread = None
        self._stop_event = __import__('threading').Event()
        
        self.current_state: Dict = {
            'gateway_ip': None,
            'gateway_mac': None,
        }

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.info("Network Intrusion Monitor started")

    def stop(self):
        self.is_running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info("Network Intrusion Monitor stopped")

    def _get_arp_mac(self, ip: str) -> Optional[str]:
        try:
            res = subprocess.run(["arp", "-a"], capture_output=True, text=True)
            # Find the line containing the IP and a MAC address
            # e.g., 192.168.1.1       00-11-22-33-44-55     dynamic
            for line in res.stdout.splitlines():
                if ip in line:
                    match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', line)
                    if match:
                        return match.group(0).lower().replace('-', ':')
        except Exception as e:
            logger.debug(f"Failed to fetch ARP table: {e}")
        return None

    def check_state(self):
        gw_ip = self.platform.get_default_gateway()
        if not gw_ip:
            return
            
        gw_mac = self._get_arp_mac(gw_ip)
        if not gw_mac:
            return

        # Initialize state if first run
        if not self.current_state['gateway_ip']:
            self.current_state['gateway_ip'] = gw_ip
            self.current_state['gateway_mac'] = gw_mac
            return

        # Check for changes
        if self.current_state['gateway_ip'] == gw_ip and self.current_state['gateway_mac'] != gw_mac:
            # ARP Spoofing detected! Gateway IP is the same, but the MAC address changed suddenly.
            if self.callback:
                self.callback({
                    'type': 'arp_spoof',
                    'message': f"Default Gateway MAC address changed unexpectedly from {self.current_state['gateway_mac']} to {gw_mac}. Potential ARP Spoofing/MITM attack detected.",
                    'old_mac': self.current_state['gateway_mac'],
                    'new_mac': gw_mac
                })
            self.current_state['gateway_mac'] = gw_mac

        elif self.current_state['gateway_ip'] != gw_ip:
            # Network changed (e.g. connected to new Wi-Fi)
            if self.callback:
                self.callback({
                    'type': 'network_change',
                    'message': f"Network changed. Default Gateway IP changed from {self.current_state['gateway_ip']} to {gw_ip}.",
                    'old_ip': self.current_state['gateway_ip'],
                    'new_ip': gw_ip
                })
            self.current_state['gateway_ip'] = gw_ip
            self.current_state['gateway_mac'] = gw_mac


    def _poll_loop(self):
        import psutil
        last_io = psutil.net_io_counters()
        
        while self.is_running:
            self.check_state()
            
            # Log bandwidth delta
            try:
                current_io = psutil.net_io_counters()
                if self.engine and hasattr(self.engine, 'db'):
                    delta_sent = max(0, current_io.bytes_sent - last_io.bytes_sent)
                    delta_recv = max(0, current_io.bytes_recv - last_io.bytes_recv)
                    if delta_sent > 0 or delta_recv > 0:
                        self.engine.db.log_bandwidth(delta_sent, delta_recv)
                last_io = current_io
            except Exception as e:
                logger.debug(f"Failed to log bandwidth: {e}")
                
            self._stop_event.wait(10) # Poll every 10 seconds
