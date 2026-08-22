"""
Connection Monitor for NetStrip
Uses psutil to poll network connections, mapping them to process names.
"""

try:
    import psutil
except ImportError:
    class DummyPsutil:
        class Error(Exception): pass
        class NoSuchProcess(Exception): pass
        class AccessDenied(Exception): pass
        
        @staticmethod
        def net_connections(*args, **kwargs):
            return []
            
        class Process:
            def __init__(self, pid):
                raise self.NoSuchProcess()
                
    psutil = DummyPsutil()
import threading
import time
import logging
import socket
import sys
import os
import concurrent.futures
from typing import Callable
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


def _looks_like_system_owner(process_name: str) -> bool:
    """True when a connection owner is an OS daemon / service-host grouping."""
    from netstrip.core.process_utils import is_system_process
    return is_system_process(process_name)


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
        
        # Origin process port and domain maps for System Idle resolution
        self._port_to_process_map = {}
        self._domain_to_process_map = {}
        self._origin_map_lock = threading.Lock()
        
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
        except (psutil.AccessDenied, PermissionError):
            logger.warning("Access Denied when getting net_connections. Need admin privileges or unsupported on this OS (e.g., Android).")
            return
        except Exception as e:
            logger.debug(f"psutil net_connections error: {e}")
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
            if not conn.raddr or conn.pid is None or not hasattr(conn.raddr, 'ip'):
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
        """Ascend the process tree to find the root parent application using process_utils."""
        from netstrip.core.process_utils import resolve_process_identity
        return resolve_process_identity(proc)

    def _handle_new_connection(self, conn, conn_sig, direction):
        original_exe = "Unknown"
        lport = conn.laddr.port if getattr(conn, 'laddr', None) else None
        now_ts = time.time()
        
        try:
            if conn.pid == os.getpid():
                process_name = "Cripple (Internal)"
                process_path = sys.executable
                original_exe = "Cripple"
            elif conn.pid in (0, 4):
                process_name = "System Idle Process" if conn.pid == 0 else "System (Kernel/Driver)"
                process_path = "System"
                original_exe = "System"
                
                # Check if local port or domain belongs to a real origin application
                with self._origin_map_lock:
                    if lport and lport in self._port_to_process_map:
                        cached_name, cached_path, cached_exe, cached_ts = self._port_to_process_map[lport]
                        if now_ts - cached_ts < 120.0:
                            process_name, process_path, original_exe = cached_name, cached_path, cached_exe
            else:
                proc = psutil.Process(conn.pid)
                process_name, process_path, root_proc, original_exe = self._resolve_process_identity(proc)
                
                # Record local port -> origin process mapping for system socket resolution
                if lport and process_name not in ("System Idle Process", "System (Kernel/Driver)"):
                    with self._origin_map_lock:
                        if len(self._port_to_process_map) > 2000:
                            self._port_to_process_map = {k: v for k, v in self._port_to_process_map.items() if now_ts - v[3] < 120.0}
                        self._port_to_process_map[lport] = (process_name, process_path, original_exe, now_ts)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_name = f"Unknown (PID {conn.pid})"
            process_path = ""

        ip = conn.raddr.ip
        port = conn.raddr.port
        protocol = "TCP" if conn.type == 1 else "UDP"
        
        # Second-stage resolution: if domain is available and process is still System, resolve via domain map
        domain = self.db.get_cached_domain(ip)
        if domain and process_name in ("System Idle Process", "System (Kernel/Driver)"):
            with self._origin_map_lock:
                if domain in self._domain_to_process_map:
                    cached_name, cached_path, cached_exe, cached_ts = self._domain_to_process_map[domain]
                    if now_ts - cached_ts < 300.0:
                        process_name, process_path, original_exe = cached_name, cached_path, cached_exe
        elif domain and process_name not in ("System Idle Process", "System (Kernel/Driver)"):
            with self._origin_map_lock:
                if len(self._domain_to_process_map) > 2000:
                    self._domain_to_process_map = {k: v for k, v in self._domain_to_process_map.items() if now_ts - v[3] < 300.0}
                self._domain_to_process_map[domain] = (process_name, process_path, original_exe, now_ts)
        
        # --- Self-service target re-attribution ---
        # GeoIP (ipwho.is / ipinfo.io / ipapi.co ...), update and telemetry endpoints
        # contacted by Cripple's own background services must never be shown under a
        # wrong process. Kernel-attributed sockets (PID 0/4), unresolvable PIDs and
        # OS daemon owners are re-attributed to "Cripple (Internal)".
        from netstrip.core.process_utils import SELF_SERVICE_TARGETS
        _t_host = str(domain or "").lower().rstrip('.')
        if _t_host:
            _is_self_target = (
                _t_host in SELF_SERVICE_TARGETS
                or any(_t_host.endswith("." + t) for t in SELF_SERVICE_TARGETS)
            )
            if _is_self_target and (
                conn.pid in (None, 0, 4, os.getpid())
                or process_name.startswith(("Unknown", "System"))
                or _looks_like_system_owner(process_name)
            ):
                process_name = "Cripple (Internal)"
                process_path = sys.executable
                original_exe = "Cripple"
        
        # --- IoT Botnet Detection ---
        now = time.time()
        if len(self._rate_limits) > 1000:
            # Periodic cleanup of idle IPs
            self._rate_limits = {k: v for k, v in self._rate_limits.items() if v and (now - v[-1]) < 5.0}
            
        if ip not in self._rate_limits:
            self._rate_limits[ip] = []
        self._rate_limits[ip] = [t for t in self._rate_limits[ip] if (now - t) < 2.0]
        self._rate_limits[ip].append(now)
        
        if len(self._rate_limits[ip]) > 50:
            # Over 50 new connections to/from this IP within 1 second!
            if self.on_malware_detected:
                self.on_malware_detected({'name': 'botnet_behavior', 'message': f"IoT Botnet / Rapid Scan detected! {process_name} established >50 connections/sec to {ip}"})

        if not domain:
            # Basic check to avoid reversing loopback/local IPs
            is_local_ipv4 = ip in ("127.0.0.1", "0.0.0.0") or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.16.")
            is_local_ipv6 = ip in ("::1", "::") or ip.lower().startswith("fe80:") or ip.lower().startswith("fc00:") or ip.lower().startswith("fd00:")
            
            if not is_local_ipv4 and not is_local_ipv6:
                domain = "" # Default to empty, look up in background
                if not hasattr(self, '_pending_dns_lookups'):
                    self._pending_dns_lookups = set()
                if ip not in self._pending_dns_lookups and len(self._pending_dns_lookups) < 100:
                    self._pending_dns_lookups.add(ip)
                    def _resolve_dns_bg(resolve_ip):
                        try:
                            name, _, _ = socket.gethostbyaddr(resolve_ip)
                            if name:
                                self.db.cache_domain_mapping(resolve_ip, name)
                        except (socket.herror, socket.gaierror, OSError):
                            pass
                        finally:
                            if hasattr(self, '_pending_dns_lookups'):
                                self._pending_dns_lookups.discard(resolve_ip)
                            
                    try:
                        self._dns_executor.submit(_resolve_dns_bg, ip)
                    except Exception:
                        self._pending_dns_lookups.discard(ip)
            elif is_local_ipv4 and ip not in ("127.0.0.1", "0.0.0.0"):
                # --- Connection-level ARP Pinning (Rate-limited to once every 5 seconds) ---
                now_ts = time.time()
                if getattr(self, '_last_arp_check', 0) + 5.0 < now_ts:
                    self._last_arp_check = now_ts
                    if self.db.get_setting("lan_shield_enabled", "false") != "true":
                        def _arp_pinning_bg(check_ip):
                            import subprocess, re
                            try:
                                kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
                                res = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=2.0, **kwargs)
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
                                    
                                    # Prevent memory leak for ARP cache
                                    if len(self._arp_cache) > 2000:
                                        self._arp_cache = {k: v for i, (k, v) in enumerate(self._arp_cache.items()) if i > 1000}
                            except Exception:
                                pass
                        try:
                            self._dns_executor.submit(_arp_pinning_bg, ip)
                        except Exception:
                            pass

        # Fetch corporate identity if we have a domain
        identity = self.classifier.blocklist.get_identity(domain) if domain else None
        
        # Force "Unknown" processes to display their Corporate Identity if known
        if process_name.startswith("Unknown") and identity:
            process_name = f"Unknown ({identity})"

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
