import sys
import time
import os
import subprocess
import logging
import hashlib
from pathlib import Path

# Setup basic logging for the watchdog
logging.basicConfig(level=logging.INFO, format='%(asctime)s - Watchdog - %(message)s')

def get_critical_files():
    base_dir = Path(__file__).parent.parent
    return [
        base_dir / "main.py",
        base_dir / "netstrip" / "core" / "engine.py",
        base_dir / "netstrip" / "core" / "dns_proxy.py",
    ]

def snapshot_integrity():
    """Hash critical files on startup to establish a trusted baseline."""
    baseline = {}
    for filepath in get_critical_files():
        if filepath.exists():
            try:
                with open(filepath, 'rb') as f:
                    baseline[str(filepath)] = hashlib.sha256(f.read()).hexdigest()
            except Exception as e:
                logging.error(f"Failed to hash {filepath}: {e}")
    return baseline

def verify_integrity(baseline):
    """Verify that critical files have not been tampered with since startup."""
    tampered = []
    for filepath in get_critical_files():
        if filepath.exists():
            try:
                with open(filepath, 'rb') as f:
                    current_hash = hashlib.sha256(f.read()).hexdigest()
                if str(filepath) in baseline and current_hash != baseline[str(filepath)]:
                    tampered.append(filepath.name)
            except Exception:
                pass
        else:
            tampered.append(f"{filepath.name} (DELETED)")
            
    if tampered:
        logging.error(f"Integrity check failed. Tampered files: {', '.join(tampered)}")
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Critical Security Alert - Tampering Detected",
                f"NetStrip (Cripple) Watchdog has blocked a restart attempt because critical core files were modified or deleted while the program was running:\n\n{', '.join(tampered)}\n\nThis may indicate malware attempting to hijack the DNS sinkhole or firewall."
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
    """Fail-Open: Restore the OS DNS settings to default if NetStrip crashes."""
    logging.info("NetStrip crash detected! Initiating emergency DNS restore...")
    
    # Send crash report to developer
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from netstrip.core.crash_reporter import send_crash_report
        send_crash_report(
            context="watchdog_crash_recovery",
            extra_info={
                "trigger": "Parent process died unexpectedly",
                "watchdog_pid": os.getpid(),
                "action": "Restoring network to fail-open state",
            }
        )
    except Exception as e:
        logging.error(f"Failed to send watchdog crash report: {e}")
    
    import platform
    sys_plat = platform.system()
    
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
                
            def get_backup_dns(interface_name):
                import sqlite3
                import re
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
                
            for interface in interfaces:
                backup_dns = get_backup_dns(interface)
                if backup_dns:
                    logging.info(f"Restoring STATIC DNS for interface: {interface} -> {backup_dns}")
                    subprocess.run(["netsh", "interface", "ipv4", "set", "dns", f'name="{interface}"', "static", backup_dns], creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    logging.info(f"Restoring DHCP DNS for interface: {interface}")
                    subprocess.run(["netsh", "interface", "ipv4", "set", "dns", f'name="{interface}"', "dhcp"], creationflags=subprocess.CREATE_NO_WINDOW)
                
                subprocess.run(["netsh", "interface", "ipv6", "set", "dns", f'name="{interface}"', "dhcp"], creationflags=subprocess.CREATE_NO_WINDOW)
                subprocess.run(["netsh", "interface", "ipv6", "set", "interface", f'interface="{interface}"', "routerdiscovery=enabled"], creationflags=subprocess.CREATE_NO_WINDOW)
                
            # Fail-open: Always re-enable IPv6/IPv4 bindings if the engine crashes, so the user has internet
            subprocess.run(["powershell", "-Command", "Enable-NetAdapterBinding -ComponentID ms_tcpip6 -Name '*'"], creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(["powershell", "-Command", "Enable-NetAdapterBinding -ComponentID ms_tcpip -Name '*'"], creationflags=subprocess.CREATE_NO_WINDOW)
                
        elif sys_plat == "Darwin": # macOS
            res = subprocess.run(["networksetup", "-listallnetworkservices"], capture_output=True, text=True)
            interfaces = [line.strip() for line in res.stdout.splitlines() if line.strip() and "*" not in line]
            if not interfaces:
                interfaces = ["Wi-Fi", "Ethernet"]
            
            for interface in interfaces:
                logging.info(f"Restoring DNS for interface: {interface}")
                subprocess.run(["networksetup", "-setdnsservers", interface, "Empty"])
                subprocess.run(["networksetup", "-setv6automatic", interface])
                
            subprocess.run(["sysctl", "-w", "net.inet6.ip6.accept_rtadv=1"])
            
        elif sys_plat == "Linux":
            logging.info("Restoring DNS for Linux (iptables)")
            for proto in ["udp", "tcp"]:
                subprocess.run(["iptables", "-t", "nat", "-D", "OUTPUT", "-p", proto, "--dport", "53", "-j", "REDIRECT", "--to-ports", "53"])
            subprocess.run(["sysctl", "-w", "net.ipv6.conf.all.accept_ra=1"])
            subprocess.run(["sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=0"])
            subprocess.run(["sysctl", "-w", "net.ipv6.conf.default.disable_ipv6=0"])
            
            # Flush any IPv4 drops
            while subprocess.run(["iptables", "-C", "INPUT", "!", "-i", "lo", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"], capture_output=True).returncode == 0:
                subprocess.run(["iptables", "-D", "INPUT", "!", "-i", "lo", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"])
            while subprocess.run(["iptables", "-C", "OUTPUT", "!", "-o", "lo", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"], capture_output=True).returncode == 0:
                subprocess.run(["iptables", "-D", "OUTPUT", "!", "-o", "lo", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"])
            
        logging.info("Emergency restore completed successfully.")
    except Exception as e:
        logging.error(f"Failed to restore network: {e}")

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
    while True:
        try:
            exit_code = None
            if parent_process and parent_process.is_running():
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
