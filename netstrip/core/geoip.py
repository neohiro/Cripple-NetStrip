"""
GeoIP Module for NetStrip
Fetches and caches the public IP and geolocation data.
"""

import urllib.request
import json
import logging
import threading
import time
from typing import Dict, Callable, Optional

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
        
        import ssl
        try:
            import certifi
            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

        # Helper to try a provider URL
        def try_provider(url: str, is_json: bool = True, timeout: float = 3.0) -> Optional[Dict]:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NetStrip/1.0'})
                with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx if url.startswith('https') else None) as resp:
                    raw = resp.read().decode('utf-8')
                    if is_json:
                        return json.loads(raw)
                    return {'ip': raw.strip()}
            except Exception as ex:
                logger.debug(f"GeoIP fetch failed for {url}: {ex}")
                return None

        # Provider 1: ipapi.co (HTTPS, highly reliable)
        d1 = try_provider('https://ipapi.co/json/')
        if d1 and d1.get('ip'):
            cc = d1.get('country_code', 'XX')
            self.current_data = {
                'ip': d1.get('ip'),
                'city': d1.get('city', 'Unknown'),
                'country': d1.get('country_name', 'Unknown'),
                'countryCode': cc,
                'flag': self.get_flag_emoji(cc)
            }
            for cb in self.callbacks:
                try: cb(old_ip, self.current_data)
                except Exception: pass
            return True

        # Provider 2: ipinfo.io (HTTPS)
        d2 = try_provider('https://ipinfo.io/json')
        if d2 and d2.get('ip'):
            cc = d2.get('country', 'XX')
            self.current_data = {
                'ip': d2.get('ip'),
                'city': d2.get('city', 'Unknown'),
                'country': cc,
                'countryCode': cc,
                'flag': self.get_flag_emoji(cc)
            }
            for cb in self.callbacks:
                try: cb(old_ip, self.current_data)
                except Exception: pass
            return True

        # Provider 3: ipwho.is (HTTPS)
        d3 = try_provider('https://ipwho.is/')
        if d3 and d3.get('success') and d3.get('ip'):
            cc = d3.get('country_code', 'XX')
            self.current_data = {
                'ip': d3.get('ip'),
                'city': d3.get('city', 'Unknown'),
                'country': d3.get('country', 'Unknown'),
                'countryCode': cc,
                'flag': self.get_flag_emoji(cc)
            }
            for cb in self.callbacks:
                try: cb(old_ip, self.current_data)
                except Exception: pass
            return True

        # Provider 4: ip-api.com (HTTP / HTTPS)
        d4 = try_provider('http://ip-api.com/json/')
        if d4 and d4.get('status') == 'success':
            cc = d4.get('countryCode', 'XX')
            self.current_data = {
                'ip': d4.get('query', 'Unknown'),
                'city': d4.get('city', 'Unknown'),
                'country': d4.get('country', 'Unknown'),
                'countryCode': cc,
                'flag': self.get_flag_emoji(cc)
            }
            for cb in self.callbacks:
                try: cb(old_ip, self.current_data)
                except Exception: pass
            return True

        # Provider 5: api.ipify.org fallback for IP-only
        d5 = try_provider('https://api.ipify.org', is_json=False)
        if d5 and d5.get('ip'):
            self.current_data['ip'] = d5.get('ip')
            for cb in self.callbacks:
                try: cb(old_ip, self.current_data)
                except Exception: pass
            return True

        return False

    def _poll_loop(self):
        # Fetch immediately on boot
        self.fetch_now()
        
        while self.is_running:
            # Poll every 30 seconds (Event-driven changes are handled instantly by WindowsMicroMonitor)
            self._stop_event.wait(30) 
            if self.is_running:
                self.fetch_now()


import os
import maxminddb
from pathlib import Path

class OfflineGeoIP:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    def __init__(self):
        self.db_path = Path(__file__).parent.parent / 'data' / 'GeoLite2-Country.mmdb'
        self.reader = None
        self.is_ready = False
        self._download_thread = None
        self._init_db()
        
    def _init_db(self):
        if self.db_path.exists():
            try:
                self.reader = maxminddb.open_database(str(self.db_path))
                self.is_ready = True
            except Exception as e:
                logger.error(f"Failed to open GeoLite2 DB: {e}")
                self._start_download()
        else:
            self._start_download()
            
    def _start_download(self):
        if self._download_thread and self._download_thread.is_alive():
            return
        self._download_thread = threading.Thread(target=self._download_db, daemon=True)
        self._download_thread.start()
        
    def _download_db(self):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info("Downloading GeoLite2-Country.mmdb for offline GeoIP...")
            url = "https://raw.githubusercontent.com/P3TERX/GeoLite.mmdb/download/GeoLite2-Country.mmdb"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(self.db_path, 'wb') as f:
                    f.write(resp.read())
            self.reader = maxminddb.open_database(str(self.db_path))
            self.is_ready = True
            logger.info("Offline GeoIP database downloaded and loaded.")
        except Exception as e:
            logger.error(f"Failed to download GeoIP database: {e}")
            
    def get_country(self, ip_str: str) -> str:
        if not self.is_ready or not self.reader or not ip_str:
            return ""
        try:
            res = self.reader.get(ip_str)
            if res and 'country' in res and 'iso_code' in res['country']:
                return res['country']['iso_code']
        except Exception:
            pass
        return ""
        
    def get_flag(self, ip_str: str) -> str:
        code = self.get_country(ip_str)
        if not code or len(code) != 2:
            return ""
        return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)
