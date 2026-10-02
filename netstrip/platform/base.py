"""
Platform Abstraction Layer for NetStrip
Provides a unified interface for OS-specific tasks like modifying DNS,
firewall rules, and checking administrative privileges.
"""

import platform
from abc import ABC, abstractmethod


class PlatformBase(ABC):
    @abstractmethod
    def is_admin(self) -> bool:
        """Check if running with administrative privileges."""

    @abstractmethod
    def request_admin(self, script_path: str) -> bool:
        """Relaunch the script with elevated privileges."""

    @abstractmethod
    def set_system_dns(self, interface: str, dns_server: str) -> bool:
        """Set the system DNS for an interface to our proxy."""

    @abstractmethod
    def restore_system_dns(self, interface: str, original_dns_server: str | None = None) -> bool:
        """Restore original DNS for the interface."""

    @abstractmethod
    def get_original_dns(self, interface: str) -> str | None:
        """Get the current original DNS settings for an interface."""

    @abstractmethod
    def get_active_interfaces(self) -> list[str]:
        """List active network interfaces."""

    @abstractmethod
    def get_default_gateway(self) -> str | None:
        """Get the default gateway IP."""

    @abstractmethod
    def get_current_ssid(self) -> str:
        """Get the current WiFi SSID, if applicable and available."""

    @abstractmethod
    def add_firewall_rule(
        self,
        rule_name: str,
        direction: str,
        action: str,
        remote_ip: str | None = None,
        remote_port: int | None = None,
        protocol: str | None = None,
        program: str | None = None,
    ) -> bool:
        """Add a firewall rule."""

    @abstractmethod
    def remove_firewall_rule(self, rule_name: str) -> bool:
        """Remove a firewall rule by name."""

    @abstractmethod
    def rule_exists(self, rule_name: str) -> bool:
        """Check if a firewall rule exists."""

    @abstractmethod
    def remove_all_NetStrip_rules(self) -> bool:
        """Remove all firewall rules created by NetStrip (starts with NetStrip_)."""

    @abstractmethod
    def remove_all_app_block_rules(self) -> bool:
        """Remove all app-specific firewall block rules created by NetStrip."""

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

    @abstractmethod
    def unblock_lan_traffic(self) -> bool:
        """Unblock all private IP ranges."""

    def kill_tcp_connections(
        self, target_ip: str | None = None, target_process_path: str | None = None
    ) -> None:
        """Forcefully terminate active TCP connections, optionally filtered by IP or process path."""

    def _get_target_connections(
        self, target_ip: str | None = None, target_process_path: str | None = None
    ) -> list:
        """Return a list of (local_ip, local_port, remote_ip, remote_port) for matching established TCP connections."""
        import psutil

        targets = []
        try:
            for conn in psutil.net_connections(kind="tcp"):
                if conn.status != "ESTABLISHED" or not conn.raddr or not conn.laddr:
                    continue

                match = False
                if target_ip and conn.raddr.ip == target_ip:
                    match = True
                elif target_process_path and conn.pid:
                    try:
                        p = psutil.Process(conn.pid)
                        if p.exe() and p.exe().lower() == target_process_path.lower():
                            match = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                elif not target_ip and not target_process_path:
                    match = True

                if match:
                    targets.append(
                        {
                            "l_ip": conn.laddr.ip,
                            "l_port": conn.laddr.port,
                            "r_ip": conn.raddr.ip,
                            "r_port": conn.raddr.port,
                        }
                    )
        except Exception:
            pass
        return targets

    @abstractmethod
    def enable_killswitch(self) -> bool:
        """Completely sever OS connection to the internet while preserving local loopback."""

    @abstractmethod
    def disable_killswitch(self) -> bool:
        """Restore OS connection to the internet."""

    @abstractmethod
    def disable_ipv6(self) -> bool:
        """Disable IPv6 globally on the system."""

    @abstractmethod
    def enable_ipv6(self) -> bool:
        """Enable IPv6 globally on the system."""

    @abstractmethod
    def is_ipv6_enabled(self) -> bool:
        """Check if IPv6 is globally enabled on the system."""

    @abstractmethod
    def disable_ipv4(self) -> bool:
        """Disable IPv4 globally on the system."""

    @abstractmethod
    def enable_ipv4(self) -> bool:
        """Enable IPv4 globally on the system."""

    @abstractmethod
    def is_ipv4_enabled(self) -> bool:
        """Check if IPv4 is globally enabled on the system."""

    @abstractmethod
    def install_autostart(self) -> bool:
        """Register as a system startup service."""

    @abstractmethod
    def uninstall_autostart(self) -> bool:
        """Unregister system startup service."""

    @abstractmethod
    def is_autostart_installed(self) -> bool:
        """Check if registered for autostart."""

    def harden_network_adapters(self, enable_hardening: bool = True) -> bool:
        """Harden adapter protocol bindings, WPAD, LLMNR, NetBIOS, and discovery."""
        if enable_hardening:
            return self.disable_protocol_bindings()
        return self.restore_protocol_bindings()

    @abstractmethod
    def disable_protocol_bindings(self) -> bool:
        """Disable redundant and privacy-sensitive adapter protocols (WPAD, LLDP, LLMNR, NetBIOS, SMB)."""

    @abstractmethod
    def restore_protocol_bindings(self) -> bool:
        """Restore standard adapter protocol bindings."""


def get_platform() -> PlatformBase:
    """Factory function to get the correct platform implementation."""
    import os
    import sys

    system = platform.system()

    # Check for Android via Chaquopy or buildozer
    if os.environ.get("NETSTRIP_ANDROID") == "1" or hasattr(sys, "getandroidapilevel"):
        from netstrip.platform.android import AndroidPlatform

        return AndroidPlatform()

    if system == "Windows":
        from netstrip.platform.windows import WindowsPlatform

        return WindowsPlatform()
    if system == "Linux":
        from netstrip.platform.linux import LinuxPlatform

        return LinuxPlatform()
    if system == "Darwin":
        from netstrip.platform.macos import MacOSPlatform

        return MacOSPlatform()
    raise NotImplementedError(f"Unsupported platform: {system}")
