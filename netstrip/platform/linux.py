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
        res = self._run_cmd(["ip", "route", "show", "default"])
        if res.stdout:
            parts = res.stdout.split()
            if len(parts) >= 3:
                return parts[2]
        return None

    def get_current_ssid(self) -> str:
        # Simplistic default for Linux (can be expanded with iwgetid)
        return ""

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

    def enable_killswitch(self) -> bool:
        # Absolute ghost mode - block everything unconditionally
        res1 = self._run_cmd(["iptables", "-I", "INPUT", "1", "-j", "DROP"]).returncode == 0
        res2 = self._run_cmd(["iptables", "-I", "OUTPUT", "1", "-j", "DROP"]).returncode == 0
        res3 = self._run_cmd(["ip6tables", "-I", "INPUT", "1", "-j", "DROP"]).returncode == 0
        res4 = self._run_cmd(["ip6tables", "-I", "OUTPUT", "1", "-j", "DROP"]).returncode == 0
        return res1 and res2

    def disable_killswitch(self) -> bool:
        res1 = self._run_cmd(["iptables", "-D", "INPUT", "-j", "DROP"]).returncode == 0
        res2 = self._run_cmd(["iptables", "-D", "OUTPUT", "-j", "DROP"]).returncode == 0
        res3 = self._run_cmd(["ip6tables", "-D", "INPUT", "-j", "DROP"]).returncode == 0
        res4 = self._run_cmd(["ip6tables", "-D", "OUTPUT", "-j", "DROP"]).returncode == 0
        return res1 and res2

    def block_lan_traffic(self) -> bool:
        lan_subnets = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        success = True
        for subnet in lan_subnets:
            if self._run_cmd(["iptables", "-A", "OUTPUT", "-d", subnet, "-j", "DROP"]).returncode != 0:
                success = False
        return success

    def unblock_lan_traffic(self) -> bool:
        success = True
        subnets = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        for subnet in subnets:
            if self._run_cmd(["iptables", "-D", "OUTPUT", "-d", subnet, "-j", "DROP"]).returncode != 0:
                success = False
            if self._run_cmd(["iptables", "-D", "INPUT", "-s", subnet, "-j", "DROP"]).returncode != 0:
                success = False
        return success

    def lockdown_arp(self, ip: str, mac: str) -> bool:
        res = self._run_cmd(["arp", "-s", ip, mac])
        return res.returncode == 0
        
    def unlock_arp(self, ip: str) -> bool:
        res = self._run_cmd(["arp", "-d", ip])
        return res.returncode == 0

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
        if not self.is_admin():
            logger.error("Root privileges required to install systemd service.")
            return False
            
        import sys
        import os
        exe_path = os.path.abspath(sys.argv[0])
        service_path = "/etc/systemd/system/netstrip.service"
        
        service_content = f"""[Unit]
Description=Cripple NetStrip Daemon
After=network.target

[Service]
Type=simple
ExecStart={exe_path}
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
"""
        try:
            with open(service_path, "w") as f:
                f.write(service_content)
            self._run_cmd(["systemctl", "daemon-reload"])
            self._run_cmd(["systemctl", "enable", "netstrip.service"])
            logger.info("systemd service installed and enabled.")
            return True
        except Exception as e:
            logger.error(f"Failed to install systemd service: {e}")
            return False

    def uninstall_autostart(self) -> bool:
        if not self.is_admin():
            logger.error("Root privileges required to uninstall systemd service.")
            return False
            
        service_path = "/etc/systemd/system/netstrip.service"
        try:
            self._run_cmd(["systemctl", "disable", "netstrip.service"])
            if os.path.exists(service_path):
                os.remove(service_path)
            self._run_cmd(["systemctl", "daemon-reload"])
            logger.info("systemd service uninstalled.")
            return True
        except Exception as e:
            logger.error(f"Failed to uninstall systemd service: {e}")
            return False

    def is_autostart_installed(self) -> bool:
        import os
        return os.path.exists("/etc/systemd/system/netstrip.service")
