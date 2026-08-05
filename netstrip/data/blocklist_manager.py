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
    ConnectionCategory.USER_ALLOWED: 250,
    ConnectionCategory.USER_BLOCKED: 240,
    ConnectionCategory.ESSENTIAL: 200,
    ConnectionCategory.SYSTEM: 190,
    ConnectionCategory.UPDATE: 180,
    ConnectionCategory.MALWARE: 100,
    ConnectionCategory.TELEMETRY: 80,
    ConnectionCategory.TRACKER: 60,
    ConnectionCategory.AD: 40,
    ConnectionCategory.SECURITY: 20,
    ConnectionCategory.UNKNOWN: 0
}

# 1. ESSENTIAL DOMAINS — Minimal set required for local IPC and NetStrip itself (Immune to all blocks)
ESSENTIAL_DOMAINS = frozenset({
    # NetStrip Core Self-Updates & Releases
    'api.github.com',
    'raw.githubusercontent.com',
    'objects.githubusercontent.com',
    'github.com',
    'frenzypenguin.media',
    # GeoIP & Connectivity Diagnostic APIs
    'ip-api.com',
    'ipinfo.io',
    'ipify.org',
    'api.ipify.org',
    'ipapi.co',
    'ipwho.is',
    'api.myip.com',
    # NTP Time Synchronization
    'pool.ntp.org', 'time.windows.com', 'time.apple.com', 'time.google.com', 'time.cloudflare.com',
    # Network Captive Portal & Connectivity Checkers
    'captive.apple.com', 'connectivitycheck.gstatic.com', 'connectivitycheck.android.com',
    # Core Secure DNS Upstream Resolvers
    'dns.google', 'dns.quad9.net', 'cloudflare-dns.com',
    # Local Loopbacks
    '127.0.0.1', '127.0.0.53', '::1', 'localhost', 'broadcasthost',
})

# 2. SYSTEM DOMAINS — OS Infrastructure, Search Engines & Cloud Services (Categorized as ConnectionCategory.SYSTEM)
# Obeys "Block System Connections" toggle and Paranoid Mode!
SYSTEM_DOMAINS = frozenset({
    # Global Search & Core Web Portals
    'google.com', 'google.co.uk', 'google.de', 'google.fr', 'google.ca',
    'google.com.au', 'google.co.jp', 'google.es', 'google.it', 'google.nl',
    'google.pl', 'google.com.br', 'google.co.in',
    'bing.com', 'bingapis.com', 'msn.com', 'live.com', 'office.com', 'microsoftonline.com',
    'duckduckgo.com', 'yahoo.com', 'wikipedia.org', 'wikimedia.org',
    # Microsoft OS & Windows System Infrastructure
    'azure.com',
    'azure.net',
    'windows.net',
    'microsoft.com',
    'msftconnecttest.com',
    'msftncsi.com',
    'trafficmanager.net',
    'skype.com',
    'visualstudio.com',
    'windowsphone.com',
    'xboxlive.com',
    's-microsoft.com',
    'onedrive.live.com',
    # Apple Ecosystem (macOS & iOS System Infrastructure)
    'apple.com',
    'icloud.com',
    'apple-dns.net',
    'cdn-apple.com',
    'mzstatic.com',
    'push.apple.com',
    'aaplimg.com',
    # Android & Google Cloud Infrastructure
    'android.com',
    'ggpht.com',
    'googleapis.com',
    'gstatic.com',
    'googleusercontent.com',
    # Amazon Web Services (AWS) & CloudFront CDN
    'amazonaws.com',
    's3.amazonaws.com',
    'cloudfront.net',
    # Global Edge CDNs & Cloud Infrastructure
    'fastly.net',
    'fastlylb.net',
    'akamaiedge.net',
    'akamaihd.net',
    'edgekey.net',
    'akadns.net',
    'cloudflare.com',
    'cloudflare-dns.com',
    # Major Cloud Host Platforms
    'oraclecloud.com',
    'digitaloceanspaces.com',
    'hetzner.com',
    'linode.com',
    'vultr.com',
    # Gaming Cloud Backends
    'steampowered.com',
    'steamstatic.com',
})

# 3. UPDATE DOMAINS — OS Repositories & Package Managers (Categorized as ConnectionCategory.UPDATE)
# Obeys "Block Software Updates" toggle and Paranoid Mode!
UPDATE_DOMAINS = frozenset({
    # Linux Distributions & Package Managers
    'ubuntu.com',
    'canonical.com',
    'debian.org',
    'archlinux.org',
    'fedoraproject.org',
    'redhat.com',
    'opensuse.org',
    'flathub.org',
    # Developer Package Registries
    'pypi.org',
    'pythonhosted.org',
    'npmjs.org',
    'npmjs.com',
    'crates.io',
    'docker.com',
    'docker.io',
    'github-releases.githubusercontent.com',
    # Software Update CDNs
    'gvt1.com',
    'gvt2.com',
    'steamcontent.com',
    'windowsupdate.com',
    'update.microsoft.com',
})

class BlocklistManager:
    def __init__(self, lists_dir: str = None, db=None, **kwargs):
        if lists_dir is not None and not isinstance(lists_dir, (str, bytes, os.PathLike)):
            db = lists_dir
            lists_dir = None
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
        self.on_loaded_callbacks = []
        
        if lists_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            lists_dir = os.path.join(base_dir, 'lists')
        self.lists_dir = lists_dir
        self.is_loading = True
        threading.Thread(target=self._load_async_worker, daemon=True).start()

    def add_loaded_callback(self, callback: callable):
        """Register a callback to be called when blocklists finish reloading."""
        if callable(callback):
            self.on_loaded_callbacks.append(callback)

    def _notify_loaded(self):
        """Invoke all registered callbacks on reload completion."""
        for cb in list(self.on_loaded_callbacks):
            try:
                cb()
            except Exception as e:
                logger.debug(f"Error executing on_loaded_callback: {e}")

    def _get_cache_paths(self) -> List[str]:
        """Return potential cache file locations in priority order."""
        paths = []
        user_dir = os.path.join(os.path.expanduser("~"), ".NetStrip")
        paths.append(os.path.join(user_dir, "NetStrip_cache.json"))
        if self.lists_dir:
            paths.append(os.path.join(self.lists_dir, "NetStrip_cache.json"))
        return paths

    def _get_lists_hash(self):
        """Generate a stable deterministic hash of the current lists directory and DNS settings."""
        h = hashlib.md5()
        h.update(b"v3.3.5_dpi_splash_centering_hash")
        allow_doh = "false"
        if hasattr(self, 'db') and self.db:
            try:
                allow_doh = str(self.db.get_setting("allow_in_browser_dns", "false")).lower()
            except Exception:
                pass
        h.update(f"allow_doh:{allow_doh}".encode('utf-8'))
        if not os.path.exists(self.lists_dir):
            return h.hexdigest()
        for filename in sorted(os.listdir(self.lists_dir)):
            if not filename.endswith('.txt'): continue
            filepath = os.path.join(self.lists_dir, filename)
            try:
                size = os.path.getsize(filepath)
                h.update(f"{filename}:{size}".encode('utf-8'))
            except Exception:
                pass
        return h.hexdigest()

    def _load_async_worker(self):
        """Worker thread to load blocklists without freezing the UI."""
        try:
            self.load_all()
        except Exception as e:
            logger.error(f"Failed to load blocklists: {e}")
        finally:
            self.is_loading = False

    def _parse_domains_from_file(self, filepath: str) -> Set[str]:
        domains = set()
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789.-_")
        if not os.path.exists(filepath):
            return domains
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('!') or line.startswith('['):
                    continue
                if line.startswith('include:'):
                    continue
                if line.startswith('@@'):
                    continue
                if '@' in line:
                    line = line.split('@')[0].strip()
                if line.startswith('full:'):
                    line = line[5:].strip()
                    
                parts = line.split()
                if not parts:
                    continue
                    
                if len(parts) >= 2 and parts[0] in ('0.0.0.0', '127.0.0.1', '::1', '127.0.0.53'):
                    domain = parts[1]
                else:
                    domain = parts[0]
                
                if domain.startswith('domain:'):
                    domain = domain[7:]
                if domain.startswith('||'):
                    domain = domain[2:]
                    
                if '^' in domain:
                    domain = domain.split('^')[0]
                if '$' in domain:
                    domain = domain.split('$')[0]
                if '/' in domain:
                    domain = domain.split('/')[0]
                if '#' in domain:
                    domain = domain.split('#')[0]
                if domain.startswith('*.'):
                    domain = domain[2:]
                if domain.startswith('.'):
                    domain = domain[1:]
                    
                domain = domain.strip().lower()
                if not domain or '*' in domain or '=' in domain or domain.startswith('!') or domain.startswith('?'):
                    continue
                
                if domain not in ('0.0.0.0', '127.0.0.1', 'localhost', 'broadcasthost') and '.' in domain and len(domain) <= 253:
                    if set(domain).issubset(allowed):
                        domains.add(domain)
        return domains

    def load_all(self):
        """Load all default blocklists, using JSON cache if available."""
        self.is_loading = True
        try:
            current_hash = self._get_lists_hash()
            
            # 1. Try loading from existing cache files
            for cache_file in self._get_cache_paths():
                if os.path.exists(cache_file):
                    try:
                        import time
                        with open(cache_file, "r", encoding="utf-8") as f:
                            cache_data = json.load(f)
                        
                        if cache_data.get("hash") == current_hash and "domain_map" in cache_data:
                            ConnectionCategory_dict = {cat.value: cat for cat in ConnectionCategory}
                            
                            items = list(cache_data["domain_map"].items())
                            new_domain_map = {}
                            chunk_size = 100000
                            for i in range(0, len(items), chunk_size):
                                chunk = items[i:i + chunk_size]
                                for k, v in chunk:
                                    new_domain_map[k] = ConnectionCategory_dict.get(v, ConnectionCategory.UNKNOWN)
                                time.sleep(0.001) # Yield GIL
                                
                            new_stats = {
                                ConnectionCategory_dict.get(k, ConnectionCategory.UNKNOWN): v 
                                for k, v in cache_data.get("stats", {}).items()
                            }
                            new_sources_metadata = {
                                ConnectionCategory_dict.get(k, ConnectionCategory.UNKNOWN): v 
                                for k, v in cache_data.get("sources_metadata", {}).items()
                            }
                            
                            # Atomic swap inside lock
                            with self.lock:
                                self.domain_map = new_domain_map
                                self.identity_map = cache_data.get("identity_map", {})
                                self.stats = new_stats
                                self.sources_metadata = new_sources_metadata
                            self.is_loading = False
                            self._notify_loaded()
                            logger.info(f"Blocklists successfully loaded from cache ({len(new_domain_map)} domains)")
                            return
                    except Exception as e:
                        logger.warning(f"Failed to load cache from {cache_file}: {e}. Checking alternatives...")
                    
            # 2. Full reload if cache miss or corrupted
            new_domain_map = {}
            new_identity_map = {}
            new_stats = {cat: 0 for cat in ConnectionCategory}
            new_sources_metadata = {}
            
            # Inject hardcoded essential, system, and update domains
            for domain in ESSENTIAL_DOMAINS:
                new_domain_map[domain] = ConnectionCategory.ESSENTIAL
            new_stats[ConnectionCategory.ESSENTIAL] = len(ESSENTIAL_DOMAINS)

            for domain in SYSTEM_DOMAINS:
                new_domain_map[domain] = ConnectionCategory.SYSTEM
            new_stats[ConnectionCategory.SYSTEM] = len(SYSTEM_DOMAINS)

            for domain in UPDATE_DOMAINS:
                new_domain_map[domain] = ConnectionCategory.UPDATE
            new_stats[ConnectionCategory.UPDATE] = len(UPDATE_DOMAINS)
            
            # Internal helper to parse list without locking
            def load_into_temp(filepath: str, category: Optional[ConnectionCategory], identity_name: str = None):
                if not os.path.exists(filepath):
                    return
                import datetime
                filename = os.path.basename(filepath)
                dt = datetime.datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
                
                domains = self._parse_domains_from_file(filepath)
                
                if category:
                    if category not in new_sources_metadata:
                        new_sources_metadata[category] = []
                    new_sources_metadata[category].append({'filename': filename, 'updated': dt, 'size': len(domains)})
                    
                # Add to temporary maps directly without locks
                for domain in domains:
                    d = domain.lower()
                    if category:
                        # Prevent lower priority blocklists from overtaking system/essential/update apex domains
                        if category in (ConnectionCategory.AD, ConnectionCategory.TRACKER, ConnectionCategory.TELEMETRY, ConnectionCategory.MALWARE, ConnectionCategory.SECURITY):
                            if d in ESSENTIAL_DOMAINS or d in SYSTEM_DOMAINS or d in UPDATE_DOMAINS:
                                continue

                        if d not in new_domain_map:
                            new_domain_map[d] = category
                            new_stats[category] = new_stats.get(category, 0) + 1
                        else:
                            existing_cat = new_domain_map[d]
                            if CATEGORY_PRIORITY.get(category, 0) > CATEGORY_PRIORITY.get(existing_cat, 0):
                                new_domain_map[d] = category
                                new_stats[existing_cat] -= 1
                                new_stats[category] = new_stats.get(category, 0) + 1
                    if identity_name:
                        new_identity_map[d] = identity_name

            if os.path.exists(self.lists_dir):
                for filename in os.listdir(self.lists_dir):
                    if not filename.endswith('.txt'): continue
                    filepath = os.path.join(self.lists_dir, filename)
                    
                    if filename.startswith('ads_') or filename == 'ads.txt':
                        load_into_temp(filepath, ConnectionCategory.AD)
                    elif filename.startswith('telemetry_') or filename == 'telemetry.txt':
                        load_into_temp(filepath, ConnectionCategory.TELEMETRY)
                    elif filename.startswith('malware_') or filename == 'malware.txt':
                        load_into_temp(filepath, ConnectionCategory.MALWARE)
                    elif filename.startswith('tracker') or filename == 'trackers.txt':
                        load_into_temp(filepath, ConnectionCategory.TRACKER)
                    elif filename.startswith('doh_providers'):
                        block_doh = True
                        if hasattr(self, 'db') and self.db:
                            allow_doh = str(self.db.get_setting("allow_in_browser_dns", "false")).lower() == "true"
                            block_doh = not allow_doh
                        if block_doh:
                            load_into_temp(filepath, ConnectionCategory.TRACKER)
                    elif filename.startswith('security_'):
                        load_into_temp(filepath, ConnectionCategory.SECURITY)
                    elif filename.startswith('update_'):
                        load_into_temp(filepath, ConnectionCategory.UPDATE)
                    elif filename.startswith('safe_') or filename.startswith('essential_'):
                        load_into_temp(filepath, ConnectionCategory.ESSENTIAL)
                    elif filename.startswith('whitelist_'):
                        load_into_temp(filepath, ConnectionCategory.USER_ALLOWED)
                    elif filename.startswith('user_blocked_') or filename.startswith('blocked_'):
                        load_into_temp(filepath, ConnectionCategory.USER_BLOCKED)
                    elif filename.startswith('system_'):
                        load_into_temp(filepath, ConnectionCategory.SYSTEM)
                    elif filename.startswith('identity_'):
                        parts = filename.split('_')
                        identity_name = parts[1].title() if len(parts) > 1 else 'Unknown'
                        load_into_temp(filepath, None, identity_name=identity_name)

            # Atomic swap inside lock
            with self.lock:
                self.domain_map = new_domain_map
                self.identity_map = new_identity_map
                self.stats = new_stats
                self.sources_metadata = new_sources_metadata
                        
            # Decouple and save cache asynchronously in background thread to avoid freezing GUI
            user_dir = os.path.join(os.path.expanduser("~"), ".NetStrip")
            os.makedirs(user_dir, exist_ok=True)
            save_targets = [os.path.join(user_dir, "NetStrip_cache.json")]
            if self.lists_dir and os.path.exists(self.lists_dir):
                save_targets.append(os.path.join(self.lists_dir, "NetStrip_cache.json"))

            def _save_cache_worker(targets, c_hash, d_map, i_map, st, sm):
                try:
                    cache_payload = {
                        "hash": c_hash,
                        "domain_map": {k: getattr(v, 'value', v) for k, v in d_map.items()},
                        "identity_map": i_map,
                        "stats": {getattr(k, 'value', k): v for k, v in st.items()},
                        "sources_metadata": {getattr(k, 'value', k): v for k, v in sm.items()}
                    }
                    for target in targets:
                        temp_target = target + ".tmp"
                        try:
                            with open(temp_target, "w", encoding="utf-8") as f:
                                json.dump(cache_payload, f)
                            if os.path.exists(target):
                                try: os.remove(target)
                                except Exception: pass
                            os.replace(temp_target, target)
                        except Exception as e:
                            logger.debug(f"Could not write cache to {target}: {e}")
                            if os.path.exists(temp_target):
                                try: os.remove(temp_target)
                                except Exception: pass
                except Exception as e:
                    logger.debug(f"Async cache save worker encountered error: {e}")

            threading.Thread(
                target=_save_cache_worker,
                args=(save_targets, current_hash, new_domain_map, new_identity_map, new_stats, new_sources_metadata),
                daemon=True
            ).start()

        finally:
            self.is_loading = False
            self._notify_loaded()

    def _load_list(self, filepath: str, category: Optional[ConnectionCategory], identity_name: str = None):
        """Parse a hosts or domain list file and add it to the map."""
        if not os.path.exists(filepath):
            return
            
        import datetime
        filename = os.path.basename(filepath)
        mod_time = os.path.getmtime(filepath)
        dt = datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
        
        domains = self._parse_domains_from_file(filepath)
        
        if category:
            if category not in self.sources_metadata:
                self.sources_metadata[category] = []
            self.sources_metadata[category].append({
                'filename': filename,
                'updated': dt,
                'size': len(domains)
            })
            
        self.add_domains_chunked(domains, category, identity_name)

    def add_domains_chunked(self, domains_list: List[str], category: Optional[ConnectionCategory] = None, identity_name: str = None, chunk_size: int = 50000):
        """Add domains in batches yielding to Tkinter event loop to prevent UI hangs."""
        for i in range(0, len(domains_list), chunk_size):
            chunk = domains_list[i:i + chunk_size]
            with self.lock:
                for domain in chunk:
                    d = domain.lower()
                    if category:
                        if category in (ConnectionCategory.AD, ConnectionCategory.TRACKER, ConnectionCategory.TELEMETRY, ConnectionCategory.MALWARE, ConnectionCategory.SECURITY):
                            if d in ESSENTIAL_DOMAINS or d in SYSTEM_DOMAINS or d in UPDATE_DOMAINS:
                                continue

                        if d not in self.domain_map:
                            self.domain_map[d] = category
                            self.stats[category] = self.stats.get(category, 0) + 1
                        else:
                            existing_cat = self.domain_map[d]
                            if CATEGORY_PRIORITY.get(category, 0) > CATEGORY_PRIORITY.get(existing_cat, 0):
                                self.domain_map[d] = category
                                self.stats[existing_cat] -= 1
                                self.stats[category] = self.stats.get(category, 0) + 1
                    if identity_name:
                        self.identity_map[d] = identity_name
            import time
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

            # 2. Blocklist Trie (Prioritized by CATEGORY_PRIORITY)
            parts = domain.split('.')
            for i in range(len(parts)):
                test_domain = '.'.join(parts[i:])
                if test_domain in self.domain_map:
                    cat = self.domain_map[test_domain]
                    is_blk = cat not in (ConnectionCategory.ESSENTIAL, ConnectionCategory.SYSTEM, ConnectionCategory.UPDATE, ConnectionCategory.USER_ALLOWED)
                    return is_blk, cat

            # 3. Fallback checks for hardcoded sets
            for essential in ESSENTIAL_DOMAINS:
                if domain == essential or domain.endswith('.' + essential):
                    return False, ConnectionCategory.ESSENTIAL

            for sys_dom in SYSTEM_DOMAINS:
                if domain == sys_dom or domain.endswith('.' + sys_dom):
                    return False, ConnectionCategory.SYSTEM

            for upd_dom in UPDATE_DOMAINS:
                if domain == upd_dom or domain.endswith('.' + upd_dom):
                    return False, ConnectionCategory.UPDATE

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

    def search(self, query: str = "", limit: int = 50, category_filter=None, offset: int = 0) -> List[dict]:
        """
        Search domains using partial match, returns up to `limit` results after skipping `offset`.
        Lock-free iteration with retry mechanism for real-time responsiveness.
        """
        if not query and not category_filter:
            return []
            
        query = query.lower() if query else ""
        
        # Normalize category filter
        target_cat = None
        if category_filter:
            if hasattr(category_filter, 'value'):
                target_cat = category_filter.value.lower()
            else:
                target_cat = str(category_filter).lower()
                
            # Map common aliases
            if target_cat in ('ad', 'ads'):
                target_cat = 'ad'
            elif target_cat in ('user_blocked', 'blocked'):
                target_cat = 'user_blocked'
            elif target_cat in ('user_allowed', 'allowed', 'whitelist'):
                target_cat = 'user_allowed'
            elif target_cat in ('tracker', 'trackers'):
                target_cat = 'tracker'

        results = []
        seen = set()
        skipped = 0
        
        # 1. Check User Whitelist
        if not target_cat or target_cat == 'user_allowed':
            for domain in list(self.whitelist):
                if not query or query in domain:
                    if domain not in seen:
                        seen.add(domain)
                        if skipped < offset:
                            skipped += 1
                        else:
                            results.append({'domain': domain, 'category': ConnectionCategory.USER_ALLOWED.value})
                            if len(results) >= limit:
                                return results
                                
        # 2. Check User Blacklist
        if not target_cat or target_cat == 'user_blocked':
            for domain in list(self.blacklist.keys()):
                if not query or query in domain:
                    if domain not in seen:
                        seen.add(domain)
                        if skipped < offset:
                            skipped += 1
                        else:
                            results.append({'domain': domain, 'category': ConnectionCategory.USER_BLOCKED.value})
                            if len(results) >= limit:
                                return results

        # 3. Check System Domains Set
        if not target_cat or target_cat == 'system':
            for domain in SYSTEM_DOMAINS:
                if not query or query in domain:
                    if domain not in seen:
                        seen.add(domain)
                        if skipped < offset:
                            skipped += 1
                        else:
                            results.append({'domain': domain, 'category': ConnectionCategory.SYSTEM.value})
                            if len(results) >= limit:
                                return results

        # 4. Check Essential Domains Set
        if not target_cat or target_cat == 'essential':
            for domain in ESSENTIAL_DOMAINS:
                if not query or query in domain:
                    if domain not in seen:
                        seen.add(domain)
                        if skipped < offset:
                            skipped += 1
                        else:
                            results.append({'domain': domain, 'category': ConnectionCategory.ESSENTIAL.value})
                            if len(results) >= limit:
                                return results

        # 5. Check Update Domains Set
        if not target_cat or target_cat == 'update':
            for domain in UPDATE_DOMAINS:
                if not query or query in domain:
                    if domain not in seen:
                        seen.add(domain)
                        if skipped < offset:
                            skipped += 1
                        else:
                            results.append({'domain': domain, 'category': ConnectionCategory.UPDATE.value})
                            if len(results) >= limit:
                                return results

        # 6. Lock-free iteration of domain_map
        retry_count = 0
        while retry_count < 5:
            try:
                for domain, category in self.domain_map.items():
                    cat_val = getattr(category, 'value', category)
                    if isinstance(cat_val, str):
                        cat_val_lower = cat_val.lower()
                        if cat_val_lower in ('ad', 'ads'):
                            cat_val_norm = 'ad'
                        elif cat_val_lower in ('user_blocked', 'blocked'):
                            cat_val_norm = 'user_blocked'
                        elif cat_val_lower in ('user_allowed', 'allowed', 'whitelist'):
                            cat_val_norm = 'user_allowed'
                        elif cat_val_lower in ('tracker', 'trackers'):
                            cat_val_norm = 'tracker'
                        else:
                            cat_val_norm = cat_val_lower
                    else:
                        cat_val_norm = str(cat_val)

                    if target_cat and cat_val_norm != target_cat:
                        continue

                    if not query or query in domain:
                        if domain not in seen:
                            seen.add(domain)
                            if skipped < offset:
                                skipped += 1
                            else:
                                results.append({
                                    'domain': domain,
                                    'category': cat_val
                                })
                                if len(results) >= limit:
                                    return results
                break
            except RuntimeError:
                # Dictionary size changed during concurrent update, retry
                retry_count += 1
                import time
                time.sleep(0.01)
                
        return results
