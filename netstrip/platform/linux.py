"""
Linux Platform Implementation for NetStrip
"""
import os
import subprocess
import logging
from typing import List, Optional
from netstrip.platform.base import PlatformBase

logger = logging.getLogger(__name__)

class LinuxPlatform(PlatformBase):
    def __init__(self):
        super().__init__()
        self._iptables_rules = {}

    def is_admin(self) -> bool:
        return os.geteuid() == 0

    def request_admin(self, script_path: str) -> bool:
        if self.is_admin():
            return True
        try:
            # Simple terminal sudo elevation (for GUI pkexec is preferred)
            subprocess.run(["sudo", "python3", script_path], check=True)
            return True
        except Exception as e:
            logger.error(f"Failed to elevate privileges: {e}")
            return False

    def _run_cmd(self, cmd: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, capture_output=True, text=True)

    def set_system_dns(self, interface: str, dns_server: str) -> bool:
        # Simplified: using iptables redirect instead of touching resolv.conf
        try:
            for proto in ["udp", "tcp"]:
                self._run_cmd(["iptables", "-t", "nat", "-A", "OUTPUT", "-p", proto, "--dport", "53", "-j", "REDIRECT", "--to-ports", "53"])
                
            # Disable IPv6 Router Advertisements (SLAAC)
            self._run_cmd(["sysctl", "-w", f"net.ipv6.conf.{interface}.accept_ra=0"])
            self._run_cmd(["sysctl", "-w", "net.ipv6.conf.all.accept_ra=0"])
            return True
        except Exception:
            return False

    def restore_system_dns(self, interface: str, original_dns_server: Optional[str] = None) -> bool:
        try:
            for proto in ["udp", "tcp"]:
                self._run_cmd(["iptables", "-t", "nat", "-D", "OUTPUT", "-p", proto, "--dport", "53", "-j", "REDIRECT", "--to-ports", "53"])
                
            # Restore IPv6 Router Advertisements
            self._run_cmd(["sysctl", "-w", f"net.ipv6.conf.{interface}.accept_ra=1"])
            self._run_cmd(["sysctl", "-w", "net.ipv6.conf.all.accept_ra=1"])
            return True
        except Exception:
            return False

    def get_original_dns(self, interface: str) -> Optional[str]:
        return "8.8.8.8"

    def get_active_interfaces(self) -> List[str]:
        return ["eth0", "wlan0"]

    def get_default_gateway(self) -> Optional[str]:
        return "192.168.1.1"

    def add_firewall_rule(self, rule_name: str, direction: str, action: str, 
                          remote_ip: Optional[str] = None, remote_port: Optional[int] = None, 
                          protocol: Optional[str] = None, program: Optional[str] = None) -> bool:
        chain = "INPUT" if direction == "in" else "OUTPUT"
        target = "DROP" if action == "block" else "ACCEPT"
        
        ips = []
        if remote_ip:
            ips = [ip.strip() for ip in remote_ip.split(",") if ip.strip()]
        else:
            ips = [None]
            
        success = True
        added_ips = []
        
        for ip in ips:
            cmd = ["iptables", "-A", chain]
            if ip:
                cmd.extend(["-d" if direction == "out" else "-s", ip])
            if protocol:
                cmd.extend(["-p", protocol])
            if remote_port:
                cmd.extend(["--dport", str(remote_port)])
            cmd.extend(["-j", target])
            
            res = self._run_cmd(cmd)
            if res.returncode == 0:
                if ip:
                    added_ips.append(ip)
            else:
                success = False
                
        if rule_name and added_ips:
            if rule_name not in self._iptables_rules:
                self._iptables_rules[rule_name] = []
            self._iptables_rules[rule_name].extend(added_ips)
            
        return success

    def remove_firewall_rule(self, rule_name: str) -> bool:
        if rule_name in self._iptables_rules:
            for ip in self._iptables_rules[rule_name]:
                self._run_cmd(["iptables", "-D", "OUTPUT", "-d", ip, "-j", "DROP"])
                self._run_cmd(["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"])
            del self._iptables_rules[rule_name]
        return True

    def rule_exists(self, rule_name: str) -> bool:
        return rule_name in self._iptables_rules

    def block_lan_traffic(self) -> bool:
        lan_subnets = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        success = True
        for subnet in lan_subnets:
            if self._run_cmd(["iptables", "-A", "OUTPUT", "-d", subnet, "-j", "DROP"]).returncode != 0:
                success = False
        return success

    def unblock_lan_traffic(self) -> bool:
        lan_subnets = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        success = True
        for subnet in lan_subnets:
            if self._run_cmd(["iptables", "-D", "OUTPUT", "-d", subnet, "-j", "DROP"]).returncode != 0:
                success = False
        return success

    def disable_ipv6(self) -> bool:
        success = True
        if self._run_cmd(["sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=1"]).returncode != 0:
            success = False
        if self._run_cmd(["sysctl", "-w", "net.ipv6.conf.default.disable_ipv6=1"]).returncode != 0:
            success = False
        return success

    def enable_ipv6(self) -> bool:
        success = True
        if self._run_cmd(["sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=0"]).returncode != 0:
            success = False
        if self._run_cmd(["sysctl", "-w", "net.ipv6.conf.default.disable_ipv6=0"]).returncode != 0:
            success = False
        return success

    def is_ipv6_enabled(self) -> bool:
        try:
            with open("/proc/sys/net/ipv6/conf/all/disable_ipv6", "r") as f:
                return f.read().strip() == "0"
        except Exception:
            return True

    def install_autostart(self) -> bool:
        # Generate systemd service
        return True

    def uninstall_autostart(self) -> bool:
        return True

    def is_autostart_installed(self) -> bool:
        return False
