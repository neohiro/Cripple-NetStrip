"""
Classifier Engine for NetStrip
Decides the category of a domain or IP based purely on the blocklist manager and modes.
"""

from typing import Tuple, Optional
import threading
import platform
from cachetools import LRUCache
from netstrip.core.modes import ConnectionCategory, ConnectionAction, ModeConfig, ProtectionLevel, get_mode
from netstrip.data.blocklist_manager import BlocklistManager

# Pre-computed constant sets for O(1) process classification
_SYSTEM_PROCESSES = frozenset({
    # Windows Core & System Subsystems
    'svchost', 'explorer', 'searchapp', 'system', 'lsass', 'services',
    'spoolsv', 'wermgr', 'taskhostw', 'smss', 'csrss', 'wininit',
    'winlogon', 'fontdrvhost', 'dwm', 'sihost', 'ctfmon', 'taskmgr',
    'dllhost', 'conhost', 'runtimebroker', 'applicationframehost',
    'systemsettings', 'securityhealthsystray', 'sgrmbroker',
    'wuauserv', 'mousocoreworker', 'usoclient', 'trustedinstaller',
    'tiworker', 'sedlauncher', 'remsh', 'waasmedicagent',
    'compattelrunner', 'devicecensus', 'invagent', 'diagtrack',
    'device-census', 'wsappx', 'appinstaller', 'winstore.app',
    'microsoft.photos', 'yourphone', 'phoneexperiencehost', 'searchhost',
    'shellexperiencehost', 'gamebar', 'gamebarftserver', 'xboxpcapp',
    'xboxpcappft', 'feedsinfobar', 'widgets', 'copilot', 'onedrive',
    'onedrivestandaloneupdater', 'settingsynchost', 'searchindexer',
    'searchprotocolhost', 'searchfilterhost', 'installagent',
    'lsaiso', 'secure system', 'registry', 'memory compression',
    'ntoskrnl', 'winrsphost', 'winrshost', 'msedgeupdate', 'microsoftedgeupdate',
    'upfc', 'wmiapsrv', 'vssvc', 'useroobebroker', 'lockapp', 'logonui',
    'werfault', 'werfaultsecure', 'systemsettingsbroker', 'castsrv',
    'textinputhost', 'provtool', 'slui', 'system idle process',
    'system (kernel/driver)', 'backgroundtaskhost', 'startmenuexperiencehost',
    'widgetservice', 'wmiprvse', 'wlanext', 'audiodg', 'dashost', 'sppsvc',
    'backgroundtransferhost',
    
    # Linux System Daemons
    'systemd-resolved', 'systemd-timesyncd', 'networkmanager', 'dhclient', 'avahi-daemon', 'cupsd', 'packagekitd', 'snapd', 'fwupd',
    'chronyd', 'ntpd', 'dbus-daemon', 'rpcbind', 'systemd-networkd', 'unattended-upgrades', 'apt', 'dpkg', 'yum', 'dnf', 'zypper', 'pacman', 'dockerd', 'containerd', 'kubelet',
    
    # macOS Daemons & System
    'mdnsresponder', 'kernel_task', 'configd', 'syspolicyd', 'networkd', 'nsurlsessiond', 'apsd', 'softwareupdated', 'trustd', 'rapportd',
    'symptomsd', 'rtcreportingd', 'awdd', 'analyticsd', 'cloudd', 'touristd', 'locationd', 'identityservicesd', 'securityd', 'cfprefsd',
    'tcc', 'corelocationagent', 'crashreporter', 'submitdiaginfo', 'com.apple.geod'
})

_AV_PROCESSES = frozenset({
    # Kaspersky
    'avp', 'avpui', 'kavfs',
    # BitDefender
    'bdservicehost', 'bdagent', 'vsserv', 'bdredline',
    # AVG / Avast
    'avgui', 'avgsvc', 'avastui', 'avastsvc',
    # McAfee
    'mcshield', 'mfevtps', 'mcods', 'mfefire',
    # Norton / Symantec
    'nortonsecurity', 'ccsvchst', 'symcorpui',
    # Malwarebytes
    'mbamservice', 'mbamtray', 'mbam',
    # ESET
    'egui', 'ekrn',
    # Sophos
    'savservice', 'sophosui', 'sedservice',
    # Windows Defender & Security
    'msmpeng', 'nissrv', 'smartscreen', 'securityhealthservice'
})

_DNS_PROXY_PROCESSES = frozenset({'dns', 'unknown (dns)'})

_IDENTITY_OS_MAP = {
    'microsoft': 'windows',
    'apple': 'darwin',
    'canonical': 'linux', 'ubuntu': 'linux', 'redhat': 'linux', 
    'suse': 'linux', 'debian': 'linux', 'fedora': 'linux',
}

# IPv6 LAN ranges for classification
_IPV6_LAN_PREFIXES = (
    'fc', 'fd',      # ULA (Unique Local Addresses) fc00::/7
    'fe80',          # Link-local fe80::/10
    'ff02',          # Multicast link-local
)

# Cache configuration
_MAX_CACHE_SIZE = 5000

class TrafficClassifier:
    def __init__(self, blocklist_manager: BlocklistManager, db=None, mode_level: ProtectionLevel = ProtectionLevel.NORMAL):
        self.blocklist = blocklist_manager
        self.db = db
        self.mode = get_mode(mode_level)
        # Thread-safe LRU caches - cachetools LRUCache is not thread-safe, so we wrap with lock
        self._domain_cache = LRUCache(maxsize=_MAX_CACHE_SIZE)
        self._ip_cache = LRUCache(maxsize=_MAX_CACHE_SIZE)
        self.lock = threading.Lock()

    def set_mode(self, level: ProtectionLevel):
        with self.lock:
            self.mode = get_mode(level)
            self._domain_cache.clear()
            self._ip_cache.clear()

    def classify_domain(self, domain: str, process_name: Optional[str] = None) -> ConnectionCategory:
        """Classify a domain into a ConnectionCategory."""
        if not domain or not isinstance(domain, str):
            return ConnectionCategory.UNKNOWN
            
        cache_key = (domain, process_name)
        
        # Fast path: check cache with lock (LRUCache is not thread-safe)
        with self.lock:
            cached = self._domain_cache.get(cache_key)
            if cached is not None:
                return cached
            
            # Check loopback specifically (local DNS resolvers)
            if domain.startswith("127.") or domain == "::1":
                return self._domain_cache.setdefault(cache_key, ConnectionCategory.ESSENTIAL)

            # If the target is actually an IP and it's a LAN IP, prioritize LAN classification
            if self._is_lan_ip(domain):
                return self._domain_cache.setdefault(cache_key, ConnectionCategory.LAN)

        # Check blocklist manager (whitelist, blacklist, trie, and fallback domain sets)
        # No lock held during blocklist lookup (may be slow)
        is_blocked, category = self.blocklist.is_blocked(domain, process_name)
        if category and category != ConnectionCategory.UNKNOWN:
            with self.lock:
                return self._domain_cache.setdefault(cache_key, category)

        if process_name:
            p_lower = process_name.lower()
            p_base = p_lower.replace('.exe', '')
            
            # Check system process prefixes first (faster than set lookup for prefixes)
            if p_base in _SYSTEM_PROCESSES or p_base.startswith('service host (') or p_base.startswith('svchost ('):
                with self.lock:
                    return self._domain_cache.setdefault(cache_key, ConnectionCategory.SYSTEM)
            if p_base in _AV_PROCESSES:
                with self.lock:
                    return self._domain_cache.setdefault(cache_key, ConnectionCategory.SECURITY)
                
            # If the PID could not be inferred (it's just a DNS query proxy request), 
            # we check the identity to label OS-level connections appropriately.
            if p_lower in _DNS_PROXY_PROCESSES:
                identity = self.blocklist.get_identity(domain)
                if identity:
                    current_os = platform.system().lower()
                    identity_lower = identity.lower()
                    expected_os = _IDENTITY_OS_MAP.get(identity_lower)
                    if expected_os:
                        result = ConnectionCategory.SYSTEM if current_os == expected_os else ConnectionCategory.TELEMETRY
                        with self.lock:
                            return self._domain_cache.setdefault(cache_key, result)

        with self.lock:
            return self._domain_cache.setdefault(cache_key, ConnectionCategory.UNKNOWN)

    def classify_ip(self, ip: str, port: int = 0, process_name: str = "Unknown") -> tuple:
        """Classify an IP address and return (category, action)."""
        if not ip or not isinstance(ip, str):
            return ConnectionCategory.UNKNOWN, ConnectionAction.ALLOW
            
        cache_key = (ip, port, process_name)
        
        # Fast path: check cache with lock
        with self.lock:
            cached = self._ip_cache.get(cache_key)
            if cached is not None:
                return cached
            
            if self._is_lan_ip(ip):
                cat = ConnectionCategory.LAN
                action = self.mode.get_action_for_category(cat, self.db)
                return self._ip_cache.setdefault(cache_key, (cat, action))
        
        # Try to resolve IP to domain using our DNS cache
        # Note: This is a sync DB call - consider caching DNS lookups separately for hot path
        domain = None
        if self.db:
            try:
                row = self.db._get_connection().execute("SELECT domain FROM dns_cache WHERE ip = ?", (ip,)).fetchone()
                if row:
                    domain = row['domain']
            except Exception:
                pass  # Log at debug level if needed
                
        target_to_classify = domain if domain else ip
        cat = self.classify_domain(target_to_classify, process_name)
            
        action = self.mode.get_action_for_category(cat, self.db)
        
        with self.lock:
            return self._ip_cache.setdefault(cache_key, (cat, action))

    def _is_lan_ip(self, ip: str) -> bool:
        if not ip:
            return False
        # IPv4 private ranges
        if ip.startswith("10.") or ip.startswith("192.168."):
            return True
        if ip.startswith("172."):
            parts = ip.split('.')
            if len(parts) == 4 and parts[1].isdigit():
                if 16 <= int(parts[1]) <= 31:
                    return True
        if ip.startswith("169.254."):  # Link-local
            return True
        if ip.startswith("100."):  # CGNAT 100.64.0.0/10
            parts = ip.split('.')
            if len(parts) == 4 and parts[1].isdigit():
                if 64 <= int(parts[1]) <= 127:
                    return True
        # IPv6 private/link-local ranges
        ip_lower = ip.lower()
        if any(ip_lower.startswith(p) for p in _IPV6_LAN_PREFIXES):
            return True
        return False
