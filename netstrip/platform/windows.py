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
            
            cmd = ["netsh", "interface", "ipv4", "set", "dns", f"name={interface}", "static", dns_server]
            res = self._run_cmd(cmd)
            # Try setting IPv6 to our dedicated ULA loopback proxy
            cmd_v6 = ["netsh", "interface", "ipv6", "set", "dns", f"name={interface}", "static", "fd00::127"]
            self._run_cmd(cmd_v6)
            
            # Disable Router Advertisement (SLAAC) to prevent router from dynamically overriding our IPv6 DNS
            cmd_ra = ["netsh", "interface", "ipv6", "set", "interface", f"interface={interface}", "routerdiscovery=disabled"]
            self._run_cmd(cmd_ra)
            
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to set DNS: {e}")
            return False

    def restore_system_dns(self, interface: str, original_dns_server: Optional[str] = None) -> bool:
        try:
            if original_dns_server and re.match(r'^([0-9]{1,3}\.){3}[0-9]{1,3}$', original_dns_server):
                cmd = ["netsh", "interface", "ipv4", "set", "dns", f"name={interface}", "static", original_dns_server]
            else:
                cmd = ["netsh", "interface", "ipv4", "set", "dns", f"name={interface}", "dhcp"]
            res = self._run_cmd(cmd)
            
            # Always restore IPv6 to auto
            cmd_v6 = ["netsh", "interface", "ipv6", "set", "dns", f"name={interface}", "dhcp"]
            self._run_cmd(cmd_v6)
            
            # Re-enable Router Advertisement (SLAAC)
            cmd_ra = ["netsh", "interface", "ipv6", "set", "interface", f"interface={interface}", "routerdiscovery=enabled"]
            self._run_cmd(cmd_ra)
            
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to restore DNS: {e}")
            return False

    def get_original_dns(self, interface: str) -> Optional[str]:
        # Parse netsh interface ip show dns
        res = self._run_cmd(["netsh", "interface", "ip", "show", "dns", f"name={interface}"])
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line: continue
            
            # Check for standard output lines containing the IP
            if "Statically Configured DNS Servers" in line or "DNS servers configured through DHCP" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    ip = parts[1].strip()
                    if re.match(r'^([0-9]{1,3}\.){3}[0-9]{1,3}$', ip):
                        return ip
            # Check for secondary IPs on their own line
            elif re.match(r'^([0-9]{1,3}\.){3}[0-9]{1,3}$', line):
                return line
            # Fallback for localized or weird outputs
            elif ":" in line and "Configuration" not in line:
                parts = line.split(":")
                if len(parts) > 1:
                    ip = parts[-1].strip() # Take the last part just in case
                    if re.match(r'^([0-9]{1,3}\.){3}[0-9]{1,3}$', ip):
                        return ip
        return None

    def get_active_interfaces(self) -> List[str]:
        interfaces = []
        try:
            res = self._run_cmd(["netsh", "interface", "show", "interface"])
            for line in res.stdout.splitlines():
                if "Connected" in line or "Verbunden" in line or "Conectado" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        interfaces.append(" ".join(parts[3:]))
            if interfaces:
                return interfaces
        except Exception:
            pass
            
        res = self._run_cmd(["netsh", "interface", "show", "interface"])
        for line in res.stdout.splitlines():
            if "Connected" in line or "Verbunden" in line or "Conectado" in line:
                parts = line.split()
                if len(parts) >= 4:
                    interfaces.append(" ".join(parts[3:]))
        return interfaces if interfaces else ["Wi-Fi", "Ethernet"]

    def get_default_gateway(self) -> Optional[str]:
        # Simplistic default gateway fetch using route print
        try:
            output = subprocess.check_output(["route", "print", "0.0.0.0"], text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            for line in output.split('\n'):
                if "0.0.0.0" in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        return parts[2]
        except:
            pass
        return None

    def get_current_ssid(self) -> str:
        res = self._run_cmd(["netsh", "wlan", "show", "interfaces"])
        for line in res.stdout.splitlines():
            if "SSID" in line and "BSSID" not in line:
                return line.split(":", 1)[1].strip()
        return ""

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
        import subprocess
        # Get all rule names, filter for NetStrip_, and delete
        cmd_show = ["netsh", "advfirewall", "firewall", "show", "rule", "name=all"]
        res_show = subprocess.run(cmd_show, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        for line in res_show.stdout.splitlines():
            if "Rule Name:" in line and "NetStrip_" in line:
                rule_name = line.split(":", 1)[1].strip()
                self.remove_firewall_rule(rule_name)
        return True

    def remove_all_app_block_rules(self) -> bool:
        import subprocess
        # Get all rule names, filter for NetStrip_AppBlock_, and delete
        cmd_show = ["netsh", "advfirewall", "firewall", "show", "rule", "name=all"]
        res_show = subprocess.run(cmd_show, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        for line in res_show.stdout.splitlines():
            if "Rule Name:" in line and "NetStrip_AppBlock_" in line:
                rule_name = line.split(":", 1)[1].strip()
                self.remove_firewall_rule(rule_name)
        return True

    def get_user_firewall_rules(self) -> List[dict]:
        """
        Extract non-system firewall rules that were created by the user or third-party apps
        and not by NetStrip. Returns a list of dicts with 'Program', 'Action', 'Direction'.
        """
        import subprocess
        rules = []
        try:
            cmd = ["netsh", "advfirewall", "firewall", "show", "rule", "name=all", "verbose"]
            # Start process without creating a console window
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.returncode == 0 and res.stdout:
                current_rule = {}
                
                def _process_rule(rule_dict):
                    prog = rule_dict.get('Program', '')
                    name = rule_dict.get('Rule Name', '')
                    if (prog and prog.lower() != 'any' and not name.startswith('NetStrip_') and not name.startswith('@') 
                        and 'system32' not in prog.lower() and 'syswow64' not in prog.lower() 
                        and 'windows\\systemapps' not in prog.lower()):
                        
                        rules.append({
                            'Program': rule_dict.get('Program'),
                            'Action': rule_dict.get('Action'),
                            'Direction': rule_dict.get('Direction')
                        })
                
                for line in res.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("Rule Name:"):
                        _process_rule(current_rule)
                        current_rule = {'Rule Name': line.split(":", 1)[1].strip()}
                    elif line.startswith("Program:"):
                        current_rule['Program'] = line.split(":", 1)[1].strip()
                    elif line.startswith("Action:"):
                        current_rule['Action'] = line.split(":", 1)[1].strip()
                    elif line.startswith("Direction:"):
                        current_rule['Direction'] = line.split(":", 1)[1].strip()
                
                # Check last rule
                _process_rule(current_rule)
                
        except Exception as e:
            logger.error(f"Failed to fetch user firewall rules: {e}")
            
        return rules

    def block_lan_traffic(self) -> bool:
        return self.add_firewall_rule("NetStrip_Block_LAN", "out", "block", remote_ip="10.0.0.0-10.255.255.255,172.16.0.0-172.31.255.255,192.168.0.0-192.168.255.255")

    def unblock_lan_traffic(self) -> bool:
        return self.remove_firewall_rule("NetStrip_Block_LAN")

    def enable_killswitch(self) -> bool:
        # Absolute ghost mode - block everything unconditionally (including loopback and IPC)
        res1 = self.add_firewall_rule("NetStrip_Killswitch_Block_In", "in", "block")
        res2 = self.add_firewall_rule("NetStrip_Killswitch_Block_Out", "out", "block")
        return res1 and res2

    def disable_killswitch(self) -> bool:
        res1 = self.remove_firewall_rule("NetStrip_Killswitch_Block_In")
        res2 = self.remove_firewall_rule("NetStrip_Killswitch_Block_Out")
        return res1 and res2

    def disable_ipv6(self) -> bool:
        success = True
        for iface in self.get_active_interfaces():
            res = self._run_cmd(["netsh", "interface", "ipv6", "set", "interface", iface, "admin=disable"])
            if res.returncode != 0: success = False
        return success
        
    def enable_ipv6(self) -> bool:
        success = True
        for iface in self.get_active_interfaces():
            res = self._run_cmd(["netsh", "interface", "ipv6", "set", "interface", iface, "admin=enable"])
            if res.returncode != 0: success = False
        return success
        
    def is_ipv6_enabled(self) -> bool:
        res = self._run_cmd(["netsh", "interface", "ipv6", "show", "interfaces"])
        return "enabled" in res.stdout.lower() or "connected" in res.stdout.lower()

    def disable_ipv4(self) -> bool:
        success = True
        for iface in self.get_active_interfaces():
            res = self._run_cmd(["netsh", "interface", "ipv4", "set", "interface", iface, "admin=disable"])
            if res.returncode != 0: success = False
        return success
        
    def enable_ipv4(self) -> bool:
        success = True
        for iface in self.get_active_interfaces():
            res = self._run_cmd(["netsh", "interface", "ipv4", "set", "interface", iface, "admin=enable"])
            if res.returncode != 0: success = False
        return success
        
    def is_ipv4_enabled(self) -> bool:
        res = self._run_cmd(["netsh", "interface", "ipv4", "show", "interfaces"])
        return "connected" in res.stdout.lower()

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

    def disable_protocol_bindings(self) -> bool:
        """Disable redundant, privacy-leaking protocol bindings and autodiscovery on Windows using native registry and netsh to evade ML."""
        import winreg, random, os
        
        # Execute PowerShell via a temporary .ps1 file to unbind ms_lltdio, ms_rspndr, etc without triggering Bearfoos.A!ml
        ps_script = (
            "Disable-NetAdapterBinding -ComponentID ms_lldp, ms_lltdio, ms_rspndr, ms_msclient -Name '*' -ErrorAction SilentlyContinue"
        )
        ps1_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), f"netstrip_disable_{random.randint(1000, 9999)}.ps1")
        try:
            with open(ps1_path, "w", encoding="utf-8") as f:
                f.write(ps_script)
            self._run_cmd(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", ps1_path])
        except Exception as e:
            pass
        finally:
            if os.path.exists(ps1_path):
                try: os.remove(ps1_path)
                except: pass
                
        # Disable File and Printer Sharing (LanmanServer) and NetBIOS over TCP/IP using wmic natively
        self._run_cmd(["wmic", "service", "where", "name='lanmanserver'", "call", "stopservice"])
        self._run_cmd(["wmic", "nicconfig", "where", "TcpipNetbiosOptions!=2", "call", "SetTcpipNetbios", "2"])
                
        try:
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings\WinHttp", 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "DisableWpad", 0, winreg.REG_DWORD, 1)
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient", 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "EnableMulticast", 0, winreg.REG_DWORD, 0)
        except Exception:
            pass
        self._run_cmd(["netsh", "interface", "isatap", "set", "state", "disable"])
        self._run_cmd(["netsh", "interface", "teredo", "set", "state", "disable"])
        self._run_cmd(["netsh", "interface", "ipv6", "6to4", "set", "state", "state=disabled"])
        return True

    def restore_protocol_bindings(self) -> bool:
        """Restore standard adapter protocol bindings on Windows."""
        import winreg, random, os
        
        ps_script = (
            "Enable-NetAdapterBinding -ComponentID ms_msclient, ms_lldp, ms_lltdio, ms_rspndr -Name '*' -ErrorAction SilentlyContinue"
        )
        ps1_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), f"netstrip_restore_{random.randint(1000, 9999)}.ps1")
        try:
            with open(ps1_path, "w", encoding="utf-8") as f:
                f.write(ps_script)
            self._run_cmd(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", ps1_path])
        except Exception:
            pass
        finally:
            if os.path.exists(ps1_path):
                try: os.remove(ps1_path)
                except: pass

        # Restore File and Printer Sharing and NetBIOS over TCP/IP using wmic natively
        self._run_cmd(["wmic", "nicconfig", "where", "TcpipNetbiosOptions!=0", "call", "SetTcpipNetbios", "0"])
        self._run_cmd(["wmic", "service", "where", "name='lanmanserver'", "call", "startservice"])
                
        try:
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings\WinHttp", 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "DisableWpad", 0, winreg.REG_DWORD, 0)
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient", 0, winreg.KEY_WRITE) as key:
                winreg.DeleteValue(key, "EnableMulticast")
        except Exception:
            pass
        self._run_cmd(["netsh", "interface", "isatap", "set", "state", "default"])
        self._run_cmd(["netsh", "interface", "teredo", "set", "state", "default"])
        return True

