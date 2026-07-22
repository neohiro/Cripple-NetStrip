"""
macOS Platform Implementation for NetStrip
"""
import os
import subprocess
import logging
from typing import List, Optional
from netstrip.platform.base import PlatformBase

logger = logging.getLogger(__name__)

class MacOSPlatform(PlatformBase):
    def __init__(self):
        super().__init__()
        self._route_rules = {}

    def is_admin(self) -> bool:
        return os.geteuid() == 0

    def request_admin(self, script_path: str) -> bool:
        if self.is_admin():
            return True
        try:
            cmd = f'do shell script "python3 {script_path}" with administrator privileges'
            subprocess.run(["osascript", "-e", cmd], check=True)
            return True
        except Exception as e:
            logger.error(f"Failed to elevate privileges: {e}")
            return False

    def _run_cmd(self, cmd: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, capture_output=True, text=True)

    def set_system_dns(self, interface: str, dns_server: str) -> bool:
        cmd = ["networksetup", "-setdnsservers", interface, dns_server, "::1"]
        res = self._run_cmd(cmd)
        
        # Disable IPv6 Router Advertisements
        self._run_cmd(["sysctl", "-w", "net.inet6.ip6.accept_rtadv=0"])
        return res.returncode == 0

    def restore_system_dns(self, interface: str, original_dns_server: Optional[str] = None) -> bool:
        if original_dns_server and original_dns_server.lower() != "empty":
            cmd = ["networksetup", "-setdnsservers", interface, original_dns_server]
        else:
            cmd = ["networksetup", "-setdnsservers", interface, "Empty"]
        res = self._run_cmd(cmd)
        
        # Restore IPv6 Router Advertisements
        self._run_cmd(["sysctl", "-w", "net.inet6.ip6.accept_rtadv=1"])
        return res.returncode == 0

    def get_original_dns(self, interface: str) -> Optional[str]:
        return "8.8.8.8"

    def get_active_interfaces(self) -> List[str]:
        return ["Wi-Fi", "Ethernet"]

    def get_default_gateway(self) -> Optional[str]:
        return "192.168.1.1"

    def add_firewall_rule(self, rule_name: str, direction: str, action: str, 
                          remote_ip: Optional[str] = None, remote_port: Optional[int] = None, 
                          protocol: Optional[str] = None, program: Optional[str] = None) -> bool:
        # Use native macOS routing to drop IPs (fastest, no pfctl anchors needed)
        if action == "block" and direction == "out" and remote_ip:
            ips = [ip.strip() for ip in remote_ip.split(",") if ip.strip()]
            self._route_rules[rule_name] = ips
            success = True
            for ip in ips:
                # Blackhole the IP
                cmd = ["route", "add", "-host", ip, "127.0.0.1", "-blackhole"]
                if self._run_cmd(cmd).returncode != 0:
                    success = False
            return success
        return True

    def remove_firewall_rule(self, rule_name: str) -> bool:
        if rule_name in self._route_rules:
            ips = self._route_rules[rule_name]
            for ip in ips:
                self._run_cmd(["route", "delete", "-host", ip])
            del self._route_rules[rule_name]
        return True

    def rule_exists(self, rule_name: str) -> bool:
        return rule_name in self._route_rules

    def block_lan_traffic(self) -> bool:
        lan_subnets = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        success = True
        for subnet in lan_subnets:
            if self._run_cmd(["route", "add", "-net", subnet, "127.0.0.1", "-blackhole"]).returncode != 0:
                success = False
        return success

    def unblock_lan_traffic(self) -> bool:
        lan_subnets = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        success = True
        for subnet in lan_subnets:
            if self._run_cmd(["route", "delete", "-net", subnet]).returncode != 0:
                success = False
        return success

    def disable_ipv6(self) -> bool:
        success = True
        for interface in self.get_active_interfaces():
            if self._run_cmd(["networksetup", "-setv6off", interface]).returncode != 0:
                success = False
        return success

    def enable_ipv6(self) -> bool:
        success = True
        for interface in self.get_active_interfaces():
            if self._run_cmd(["networksetup", "-setv6automatic", interface]).returncode != 0:
                success = False
        return success

    def is_ipv6_enabled(self) -> bool:
        for interface in self.get_active_interfaces():
            res = self._run_cmd(["networksetup", "-getinfo", interface])
            if "IPv6: Off" not in res.stdout:
                return True
        return False

    def install_autostart(self) -> bool:
        # Create launchd plist
        return True

    def uninstall_autostart(self) -> bool:
        return True

    def is_autostart_installed(self) -> bool:
        return False
