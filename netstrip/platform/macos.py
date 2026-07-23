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
        return rule_name in self._pf_rules

    def enable_killswitch(self) -> bool:
        # Absolute ghost mode for macOS using pfctl
        # -e enables pf, -q suppresses output
        # echo "block drop all" | pfctl -a com.netstrip.killswitch -f -
        cmd = ["pfctl", "-a", "com.netstrip.killswitch", "-f", "-"]
        try:
            import subprocess
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            proc.communicate(input=b"block drop all\n")
            self._run_cmd(["pfctl", "-E"]) # Ensure PF is enabled
            return proc.returncode == 0
        except Exception:
            return False

    def disable_killswitch(self) -> bool:
        return self._run_cmd(["pfctl", "-a", "com.netstrip.killswitch", "-F", "rules"]).returncode == 0

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

    def lockdown_arp(self, ip: str, mac: str) -> bool:
        res = self._run_cmd(["arp", "-s", ip, mac])
        return res.returncode == 0
        
    def unlock_arp(self, ip: str) -> bool:
        res = self._run_cmd(["arp", "-d", ip])
        return res.returncode == 0

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
        res = self._run_cmd(["networksetup", "-getinfo", "Wi-Fi"])
        return "IPv6: Automatic" in res.stdout
        
    def disable_ipv4(self) -> bool:
        return False # Experimental
        
    def enable_ipv4(self) -> bool:
        return True
        
    def is_ipv4_enabled(self) -> bool:
        return True

    def install_autostart(self) -> bool:
        if not self.is_admin():
            logger.error("Root privileges required to install launchd daemon.")
            return False
            
        import sys
        import os
        exe_path = os.path.abspath(sys.argv[0])
        plist_path = "/Library/LaunchDaemons/com.netstrip.daemon.plist"
        
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.netstrip.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/netstrip.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/netstrip_err.log</string>
</dict>
</plist>
"""
        try:
            with open(plist_path, "w") as f:
                f.write(plist_content)
            # Fix permissions
            self._run_cmd(["chown", "root:wheel", plist_path])
            self._run_cmd(["chmod", "644", plist_path])
            # Load the daemon
            self._run_cmd(["launchctl", "load", "-w", plist_path])
            logger.info("launchd daemon installed and loaded.")
            return True
        except Exception as e:
            logger.error(f"Failed to install launchd daemon: {e}")
            return False

    def uninstall_autostart(self) -> bool:
        if not self.is_admin():
            logger.error("Root privileges required to uninstall launchd daemon.")
            return False
            
        plist_path = "/Library/LaunchDaemons/com.netstrip.daemon.plist"
        try:
            if os.path.exists(plist_path):
                self._run_cmd(["launchctl", "unload", "-w", plist_path])
                os.remove(plist_path)
            logger.info("launchd daemon uninstalled.")
            return True
        except Exception as e:
            logger.error(f"Failed to uninstall launchd daemon: {e}")
            return False

    def is_autostart_installed(self) -> bool:
        import os
        return os.path.exists("/Library/LaunchDaemons/com.netstrip.daemon.plist")
