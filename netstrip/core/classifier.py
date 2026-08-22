"""
Classifier Engine for NetStrip
Decides the category of a domain or IP based purely on the blocklist manager and modes.
"""

from typing import Optional
from netstrip.core.modes import ConnectionCategory, ProtectionLevel, get_mode
from netstrip.data.blocklist_manager import BlocklistManager

class TrafficClassifier:
    def __init__(self, blocklist_manager: BlocklistManager, db=None, mode_level: ProtectionLevel = ProtectionLevel.NORMAL):
        self.blocklist = blocklist_manager
        self.db = db
        self.mode = get_mode(mode_level)
        self._domain_cache = {}

    def set_mode(self, level: ProtectionLevel):
        self.mode = get_mode(level)
        self._domain_cache.clear()
        if hasattr(self, '_ip_cache'):
            self._ip_cache.clear()

    def classify_domain(self, domain: str, process_name: Optional[str] = None) -> ConnectionCategory:
        """Classify a domain into a ConnectionCategory."""
        if not domain:
            return ConnectionCategory.UNKNOWN
            
        cache_key = (domain, process_name)
        if cache_key in self._domain_cache:
            return self._domain_cache[cache_key]
            
        if len(self._domain_cache) > 5000:
            self._domain_cache.clear()
            
        # Check loopback specifically (local DNS resolvers)
        if domain.startswith("127.") or domain == "::1":
            self._domain_cache[cache_key] = ConnectionCategory.ESSENTIAL
            return ConnectionCategory.ESSENTIAL

        # If the target is actually an IP and it's a LAN IP, prioritize LAN classification
        if self._is_lan_ip(domain):
            self._domain_cache[cache_key] = ConnectionCategory.LAN
            return ConnectionCategory.LAN

        # Check blocklist manager (whitelist, blacklist, trie, and fallback domain sets)
        is_blocked, category = self.blocklist.is_blocked(domain, process_name)
        if category and category != ConnectionCategory.UNKNOWN:
            self._domain_cache[cache_key] = category
            return category

        if process_name:
            p_lower = process_name.lower()
            # Shared comprehensive cross-OS system process identification
            # (Windows / Linux / macOS / Android) from process_utils.
            from netstrip.core.process_utils import is_system_process
            
            av_processes = {
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
            }
            
            p_base = p_lower.replace('.exe', '')
            if is_system_process(p_base) or p_base.startswith('service host (') or p_base.startswith('svchost ('):
                self._domain_cache[cache_key] = ConnectionCategory.SYSTEM
                return ConnectionCategory.SYSTEM
            if p_base in av_processes:
                self._domain_cache[cache_key] = ConnectionCategory.SECURITY
                return ConnectionCategory.SECURITY
                
            # If the PID could not be inferred (it's just a DNS query proxy request), 
            # we check the identity to label OS-level connections appropriately.
            if p_lower in ('dns', 'unknown (dns)'):
                identity = self.blocklist.get_identity(domain)
                if identity:
                    import platform
                    current_os = platform.system().lower()
                    identity_lower = identity.lower()
                    
                    if identity_lower == 'microsoft':
                        if current_os == 'windows':
                            self._domain_cache[cache_key] = ConnectionCategory.SYSTEM
                            return ConnectionCategory.SYSTEM
                        else:
                            self._domain_cache[cache_key] = ConnectionCategory.TELEMETRY
                            return ConnectionCategory.TELEMETRY
                            
                    elif identity_lower == 'apple':
                        if current_os == 'darwin':
                            self._domain_cache[cache_key] = ConnectionCategory.SYSTEM
                            return ConnectionCategory.SYSTEM
                        else:
                            self._domain_cache[cache_key] = ConnectionCategory.TELEMETRY
                            return ConnectionCategory.TELEMETRY
                            
                    elif identity_lower in ('canonical', 'ubuntu', 'redhat', 'suse', 'debian', 'fedora'):
                        if current_os == 'linux':
                            self._domain_cache[cache_key] = ConnectionCategory.SYSTEM
                            return ConnectionCategory.SYSTEM
                        else:
                            self._domain_cache[cache_key] = ConnectionCategory.TELEMETRY
                            return ConnectionCategory.TELEMETRY

        self._domain_cache[cache_key] = ConnectionCategory.UNKNOWN
        return ConnectionCategory.UNKNOWN

    def classify_ip(self, ip: str, port: int = 0, process_name: str = "Unknown") -> tuple:
        """Classify an IP address and return (category, action)."""
        cache_key = (ip, port, process_name)
        if not hasattr(self, '_ip_cache'):
            self._ip_cache = {}
            
        if cache_key in self._ip_cache:
            return self._ip_cache[cache_key]
            
        if len(self._ip_cache) > 5000:
            self._ip_cache.clear()
            
        if self._is_lan_ip(ip):
            cat = ConnectionCategory.LAN
            action = self.mode.get_action_for_category(cat, self.db)
            self._ip_cache[cache_key] = (cat, action)
            return cat, action
            
        # Try to resolve IP to domain using our DNS cache
        domain = None
        if self.db:
            try:
                row = self.db._get_connection().execute("SELECT domain FROM dns_cache WHERE ip = ?", (ip,)).fetchone()
                if row:
                    domain = row['domain']
            except Exception:
                pass
                
        target_to_classify = domain if domain else ip
        cat = self.classify_domain(target_to_classify, process_name)
            
        action = self.mode.get_action_for_category(cat, self.db)
        
        self._ip_cache[cache_key] = (cat, action)
        return cat, action

    def _is_lan_ip(self, ip: str) -> bool:
        if not ip:
            return False
        # Simplified check for private IPs
        if ip.startswith("10.") or ip.startswith("192.168."):
            return True
        if ip.startswith("172."):
            parts = ip.split('.')
            if len(parts) == 4 and parts[1].isdigit():
                if 16 <= int(parts[1]) <= 31:
                    return True
        if ip.startswith("169.254."):
            return True
        if ip.startswith("100."): # CGNAT 100.64.0.0/10
            parts = ip.split('.')
            if len(parts) == 4 and parts[1].isdigit():
                if 64 <= int(parts[1]) <= 127:
                    return True
        ip_lower = ip.lower()
        if ip_lower.startswith("fc") or ip_lower.startswith("fd"): # IPv6 ULA
            return True
        if ip_lower.startswith("fe80:"): # IPv6 link-local
            return True
        return False

