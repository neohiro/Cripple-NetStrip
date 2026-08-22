"""
Blocklist Manager for NetStrip
Manages the offline domain blocklists using high-performance Python sets,
indexed category sets, and fast binary serialization.
"""

import os
import threading
import json
import pickle
import hashlib
import hmac
import logging
import re
import datetime
from typing import Tuple, Optional, Dict, Set, List, Any, Callable
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
ESSENTIAL_DOMAINS = {
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
}

# 2. SYSTEM DOMAINS — OS Infrastructure, Search Engines & Cloud Services (Categorized as ConnectionCategory.SYSTEM)
SYSTEM_DOMAINS = {
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
}

# 3. UPDATE DOMAINS — OS Repositories & Package Managers (Categorized as ConnectionCategory.UPDATE)
UPDATE_DOMAINS = {
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
}

# Dynamically inject updater source domains into ESSENTIAL_DOMAINS to prevent updater lockout
try:
    import json
    import os
    import urllib.parse
    _bundled_sources = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'updater_sources.json')
    if os.path.exists(_bundled_sources):
        with open(_bundled_sources, 'r', encoding='utf-8') as _f:
            _data = json.load(_f)
        for _s in _data.get('sources', []):
            _url = _s.get('url')
            if _url and _s.get('enabled', True):
                _netloc = urllib.parse.urlparse(_url).netloc
                if _netloc:
                    ESSENTIAL_DOMAINS.add(_netloc)
except Exception:
    pass

DOM_RE = re.compile(r'^[a-z0-9_\*\-\.\u0080-\uFFFF]+$')

class BlocklistManager:
    def __init__(self, lists_dir: str = None, db=None, progress_callback: Optional[Callable[[str, float], None]] = None, async_load: bool = True, **kwargs):
        if lists_dir is not None and not isinstance(lists_dir, (str, bytes, os.PathLike)):
            db = lists_dir
            lists_dir = None
        self.db = db
        self.domain_map: Dict[str, ConnectionCategory] = {}
        self.category_domains: Dict[ConnectionCategory, Set[str]] = {cat: set() for cat in ConnectionCategory}
        self.identity_map: Dict[str, str] = {}
        self.whitelist: Set[str] = set()
        self.app_whitelist: Set[str] = set()
        self.app_blacklist: Set[str] = set()
        self.app_neutral: Set[str] = set()
        self.blacklist: Dict[str, bool] = {}
        # Per-category bulk overrides set from the Filter Manager UI cards.
        # {category_value: 'allow' | 'block'} — absent means default behavior.
        self.category_overrides: Dict[str, str] = {}
        self.lock = threading.RLock()
        self.stats: Dict[ConnectionCategory, int] = {cat: 0 for cat in ConnectionCategory}
        self.sources_metadata: Dict[ConnectionCategory, List[Dict[str, Any]]] = {}
        self.on_loaded_callbacks: List[Callable[[], None]] = []
        self.progress_callback = progress_callback
        
        if lists_dir is None:
            user_dir = os.path.join(os.path.expanduser("~"), ".NetStrip")
            lists_dir = os.path.join(user_dir, "lists")
            os.makedirs(lists_dir, exist_ok=True)
            
            # Copy bundled lists and updater_sources.json to persistent storage if missing
            bundled_data_dir = os.path.dirname(os.path.abspath(__file__))
            bundled_lists = os.path.join(bundled_data_dir, 'lists')
            bundled_sources = os.path.join(bundled_data_dir, 'updater_sources.json')
            
            import shutil
            import json
            if os.path.exists(bundled_sources):
                target_sources = os.path.join(user_dir, 'updater_sources.json')
                if not os.path.exists(target_sources):
                    try: shutil.copy2(bundled_sources, target_sources)
                    except Exception: pass
                else:
                    try:
                        # Self-healing merge: bundled definitions always win
                        # (fixes dead/moved/re-named upstream feeds on every
                        # upgrade), while the user's per-source enabled/disabled
                        # toggles are preserved by matching name first, then
                        # URL. Custom user-added sources are kept verbatim.
                        with open(bundled_sources, 'r', encoding='utf-8') as f:
                            b_data = json.load(f)
                        with open(target_sources, 'r', encoding='utf-8') as f:
                            t_data = json.load(f)

                        b_sources = b_data.get('sources', [])
                        t_sources = t_data.get('sources', [])

                        enabled_by_name = {}
                        enabled_by_url = {}
                        custom_sources = []
                        b_names = {s.get('name') for s in b_sources if s.get('name')}

                        def _norm(s):
                            return ''.join(ch for ch in str(s).lower() if ch.isalnum())

                        enabled_by_norm = {}
                        for s in t_sources:
                            if s.get('name'):
                                enabled_by_name[s['name']] = s.get('enabled', True)
                                n = _norm(s['name'])
                                if n and n not in enabled_by_norm:
                                    enabled_by_norm[n] = s.get('enabled', True)
                            if s.get('url'):
                                enabled_by_url[s['url']] = s.get('enabled', True)

                        for s in t_sources:
                            if s.get('name') not in b_names and str(s.get('name', '')).startswith('Custom:'):
                                custom_sources.append(s)

                        merged = []
                        modified = False
                        for b_s in b_sources:
                            new_s = dict(b_s)
                            name = new_s.get('name')
                            norm = _norm(name) if name else ''
                            if name in enabled_by_name:
                                new_s['enabled'] = enabled_by_name[name]
                            elif new_s.get('url') in enabled_by_url:
                                new_s['enabled'] = enabled_by_url[new_s['url']]
                            else:
                                # Normalized-name containment: keeps a user's
                                # opt-out alive across upstream renames/repoints
                                # (e.g. 'KADhosts (Fraud/Scam)' ->
                                #  'KADhosts Fraud/Scam (PolishFiltersTeam)').
                                for n_old, en in enabled_by_norm.items():
                                    if n_old and (norm.startswith(n_old) or n_old.startswith(norm)):
                                        new_s['enabled'] = en
                                        break
                            old = next((t for t in t_sources if t.get('name') == name), None)
                            if old is None or any(old.get(k) != new_s.get(k) for k in ('url', 'category', 'format', 'enabled')):
                                modified = True
                            merged.append(new_s)
                        merged.extend(custom_sources)
                        modified = modified or len(merged) != len(t_sources)

                        if modified:
                            t_data['sources'] = merged
                            with open(target_sources, 'w', encoding='utf-8') as f:
                                json.dump(t_data, f, indent=4)
                    except Exception:
                        pass
            
            if os.path.exists(bundled_lists):
                for item in os.listdir(bundled_lists):
                    if item.endswith('.txt') or item.endswith('.json'):
                        src = os.path.join(bundled_lists, item)
                        dst = os.path.join(lists_dir, item)
                        if not os.path.exists(dst):
                            try: shutil.copy2(src, dst)
                            except Exception: pass
                            
        self.lists_dir = lists_dir
        self.is_loading = True
        
        self._load_category_overrides()
        
        if async_load:
            threading.Thread(target=self._load_async_worker, daemon=True).start()
        else:
            self.load_all(progress_callback=self.progress_callback)

    def set_progress_callback(self, callback: Optional[Callable[[str, float], None]]):
        self.progress_callback = callback

    def add_loaded_callback(self, callback: Callable[[], None]):
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

    def _report_progress(self, text: str, progress: float, callback: Optional[Callable[[str, float], None]] = None):
        cb = callback or self.progress_callback
        if cb:
            try:
                cb(text, min(1.0, max(0.0, progress)))
            except Exception:
                pass

    def _get_cache_paths(self) -> List[str]:
        """Return potential cache file locations in priority order (.pkl binary then .json)."""
        paths = []
        user_dir = os.path.join(os.path.expanduser("~"), ".NetStrip")
        # 1. High-speed binary pickle caches
        paths.append(os.path.join(user_dir, "NetStrip_cache.pkl"))
        if self.lists_dir:
            paths.append(os.path.join(self.lists_dir, "NetStrip_cache.pkl"))
        # 2. JSON caches (fallback / compatibility)
        paths.append(os.path.join(user_dir, "NetStrip_cache.json"))
        if self.lists_dir:
            paths.append(os.path.join(self.lists_dir, "NetStrip_cache.json"))
        return paths

    # --- Signed binary cache (anti-tampering) -------------------------------
    # pickle.load on a user-writable file is arbitrary-code-execution vector.
    # The cache is therefore sealed with an HMAC-SHA256 tag; a modified or
    # planted cache file fails verification and is rebuilt from the feeds.
    CACHE_MAGIC = b"NSPK1"

    def _get_cache_signing_key(self) -> bytes:
        key_path = os.path.join(os.path.expanduser("~"), ".NetStrip", "cache.key")
        try:
            if os.path.exists(key_path):
                with open(key_path, "rb") as kf:
                    key = kf.read()
                if len(key) >= 32:
                    return key
            import secrets
            key = secrets.token_bytes(32)
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            with open(key_path, "wb") as kf:
                os.chmod(key_path, 0o600)
                kf.write(key)
            return key
        except Exception:
            return b"NetStrip-fallback-cache-key-v1"

    def _load_signed_pickle(self, path: str):
        """Verify the HMAC seal of a .pkl cache before deserializing it."""
        with open(path, "rb") as f:
            blob = f.read()
        if len(blob) < len(self.CACHE_MAGIC) + 32 + 2:
            raise ValueError("Cache file too small")
        magic = blob[:len(self.CACHE_MAGIC)]
        sig = blob[len(self.CACHE_MAGIC):len(self.CACHE_MAGIC) + 32]
        payload = blob[len(self.CACHE_MAGIC) + 32:]
        if magic != self.CACHE_MAGIC:
            raise ValueError("Legacy unsigned cache format")
        expected = hmac.new(self._get_cache_signing_key(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("Cache signature verification failed")
        return pickle.loads(payload)  # nosec B301 - container is HMAC-SHA256 verified above

    @staticmethod
    def _seal_pickle(payload_obj) -> bytes:
        """Serialize + HMAC-seal a cache payload into the signed container format."""
        body = pickle.dumps(payload_obj, protocol=pickle.HIGHEST_PROTOCOL)
        key = BlocklistManager._get_cache_signing_key(BlocklistManager)
        sig = hmac.new(key, body, hashlib.sha256).digest()
        return BlocklistManager.CACHE_MAGIC + sig + body

    def _get_lists_hash(self) -> str:
        """Generate a stable deterministic hash of the current lists directory, updater sources, and DNS settings."""
        h = hashlib.md5(usedforsecurity=False)  # non-crypto cache key only
        h.update(b"v3.5.15_cache_fix")
        allow_doh = "false"
        if hasattr(self, 'db') and self.db:
            try:
                allow_doh = str(self.db.get_setting("allow_in_browser_dns", "false")).lower()
            except Exception:
                pass
        h.update(f"allow_doh:{allow_doh}".encode('utf-8'))
        
        # Include updater_sources.json status/toggles in cache key
        sources_file = os.path.join(self.lists_dir, '..', 'updater_sources.json')
        if os.path.exists(sources_file):
            try:
                with open(sources_file, 'rb') as sf:
                    h.update(sf.read())
            except Exception:
                pass

        if not os.path.exists(self.lists_dir):
            return h.hexdigest()
        for filename in sorted(os.listdir(self.lists_dir)):
            if not filename.endswith('.txt'): continue
            filepath = os.path.join(self.lists_dir, filename)
            try:
                size = os.path.getsize(filepath)
                mtime = os.path.getmtime(filepath)
                h.update(f"{filename}:{size}:{mtime}".encode('utf-8'))
            except Exception:
                pass
        return h.hexdigest()

    def get_updater_sources(self) -> List[Dict[str, Any]]:
        """Return all online blocklist sources with robust file matching."""
        sources_file = os.path.join(self.lists_dir, '..', 'updater_sources.json')
        if not os.path.exists(sources_file):
            return []
        try:
            with open(sources_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            sources = data.get('sources', [])
            
            disk_files = [f for f in os.listdir(self.lists_dir) if f.endswith('.txt')] if os.path.exists(self.lists_dir) else []
            
            # Enrich with local disk status
            for s in sources:
                name = s.get('name', '')
                category = s.get('category', 'ad')
                safe_name = name.replace(' ', '_').replace('/', '_').replace(':', '')
                
                candidates = [
                    f"{category}_{safe_name}.txt",
                    f"{category}s_{safe_name}.txt",
                    f"{category[:-1]}_{safe_name}.txt" if category.endswith('s') else f"{category}s_{safe_name}.txt",
                    f"{safe_name}.txt"
                ]
                
                found_filename = None
                for c in candidates:
                    if os.path.exists(os.path.join(self.lists_dir, c)):
                        found_filename = c
                        break
                        
                if not found_filename:
                    for df in disk_files:
                        if safe_name.lower() in df.lower():
                            found_filename = df
                            break
                            
                s['filename'] = found_filename or f"{category}_{safe_name}.txt"
                s['is_local'] = found_filename is not None
                
                if found_filename:
                    filepath = os.path.join(self.lists_dir, found_filename)
                    try:
                        s['local_size'] = os.path.getsize(filepath)
                        s['local_mtime'] = os.path.getmtime(filepath)
                    except Exception:
                        s['local_size'] = 0
                        s['local_mtime'] = 0
                else:
                    s['local_size'] = 0
                    s['local_mtime'] = 0
            return sources
        except Exception as e:
            logger.error(f"Error reading updater sources: {e}")
            return []

    def toggle_updater_source(self, source_name: str, enabled: bool) -> bool:
        """Enable or disable a specific online source by name and reload memory."""
        sources_file = os.path.join(self.lists_dir, '..', 'updater_sources.json')
        if not os.path.exists(sources_file):
            return False
        try:
            with open(sources_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            modified = False
            for s in data.get('sources', []):
                if s.get('name') == source_name:
                    s['enabled'] = enabled
                    modified = True
                    break
            if modified:
                with open(sources_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                # Asynchronously reload blocklists with the new active configuration
                threading.Thread(target=lambda: self.load_all(force_reload=True), daemon=True).start()
            return modified
        except Exception as e:
            logger.error(f"Error toggling updater source '{source_name}': {e}")
            return False

    def _load_async_worker(self):
        """Worker thread to load blocklists with progress reporting."""
        try:
            self.load_all(progress_callback=self.progress_callback)
        except Exception as e:
            logger.error(f"Failed to load blocklists: {e}")
        finally:
            self.is_loading = False

    def _parse_domains_from_file(self, filepath: str, is_whitelist_file: bool = False) -> Set[str]:
        """High-speed universal parser for ABP, AdGuard, DNSMasq, Hosts, and plain domain lists."""
        domains = set()
        if not os.path.exists(filepath):
            return domains
            
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            return domains

        for raw_line in lines:
            line = raw_line.strip()
            if not line or line[0] in ('#', '!', '[', ';'):
                continue
            if line.startswith('include:'):
                continue
            if line.startswith('@@'):
                if not is_whitelist_file:
                    continue
                line = line[2:]
            if '@' in line:
                line = line.partition('@')[0].strip()
            if line.startswith('full:'):
                line = line[5:].strip()
            elif line.startswith('domain:'):
                line = line[7:].strip()
                
            # DNSMasq format: address=/domain.com/0.0.0.0 or server=/domain.com/
            if line.startswith(('address=/', 'server=/')):
                parts = line.split('/')
                if len(parts) >= 2:
                    line = parts[1]
                    
            parts = line.split()
            if not parts:
                continue
                
            # v2fly domain-list-community format:
            #   "domain example.com" / "full:example.com" / "keyword:xxx"
            # The first token is the rule type — only the second token is a domain.
            if parts[0] in ('domain', 'full') and len(parts) >= 2:
                candidates = [parts[1]]
            elif parts[0] in ('keyword', 'regexp', 'include') or parts[0].startswith(('keyword:', 'regexp:')):
                continue
            # Hosts format (any IP prefix)
            elif len(parts) >= 2 and (parts[0] in ('0.0.0.0', '127.0.0.1', '::1', '127.0.0.53', '::', '0') or re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$|^[0-9a-fA-F:]+$', parts[0])):
                candidates = parts[1:]
            else:
                candidates = [parts[0]]
                
            for raw_d in candidates:
                if not raw_d or raw_d[0] == '#':
                    break
                if raw_d.startswith('||'):
                    raw_d = raw_d[2:]
                if '^' in raw_d:
                    raw_d = raw_d.partition('^')[0]
                if '$' in raw_d:
                    raw_d = raw_d.partition('$')[0]
                if '/' in raw_d:
                    raw_d = raw_d.partition('/')[0]
                if '#' in raw_d:
                    raw_d = raw_d.partition('#')[0]
                if raw_d.startswith('*.'):
                    raw_d = raw_d[2:]
                elif raw_d.startswith('.'):
                    raw_d = raw_d[1:]
                    
                d = raw_d.strip().lower().rstrip('.')
                if not d or len(d) > 253 or '.' not in d:
                    continue
                # Skip bare IPs (e.g. Feodo C2 IP lists) — they are not domains
                # and would poison the domain map with useless pseudo-entries.
                if re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', d) or ':' in d:
                    continue
                if d in ('0.0.0.0', '127.0.0.1', 'localhost', 'broadcasthost', 'local'):
                    continue
                if DOM_RE.match(d):
                    domains.add(d)
        return domains

    def load_all(self, progress_callback: Optional[Callable[[str, float], None]] = None, force_reload: bool = False):
        """Load all blocklists using ultra-fast binary cache or multi-core parallel parsing with live progress."""
        self.is_loading = True
        cb = progress_callback or self.progress_callback
        try:
            self._report_progress("Checking intelligence cache...", 0.1, cb)
            current_hash = self._get_lists_hash()
            
            # 1. Try loading from existing high-speed binary cache (.pkl)
            if not force_reload:
                ConnectionCategory_dict = {cat.value: cat for cat in ConnectionCategory}
                for cat in ConnectionCategory:
                    ConnectionCategory_dict[cat] = cat

                for cache_file in self._get_cache_paths():
                    if os.path.exists(cache_file):
                        try:
                            self._report_progress("Loading domain database cache...", 0.3, cb)
                            cache_data = None
                            if cache_file.endswith('.pkl'):
                                # HMAC-sealed container: refuse tampered/planted files
                                cache_data = self._load_signed_pickle(cache_file)
                            elif cache_file.endswith('.json'):
                                with open(cache_file, "r", encoding="utf-8") as f:
                                    cache_data = json.load(f)

                            if cache_data and cache_data.get("hash") == current_hash and "domain_map" in cache_data:
                                raw_map = cache_data["domain_map"]
                                sample_val = next(iter(raw_map.values())) if raw_map else None
                                
                                # Robust Enum normalizer to handle PyInstaller / Pickle module path mismatches
                                def _norm_enum(k):
                                    if isinstance(k, ConnectionCategory): return k
                                    return ConnectionCategory_dict.get(getattr(k, 'value', str(k)), ConnectionCategory.UNKNOWN)

                                if isinstance(sample_val, ConnectionCategory):
                                    new_domain_map = raw_map
                                else:
                                    new_domain_map = {
                                        k: _norm_enum(v)
                                        for k, v in raw_map.items()
                                    }
                                
                                new_stats = {
                                    _norm_enum(k): v 
                                    for k, v in cache_data.get("stats", {}).items()
                                }
                                new_sources_metadata = {
                                    _norm_enum(k): v 
                                    for k, v in cache_data.get("sources_metadata", {}).items()
                                }
                                
                                # Restore or build indexed category sets
                                new_category_domains = {cat: set() for cat in ConnectionCategory}
                                if "category_domains" in cache_data:
                                    raw_cat_doms = cache_data["category_domains"]
                                    for k, dom_set in raw_cat_doms.items():
                                        cat_enum = _norm_enum(k)
                                        new_category_domains[cat_enum] = dom_set if isinstance(dom_set, set) else set(dom_set)
                                else:
                                    for d, cat_enum in new_domain_map.items():
                                        new_category_domains[cat_enum].add(d)

                                # Atomic swap inside lock
                                with self.lock:
                                    self.domain_map = new_domain_map
                                    self.category_domains = new_category_domains
                                    self.identity_map = cache_data.get("identity_map", {})
                                    self.stats = new_stats
                                    self.sources_metadata = new_sources_metadata
                                    
                                self.is_loading = False
                                self._report_progress("Filter engine fully loaded", 1.0, cb)
                                self._notify_loaded()
                                logger.info(f"Blocklists successfully loaded from cache {os.path.basename(cache_file)} ({len(new_domain_map)} domains)")
                                return
                        except Exception as e:
                            logger.warning(f"Failed to load cache from {cache_file}: {e}. Falling back...")

            # 2. Cold Reload: Multi-core parallel parsing
            self._report_progress("Parsing filter lists from disk...", 0.2, cb)
            new_domain_map = {}
            new_category_domains = {cat: set() for cat in ConnectionCategory}
            new_identity_map = {}
            new_stats = {cat: 0 for cat in ConnectionCategory}
            new_sources_metadata = {}

            # Inject hardcoded essential, system, and update domains
            for domain in ESSENTIAL_DOMAINS:
                new_domain_map[domain] = ConnectionCategory.ESSENTIAL
                new_category_domains[ConnectionCategory.ESSENTIAL].add(domain)
            new_stats[ConnectionCategory.ESSENTIAL] = len(ESSENTIAL_DOMAINS)

            for domain in SYSTEM_DOMAINS:
                new_domain_map[domain] = ConnectionCategory.SYSTEM
                new_category_domains[ConnectionCategory.SYSTEM].add(domain)
            new_stats[ConnectionCategory.SYSTEM] = len(SYSTEM_DOMAINS)

            for domain in UPDATE_DOMAINS:
                new_domain_map[domain] = ConnectionCategory.UPDATE
                new_category_domains[ConnectionCategory.UPDATE].add(domain)
            new_stats[ConnectionCategory.UPDATE] = len(UPDATE_DOMAINS)

            if os.path.exists(self.lists_dir):
                # Identify disabled sources from updater_sources.json
                disabled_file_patterns = set()
                sources_file = os.path.join(self.lists_dir, '..', 'updater_sources.json')
                if os.path.exists(sources_file):
                    try:
                        with open(sources_file, 'r', encoding='utf-8') as sf:
                            sdata = json.load(sf)
                        for s in sdata.get('sources', []):
                            if not s.get('enabled', True):
                                name = s.get('name', '')
                                cat_s = s.get('category', 'ad')
                                safe_n = name.replace(' ', '_').replace('/', '_').replace(':', '')
                                disabled_file_patterns.add(f"{cat_s}_{safe_n}.txt".lower())
                                disabled_file_patterns.add(f"{cat_s}s_{safe_n}.txt".lower())
                                if cat_s.endswith('s'):
                                    disabled_file_patterns.add(f"{cat_s[:-1]}_{safe_n}.txt".lower())
                                disabled_file_patterns.add(f"{safe_n}.txt".lower())
                                disabled_file_patterns.add(f"temp_{cat_s}_{safe_n}.txt".lower())
                    except Exception:
                        pass

                all_files = sorted([f for f in os.listdir(self.lists_dir) if f.endswith('.txt')])
                active_files = []
                for filename in all_files:
                    fn_lower = filename.lower()
                    if fn_lower in disabled_file_patterns:
                        continue
                    active_files.append(filename)

                total_files = len(active_files)

                # Multi-core concurrent parsing of all list files
                from concurrent.futures import ThreadPoolExecutor
                max_workers = min(8, max(2, os.cpu_count() or 4))
                
                def parse_worker(filename):
                    filepath = os.path.join(self.lists_dir, filename)
                    cat: Optional[ConnectionCategory] = None
                    identity_name: Optional[str] = None
                    is_whitelist_file = False

                    if filename.startswith(('ads_', 'ad_')) or filename == 'ads.txt':
                        cat = ConnectionCategory.AD
                    elif filename.startswith('telemetry_') or filename == 'telemetry.txt':
                        cat = ConnectionCategory.TELEMETRY
                    elif filename.startswith('malware_') or filename == 'malware.txt':
                        cat = ConnectionCategory.MALWARE
                    elif filename.startswith('tracker') or filename == 'trackers.txt':
                        cat = ConnectionCategory.TRACKER
                    elif filename.startswith('doh_providers'):
                        block_doh = True
                        if hasattr(self, 'db') and self.db:
                            allow_doh = str(self.db.get_setting("allow_in_browser_dns", "false")).lower() == "true"
                            block_doh = not allow_doh
                        if block_doh:
                            cat = ConnectionCategory.TRACKER
                        else:
                            cat = ConnectionCategory.DNS
                    elif filename.startswith('security_'):
                        cat = ConnectionCategory.SECURITY
                    elif filename.startswith('update_'):
                        cat = ConnectionCategory.UPDATE
                    elif filename.startswith(('safe_', 'essential_')):
                        cat = ConnectionCategory.ESSENTIAL
                        is_whitelist_file = True
                    elif filename.startswith('whitelist_'):
                        cat = ConnectionCategory.USER_ALLOWED
                        is_whitelist_file = True
                    elif filename.startswith(('user_blocked_', 'blocked_')):
                        cat = ConnectionCategory.USER_BLOCKED
                    elif filename.startswith('system_'):
                        cat = ConnectionCategory.SYSTEM
                    elif filename.startswith('identity_'):
                        parts = filename.split('_')
                        identity_name = parts[1].title() if len(parts) > 1 else 'Unknown'
                        cat = ConnectionCategory.IDENTITY
                        
                    if cat is None:
                        cat = ConnectionCategory.UNKNOWN

                    domains = self._parse_domains_from_file(filepath, is_whitelist_file=is_whitelist_file)
                    dt = datetime.datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
                    return filename, cat, identity_name, domains, dt

                completed_count = 0
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [executor.submit(parse_worker, f) for f in active_files]
                    for fut in futures:
                        filename, cat, identity_name, domains, dt = fut.result()
                        completed_count += 1
                        prog = 0.2 + (0.7 * (completed_count / max(1, total_files)))
                        clean_name = filename.replace('.txt', '').replace('_', ' ')
                        self._report_progress(f"Parsed ({completed_count}/{total_files}): {clean_name}", prog, cb)

                        if cat:
                            if cat not in new_sources_metadata:
                                new_sources_metadata[cat] = []
                            new_sources_metadata[cat].append({'filename': filename, 'updated': dt, 'size': len(domains)})

                        for d in domains:
                            if cat:
                                new_stats[cat] = new_stats.get(cat, 0) + 1
                                if cat in (ConnectionCategory.AD, ConnectionCategory.TRACKER, ConnectionCategory.TELEMETRY, ConnectionCategory.MALWARE, ConnectionCategory.SECURITY):
                                    if d in ESSENTIAL_DOMAINS or d in SYSTEM_DOMAINS or d in UPDATE_DOMAINS:
                                        continue

                                if d not in new_domain_map:
                                    new_domain_map[d] = cat
                                    new_category_domains[cat].add(d)
                                else:
                                    existing_cat = new_domain_map[d]
                                    if CATEGORY_PRIORITY.get(cat, 0) > CATEGORY_PRIORITY.get(existing_cat, 0):
                                        new_domain_map[d] = cat
                                        new_category_domains[existing_cat].discard(d)
                                        new_category_domains[cat].add(d)
                            if identity_name:
                                new_identity_map[d] = identity_name

            # Atomic swap inside lock
            with self.lock:
                self.domain_map = new_domain_map
                self.category_domains = new_category_domains
                self.identity_map = new_identity_map
                self.stats = new_stats
                self.sources_metadata = new_sources_metadata

            self._report_progress("Saving intelligence cache...", 0.95, cb)
            
            # Save fast binary cache directly and asynchronously to both user directory and lists directory
            user_dir = os.path.join(os.path.expanduser("~"), ".NetStrip")
            os.makedirs(user_dir, exist_ok=True)

            def _save_cache_worker(user_d, lists_d, c_hash, d_map, cat_doms, i_map, st, sm):
                try:
                    pkl_payload = {
                        "hash": c_hash,
                        "domain_map": d_map,
                        "category_domains": cat_doms,
                        "identity_map": i_map,
                        "stats": st,
                        "sources_metadata": sm
                    }
                    
                    target_dirs = [user_d]
                    if lists_d and os.path.exists(lists_d):
                        target_dirs.append(lists_d)
                        
                    for t_dir in target_dirs:
                        pkl_target = os.path.join(t_dir, "NetStrip_cache.pkl")
                        pkl_tmp = pkl_target + ".tmp"
                        try:
                            sealed = BlocklistManager._seal_pickle(pkl_payload)
                            with open(pkl_tmp, "wb") as f:
                                f.write(sealed)
                            if os.path.exists(pkl_target):
                                try: os.remove(pkl_target)
                                except Exception: pass
                            os.replace(pkl_tmp, pkl_target)
                            logger.info(f"Updated signed binary cache at {pkl_target}")
                        except Exception as e:
                            logger.debug(f"Could not write pkl cache to {pkl_target}: {e}")
                            if os.path.exists(pkl_tmp):
                                try: os.remove(pkl_tmp)
                                except Exception: pass
                except Exception as e:
                    logger.debug(f"Cache save worker error: {e}")

            threading.Thread(
                target=_save_cache_worker,
                args=(user_dir, self.lists_dir, current_hash, new_domain_map, new_category_domains, new_identity_map, new_stats, new_sources_metadata),
                daemon=True
            ).start()

            self._report_progress("Protection engine ready", 1.0, cb)

        finally:
            self.is_loading = False
            self._notify_loaded()

    def _load_category_overrides(self):
        """Restore persisted per-category Allow/Block overrides from the DB."""
        if not self.db:
            return
        try:
            raw = self.db.get_setting("category_overrides", "{}")
            data = json.loads(raw) if isinstance(raw, str) else (raw or {})
            if isinstance(data, dict):
                self.category_overrides = {
                    str(k).lower(): str(v).lower()
                    for k, v in data.items() if v in ('allow', 'block')
                }
        except Exception as e:
            logger.debug(f"Failed to load category overrides: {e}")

    def get_category_override(self, category_value: str) -> Optional[str]:
        with self.lock:
            return self.category_overrides.get(str(category_value).lower())

    def set_category_override(self, category_value: str, state: Optional[str]):
        """
        Bulk-switch an entire indexed category to Allow or Block.
        state: 'allow' | 'block' | None (reset to default evaluation).
        Persists to the settings store and applies instantly.
        """
        key = str(category_value).lower()
        with self.lock:
            if state in ('allow', 'block'):
                self.category_overrides[key] = state
            else:
                self.category_overrides.pop(key, None)
        if self.db:
            try:
                self.db.set_setting("category_overrides", json.dumps(dict(self.category_overrides)))
            except Exception as e:
                logger.debug(f"Failed to persist category override: {e}")

    def is_blocked(self, domain: str, process_name: str = None) -> Tuple[bool, Optional[ConnectionCategory]]:
        """
        Check if a domain is blocked. Checks whitelist, blacklist, and Maps.
        Subdomain matching: if tracker.com is blocked, sub.tracker.com is also blocked.
        Priority hierarchy: user domain rules > app rules > category overrides >
        indexed feed categories > hardcoded essential/system/update presets.
        """
        if not domain:
            return False, ConnectionCategory.UNKNOWN
            
        domain = domain.lower()
        if domain.endswith('.'):
            domain = domain[:-1]

        # Fast-path category override lookup helper
        def _check_override(cat):
            ov = self.category_overrides.get(getattr(cat, 'value', str(cat)).lower())
            if ov == 'allow':
                return False, ConnectionCategory.USER_ALLOWED
            if ov == 'block':
                return True, ConnectionCategory.USER_BLOCKED
            return None

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
                    ov = _check_override(cat)
                    if ov is not None:
                        return ov
                    is_blk = cat not in (ConnectionCategory.ESSENTIAL, ConnectionCategory.SYSTEM, ConnectionCategory.UPDATE, ConnectionCategory.USER_ALLOWED)
                    return is_blk, cat

            # 3. Fallback checks for hardcoded sets
            for essential in ESSENTIAL_DOMAINS:
                if domain == essential or domain.endswith('.' + essential):
                    return False, ConnectionCategory.ESSENTIAL

            for sys_dom in SYSTEM_DOMAINS:
                if domain == sys_dom or domain.endswith('.' + sys_dom):
                    ov = _check_override(ConnectionCategory.SYSTEM)
                    if ov is not None:
                        return ov
                    return False, ConnectionCategory.SYSTEM

            for upd_dom in UPDATE_DOMAINS:
                if domain == upd_dom or domain.endswith('.' + upd_dom):
                    ov = _check_override(ConnectionCategory.UPDATE)
                    if ov is not None:
                        return ov
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
            self.app_neutral.clear()
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
                    elif action in ('neutral', 'none'):
                        self.app_neutral.add(app_name)
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
        Ultra-fast indexed category and domain search.
        Takes advantage of category_domains sets for O(1) instant slice access.
        """
        if not query and not category_filter:
            return []
            
        query = query.lower() if query else ""
        
        # Normalize category filter
        target_cat_enum: Optional[ConnectionCategory] = None
        if category_filter:
            if isinstance(category_filter, ConnectionCategory):
                target_cat_enum = category_filter
            else:
                cat_str = str(category_filter).lower()
                if cat_str in ('ad', 'ads'):
                    target_cat_enum = ConnectionCategory.AD
                elif cat_str in ('user_blocked', 'blocked'):
                    target_cat_enum = ConnectionCategory.USER_BLOCKED
                elif cat_str in ('user_allowed', 'allowed', 'whitelist'):
                    target_cat_enum = ConnectionCategory.USER_ALLOWED
                elif cat_str in ('tracker', 'trackers'):
                    target_cat_enum = ConnectionCategory.TRACKER
                else:
                    for cat in ConnectionCategory:
                        if cat.value.lower() == cat_str:
                            target_cat_enum = cat
                            break

        results = []
        seen = set()
        skipped = 0

        with self.lock:
            # 1. User Whitelist (Global Domains + App Rules)
            if not target_cat_enum or target_cat_enum == ConnectionCategory.USER_ALLOWED:
                for domain in (self.whitelist | self.app_whitelist):
                    if not query or query in domain:
                        if domain not in seen:
                            seen.add(domain)
                            if skipped < offset:
                                skipped += 1
                            else:
                                results.append({'domain': domain, 'category': ConnectionCategory.USER_ALLOWED.value})
                                if len(results) >= limit:
                                    return results

            # 2. User Blacklist (Global Domains + App Rules)
            if not target_cat_enum or target_cat_enum == ConnectionCategory.USER_BLOCKED:
                blocked_items = set(self.blacklist.keys()) | self.app_blacklist
                for domain in blocked_items:
                    if not query or query in domain:
                        if domain not in seen:
                            seen.add(domain)
                            if skipped < offset:
                                skipped += 1
                            else:
                                results.append({'domain': domain, 'category': ConnectionCategory.USER_BLOCKED.value})
                                if len(results) >= limit:
                                    return results

            # 3. If filtered by category, search ONLY that category set!
            if target_cat_enum:
                cat_set = self.category_domains.get(target_cat_enum)
                if cat_set is None:
                    for k, v in self.category_domains.items():
                        if getattr(k, 'value', str(k)) == target_cat_enum.value:
                            cat_set = v
                            break

                if cat_set:
                    for domain in cat_set:
                        if not query or query in domain:
                            if domain not in seen:
                                seen.add(domain)
                                if skipped < offset:
                                    skipped += 1
                                else:
                                    results.append({
                                        'domain': domain,
                                        'category': target_cat_enum.value
                                    })
                                    if len(results) >= limit:
                                        return results
                    return results

            # 4. If global search across all categories (query without category filter):
            for domain, category in self.domain_map.items():
                if query in domain:
                    if domain not in seen:
                        seen.add(domain)
                        if skipped < offset:
                            skipped += 1
                        else:
                            results.append({
                                'domain': domain,
                                'category': getattr(category, 'value', str(category))
                            })
                            if len(results) >= limit:
                                return results

        return results
