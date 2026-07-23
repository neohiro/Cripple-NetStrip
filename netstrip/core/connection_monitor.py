"""
Connection Monitor for NetStrip
Uses psutil to poll network connections, mapping them to process names.
"""

import psutil
import threading
import time
import logging
import socket
import sys
import os
import concurrent.futures
from typing import Callable, List, Dict
from netstrip.core.classifier import TrafficClassifier
from netstrip.core.modes import ConnectionAction, ConnectionCategory
from netstrip.core.sound import sound_manager
from netstrip.data.database import Database
import platform
try:
    from netstrip.core.linux_ebpf_monitor import EBPFMonitor
except ImportError:
    EBPFMonitor = None

logger = logging.getLogger(__name__)

class ConnectionMonitor:
    def __init__(self, classifier: TrafficClassifier, db: Database, poll_interval: float = 1.0):
        self.classifier = classifier
        self.db = db
        self.poll_interval = poll_interval
        self.is_running = False
        self.thread = None
        self._stop_event = threading.Event()
        self.known_connections = set()
        self.port_to_pid = {}
        self._notified_targets = set()
        self._dns_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self._rate_limits = {}
        self._arp_cache = {}
        
        # Callback for the GUI or Notifier
        self.on_new_connection: Callable = None
        self.on_malware_detected: Callable = None
        self.on_status: Callable = None
        
        # eBPF Kernel Verification
        self.ebpf_monitor = None
        if platform.system() == "Linux" and EBPFMonitor:
            self.ebpf_monitor = EBPFMonitor(self._handle_ebpf_event)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        
        if self.ebpf_monitor:
            self.ebpf_monitor.start()
            
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("Connection Monitor started")

    def stop(self):
        self.is_running = False
        self._stop_event.set()
        
        if self._dns_executor:
            self._dns_executor.shutdown(wait=False)
        
        if self.ebpf_monitor:
            self.ebpf_monitor.stop()
            
        if self.thread:
            self.thread.join(timeout=2.0)
            
        logger.info("Connection Monitor stopped")

    def _monitor_loop(self):
        while self.is_running:
            try:
                self._poll_connections()
            except Exception as e:
                logger.error(f"Error in connection monitor loop: {e}")
            self._stop_event.wait(self.poll_interval)

    def _poll_connections(self):
        try:
            # Requires root/admin on some OSes to see all connections
            connections = psutil.net_connections(kind='all')
        except psutil.AccessDenied:
            logger.warning("Access Denied when getting net_connections. Need admin privileges.")
            return

        current_connections = set()
        listening_ports = set()
        new_port_to_pid = {}
        
        for conn in connections:
            if conn.status == 'LISTEN' and conn.laddr:
                listening_ports.add(conn.laddr.port)
            if conn.laddr and conn.pid:
                new_port_to_pid[conn.laddr.port] = conn.pid
                
        self.port_to_pid = new_port_to_pid
        
        for conn in connections:
            if not conn.raddr or not conn.pid or not hasattr(conn.raddr, 'ip'):
                continue
                
            # Ignore internal loopback connections (e.g. dnscrypt-proxy communicating locally, or DNS requests to 127.127.127.127)
            if conn.laddr and conn.laddr.ip.startswith('127.') and conn.raddr.ip.startswith('127.'):
                continue
            if conn.laddr and conn.laddr.ip == '::1' and conn.raddr.ip == '::1':
                continue
                
            # Create a unique signature for the connection
            lport = conn.laddr.port if conn.laddr else 0
            conn_sig = f"{conn.pid}:{conn.raddr.ip}:{conn.raddr.port}:{lport}:{conn.type}"
            current_connections.add(conn_sig)
            
            if conn_sig not in self.known_connections:
                # Determine direction: if local port is in our listening ports, it's inbound. Otherwise outbound.
                direction = "inbound" if (conn.laddr and conn.laddr.port in listening_ports) else "outbound"
                
                # New connection found
                self._handle_new_connection(conn, conn_sig, direction)
                
        # IoT Botnet / Rapid Ping Detection (Sliding Window)
        now = time.time()
        # Clean up old timestamps from rate limiter
        for ip in list(self._rate_limits.keys()):
            self._rate_limits[ip] = [ts for ts in self._rate_limits[ip] if now - ts < 1.0]
            if not self._rate_limits[ip]:
                del self._rate_limits[ip]
                
        # Update known connections
        self.known_connections = current_connections

    def _resolve_process_identity(self, proc: psutil.Process):
        """Ascend the process tree to find the root parent application."""
        system_launchers = {'explorer.exe', 'cmd.exe', 'powershell.exe', 'pwsh.exe', 'svchost.exe', 'services.exe', 'wininit.exe', 'smss.exe', 'systemd', 'init', 'bash', 'sh', 'zsh', 'conhost.exe', 'wsl.exe', 'taskhostw.exe'}
        
        current_proc = proc
        root_proc = proc
        
        try:
            depth = 0
            while depth < 10:
                parent = current_proc.parent()
                if not parent:
                    break
                
                parent_name = parent.name().lower()
                if parent_name in system_launchers:
                    break
                    
                root_proc = parent
                current_proc = parent
                depth += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
        try:
            process_name = root_proc.name()
        except Exception:
            process_name = "Unknown"
            
        try:
            process_path = root_proc.exe()
        except Exception:
            process_path = ""
            
        try:
            original_exe = proc.name()
        except Exception:
            original_exe = process_name
            
        return process_name, process_path, root_proc, original_exe

    def _handle_new_connection(self, conn, conn_sig, direction):
        original_exe = "Unknown"
        try:
            if conn.pid == os.getpid():
                process_name = "Cripple (Internal)"
                process_path = sys.executable
                original_exe = "Cripple"
            else:
                proc = psutil.Process(conn.pid)
                process_name, process_path, root_proc, original_exe = self._resolve_process_identity(proc)
                    
                # Enhance process name for generic runtimes (using root_proc)
                if process_name.lower() in ('python.exe', 'python3.exe', 'pythonw.exe', 'node.exe', 'java.exe', 'ruby.exe', 'javaw.exe', 'cmd.exe', 'powershell.exe'):
                    try:
                        cmdline = root_proc.cmdline()
                        cmd_str = " ".join(cmdline).lower()
                        if "antigravity" in cmd_str or "agy" in cmd_str:
                            process_name = "Antigravity"
                        elif len(cmdline) > 1:
                            script_arg = cmdline[1]
                            if script_arg.endswith(('.py', '.js', '.jar', '.rb')):
                                script_name = os.path.basename(script_arg)
                                process_name = f"{process_name} ({script_name})"
                    except Exception:
                        pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_name = "Unknown"
            process_path = ""

        ip = conn.raddr.ip
        port = conn.raddr.port
        protocol = "TCP" if conn.type == 1 else "UDP"
        
        # --- IoT Botnet Detection ---
        now = time.time()
        if ip not in self._rate_limits:
            self._rate_limits[ip] = []
        self._rate_limits[ip].append(now)
        
        if len(self._rate_limits[ip]) > 50:
            # Over 50 new connections to/from this IP within 1 second!
            if self.on_malware_detected:
                self.on_malware_detected({'name': 'botnet_behavior', 'message': f"IoT Botnet / Rapid Scan detected! {process_name} established >50 connections/sec to {ip}"})

        domain = self.db.get_cached_domain(ip)
        if not domain:
            # Basic check to avoid reversing loopback/local IPs
            is_local_ipv4 = ip in ("127.0.0.1", "0.0.0.0") or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.16.")
            is_local_ipv6 = ip in ("::1", "::") or ip.lower().startswith("fe80:") or ip.lower().startswith("fc00:") or ip.lower().startswith("fd00:")
            
            if not is_local_ipv4 and not is_local_ipv6:
                domain = "" # Default to empty, look up in background
                def _resolve_dns_bg(resolve_ip):
                    try:
                        default_timeout = socket.getdefaulttimeout()
                        socket.setdefaulttimeout(0.5)
                        name, _, _ = socket.gethostbyaddr(resolve_ip)
                        self.db.cache_domain_mapping(resolve_ip, name)
                    except socket.herror:
                        pass
                    finally:
                        socket.setdefaulttimeout(default_timeout)
                        
                self._dns_executor.submit(_resolve_dns_bg, ip)
            elif is_local_ipv4 and ip not in ("127.0.0.1", "0.0.0.0"):
                # --- Connection-level ARP Pinning ---
                if self.db.get_setting("lan_shield_enabled", "false") != "true":
                    def _arp_pinning_bg(check_ip):
                        import subprocess, re
                        try:
                            kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
                            res = subprocess.run(["arp", "-a"], capture_output=True, text=True, **kwargs)
                            mac = None
                            for line in res.stdout.splitlines():
                                if check_ip in line:
                                    match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', line)
                                    if match:
                                        mac = match.group(0).lower().replace('-', ':')
                                        break
                            if mac:
                                if check_ip in self._arp_cache and self._arp_cache[check_ip] != mac:
                                    if self.on_malware_detected:
                                        self.on_malware_detected({'name': 'arp_spoof_local', 'message': f"Deep ARP Pinning failed! {check_ip} MAC changed from {self._arp_cache[check_ip]} to {mac}. Spoofing detected!"})
                                self._arp_cache[check_ip] = mac
                        except Exception:
                            pass
                    self._dns_executor.submit(_arp_pinning_bg, ip)

        # Fetch corporate identity if we have a domain
        identity = self.classifier.blocklist.get_identity(domain) if domain else None

        # Classify by domain if we found one, else by IP
        target_to_classify = domain if domain else ip
        category = self.classifier.classify_domain(target_to_classify, process_name)
        
        # Pre-classification hook for DNS and VPN traffic
        is_dns = (port in (53, 853)) or (process_name == "dnscrypt-proxy.exe") or ("dns" in process_name.lower())
        
        # Unconditionally whitelist known third-party local DNS proxies so they can reach upstream DoH/DoT endpoints
        if process_name.lower() in ("dnscrypt-proxy.exe", "yogadns.exe", "unbound.exe", "stubby.exe"):
            category = ConnectionCategory.DNS
        elif is_dns and category == ConnectionCategory.UNKNOWN:
            category = ConnectionCategory.DNS
        elif (port == 443 and ip.startswith("10.")) and category == ConnectionCategory.UNKNOWN:
            # Often VPN DoH endpoints (like Mullvad)
            category = ConnectionCategory.DNS
            
        if category == ConnectionCategory.UNKNOWN: # Fixed fallback
            category, action = self.classifier.classify_ip(ip)
        else:
            action = self.classifier.mode.get_action_for_category(category, self.db)
             
        # Cripple Traffic Override
        if process_name == "Cripple (Internal)":
            category = ConnectionCategory.ESSENTIAL
            action = ConnectionAction.ALLOW

        conn_data = {
            'process_name': process_name,
            'process_path': process_path,
            'pid': conn.pid,
            'domain': domain,
            'ip': ip,
            'port': port,
            'protocol': protocol,
            'direction': direction,
            'status': getattr(conn, 'status', 'UNKNOWN'),
            'category': category.value,
            'action': action.value,
            'mode': self.classifier.mode.name,
            'identity': identity,
            'original_exe': original_exe
        }
        
        # Smart Paranoid Mode: If it's a known malware domain, alert engine
        if category.value == 'malware' and self.on_malware_detected:
            self.on_malware_detected(conn_data)

        # Log to DB
        self.db.log_connection(conn_data)
        
        # Increment Traffic Stats based on actual connections
        self.db.update_daily_stats(action.value, category.value)
        
        
        if self.on_status and target_to_classify not in self._notified_targets:
            if len(self._notified_targets) > 5000:
                self._notified_targets.clear()
            self._notified_targets.add(target_to_classify)
            if action.value == 'block':
                sound_manager.play_alert()
                self.on_status(f"Autoblocked {category.value.capitalize()}: {process_name} -> {target_to_classify}")
            elif action.value == 'allow' and category.value != 'unknown':
                self.on_status(f"Allowed {category.value.capitalize()}: {process_name} -> {target_to_classify}")

    def _handle_ebpf_event(self, ebpf_data):
        """Handle raw kernel connection events from eBPF for cross-verification."""
        ip = ebpf_data['ip']
        port = ebpf_data['port']
        pid = ebpf_data['pid']
        process_name = ebpf_data['process_name']
        
        # Create a signature to check against psutil known connections (match psutil format: PID:IP:PORT:LPORT:TYPE)
        conn_sig = f"{pid}:{ip}:{port}:0:1"
        
        if conn_sig not in self.known_connections:
            # If eBPF sees it but psutil hasn't, log it uniquely. 
            # We add it to known_connections so we don't log it twice if psutil catches up.
            self.known_connections.add(conn_sig)
            logger.warning(f"[eBPF verification] Captured direct kernel connection before/without user-space polling: {process_name} -> {ip}:{port}")
            
            # Formulate pseudo-connection object to feed into standard pipeline
            class PseudoConn:
                pass
            conn = PseudoConn()
            conn.pid = pid
            conn.raddr = PseudoConn()
            conn.raddr.ip = ip
            conn.raddr.port = port
            conn.type = 1 # TCP
            conn.laddr = None
            
            # Treat as outbound since it's caught at tcp_connect
            self._handle_new_connection(conn, conn_sig, direction="outbound")
