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
        # Privacy Hardening: Abort public IP checks entirely in Ghost or Streamer Privacy mode
        is_privacy = False
        if self.engine:
            if getattr(self.engine, 'db', None) and str(self.engine.db.get_setting("privacy_stream_mode", "false")).lower() == "true":
                is_privacy = True
            elif getattr(self.engine, 'classifier', None) and getattr(self.engine.classifier, 'mode', None) and self.engine.classifier.mode.name == "GHOST":
                is_privacy = True
                
        if is_privacy:
            self.current_data = {
                'ip': 'PRIVACY MODE',
                'city': 'Hidden',
                'country': 'Hidden',
                'countryCode': 'XX',
                'flag': '🌐'
            }
            for cb in self.callbacks:
                try: cb('PRIVACY MODE', self.current_data)
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

        # Randomize provider pool for redundancy and privacy (don't always hit same domain)
        providers = [
            {'url': 'https://ipapi.co/json/', 'type': 'ipapi'},
            {'url': 'https://ipinfo.io/json', 'type': 'ipinfo'},
            {'url': 'https://ipwho.is/', 'type': 'ipwho'},
            {'url': 'http://ip-api.com/json/', 'type': 'ip-api'}
        ]
        import random
        random.shuffle(providers)
        
        for prov in providers:
            d = try_provider(prov['url'])
            if d and (d.get('ip') or d.get('query')):
                cc = d.get('country_code') or d.get('countryCode') or d.get('country', 'XX')
                ip_str = d.get('ip') or d.get('query')
                if not ip_str: continue
                self.current_data = {
                    'ip': ip_str,
                    'city': d.get('city', 'Unknown'),
                    'country': d.get('country_name') or d.get('country', 'Unknown'),
                    'countryCode': cc,
                    'flag': self.get_flag_emoji(cc)
                }
                for cb in self.callbacks:
                    try: cb(old_ip, self.current_data)
                    except Exception: pass
                return True

        # Fallback to ipify for IP-only
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
    def get_instance(cls, engine=None):
        if cls._instance is None:
            cls._instance = cls(engine)
        return cls._instance
        
    def __init__(self, engine=None):
        self.engine = engine
        self.db_path = Path(__file__).parent.parent / 'data' / 'GeoLite2-City.mmdb'
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
            # Check privacy modes before downloading
            if self.engine:
                mode = getattr(getattr(self.engine, 'classifier', None), 'mode', None)
                if mode and mode.name == "GHOST":
                    logger.info("GeoLite2 download blocked by Ghost Mode. Retrying later.")
                    return
                if hasattr(self.engine, 'db') and self.engine.db.get_setting("privacy_stream_mode", "false") == "true":
                    logger.info("GeoLite2 download blocked by Streamer Privacy Mode. Retrying later.")
                    return
                    
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info("Downloading GeoLite2-Country.mmdb for offline GeoIP...")
            url = "https://raw.githubusercontent.com/P3TERX/GeoLite.mmdb/download/GeoLite2-City.mmdb"
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
        
    def get_city(self, ip_str: str) -> str:
        if not self.is_ready or not self.reader or not ip_str:
            return ""
        try:
            res = self.reader.get(ip_str)
            if res and 'city' in res and 'names' in res['city'] and 'en' in res['city']['names']:
                return res['city']['names']['en']
        except Exception:
            pass
        return ""
        
    def get_flag(self, ip_str: str) -> str:
        code = self.get_country(ip_str)
        if not code or len(code) != 2:
            return ""
        return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)
        
    def get_full_location(self, ip_str: str) -> str:
        flag = self.get_flag(ip_str)
        city = self.get_city(ip_str)
        
        parts = []
        if flag: parts.append(flag)
        if city: parts.append(city)
        elif not city: 
            # Fallback to country name if city is unknown
            country = self.get_country(ip_str)
            if country: parts.append(country)
            
        return " ".join(parts) if parts else "" 
