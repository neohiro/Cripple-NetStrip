"""
Platform Abstraction Layer for NetStrip
Provides a unified interface for OS-specific tasks like modifying DNS,
firewall rules, and checking administrative privileges.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import platform

class PlatformBase(ABC):
    
    @abstractmethod
    def is_admin(self) -> bool:
        """Check if running with administrative privileges."""
        pass

    @abstractmethod
    def request_admin(self, script_path: str) -> bool:
        """Relaunch the script with elevated privileges."""
        pass

    @abstractmethod
    def set_system_dns(self, interface: str, dns_server: str) -> bool:
        """Set the system DNS for an interface to our proxy."""
        pass

    @abstractmethod
    def restore_system_dns(self, interface: str, original_dns_server: Optional[str] = None) -> bool:
        """Restore original DNS for the interface."""
        pass

    @abstractmethod
    def get_original_dns(self, interface: str) -> Optional[str]:
        """Get the current original DNS settings for an interface."""
        pass

    @abstractmethod
    def get_active_interfaces(self) -> List[str]:
        """List active network interfaces."""
        pass

    @abstractmethod
    def get_default_gateway(self) -> Optional[str]:
        """Get the default gateway IP."""
        pass

    @abstractmethod
    def add_firewall_rule(self, rule_name: str, direction: str, action: str, 
                          remote_ip: Optional[str] = None, 
                          remote_port: Optional[int] = None, 
                          protocol: Optional[str] = None, 
                          program: Optional[str] = None) -> bool:
        """Add a firewall rule."""
        pass

    @abstractmethod
    def remove_firewall_rule(self, rule_name: str) -> bool:
        """Remove a firewall rule by name."""
        pass

    @abstractmethod
    def rule_exists(self, rule_name: str) -> bool:
        """Check if a firewall rule exists."""
        pass

    @abstractmethod
    def remove_all_NetStrip_rules(self) -> bool:
        """Remove all firewall rules created by NetStrip (starts with NetStrip_)."""
        pass

    @abstractmethod
    def remove_all_app_block_rules(self) -> bool:
        """Remove all app-specific firewall block rules created by NetStrip."""
        pass

    def block_ip(self, ip: str, rule_name: str = None) -> bool:
        """Convenience method to block an IP both in and out."""
        if not rule_name:
            rule_name = f"NetStrip_Block_{ip}"
        success_in = self.add_firewall_rule(f"{rule_name}_IN", "in", "block", remote_ip=ip)
        success_out = self.add_firewall_rule(f"{rule_name}_OUT", "out", "block", remote_ip=ip)
        return success_in and success_out

    def unblock_ip(self, ip: str, rule_name: str = None) -> bool:
        """Convenience method to unblock an IP."""
        if not rule_name:
            rule_name = f"NetStrip_Block_{ip}"
        success_in = self.remove_firewall_rule(f"{rule_name}_IN")
        success_out = self.remove_firewall_rule(f"{rule_name}_OUT")
        return success_in and success_out

    @abstractmethod
    def block_lan_traffic(self) -> bool:
        """Block all private IP ranges."""
        pass

    @abstractmethod
    def unblock_lan_traffic(self) -> bool:
        """Unblock all private IP ranges."""
        pass

    @abstractmethod
    def enable_killswitch(self) -> bool:
        """Completely sever OS connection to the internet while preserving local loopback."""
        pass

    @abstractmethod
    def disable_killswitch(self) -> bool:
        """Restore OS connection to the internet."""
        pass
        
    @abstractmethod
    def disable_ipv6(self) -> bool:
        """Disable IPv6 globally on the system."""
        pass
        
    @abstractmethod
    def enable_ipv6(self) -> bool:
        """Enable IPv6 globally on the system."""
        pass
        
    @abstractmethod
    def is_ipv6_enabled(self) -> bool:
        """Check if IPv6 is globally enabled on the system."""
        pass

    @abstractmethod
    def install_autostart(self) -> bool:
        """Register as a system startup service."""
        pass

    @abstractmethod
    def uninstall_autostart(self) -> bool:
        """Unregister system startup service."""
        pass

    @abstractmethod
    def is_autostart_installed(self) -> bool:
        """Check if registered for autostart."""
        pass


def get_platform() -> PlatformBase:
    """Factory function to get the correct platform implementation."""
    system = platform.system()
    if system == "Windows":
        from netstrip.platform.windows import WindowsPlatform
        return WindowsPlatform()
    elif system == "Linux":
        from netstrip.platform.linux import LinuxPlatform
        return LinuxPlatform()
    elif system == "Darwin":
        from netstrip.platform.macos import MacOSPlatform
        return MacOSPlatform()
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")
