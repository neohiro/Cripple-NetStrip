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

    def add_callback(self, cb: Callable):
        if cb and cb not in self.callbacks:
            self.callbacks.append(cb)
            # Notify newly registered callback immediately if data is already fetched
            if self.current_data.get('ip') != 'Loading...':
                try:
                    cb(self.current_data.get('ip'), self.current_data)
                except Exception:
                    pass

    def fetch_now(self) -> bool:
        """Fetch immediately and return True if successful."""
        if self.engine and getattr(self.engine, 'classifier', None) and getattr(self.engine.classifier, 'mode', None) and self.engine.classifier.mode.name == "PARANOID":
            self.current_data = {
                'ip': 'PARANOID MODE',
                'city': 'Blocked (No Update)',
                'country': 'Blocked',
                'countryCode': 'XX',
                'flag': '🛡️'
            }
            for cb in self.callbacks:
                try: cb('PARANOID MODE', self.current_data)
                except Exception: pass
            return True
            
        old_ip = self.current_data.get('ip')
        
        # Provider 1: ipinfo.io (HTTPS)
        try:
            req = urllib.request.Request('https://ipinfo.io/json', headers={'User-Agent': 'Mozilla/5.0 NetStrip/1.0'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('ip'):
                    ip = data.get('ip')
                    city = data.get('city', 'Unknown')
                    country = data.get('country', 'XX')
                    self.current_data = {
                        'ip': ip,
                        'city': city,
                        'country': country,
                        'countryCode': country,
                        'flag': self.get_flag_emoji(country)
                    }
                    for cb in self.callbacks:
                        try: cb(old_ip, self.current_data)
                        except Exception: pass
                    return True
        except Exception as e:
            logger.debug(f"GeoIP ipinfo.io failed: {e}")

        # Provider 2: ip-api.com (HTTP)
        try:
            req = urllib.request.Request('http://ip-api.com/json/', headers={'User-Agent': 'Mozilla/5.0 NetStrip/1.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('status') == 'success':
                    ip = data.get('query', 'Unknown')
                    city = data.get('city', 'Unknown')
                    country = data.get('country', 'Unknown')
                    cc = data.get('countryCode', 'XX')
                    self.current_data = {
                        'ip': ip,
                        'city': city,
                        'country': country,
                        'countryCode': cc,
                        'flag': self.get_flag_emoji(cc)
                    }
                    for cb in self.callbacks:
                        try: cb(old_ip, self.current_data)
                        except Exception: pass
                    return True
        except Exception as e:
            logger.debug(f"GeoIP ip-api.com failed: {e}")

        # Provider 3: api.ipify.org fallback for IP-only
        try:
            req = urllib.request.Request('https://api.ipify.org', headers={'User-Agent': 'Mozilla/5.0 NetStrip/1.0'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                fast_ip = resp.read().decode('utf-8').strip()
                if fast_ip:
                    self.current_data['ip'] = fast_ip
                    for cb in self.callbacks:
                        try: cb(old_ip, self.current_data)
                        except Exception: pass
                    return True
        except Exception as e:
            logger.debug(f"GeoIP ipify fallback failed: {e}")

        return False

    def _poll_loop(self):
        # Fetch immediately on boot
        self.fetch_now()
        
        while self.is_running:
            # Poll every 30 seconds (Event-driven changes are handled instantly by WindowsMicroMonitor)
            self._stop_event.wait(30) 
            if self.is_running:
                self.fetch_now()
