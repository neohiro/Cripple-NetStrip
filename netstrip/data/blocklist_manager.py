"""
Blocklist Manager for NetStrip
Manages the offline domain blocklists using high-performance Python sets and dictionary caching.
"""

import os
import threading
import json
import hashlib
import logging
from typing import Tuple, Optional, Dict, Set, List, Any
from netstrip.core.modes import ConnectionCategory

logger = logging.getLogger(__name__)

CATEGORY_PRIORITY = {
    ConnectionCategory.MALWARE: 100,
    ConnectionCategory.TELEMETRY: 80,
    ConnectionCategory.TRACKER: 60,
    ConnectionCategory.AD: 40,
    ConnectionCategory.SECURITY: 20,
    ConnectionCategory.SYSTEM: 20,
    ConnectionCategory.UPDATE: 10,
    ConnectionCategory.UNKNOWN: 0
}

class BlocklistManager:
    def __init__(self, lists_dir: str = None, db=None):
        self.db = db
        self.domain_map = {}
        self.identity_map = {}
        self.whitelist = set()
        self.app_whitelist = set()
        self.app_blacklist = set()
        self.blacklist = {}
        self.lock = threading.RLock()
        self.stats = {cat: 0 for cat in ConnectionCategory}

        self.sources_metadata = {}
        
        if lists_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            lists_dir = os.path.join(base_dir, 'lists')
        self.lists_dir = lists_dir
        self.is_loading = True
        threading.Thread(target=self._load_async_worker, daemon=True).start()

    def _get_lists_hash(self):
        """Generate a hash of the current lists directory to detect changes."""
        h = hashlib.md5()
        if not os.path.exists(self.lists_dir):
            return h.hexdigest()
        for filename in sorted(os.listdir(self.lists_dir)):
            if not filename.endswith('.txt'): continue
            filepath = os.path.join(self.lists_dir, filename)
            h.update(filename.encode('utf-8'))
            h.update(str(os.path.getmtime(filepath)).encode('utf-8'))
        return h.hexdigest()

    def _load_async_worker(self):
        """Worker thread to load blocklists without freezing the UI."""
        try:
            self.load_all()
        except Exception as e:
            logger.error(f"Failed to load blocklists: {e}")
        finally:
            self.is_loading = False

    def load_all(self):
        """Load all default blocklists, using JSON cache if available."""
        cache_file = os.path.join(self.lists_dir, "NetStrip_cache.json")
        current_hash = self._get_lists_hash()
        
        # Remove old pickle cache if it exists (one-time migration)
        old_pkl = os.path.join(self.lists_dir, "NetStrip_cache.pkl")
        if os.path.exists(old_pkl):
            try:
                os.remove(old_pkl)
            except Exception:
                pass
        
        if os.path.exists(cache_file):
            try:
                import time
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                if cache_data.get("hash") == current_hash:
                    # Chunk reconstruction to prevent GIL lock
                    items = list(cache_data["domain_map"].items())
                    new_domain_map = {}
                    chunk_size = 25000
                    for i in range(0, len(items), chunk_size):
                        chunk = items[i:i + chunk_size]
                        for k, v in chunk:
                            new_domain_map[k] = ConnectionCategory(v)
                        time.sleep(0.005) # Yield GIL
                        
                    with self.lock:
                        self.domain_map = new_domain_map
                        self.identity_map = cache_data["identity_map"]
                        self.stats = {
                            ConnectionCategory(k): v for k, v in cache_data["stats"].items()
                        }
                        self.sources_metadata = {
                            ConnectionCategory(k): v for k, v in cache_data["sources_metadata"].items()
                        }
                    return
            except Exception as e:
                logger.debug(f"Cache load failed, rebuilding: {e}")
                
        with self.lock:
            self.domain_map.clear()
            self.identity_map.clear()
            self.stats = {cat: 0 for cat in ConnectionCategory}
            self.sources_metadata.clear()
            
            if os.path.exists(self.lists_dir):
                for filename in os.listdir(self.lists_dir):
                    if not filename.endswith('.txt'): continue
                    filepath = os.path.join(self.lists_dir, filename)
                    
                    if filename.startswith('ads_') or filename == 'ads.txt':
                        self._load_list(filepath, ConnectionCategory.AD)
                    elif filename.startswith('telemetry_') or filename == 'telemetry.txt':
                        self._load_list(filepath, ConnectionCategory.TELEMETRY)
                    elif filename.startswith('malware_') or filename == 'malware.txt':
                        self._load_list(filepath, ConnectionCategory.MALWARE)
                    elif filename.startswith('tracker') or filename == 'trackers.txt':
                        self._load_list(filepath, ConnectionCategory.TRACKER)
                    elif filename.startswith('doh_providers'):
                        block_doh = True
                        if self.db:
                            allow_doh = str(self.db.get_setting("allow_in_browser_dns", "false")).lower() == "true"
                            block_doh = not allow_doh
                        if block_doh:
                            self._load_list(filepath, ConnectionCategory.TRACKER)
                    elif filename.startswith('security_'):
                        self._load_list(filepath, ConnectionCategory.SECURITY)
                    elif filename.startswith('update_'):
                        self._load_list(filepath, ConnectionCategory.UPDATE)
                    elif filename.startswith('safe_') or filename.startswith('essential_'):
                        self._load_list(filepath, ConnectionCategory.ESSENTIAL)
                    elif filename.startswith('whitelist_'):
                        self._load_list(filepath, ConnectionCategory.USER_ALLOWED)
                    elif filename.startswith('user_blocked_') or filename.startswith('blocked_'):
                        self._load_list(filepath, ConnectionCategory.USER_BLOCKED)
                    elif filename.startswith('system_'):
                        import platform
                        sys_name = platform.system().lower()
                        fname = filename.lower()
                        
                        is_native_os = False
                        if "windows" in fname or "winoffice" in fname or "spyblocker" in fname:
                            if sys_name == "windows": is_native_os = True
                        elif "apple" in fname or "macos" in fname or "darwin" in fname:
                            if sys_name == "darwin": is_native_os = True
                        elif "linux" in fname or "ubuntu" in fname:
                            if sys_name == "linux": is_native_os = True
                        else:
                            is_native_os = True
                            
                        if is_native_os:
                            # Native OS background noise
                            self._load_list(filepath, ConnectionCategory.SYSTEM)
                        else:
                            # Non-native (e.g., Apple software on Windows), treat as standard App Telemetry
                            self._load_list(filepath, ConnectionCategory.TELEMETRY)
                    elif filename.startswith('identity_'):
                        parts = filename.split('_')
                        identity_name = parts[1].title() if len(parts) > 1 else 'Unknown'
                        self._load_list(filepath, None, identity_name=identity_name)
                        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "hash": current_hash,
                    "domain_map": {k: v.value for k, v in self.domain_map.items()},
                    "identity_map": self.identity_map,
                    "stats": {k.value: v for k, v in self.stats.items()},
                    "sources_metadata": {k.value: v for k, v in self.sources_metadata.items()}
                }, f)
        except Exception:
            pass

    def _load_list(self, filepath: str, category: Optional[ConnectionCategory], identity_name: str = None):
        """Parse a hosts or domain list file and add it to the map."""
        if not os.path.exists(filepath):
            return
            
        import time
        import datetime
        
        filename = os.path.basename(filepath)
        mod_time = os.path.getmtime(filepath)
        dt = datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
        
        if category:
            if category not in self.sources_metadata:
                self.sources_metadata[category] = []
            self.sources_metadata[category].append({
                'filename': filename,
                'updated': dt,
                'size': 0
            })
            
        domains = set()
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('include:'):
                    continue
                if '@' in line:
                    line = line.split('@')[0]
                if line.startswith('full:'):
                    line = line[5:]
                    
                parts = line.split()
                if not parts:
                    continue
                    
                if len(parts) >= 2 and parts[0] in ('0.0.0.0', '127.0.0.1'):
                    domain = parts[1]
                else:
                    domain = parts[0]
                
                if domain.startswith('domain:'):
                    domain = domain[7:]
                    
                if domain.startswith('||'):
                    domain = domain[2:]
                if domain.endswith('^'):
                    domain = domain[:-1]
                if domain.startswith('*.'):
                    domain = domain[2:]
                if domain.startswith('^'):
                    domain = domain[1:]
                    
                if '/' in domain or '*' in domain or '=' in domain or domain.startswith('!'):
                    continue
                
                if domain != '0.0.0.0' and domain != 'localhost' and '.' in domain:
                    domains.add(domain)
                    
        if category and self.sources_metadata.get(category):
            self.sources_metadata[category][-1]['size'] = len(domains)
            
        self.add_domains(domains, category, identity_name)

    def add_domains(self, domains: Set[str], category: Optional[ConnectionCategory], identity_name: str = None):
        """Thread-safe method to add multiple domains in chunks to avoid blocking the GIL and UI."""
        import time
        domains_list = list(domains)
        chunk_size = 5000
        
        for i in range(0, len(domains_list), chunk_size):
            chunk = domains_list[i:i + chunk_size]
            with self.lock:
                for domain in chunk:
                    d = domain.lower()
                    if category:
                        if d not in self.domain_map:
                            self.domain_map[d] = category
                            self.stats[category] = self.stats.get(category, 0) + 1
                        else:
                            existing_cat = self.domain_map[d]
                            # If the new category is higher priority, overwrite it
                            if CATEGORY_PRIORITY.get(category, 0) > CATEGORY_PRIORITY.get(existing_cat, 0):
                                self.domain_map[d] = category
                                self.stats[existing_cat] -= 1
                                self.stats[category] = self.stats.get(category, 0) + 1
                                
                    if identity_name:
                        self.identity_map[d] = identity_name
            
            # Yield GIL and processor time to ensure GUI (Tkinter mainloop) stays 60fps
            time.sleep(0.001)

    def remove_domains(self, domains: Set[str]):
        pass

    def is_blocked(self, domain: str, process_name: str = None) -> Tuple[bool, Optional[ConnectionCategory]]:
        """
        Check if a domain is blocked. Checks whitelist, blacklist, and Maps.
        Subdomain matching: if tracker.com is blocked, sub.tracker.com is also blocked.
        """
        if not domain:
            return False, ConnectionCategory.UNKNOWN
            
        domain = domain.lower()
        if domain.endswith('.'):
            domain = domain[:-1]

        with self.lock:
            # 1. User overrides (Highest Priority)
            if process_name and process_name in self.app_whitelist:
                return False, ConnectionCategory.USER_ALLOWED
            if process_name and process_name in self.app_blacklist:
                return True, ConnectionCategory.USER_BLOCKED
                
            if domain in self.whitelist:
                return False, ConnectionCategory.USER_ALLOWED
            if domain in self.blacklist:
                return True, ConnectionCategory.USER_BLOCKED

            # 2. Blocklist Trie (Standard Priority)

            parts = domain.split('.')
            for i in range(len(parts)):
                test_domain = '.'.join(parts[i:])
                if test_domain in self.domain_map:
                    return True, self.domain_map[test_domain]
                    
            return False, ConnectionCategory.UNKNOWN

    def get_identity(self, domain: str) -> Optional[str]:
        """Check the identity map to find the corporate owner of the domain."""
        if not domain:
            return None
        domain = domain.lower()
        if domain.endswith('.'):
            domain = domain[:-1]
            
        with self.lock:
            parts = domain.split('.')
            for i in range(len(parts)):
                test_domain = '.'.join(parts[i:])
                if test_domain in self.identity_map:
                    return self.identity_map[test_domain]
            return None

    def sync_user_rules(self, rules: List[Any]):
        with self.lock:
            self.whitelist.clear()
            self.app_whitelist.clear()
            self.app_blacklist.clear()
            self.blacklist.clear()
            for rule in rules:
                pattern = rule['pattern'].lower()
                action = rule['action']
                scope = rule['scope']
                app_name = rule['app_name']
                
                if scope == 'app' and app_name:
                    if action == 'allow':
                        self.app_whitelist.add(app_name)
                    elif action == 'block':
                        self.app_blacklist.add(app_name)
                else:
                    if action == 'allow':
                        self.whitelist.add(pattern)
                    elif action == 'block':
                        self.blacklist[pattern] = True

    def add_user_whitelist(self, domain: str):
        with self.lock:
            self.whitelist.add(domain.lower())

    def add_user_blacklist(self, domain: str):
        with self.lock:
            self.blacklist[domain.lower()] = True

    def get_stats(self) -> Dict[ConnectionCategory, int]:
        with self.lock:
            return dict(self.stats)

    def search(self, query: str = "", limit: int = 50, category_filter=None) -> List[dict]:
        """Search domains using partial match, returns up to `limit` results."""
        if not query and not category_filter:
            return []
            
        query = query.lower() if query else ""
        results = []
        with self.lock:
            # First add dynamic user rules if they match
            if not category_filter or category_filter == ConnectionCategory.USER_ALLOWED.value:
                for domain in self.whitelist:
                    if not query or query in domain:
                        results.append({'domain': domain, 'category': ConnectionCategory.USER_ALLOWED.value})
                        if len(results) >= limit: break
            
            if not category_filter or category_filter == 'user_blocked':
                for domain in self.blacklist:
                    if not query or query in domain:
                        results.append({'domain': domain, 'category': 'user_blocked'})
                        if len(results) >= limit: break

            if not category_filter or category_filter == 'essential':
                essential_dns = (
                    '127.0.0.1', '127.0.0.53', '::1',
                    '1.1.1.1', '1.0.0.1', 'cloudflare-dns.com', 'one.one.one.one',
                    '1.1.1.2', '1.0.0.2', 'security.cloudflare-dns.com',
                    '1.1.1.3', '1.0.0.3', 'family.cloudflare-dns.com',
                    '8.8.8.8', '8.8.4.4', 'dns.google',
                    '9.9.9.9', '149.112.112.112', 'dns.quad9.net',
                    '9.9.9.11', '149.112.112.11', 'dns11.quad9.net',
                    '94.140.14.14', '94.140.15.15', 'dns.adguard-dns.com',
                    '76.76.2.0', '76.76.10.0', 'freedns.controld.com',
                    '208.67.222.222', '208.67.220.220', 'dns.opendns.com',
                    '45.90.28.0', '45.90.30.0', 'dns.nextdns.io',
                    '194.242.2.2', '193.19.108.2', 'dns.mullvad.net',
                    '185.228.168.9', '185.228.169.9', 'security-filter-dns.cleanbrowsing.org',
                    'ip-api.com', 'ipify.org'
                )
                for d in essential_dns:
                    if not query or query in d:
                        results.append({'domain': d, 'category': 'essential'})
                        if len(results) >= limit: break

            if not category_filter or category_filter == 'system':
                for d in ('microsoft.com', 'windowsupdate.com', 'msftconnecttest.com', 'apple.com', 'ubuntu.com', 'debian.org'):
                    if not query or query in d:
                        results.append({'domain': d, 'category': 'system'})
                        if len(results) >= limit: break

            if len(results) >= limit:
                return results
                
            # Iterate domain_map directly instead of a duplicate searchable_domains list
            for domain, category in self.domain_map.items():
                if category_filter and category.value != category_filter:
                    continue
                if not query or query in domain:
                    results.append({
                        'domain': domain,
                        'category': category.value
                    })
                    if len(results) >= limit:
                        break
        return results
