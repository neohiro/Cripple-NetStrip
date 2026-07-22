"""
Firewall Controller for NetStrip
Wraps the platform-specific firewall implementations to provide a high-level API for the engine.
"""

import logging
from typing import List, Optional
from netstrip.platform.base import get_platform

logger = logging.getLogger(__name__)

class FirewallController:
    def __init__(self):
        self.platform = get_platform()
        self.active_rules = set()

    def block_ip(self, ip: str, rule_name: Optional[str] = None) -> bool:
        """Block an IP address completely (inbound and outbound)."""
        name = rule_name or f"NetStrip_Block_{ip}"
        success = self.platform.block_ip(ip, name)
        if success:
            self.active_rules.add(name)
        return success

    def unblock_ip(self, ip: str, rule_name: Optional[str] = None) -> bool:
        """Unblock an IP address."""
        name = rule_name or f"NetStrip_Block_{ip}"
        success = self.platform.unblock_ip(ip, name)
        if success and name in self.active_rules:
            self.active_rules.remove(name)
        return success

    def allow_process(self, process_path: str, rule_name: Optional[str] = None) -> bool:
        """Allow a specific executable full network access (Windows specific mostly)."""
        name = rule_name or f"NetStrip_Allow_{process_path.replace('\\', '_').replace('/', '_')}"
        success_out = self.platform.add_firewall_rule(f"{name}_OUT", "out", "allow", program=process_path)
        success_in = self.platform.add_firewall_rule(f"{name}_IN", "in", "allow", program=process_path)
        
        if success_out and success_in:
            self.active_rules.add(name)
            return True
        return False

    def block_process(self, process_path: str, rule_name: Optional[str] = None) -> bool:
        """Block a specific executable from network access."""
        name = rule_name or f"NetStrip_Block_{process_path.replace('\\', '_').replace('/', '_')}"
        success_out = self.platform.add_firewall_rule(f"{name}_OUT", "out", "block", program=process_path)
        success_in = self.platform.add_firewall_rule(f"{name}_IN", "in", "block", program=process_path)
        
        if success_out and success_in:
            self.active_rules.add(name)
            return True
        return False

    def clear_all_rules(self) -> bool:
        """Remove all rules created by NetStrip."""
        success = self.platform.remove_all_NetStrip_rules()
        if success:
            self.active_rules.clear()
        
        # Ensure LAN block is removed
        self.platform.unblock_lan_traffic()
        return success

    def apply_paranoid_mode(self):
        """Apply strict firewall rules for Paranoid mode."""
        # Conceptually: block everything outbound by default, only allow explicitly whitelisted.
        # This is complex to implement correctly without breaking the system.
        # For prototype, we rely on DNS proxy blocking + IP blocking.
        pass

    def sync_ip_blocklist(self, ip_list: List[str], rule_name: str = "NetStrip_Malware_Block") -> bool:
        """Injects a batch of high-risk IP addresses directly into the Windows OS firewall."""
        if not ip_list:
            return True
            
        # Remove any existing rule with this name first
        self.platform.remove_firewall_rule(rule_name)
        
        # Windows firewall remoteip accepts comma separated lists. Max length is theoretically 32KB.
        # Chunking into 1000 IPs at a time to be safe.
        chunk_size = 500
        success_all = True
        
        for i in range(0, len(ip_list), chunk_size):
            chunk = ip_list[i:i + chunk_size]
            ip_str = ",".join(chunk)
            chunk_name = f"{rule_name}_{i // chunk_size}"
            success = self.platform.add_firewall_rule(chunk_name, "out", "block", remote_ip=ip_str)
            if success:
                self.active_rules.add(chunk_name)
            else:
                success_all = False
                
        return success_all
