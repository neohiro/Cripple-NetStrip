"""
GeoIP Module for NetStrip
Fetches and caches the public IP and geolocation data.
"""

import urllib.request
import json
import logging
import threading
import time
from typing import Dict, Callable

logger = logging.getLogger(__name__)

class GeoIPService:
    def __init__(self, callback: Callable = None, engine=None):
        self.callbacks = [callback] if callback else []
        self.engine = engine
        self.current_data: Dict = {
            'ip': 'Loading...',
            'city': 'Pending',
            'country': 'Pending',
            'countryCode': 'XX',
            'flag': '🌐'
        }
        self.is_running = False
        self.thread = None
        self._stop_event = __import__('threading').Event()

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.info("GeoIP Service started")

    def stop(self):
        self.is_running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info("GeoIP Service stopped")

    def get_flag_emoji(self, country_code: str) -> str:
        if not country_code or len(country_code) != 2:
            return '🌐'
        return chr(ord(country_code[0]) + 127397) + chr(ord(country_code[1]) + 127397)

    def fetch_now(self) -> bool:
        """Fetch immediately and return True if successful."""
        if self.engine and self.engine.classifier.mode.name == "PARANOID":
            self.current_data = {
                'ip': 'PARANOID MODE',
                'city': 'Blocked (No Update)',
                'country': 'Blocked',
                'countryCode': 'XX',
                'flag': '🛡️'
            }
            if self.callbacks:
                for cb in self.callbacks:
                    cb('PARANOID MODE', self.current_data)
            return True
            
        try:
            # 1. Fast check to get just the IP immediately
            old_ip = self.current_data.get('ip')
            fast_ip = None
            try:
                ip_req = urllib.request.Request('https://api.ipify.org', headers={'User-Agent': 'NetStrip/1.0'})
                with urllib.request.urlopen(ip_req, timeout=2) as response:
                    fast_ip = response.read().decode('utf-8').strip()
                    
                if fast_ip and fast_ip != old_ip:
                    self.current_data['ip'] = fast_ip
                    if old_ip != 'Loading...':
                        for cb in self.callbacks:
                            cb(old_ip, self.current_data)
            except Exception as e:
                logger.debug(f"Fast IP fetch failed: {e}")
                
            # If IP didn't change and we already have city data, don't waste rate limits on ip-api
            if fast_ip and fast_ip == old_ip and self.current_data.get('city') != 'Pending':
                return True
                
            # 2. Fetch full GeoIP data only on change or first boot
            req = urllib.request.Request(
                'http://ip-api.com/json/',
                headers={'User-Agent': 'NetStrip/1.0'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
            if data.get('status') == 'success':
                new_ip = data.get('query', self.current_data['ip'])
                
                self.current_data = {
                    'ip': new_ip,
                    'city': data.get('city', 'Unknown'),
                    'country': data.get('country', 'Unknown'),
                    'countryCode': data.get('countryCode', 'XX'),
                    'flag': self.get_flag_emoji(data.get('countryCode', 'XX'))
                }
                
                # If we just booted, update the UI with full GeoIP data (using a pseudo-old_ip to force UI update without triggering flux)
                if old_ip == 'Loading...':
                    for cb in self.callbacks:
                        cb('Loading...', self.current_data)
                
                return True
        except Exception as e:
            logger.debug(f"GeoIP fetch failed: {e}")
        return False

    def _poll_loop(self):
        # Fetch immediately on boot
        self.fetch_now()
        
        while self.is_running:
            # Poll every 30 seconds (Event-driven changes are handled instantly by WindowsMicroMonitor)
            self._stop_event.wait(30) 
            if self.is_running:
                self.fetch_now()
