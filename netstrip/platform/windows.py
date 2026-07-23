"""
Windows Platform Implementation for NetStrip
"""
import subprocess
import ctypes
import os
import sys
import logging
import re
from typing import List, Optional
from netstrip.platform.base import PlatformBase

logger = logging.getLogger(__name__)

class WindowsPlatform(PlatformBase):
    def is_admin(self) -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() == 1
        except Exception:
            return False

    def request_admin(self, script_path: str) -> bool:
        if self.is_admin():
            return True
        try:
            if getattr(sys, 'frozen', False):
                # If packaged by PyInstaller, sys.executable is the .exe
                import subprocess
                args_list = sys.argv[1:]
                if "--elevated" not in args_list:
                    args_list.append("--elevated")
                if "--parent-pid" not in args_list:
                    args_list.extend(["--parent-pid", str(os.getpid())])
                args = subprocess.list2cmdline(args_list)
                ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, None, 1)
            else:
                import subprocess
                args = subprocess.list2cmdline([script_path, "--elevated", "--parent-pid", str(os.getpid())])
                ret = ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, args, None, 1
                )
            return ret > 32
        except Exception as e:
            logger.error(f"Failed to elevate privileges: {e}")
            return False

    def _run_cmd(self, cmd: List[str]) -> subprocess.CompletedProcess:
        import subprocess
        return subprocess.run(
            cmd, 
            shell=False, 
            capture_output=True, 
            text=True, 
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    def set_system_dns(self, interface: str, dns_server: str) -> bool:
        try:
            # Provision a dedicated IPv6 ULA loopback address for NetStrip to avoid port conflicts with DNSCrypt/Torifier on ::1
            self._run_cmd(["netsh", "interface", "ipv6", "add", "address", "interface=1", "address=fd00::127"])
            
            cmd = ["netsh", "interface", "ipv4", "set", "dns", f'name="{interface}"', "static", dns_server]
            res = self._run_cmd(cmd)
            # Try setting IPv6 to our dedicated ULA loopback proxy
            cmd_v6 = ["netsh", "interface", "ipv6", "set", "dns", f'name="{interface}"', "static", "fd00::127"]
            self._run_cmd(cmd_v6)
            
            # Disable Router Advertisement (SLAAC) to prevent router from dynamically overriding our IPv6 DNS
            cmd_ra = ["netsh", "interface", "ipv6", "set", "interface", f'interface="{interface}"', "routerdiscovery=disabled"]
            self._run_cmd(cmd_ra)
            
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to set DNS: {e}")
            return False

    def restore_system_dns(self, interface: str, original_dns_server: Optional[str] = None) -> bool:
        try:
            if original_dns_server and re.match(r'^([0-9]{1,3}\.){3}[0-9]{1,3}$', original_dns_server):
                cmd = ["netsh", "interface", "ipv4", "set", "dns", f'name="{interface}"', "static", original_dns_server]
            else:
                cmd = ["netsh", "interface", "ipv4", "set", "dns", f'name="{interface}"', "dhcp"]
            res = self._run_cmd(cmd)
            
            # Always restore IPv6 to auto
            cmd_v6 = ["netsh", "interface", "ipv6", "set", "dns", f'name="{interface}"', "dhcp"]
            self._run_cmd(cmd_v6)
            
            # Re-enable Router Advertisement (SLAAC)
            cmd_ra = ["netsh", "interface", "ipv6", "set", "interface", f'interface="{interface}"', "routerdiscovery=enabled"]
            self._run_cmd(cmd_ra)
            
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to restore DNS: {e}")
            return False

    def get_original_dns(self, interface: str) -> Optional[str]:
        # Parse netsh interface ip show dns
        res = self._run_cmd(["netsh", "interface", "ip", "show", "dns", f'name="{interface}"'])
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line: continue
            if "Statically Configured DNS Servers" in line or "DNS servers configured through DHCP" in line:
                pass
            elif re.match(r'^([0-9]{1,3}\.){3}[0-9]{1,3}$', line):
                return line
            elif ":" in line and "Configuration" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    ip = parts[1].strip()
                    if re.match(r'^([0-9]{1,3}\.){3}[0-9]{1,3}$', ip):
                        return ip
        return None

    def get_active_interfaces(self) -> List[str]:
        interfaces = []
        res = self._run_cmd(["netsh", "interface", "show", "interface"])
        for line in res.stdout.splitlines():
            if "Connected" in line:
                parts = line.split()
                if len(parts) >= 4:
                    interfaces.append(" ".join(parts[3:]))
        return interfaces if interfaces else ["Wi-Fi", "Ethernet"]

    def get_default_gateway(self) -> Optional[str]:
        res = self._run_cmd(["netsh", "interface", "ip", "show", "config"])
        for line in res.stdout.splitlines():
            if "Default Gateway" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    ip = parts[1].strip()
                    if ip: return ip
        return None

    def add_firewall_rule(self, rule_name: str, direction: str, action: str, 
                          remote_ip: Optional[str] = None, remote_port: Optional[int] = None, 
                          protocol: Optional[str] = None, program: Optional[str] = None) -> bool:
        # Sanitize arguments against netsh parsing bypass
        rule_name = rule_name.replace('"', '')
        cmd = ["netsh", "advfirewall", "firewall", "add", "rule", f'name="{rule_name}"', f"dir={direction}", f"action={action}"]
        if remote_ip:
            cmd.append(f"remoteip={remote_ip}")
        if remote_port:
            cmd.append(f"remoteport={remote_port}")
        if protocol:
            cmd.append(f"protocol={protocol}")
        if program:
            program_sanitized = program.replace('"', '')
            cmd.append(f'program="{program_sanitized}"')
            
        res = self._run_cmd(cmd)
        return res.returncode == 0

    def remove_firewall_rule(self, rule_name: str) -> bool:
        cmd = ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"]
        res = self._run_cmd(cmd)
        return res.returncode == 0

    def rule_exists(self, rule_name: str) -> bool:
        cmd = ["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule_name}"]
        res = self._run_cmd(cmd)
        return "No rules match" not in res.stdout

    def remove_all_NetStrip_rules(self) -> bool:
        # Use PowerShell to safely remove all rules with the NetStrip_ prefix
        cmd = ["powershell", "-Command", "Remove-NetFirewallRule -DisplayName 'NetStrip_*' -ErrorAction SilentlyContinue"]
        res = self._run_cmd(cmd)
        return res.returncode == 0

    def remove_all_app_block_rules(self) -> bool:
        cmd = ["powershell", "-Command", "Remove-NetFirewallRule -DisplayName 'NetStrip_AppBlock_*' -ErrorAction SilentlyContinue"]
        res = self._run_cmd(cmd)
        return res.returncode == 0

    def block_lan_traffic(self) -> bool:
        return self.add_firewall_rule("NetStrip_Block_LAN", "out", "block", remote_ip="10.0.0.0-10.255.255.255,172.16.0.0-172.31.255.255,192.168.0.0-192.168.255.255")

    def unblock_lan_traffic(self) -> bool:
        return self.remove_firewall_rule("NetStrip_Block_LAN")

    def enable_killswitch(self) -> bool:
        # Instead of modifying the OS default policy (which ruins user setups), we inject a master block rule
        res1 = self.add_firewall_rule("NetStrip_Killswitch_Block_In", "in", "block")
        res2 = self.add_firewall_rule("NetStrip_Killswitch_Block_Out", "out", "block")
        # Allow loopback so NetStrip internal IPC doesn't break
        res3 = self.add_firewall_rule("NetStrip_Killswitch_Loopback_In", "in", "allow", remote_ip="127.0.0.1")
        res4 = self.add_firewall_rule("NetStrip_Killswitch_Loopback_Out", "out", "allow", remote_ip="127.0.0.1")
        return res1 and res2

    def disable_killswitch(self) -> bool:
        res1 = self.remove_firewall_rule("NetStrip_Killswitch_Block_In")
        res2 = self.remove_firewall_rule("NetStrip_Killswitch_Block_Out")
        self.remove_firewall_rule("NetStrip_Killswitch_Loopback_In")
        self.remove_firewall_rule("NetStrip_Killswitch_Loopback_Out")
        return res1 and res2

    def disable_ipv6(self) -> bool:
        cmd = ["powershell", "-Command", "Disable-NetAdapterBinding -ComponentID ms_tcpip6 -Name '*'"]
        res = self._run_cmd(cmd)
        return res.returncode == 0
        
    def enable_ipv6(self) -> bool:
        cmd = ["powershell", "-Command", "Enable-NetAdapterBinding -ComponentID ms_tcpip6 -Name '*'"]
        res = self._run_cmd(cmd)
        return res.returncode == 0
        
    def is_ipv6_enabled(self) -> bool:
        cmd = ["powershell", "-Command", "Get-NetAdapterBinding -ComponentID ms_tcpip6 | Select-Object -ExpandProperty Enabled"]
        res = self._run_cmd(cmd)
        return "True" in res.stdout

    def disable_ipv4(self) -> bool:
        cmd = ["powershell", "-Command", "Disable-NetAdapterBinding -ComponentID ms_tcpip -Name '*'"]
        res = self._run_cmd(cmd)
        return res.returncode == 0
        
    def enable_ipv4(self) -> bool:
        cmd = ["powershell", "-Command", "Enable-NetAdapterBinding -ComponentID ms_tcpip -Name '*'"]
        res = self._run_cmd(cmd)
        return res.returncode == 0
        
    def is_ipv4_enabled(self) -> bool:
        cmd = ["powershell", "-Command", "Get-NetAdapterBinding -ComponentID ms_tcpip | Select-Object -ExpandProperty Enabled"]
        res = self._run_cmd(cmd)
        return "True" in res.stdout

    def install_autostart(self) -> bool:
        # Use schtasks to create a task running as SYSTEM on boot
        exe_path = sys.executable
        if getattr(sys, 'frozen', False):
            # PyInstaller exe
            target = f'"{exe_path}" --fallback-admin'
        else:
            # Python script
            script_path = os.path.abspath(sys.argv[0])
            target = f'"{exe_path}" "{script_path}" --fallback-admin'
            
        cmd = ["schtasks", "/Create", "/RU", "SYSTEM", "/SC", "ONSTART", "/TN", "NetStrip", "/TR", target, "/F"]
        res = self._run_cmd(cmd)
        return res.returncode == 0

    def uninstall_autostart(self) -> bool:
        cmd = ["schtasks", "/Delete", "/TN", "NetStrip", "/F"]
        res = self._run_cmd(cmd)
        return res.returncode == 0

    def is_autostart_installed(self) -> bool:
        cmd = ["schtasks", "/Query", "/TN", "NetStrip"]
        res = self._run_cmd(cmd)
        return res.returncode == 0

