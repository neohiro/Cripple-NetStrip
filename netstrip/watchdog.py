import sys
import time
import os
import subprocess
import logging
import hashlib
from pathlib import Path

# Setup basic logging for the watchdog
logging.basicConfig(level=logging.INFO, format='%(asctime)s - Watchdog - %(message)s')

import hmac
import secrets

# Generate ephemeral in-memory 512-bit secret key per watchdog session (Post-Quantum Keyed Hashing)
HMAC_SECRET_KEY = secrets.token_bytes(64)

def get_critical_files():
    base_dir = Path(__file__).parent.parent
    files = [
        base_dir / "main.py",
    ]
    netstrip_dir = base_dir / "netstrip"
    if netstrip_dir.exists():
        for path in netstrip_dir.rglob("*.py"):
            files.append(path)
    return files

def snapshot_integrity():
    """Hash all critical files on startup using keyed HMAC-SHA512 baseline to prevent hash forgery."""
    baseline = {}
    for filepath in get_critical_files():
        if filepath.exists():
            try:
                with open(filepath, 'rb') as f:
                    content = f.read()
                h = hmac.new(HMAC_SECRET_KEY, content, hashlib.sha512).hexdigest()
                baseline[str(filepath)] = h
            except Exception as e:
                logging.error(f"Failed to hash {filepath}: {e}")
    return baseline

def verify_integrity(baseline):
    """Verify keyed HMAC-SHA512 baseline of all core modules and engine files."""
    tampered = []
    for filepath in get_critical_files():
        if filepath.exists():
            try:
                with open(filepath, 'rb') as f:
                    content = f.read()
                current_hmac = hmac.new(HMAC_SECRET_KEY, content, hashlib.sha512).hexdigest()
                if str(filepath) in baseline and current_hmac != baseline[str(filepath)]:
                    tampered.append(filepath.name)
            except Exception:
                pass
        else:
            tampered.append(f"{filepath.name} (DELETED)")
            
    if tampered:
        logging.error(f"Integrity check failed. Tampered/Modified files: {', '.join(tampered)}")
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Critical Security Alert - Tampering Detected",
                f"NetStrip (Cripple) Watchdog detected unauthorized tampering or deletion of core security components:\n\n{', '.join(tampered)}\n\nExecution terminated to prevent malicious hijacking."
            )
            root.update()
            time.sleep(2)
        except Exception:
            pass
        return False
    return True

def get_clean_exit_path():
    return Path.home() / ".netstrip" / ".clean_exit"

def restore_network():
    """Fail-Open: Restore the OS DNS settings and firewall rules to default if NetStrip crashes."""
    logging.info("NetStrip crash detected! Initiating emergency DNS and network restore...")
    
    import platform
    import sqlite3
    import re
    sys_plat = platform.system()
    
    def get_backup_dns(interface_name):
        db_path = Path.home() / ".netstrip" / "netstrip.db"
        if db_path.exists():
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT value FROM settings WHERE key=?", (f"backup_dns_{interface_name}",))
                row = c.fetchone()
                conn.close()
                if row and row[0] and row[0] != "dhcp":
                    ip = row[0]
                    if re.match(r'^([0-9]{1,3}\.){3}[0-9]{1,3}$', ip):
                        return ip
            except Exception as e:
                logging.error(f"Failed to read backup DNS from DB: {e}")
        return None

    def get_db_setting(key, default="false"):
        db_path = Path.home() / ".netstrip" / "netstrip.db"
        if db_path.exists():
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT value FROM settings WHERE key=?", (key,))
                row = c.fetchone()
                conn.close()
                if row and row[0]:
                    return row[0]
            except Exception:
                pass
        return default

    def clear_db_setting(key):
        db_path = Path.home() / ".netstrip" / "netstrip.db"
        if db_path.exists():
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("UPDATE settings SET value=? WHERE key=?", ("false", key))
                conn.commit()
                conn.close()
            except Exception:
                pass
    
    try:
        if sys_plat == "Windows":
            res = subprocess.run(["netsh", "interface", "show", "interface"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            interfaces = []
            for line in res.stdout.splitlines():
                if "Connected" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        interfaces.append(" ".join(parts[3:]))
            if not interfaces:
                interfaces = ["Wi-Fi", "Ethernet"]
                
            for interface in interfaces:
                backup_dns = get_backup_dns(interface)
                if backup_dns:
                    logging.info(f"Restoring STATIC DNS for interface: {interface} -> {backup_dns}")
                    subprocess.run(["netsh", "interface", "ipv4", "set", "dns", f"name={interface}", "static", backup_dns], creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    logging.info(f"Restoring DHCP DNS for interface: {interface}")
                    subprocess.run(["netsh", "interface", "ipv4", "set", "dns", f"name={interface}", "dhcp"], creationflags=subprocess.CREATE_NO_WINDOW)
                
                subprocess.run(["netsh", "interface", "ipv6", "set", "dns", f"name={interface}", "dhcp"], creationflags=subprocess.CREATE_NO_WINDOW)
                subprocess.run(["netsh", "interface", "ipv6", "set", "interface", f"interface={interface}", "routerdiscovery=enabled"], creationflags=subprocess.CREATE_NO_WINDOW)
                
            # Fail-open: Fast batch command to wipe all NetStrip firewall rules.
            # IPv6/IPv4 protocol bindings are restored below based on the database state.
            logging.info("Removing NetStrip firewall rules...")
            try:
                res = subprocess.run(["netsh", "advfirewall", "firewall", "show", "rule", "name=all"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                for line in res.stdout.splitlines():
                    if line.startswith("Rule Name:") and "NetStrip" in line:
                        name = line.split(":", 1)[1].strip()
                        subprocess.run(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={name}"], creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception:
                pass
            
            # Re-enable standard protocol bindings, WPAD, LLMNR, and NetBIOS on Windows
            logging.info("Restoring Windows network adapter protocol bindings and discovery...")
            
            import winreg, random, os
            ps_restore_bindings = (
                "Enable-NetAdapterBinding -ComponentID ms_msclient, ms_lldp, ms_lltdio, ms_rspndr -Name '*' -ErrorAction SilentlyContinue"
            )
            ps1_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), f"netstrip_restore_{random.randint(1000, 9999)}.ps1")
            try:
                with open(ps1_path, "w", encoding="utf-8") as f:
                    f.write(ps_restore_bindings)
                subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", ps1_path], creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception:
                pass
            finally:
                if os.path.exists(ps1_path):
                    try: os.remove(ps1_path)
                    except: pass
            
            subprocess.run(["wmic", "nicconfig", "where", "TcpipNetbiosOptions!=0", "call", "SetTcpipNetbios", "0"], creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(["wmic", "service", "where", "name='lanmanserver'", "call", "startservice"], creationflags=subprocess.CREATE_NO_WINDOW)
            
            try:
                with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings\WinHttp", 0, winreg.KEY_WRITE) as key:
                    winreg.SetValueEx(key, "DisableWpad", 0, winreg.REG_DWORD, 0)
                with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient", 0, winreg.KEY_WRITE) as key:
                    winreg.DeleteValue(key, "EnableMulticast")
            except Exception:
                pass
            subprocess.run(["netsh", "interface", "isatap", "set", "state", "default"], creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(["netsh", "interface", "teredo", "set", "state", "default"], creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(["netsh", "interface", "ipv6", "6to4", "set", "state", "default"], creationflags=subprocess.CREATE_NO_WINDOW)

            if get_db_setting("disable_ipv6_globally") == "true" or get_db_setting("disable_ipv4_globally") == "true":
                try:
                    res = subprocess.run(["netsh", "interface", "show", "interface"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    ifaces = []
                    for line in res.stdout.splitlines():
                        if "Connected" in line or "Verbunden" in line or "Conectado" in line:
                            parts = line.split()
                            if len(parts) >= 4:
                                ifaces.append(" ".join(parts[3:]))
                                
                    if get_db_setting("disable_ipv6_globally") == "true":
                        logging.info("Re-enabling global IPv6 (was disabled by engine before crash)...")
                        for iface in ifaces:
                            subprocess.run(["netsh", "interface", "ipv6", "set", "interface", iface, "admin=enable"], creationflags=subprocess.CREATE_NO_WINDOW)
                        clear_db_setting("disable_ipv6_globally")
                        
                    if get_db_setting("disable_ipv4_globally") == "true":
                        logging.info("Re-enabling global IPv4 (was disabled by engine before crash)...")
                        for iface in ifaces:
                            subprocess.run(["netsh", "interface", "ipv4", "set", "interface", iface, "admin=enable"], creationflags=subprocess.CREATE_NO_WINDOW)
                        clear_db_setting("disable_ipv4_globally")
                except Exception as e:
                    logging.error(f"Failed to re-enable interfaces: {e}")
            
            # Reset killswitch state in DB so the app starts fresh
            clear_db_setting("killswitch_active")
                
        elif sys_plat == "Darwin": # macOS
            res = subprocess.run(["networksetup", "-listallnetworkservices"], capture_output=True, text=True)
            interfaces = [line.strip() for line in res.stdout.splitlines() if line.strip() and "*" not in line]
            if not interfaces:
                interfaces = ["Wi-Fi", "Ethernet"]
            
            for interface in interfaces:
                backup_dns = get_backup_dns(interface)
                if backup_dns:
                    logging.info(f"Restoring STATIC DNS for interface: {interface} -> {backup_dns}")
                    subprocess.run(["networksetup", "-setdnsservers", interface, backup_dns])
                else:
                    logging.info(f"Restoring DHCP DNS for interface: {interface}")
                    subprocess.run(["networksetup", "-setdnsservers", interface, "Empty"])
                    
                if get_db_setting("disable_ipv6_globally") == "true":
                    subprocess.run(["networksetup", "-setv6automatic", interface])
                
            subprocess.run(["sysctl", "-w", "net.inet6.ip6.accept_rtadv=1"])
            subprocess.run(["sysctl", "-w", "net.inet.icmp.drop_redirect=0"])
            subprocess.run(["sysctl", "-w", "net.inet.ip.redirect=1"])
            subprocess.run(["defaults", "write", "/Library/Preferences/com.apple.mDNSResponder.plist", "NoMulticastAdvertisements", "-bool", "NO"])
            
            clear_db_setting("disable_ipv6_globally")
            clear_db_setting("killswitch_active")
            
        elif sys_plat == "Linux":
            logging.info("Restoring DNS for Linux (iptables)")
            for proto in ["udp", "tcp"]:
                subprocess.run(["iptables", "-t", "nat", "-D", "OUTPUT", "-p", proto, "--dport", "53", "-j", "REDIRECT", "--to-ports", "53"])
            
            if get_db_setting("disable_ipv6_globally") == "true":
                subprocess.run(["sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=0"])
                subprocess.run(["sysctl", "-w", "net.ipv6.conf.default.disable_ipv6=0"])
            
            subprocess.run(["sysctl", "-w", "net.ipv6.conf.all.accept_ra=1"])
            subprocess.run(["sysctl", "-w", "net.ipv6.conf.default.accept_ra=1"])
            subprocess.run(["sysctl", "-w", "net.ipv4.conf.all.accept_redirects=1"])
            subprocess.run(["sysctl", "-w", "net.ipv4.conf.default.accept_redirects=1"])
            subprocess.run(["sysctl", "-w", "net.ipv4.conf.all.drop_unicast_in_l2_multicast=0"])
            
            clear_db_setting("disable_ipv6_globally")
            clear_db_setting("killswitch_active")
            
            # Flush any IPv4 drops
            while subprocess.run(["iptables", "-C", "INPUT", "!", "-i", "lo", "-p", "all", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"], capture_output=True).returncode == 0:
                subprocess.run(["iptables", "-D", "INPUT", "!", "-i", "lo", "-p", "all", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"])
            while subprocess.run(["iptables", "-C", "OUTPUT", "!", "-o", "lo", "-p", "all", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"], capture_output=True).returncode == 0:
                subprocess.run(["iptables", "-D", "OUTPUT", "!", "-o", "lo", "-p", "all", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"])
            
        logging.info("Emergency network restore completed successfully.")
    except Exception as e:
        logging.error(f"Failed to restore network: {e}")

    # Briefly wait for OS network interface sockets and routes to settle
    time.sleep(0.3)
    
    # Send crash report to developer (consent-aware) AFTER internet connectivity is restored
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from netstrip.core.crash_reporter import send_crash_report
        send_crash_report(
            context="watchdog_crash_recovery",
            extra_info={
                "trigger": "Parent process died unexpectedly",
                "watchdog_pid": os.getpid(),
                "action": "Restored network to fail-open state",
            },
            require_consent=True,
        )
    except Exception as e:
        logging.error(f"Failed to send watchdog crash report: {e}")

def main():
    baseline_hashes = snapshot_integrity()
    
    import psutil
    
    if len(sys.argv) < 2:
        logging.error("Parent PID required.")
        sys.exit(1)
        
    try:
        parent_pid = int(sys.argv[1])
    except ValueError:
        logging.error("Invalid PID.")
        sys.exit(1)
        
    launch_cmd = sys.argv[2:] if len(sys.argv) > 2 else None
    restarts_remaining = 3
        
    logging.info(f"Watchdog started, monitoring PID {parent_pid}")
    
    # Clear any old clean exit flags
    clean_exit_file = get_clean_exit_path()
    if clean_exit_file.exists():
        try:
            clean_exit_file.unlink()
        except: pass
    
    # Check if process exists immediately
    if not psutil.pid_exists(parent_pid):
        logging.warning("Parent process already dead on startup.")
        if not launch_cmd:
            sys.exit(0)
            
    try:
        if psutil.pid_exists(parent_pid):
            parent_process = psutil.Process(parent_pid)
        else:
            parent_process = None
    except psutil.NoSuchProcess:
        parent_process = None
        
    # Monitor loop
    loop_ticks = 0
    while True:
        try:
            exit_code = None
            if parent_process and parent_process.is_running():
                # Perform periodic live HMAC integrity check every ~10 seconds
                loop_ticks += 1
                if loop_ticks % 5 == 0:
                    if not verify_integrity(baseline_hashes):
                        logging.critical("Live tampering detected during process execution! Terminating process...")
                        try: parent_process.kill()
                        except: pass
                        restore_network()
                        break

                exit_code = parent_process.wait(timeout=2.0)
            
            # If we get here, process died!
            logging.info(f"Parent process terminated with exit code: {exit_code}")
            
            # Check for the explicit clean_exit flag set by the user closing the app
            if clean_exit_file.exists():
                logging.info("User requested clean exit flag detected. Watchdog terminating cleanly.")
                try: clean_exit_file.unlink()
                except: pass
                break
            
            # If the exit code is 0 (or specifically 100 which some apps use for manual exit), it was gracefully closed by the user.
            if exit_code in (0,):
                logging.info("Graceful shutdown detected via exit code. Watchdog terminating cleanly.")
                break
            
            if launch_cmd and restarts_remaining > 0:
                # Before restarting, check integrity again
                if not verify_integrity(baseline_hashes):
                    logging.error("Tampering detected. Aborting restart.")
                    restore_network()
                    break
                
                logging.info(f"Attempting to restart NetStrip... ({restarts_remaining} attempts left)")
                restarts_remaining -= 1
                try:
                    # Relaunch NetStrip
                    new_proc = subprocess.Popen(launch_cmd, creationflags=subprocess.CREATE_NO_WINDOW)
                    parent_pid = new_proc.pid
                    parent_process = psutil.Process(parent_pid)
                    logging.info(f"Successfully restarted with new PID {parent_pid}")
                    # Keep monitoring the new process!
                    continue
                except Exception as e:
                    logging.error(f"Failed to restart: {e}")
            
            # If we couldn't restart or ran out of attempts, restore network
            restore_network()
            break
            
        except psutil.TimeoutExpired:
            # Still alive, continue waiting
            continue
        except Exception as e:
            logging.error(f"Watchdog error: {e}")
            # Failsafe
            if not psutil.pid_exists(parent_pid):
                if launch_cmd and restarts_remaining > 0:
                    parent_process = None # Force restart block next loop
                    continue
                restore_network()
                break
            time.sleep(2.0)

if __name__ == "__main__":
    main()
