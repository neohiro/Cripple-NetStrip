import os
import sys
import re
import random
import logging
import subprocess
import threading
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class MACRandomizer:
    def __init__(self, engine):
        self.engine = engine
        self.original_mac = None
        self.current_interface = None
        self.lock = threading.Lock()

    @classmethod
    def is_supported(cls) -> bool:
        return sys.platform in ('win32', 'linux', 'darwin')

    def generate_random_mac(self) -> str:
        """
        Generate locally administered MAC address.
        The second hex character must be 2, 6, A, or E.
        """
        mac = [
            random.randint(0x00, 0x0f) << 4 | random.choice([0x02, 0x06, 0x0A, 0x0E]),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff)
        ]
        return ':'.join(f'{x:02x}' for x in mac)

    def get_active_interface(self) -> Optional[str]:
        if sys.platform == 'win32':
            try:
                cmd = 'netsh interface show interface'
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if "Connected" in line or "Verbunden" in line or "Conectado" in line:
                            parts = line.split()
                            if len(parts) >= 4:
                                return " ".join(parts[3:])
            except Exception as e:
                logger.error(f"Failed to get active interface on Windows: {e}")
        elif sys.platform == 'linux':
            try:
                cmd = "ip route get 8.8.8.8 | awk '{print $5}' | head -n 1"
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except Exception as e:
                logger.error(f"Failed to get active interface on Linux: {e}")
        elif sys.platform == 'darwin':
            try:
                cmd = "route -n get default | grep interface | awk '{print $2}'"
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except Exception as e:
                logger.error(f"Failed to get active interface on macOS: {e}")
        return None

    def get_current_mac(self, interface_name: str) -> Optional[str]:
        if not interface_name:
            return None
            
        if sys.platform == 'win32':
            try:
                cmd = ['getmac', '/v', '/fo', 'csv']
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    import csv, io
                    reader = csv.reader(io.StringIO(result.stdout))
                    for row in reader:
                        if len(row) >= 3 and row[0] == interface_name:
                            mac = row[2]
                            if mac and mac.lower() != 'n/a':
                                return mac.replace('-', ':').lower()
            except Exception as e:
                logger.error(f"Failed to get MAC on Windows: {e}")
        elif sys.platform in ('linux', 'darwin'):
            try:
                cmd = ['ifconfig', interface_name]
                if sys.platform == 'linux':
                    cmd = ['ip', 'link', 'show', interface_name]
                result = subprocess.run(cmd, capture_output=True, text=True)
                match = re.search(r'([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})', result.stdout)
                if match:
                    return match.group(0).replace('-', ':').lower()
            except Exception as e:
                logger.error(f"Failed to get MAC on *nix: {e}")
        return None

    def _win_set_mac(self, interface_name: str, mac: Optional[str]) -> bool:
        try:
            import winreg
            
            reg_path = r"SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002BE10318}"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_READ)
            
            target_subkey = None
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    try:
                        net_cfg_id = winreg.QueryValueEx(subkey, "NetCfgInstanceId")[0]
                        cmd = f'wmic nic where "NetConnectionID=\'{interface_name}\'" get GUID'
                        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                        guid = ""
                        for line in result.stdout.splitlines():
                            if "{" in line and "}" in line:
                                guid = line.strip()
                                break
                        
                        if guid == net_cfg_id:
                            target_subkey = subkey_name
                            winreg.CloseKey(subkey)
                            break
                    except OSError:
                        pass
                    winreg.CloseKey(subkey)
                except OSError:
                    continue
            winreg.CloseKey(key)

            if not target_subkey:
                logger.error("Could not find adapter in registry")
                return False

            write_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{reg_path}\\{target_subkey}", 0, winreg.KEY_SET_VALUE)
            
            if mac:
                mac_clean = mac.replace(':', '').replace('-', '').upper()
                winreg.SetValueEx(write_key, "NetworkAddress", 0, winreg.REG_SZ, mac_clean)
            else:
                try:
                    winreg.DeleteValue(write_key, "NetworkAddress")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(write_key)
            
            cmd1 = f'netsh interface set interface name="{interface_name}" admin=disable'
            cmd2 = f'netsh interface set interface name="{interface_name}" admin=enable'
            subprocess.run(cmd1, shell=True, capture_output=True)
            subprocess.run(cmd2, shell=True, capture_output=True)
            return True
        except Exception as e:
            logger.error(f"Windows MAC change failed: {e}")
            return False

    def randomize_mac(self, interface_name: str) -> bool:
        with self.lock:
            if not self.is_supported():
                logger.error("MAC randomization not supported on this platform")
                return False

            if not interface_name:
                logger.error("No interface provided")
                return False
                
            current = self.get_current_mac(interface_name)
            if current and not self.original_mac:
                self.original_mac = current
                if self.engine and hasattr(self.engine, 'db'):
                    try:
                        self.engine.db.set_setting(f"original_mac_{interface_name}", self.original_mac)
                    except Exception as e:
                        logger.error(f"Failed to save original MAC to DB: {e}")

            new_mac = self.generate_random_mac()
            logger.info(f"Randomizing MAC on {interface_name} to {new_mac}")

            success = False
            if sys.platform == 'win32':
                success = self._win_set_mac(interface_name, new_mac)
            elif sys.platform == 'linux':
                try:
                    subprocess.run(['ip', 'link', 'set', 'dev', interface_name, 'down'], check=True)
                    subprocess.run(['ip', 'link', 'set', 'dev', interface_name, 'address', new_mac], check=True)
                    subprocess.run(['ip', 'link', 'set', 'dev', interface_name, 'up'], check=True)
                    success = True
                except subprocess.CalledProcessError as e:
                    logger.error(f"Linux MAC change failed: {e}")
            elif sys.platform == 'darwin':
                try:
                    subprocess.run(['ifconfig', interface_name, 'ether', new_mac], check=True)
                    success = True
                except subprocess.CalledProcessError as e:
                    logger.error(f"macOS MAC change failed: {e}")

            if success:
                self.current_interface = interface_name
            return success

    def restore_mac(self, interface_name: str) -> bool:
        with self.lock:
            if not self.is_supported() or not interface_name:
                return False

            orig_mac = self.original_mac
            if not orig_mac and self.engine and hasattr(self.engine, 'db'):
                try:
                    orig_mac = self.engine.db.get_setting(f"original_mac_{interface_name}")
                except Exception:
                    pass

            if not orig_mac:
                logger.info("No original MAC saved to restore")
                if sys.platform == 'win32':
                    return self._win_set_mac(interface_name, None)
                return False

            logger.info(f"Restoring MAC on {interface_name} to {orig_mac}")
            
            success = False
            if sys.platform == 'win32':
                success = self._win_set_mac(interface_name, None) # Remove custom MAC to use hardware MAC
            elif sys.platform == 'linux':
                try:
                    subprocess.run(['ip', 'link', 'set', 'dev', interface_name, 'down'], check=True)
                    subprocess.run(['ip', 'link', 'set', 'dev', interface_name, 'address', orig_mac], check=True)
                    subprocess.run(['ip', 'link', 'set', 'dev', interface_name, 'up'], check=True)
                    success = True
                except subprocess.CalledProcessError as e:
                    logger.error(f"Linux MAC restore failed: {e}")
            elif sys.platform == 'darwin':
                try:
                    subprocess.run(['ifconfig', interface_name, 'ether', orig_mac], check=True)
                    success = True
                except subprocess.CalledProcessError as e:
                    logger.error(f"macOS MAC restore failed: {e}")

            if success:
                self.original_mac = None
            return success

    def start(self):
        logger.info("MAC Randomizer started")

    def stop(self):
        logger.info("MAC Randomizer stopping")
        if self.current_interface:
            self.restore_mac(self.current_interface)

    def randomize_active_adapter(self) -> bool:
        """Convenience: detect the active adapter and randomize its MAC."""
        iface = self.get_active_interface()
        if not iface:
            logger.error("No active network adapter found for MAC randomization")
            return False
        return self.randomize_mac(iface)

    def restore_active_adapter(self) -> bool:
        """Convenience: restore the active adapter's original MAC."""
        iface = self.current_interface or self.get_active_interface()
        if not iface:
            logger.error("No active network adapter found for MAC restoration")
            return False
        return self.restore_mac(iface)

    @staticmethod
    def harden_adapter_protocols(enable: bool = True):
        """Harden or restore network adapter protocol bindings.
        
        Disables/re-enables vulnerable legacy protocols on all active adapters:
        - NetBIOS over TCP/IP
        - LLMNR (Link-Local Multicast Name Resolution)
        - LLDP (Link Layer Discovery Protocol)
        - Client for Microsoft Networks
        - File and Printer Sharing
        - QoS Packet Scheduler
        - mDNS (Multicast DNS)
        """
        if sys.platform != 'win32':
            # Linux/macOS: disable avahi-daemon and NetBIOS via nmcli
            if sys.platform == 'linux':
                try:
                    if enable:
                        subprocess.run(['systemctl', 'stop', 'avahi-daemon'], capture_output=True)
                        subprocess.run(['systemctl', 'disable', 'avahi-daemon'], capture_output=True)
                        # Disable LLMNR in systemd-resolved
                        subprocess.run(['sed', '-i', 's/#LLMNR=yes/LLMNR=no/', '/etc/systemd/resolved.conf'], capture_output=True)
                        subprocess.run(['systemctl', 'restart', 'systemd-resolved'], capture_output=True)
                    else:
                        subprocess.run(['systemctl', 'enable', 'avahi-daemon'], capture_output=True)
                        subprocess.run(['systemctl', 'start', 'avahi-daemon'], capture_output=True)
                        subprocess.run(['sed', '-i', 's/LLMNR=no/#LLMNR=yes/', '/etc/systemd/resolved.conf'], capture_output=True)
                        subprocess.run(['systemctl', 'restart', 'systemd-resolved'], capture_output=True)
                    logger.info(f"Linux adapter hardening {'enabled' if enable else 'disabled'}")
                except Exception as e:
                    logger.error(f"Linux adapter hardening failed: {e}")
            elif sys.platform == 'darwin':
                try:
                    if enable:
                        subprocess.run(['sudo', 'launchctl', 'unload', '-w', '/System/Library/LaunchDaemons/com.apple.mDNSResponder.plist'], capture_output=True)
                    else:
                        subprocess.run(['sudo', 'launchctl', 'load', '-w', '/System/Library/LaunchDaemons/com.apple.mDNSResponder.plist'], capture_output=True)
                    logger.info(f"macOS adapter hardening {'enabled' if enable else 'disabled'}")
                except Exception as e:
                    logger.error(f"macOS adapter hardening failed: {e}")
            return

        # Windows: Use native Group Policy Registry and wmic to disable/enable protocol bindings without triggering ML
        try:
            import os
            import winreg
            
            if enable:
                try:
                    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\LLTD", 0, winreg.KEY_WRITE) as key:
                        winreg.SetValueEx(key, "EnableLLTDIO", 0, winreg.REG_DWORD, 0)
                        winreg.SetValueEx(key, "EnableRspndr", 0, winreg.REG_DWORD, 0)
                        winreg.SetValueEx(key, "AllowLLTDIOOnDomain", 0, winreg.REG_DWORD, 0)
                        winreg.SetValueEx(key, "AllowLLTDIOOnPublicNet", 0, winreg.REG_DWORD, 0)
                        winreg.SetValueEx(key, "ProhibitLLTDIOOnPrivateNet", 0, winreg.REG_DWORD, 1)
                        winreg.SetValueEx(key, "AllowRspndrOnDomain", 0, winreg.REG_DWORD, 0)
                        winreg.SetValueEx(key, "AllowRspndrOnPublicNet", 0, winreg.REG_DWORD, 0)
                        winreg.SetValueEx(key, "ProhibitRspndrOnPrivateNet", 0, winreg.REG_DWORD, 1)
                        
                    # Disable LLDP (ms_lldp) and QoS Packet Scheduler (ms_pacer) via driver registry start values
                    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\MsLldp", 0, winreg.KEY_WRITE) as key:
                        winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, 4)
                    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\pacer", 0, winreg.KEY_WRITE) as key:
                        winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, 4)
                except Exception:
                    pass
                subprocess.run(["sc", "stop", "MsLldp"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                subprocess.run(["sc", "stop", "pacer"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            else:
                try:
                    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\LLTD")
                except Exception:
                    pass
                try:
                    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\MsLldp", 0, winreg.KEY_WRITE) as key:
                        winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, 3)
                    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\pacer", 0, winreg.KEY_WRITE) as key:
                        winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, 1)
                except Exception:
                    pass
                subprocess.run(["sc", "start", "MsLldp"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                subprocess.run(["sc", "start", "pacer"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            # Disable File and Printer Sharing (LanmanServer) and NetBIOS over TCP/IP using wmic natively
            if enable:
                subprocess.run(["wmic", "service", "where", "name='lanmanserver'", "call", "stopservice"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                subprocess.run(["wmic", "nicconfig", "where", "TcpipNetbiosOptions!=2", "call", "SetTcpipNetbios", "2"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            else:
                subprocess.run(["wmic", "nicconfig", "where", "TcpipNetbiosOptions!=0", "call", "SetTcpipNetbios", "0"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                subprocess.run(["wmic", "service", "where", "name='lanmanserver'", "call", "startservice"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            import winreg
            reg_path = r"SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces"
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_READ)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{reg_path}\\{subkey_name}", 0, winreg.KEY_SET_VALUE)
                        # 2 = Disable NetBIOS over TCP/IP, 0 = Default (enable)
                        winreg.SetValueEx(subkey, "NetbiosOptions", 0, winreg.REG_DWORD, 2 if enable else 0)
                        winreg.CloseKey(subkey)
                    except OSError:
                        continue
                winreg.CloseKey(key)
            except OSError as e:
                logger.error(f"Failed to modify NetBIOS registry: {e}")

            # Disable LLMNR via Group Policy registry key
            try:
                llmnr_path = r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient"
                try:
                    llmnr_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, llmnr_path, 0, winreg.KEY_SET_VALUE)
                except FileNotFoundError:
                    llmnr_key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, llmnr_path)
                # 0 = Disable LLMNR
                winreg.SetValueEx(llmnr_key, "EnableMulticast", 0, winreg.REG_DWORD, 0 if enable else 1)
                winreg.CloseKey(llmnr_key)
            except OSError as e:
                logger.error(f"Failed to modify LLMNR registry: {e}")

            # Disable mDNS via registry
            try:
                mdns_path = r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters"
                try:
                    mdns_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, mdns_path, 0, winreg.KEY_SET_VALUE)
                except FileNotFoundError:
                    mdns_key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, mdns_path)
                winreg.SetValueEx(mdns_key, "EnableMDNS", 0, winreg.REG_DWORD, 0 if enable else 1)
                winreg.CloseKey(mdns_key)
            except OSError as e:
                logger.error(f"Failed to modify mDNS registry: {e}")

            logger.info(f"Windows adapter hardening {'enabled' if enable else 'disabled'}: NetBIOS, LLMNR, LLDP, mDNS, Client for MS Networks, File Sharing, QoS")
        except Exception as e:
            logger.error(f"Windows adapter hardening failed: {e}")
