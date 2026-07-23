"""
Core Engine for NetStrip
The central orchestrator that initializes and manages all subsystems.
"""

import logging
import os
import time
import threading
import sys
from typing import Callable, Optional

import psutil

from netstrip.core.modes import ProtectionLevel, get_mode, ConnectionAction
from netstrip.data.database import Database
from netstrip.data.blocklist_manager import BlocklistManager
from netstrip.core.classifier import TrafficClassifier
from netstrip.core.dns_proxy import DNSProxyService
from netstrip.core.connection_monitor import ConnectionMonitor
from netstrip.core.firewall import FirewallController
from netstrip.core.lan_shield import LANShield
from netstrip.core.notifier import NotificationManager
from netstrip.core.updater import BlocklistUpdater
from netstrip.core.geoip import GeoIPService
from netstrip.core.network_monitor import NetworkMonitor
from netstrip.core.interceptor import get_interceptor
from netstrip.platform.base import get_platform
from netstrip.core.iot_local_api import IoTLocalAPI
from netstrip.core.iot_sync import IoTTelemetrySync

logger = logging.getLogger(__name__)

class NetStripEngine:
    def __init__(self, is_headless=False):
        self.is_headless = is_headless
        self.is_running = False
        self._stop_event = threading.Event()
        
        # Data layer
        self.db = Database()
        
        # Platform layer
        self.platform = get_platform()
        
        self.blocklist = BlocklistManager(db=self.db)
        self.classifier = TrafficClassifier(self.blocklist, db=self.db)
        
        # On Android, binding to port 53 is forbidden without root. Bind to 5353 instead.
        is_android = os.environ.get('NETSTRIP_ANDROID') == '1' or hasattr(sys, 'getandroidapilevel')
        dns_bind_ip = "127.0.0.1" if is_android else "127.127.127.127"
        dns_port = 5353 if is_android else 53
        
        self.dns_proxy = DNSProxyService(self.classifier, self.db, bind_ip=dns_bind_ip, port=dns_port, engine=self)
        poll_interval = 2.0 if self.is_headless else 0.2
        self.connection_monitor = ConnectionMonitor(self.classifier, self.db, poll_interval=poll_interval)
        
        self.firewall = FirewallController()
        self.lan_shield = LANShield(engine=self)
        self.notifier = NotificationManager(self.db)
        self.updater = BlocklistUpdater(self.blocklist.lists_dir)
        
        self.geoip = GeoIPService(self._handle_geoip_change, engine=self)
        self.network_monitor = NetworkMonitor(self._handle_network_change, engine=self)
        
        from netstrip.core.anomaly_scanner import AnomalyScanner
        self.anomaly_scanner = AnomalyScanner(engine=self)
        self.anomaly_scanner.set_callback(self._handle_anomaly)
        
        from netstrip.core.analytics import AnalyticsReporter
        self.analytics = AnalyticsReporter(engine=self)
        self._start_time = time.time()
        
        self.ebpf_manager = None
        if os.name != 'nt' and os.uname().sysname == 'Linux':
            from netstrip.platform.linux_ebpf import EBPFManager
            self.ebpf_manager = EBPFManager(interface="eth0") # Default fallback, will bind active later
        
        # Zero-leak interceptor
        self.interceptor = get_interceptor(self._evaluate_packet, engine=self)
        
        self.iot_sync = IoTTelemetrySync(self)
        self.iot_local_api = IoTLocalAPI(self)
        
        self.engine_ready = False
        self.interceptor.start() # Start immediately to catch early boot connections
        
        # Boost process priority to ensure GUI responsiveness and low-latency packet inspection
        try:
            p = psutil.Process(os.getpid())
            if sys.platform == 'win32':
                p.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
            else:
                p.nice(-5)
        except Exception:
            pass

        self.on_status_update: Callable = lambda x: None
        self.on_smart_trigger: Callable = None
        self.killswitch_active = False
        
        # HIGH-7: PID→process name cache to avoid costly psutil.Process().name() on every packet
        self._pid_name_cache = {}  # {pid: (name, timestamp)}
        self._pid_cache_ttl = 60  # seconds
        
        self.connection_monitor.on_new_connection = self._handle_new_connection
        self.connection_monitor.on_malware_detected = self._handle_malware_detected
        self.connection_monitor.on_status = self.broadcast_status
        self.dns_proxy.resolver.on_status = self.broadcast_status
        
        # GUI callbacks
        self.gui_update_callback: Callable = None
        self.on_critical_network_event: Callable = None
        
        self.watchdog_thread = None
        self.route_monitor_thread = None
        self._last_wan_local_ip = None
        
        # Updater state
        self.update_available = False
        self.latest_version = None

    def set_status_callback(self, callback: Callable):
        self.on_status_update = callback
        
    def broadcast_status(self, msg: str):
        if self.on_status_update:
            if not getattr(self, 'is_headless', False):
                # We are likely running in a background thread, so wrap it
                import tkinter as tk
                root = tk._default_root
                if root:
                    try:
                        root.after(0, lambda: self.on_status_update(msg))
                        return
                    except Exception:
                        pass
            
            # Headless or rootless fallback
            try:
                self.on_status_update(msg)
            except Exception:
                pass
                    
    def trigger_threat_escalation(self, threat_data: dict):
        """Escalate to Paranoid Mode + Killswitch and broadcast anomaly."""
        logger.critical(f"THREAT ESCALATION: {threat_data}")
        # Log to DB
        self.db.log_connection({
            'process_name': threat_data.get('process_name', 'KERNEL_ANOMALY'),
            'domain': threat_data.get('domain', 'SYSTEM_THREAT'),
            'category': 'ANOMALY',
            'action': 'block',
            'note': threat_data.get('note', '')
        })
        # Set modes
        self.set_mode(ProtectionLevel.PARANOID)
        self.set_killswitch(True)
        # Broadcast via LAN Shield
        if hasattr(self, 'lan_shield') and hasattr(self.lan_shield, 'broadcast_anomaly'):
            self.lan_shield.broadcast_anomaly(threat_data)
            
        # Broadcast via IoT Webhook (e.g. Home Assistant)
        webhook_url = self.db.get_setting("iot_webhook_url", "")
        if webhook_url and not threat_data.get('is_remote', False): # Prevent infinite webhook loops on LAN
            def send_webhook():
                try:
                    import requests
                    headers = {"Content-Type": "application/json"}
                    secret = self.db.get_setting("iot_webhook_secret", "")
                    if secret: headers["Authorization"] = f"Bearer {secret}"
                    requests.post(webhook_url, json=threat_data, headers=headers, timeout=3.0)
                except Exception as e:
                    logger.debug(f"IoT Webhook failed: {e}")
            import threading
            threading.Thread(target=send_webhook, daemon=True).start()

    def _handle_anomaly(self, anomaly_data: dict):
        logger.warning(f"Kernel Anomaly Detected: {anomaly_data['message']}")
        
        # 1. Instantly trigger CRITICAL threat escalation (Paranoid Mode + Killswitch)
        self.trigger_threat_escalation({
            'process_name': 'Kernel Bypass Scanner',
            'domain': 'SYSTEM ANOMALY',
            'threat_level': 'CRITICAL',
            'note': anomaly_data['message']
        })
        
        anomaly_name = anomaly_data.get('name', 'unknown')
        
        # 1.5. Persist the state for headless servers / system tray
        self.db.set_setting("pending_kernel_threat", f"{anomaly_name}|{anomaly_data['message']}")
        
        # 2. Fire OS Notification via Tray
        self.broadcast_status(f"CRITICAL ANOMALY: {anomaly_data['message']}")
        
        # 3. Always show GUI Popup (Even in headless mode, the hidden Tk root allows Toplevels)
        def _handle_decision(decision):
            self.db.set_setting("pending_kernel_threat", "")
            if decision == 'neutralize':
                logger.warning(f"User neutralized threat: {anomaly_name}")
                if 'adapter' in anomaly_data.get('type', '') and self.anomaly_scanner:
                    self.anomaly_scanner._neutralize_adapter(anomaly_name)
                elif 'software' in anomaly_data.get('type', '') and self.anomaly_scanner:
                    self.anomaly_scanner._neutralize_pcap()
            elif decision == 'whitelist':
                logger.info(f"User whitelisted anomaly: {anomaly_name}")
                self.db.whitelist_anomaly(anomaly_name)
                self.set_killswitch(False) # Restore network
            elif decision == 'disable_scanner':
                logger.warning("User disabled Kernel Anomaly Scanner.")
                self.db.set_setting("kernel_anomaly_scanner", "false")
                if self.anomaly_scanner:
                    self.anomaly_scanner.stop()
                self.set_killswitch(False) # Restore network
        
        try:
            import tkinter as tk
            from netstrip.gui.views.anomaly_alert import CTkAnomalyAlert
            
            # Get the root window from the App
            # We need to find the main root to attach the toplevel
            # The engine has access to the app or root via callbacks, but easiest is to just use tk._default_root
            root = tk._default_root
            if root:
                root.after(0, lambda: CTkAnomalyAlert(root, self, anomaly_data, _handle_decision))
            else:
                _handle_decision('neutralize')
        except Exception as e:
            logger.error(f"Failed to show Anomaly Alert GUI: {e}")
            _handle_decision('neutralize')

    def _evaluate_packet(self, dst_ip: str, dst_port: int, protocol: str, src_port: int, src_ip: str, is_inbound: bool = False) -> bool:
        """High-speed synchronous packet evaluation for WinDivert/NFQueue."""

        # SSH Safeguard: Always allow inbound SSH (port 22, 2222) when enabled.
        # This prevents lockout on headless/remote-managed devices during
        # killswitch, ghost mode, paranoid mode, or strict inbound shield.
        if is_inbound and dst_port in (22, 2222):
            ssh_safeguard = self.db.get_setting('ssh_safeguard', 'true' if self.is_headless else 'false')
            if ssh_safeguard == 'true':
                return True

        if self.killswitch_active:
            if dst_ip not in ("127.0.0.1", "127.127.127.127", "::1"):
                return False
                
        # Bypass loopback
        if dst_ip.startswith("127.") or dst_ip == "::1":
            return True
            
        if not getattr(self, 'engine_ready', True):
            return False
            
        # ----------------------------------------------------
        # INBOUND CONNECTION HANDLING
        # ----------------------------------------------------
        if is_inbound:
            # For inbound connections, the "remote attacker" is the src_ip
            remote_ip = src_ip
            
            strict_shield = self.db.get_setting('strict_inbound_shield', 'true') == 'true'
            if strict_shield:
                
                # Headless Admin Bypass / LAN Shield Bypass
                default_bypass = 'true' if self.is_headless else 'false'
                inbound_lan_bypass = self.db.get_setting('inbound_lan_bypass', default_bypass) == 'true'
                
                if inbound_lan_bypass:
                    import ipaddress
                    try:
                        if ipaddress.ip_address(remote_ip).is_private:
                            return True
                    except:
                        pass
                
                notify = self.db.get_setting('inbound_notifications', 'true') == 'true'
                if notify:
                    self.notifier.push({
                        'process_name': 'Inbound Shield',
                        'domain': remote_ip,
                        'protocol': protocol,
                        'category': 'security',
                        'action': 'block',
                        'ip': remote_ip,
                        'port': dst_port
                    })
                return False # Silently drop the packet
                
            # If Strict Shield is disabled, we evaluate the inbound connection
            # against our standard IP blocklists using the remote src_ip
            cat, action = self.classifier.classify_ip(remote_ip, dst_port, "Inbound Connection")
            if action == ConnectionAction.BLOCK or action == ConnectionAction.SINKHOLE:
                try:
                    self.db.log_connection({
                        'process_name': "Inbound Connection",
                        'domain': remote_ip,
                        'protocol': protocol,
                        'category': cat.value,
                        'action': action.value,
                        'mode': self.classifier.mode.name
                    })
                except:
                    pass
                return False
            return True
        # ----------------------------------------------------
            
        pid = self.connection_monitor.port_to_pid.get(src_port)
        process_name = "Unknown"
        if pid:
            if pid == os.getpid():
                # Allow NetStrip's own traffic (DNS upstream, updates)
                if self.classifier.mode.name == "PARANOID" and dst_port in (80, 443):
                    return False
                return True
            
            # HIGH-7: Use PID→name cache instead of psutil.Process().name() on every packet
            now = time.time()
            cached = self._pid_name_cache.get(pid)
            if cached and (now - cached[1]) < self._pid_cache_ttl:
                process_name = cached[0]
            else:
                try:
                    process_name = psutil.Process(pid).name()
                    self._pid_name_cache[pid] = (process_name, now)
                    # Evict stale entries periodically
                    if len(self._pid_name_cache) > 1000:
                        cutoff = now - self._pid_cache_ttl
                        self._pid_name_cache = {
                            k: v for k, v in self._pid_name_cache.items() if v[1] > cutoff
                        }
                except Exception:
                    pass
                
        cat, action = self.classifier.classify_ip(dst_ip, dst_port, process_name)
        
        if action == ConnectionAction.BLOCK or action == ConnectionAction.SINKHOLE:
            try:
                self.db.log_connection({
                    'process_name': process_name,
                    'domain': dst_ip, # IP if no domain
                    'protocol': protocol,
                    'category': cat.value,
                    'action': action.value,
                    'mode': self.classifier.mode.name
                })
            except:
                pass
            return False
            
        return True

    def start(self) -> bool:
        """Start all subsystems."""
        if self.is_running:
            return
            
        logger.info("Starting NetStrip Engine...")
        
        # Check permissions
        if False and not self.platform.is_admin():
            logger.error("Admin privileges required to start NetStrip.")
            return False

        # Clean up data older than 24 hours on initialization
        try:
            self.db.prune_old_logs(hours=24)
        except Exception as e:
            logger.error(f"Error wiping initial data: {e}")

        # Load settings
        saved_mode_str = self.db.get_setting("protection_mode", "NORMAL")
        try:
            self.set_mode(ProtectionLevel[saved_mode_str])
        except KeyError:
            self.set_mode(ProtectionLevel.NORMAL)

        # Wait for blocklists to finish loading (Splash screen runs concurrently)
        import time
        while hasattr(self, 'blocklist') and self.blocklist.is_loading:
            time.sleep(0.1)

        # Start subsystems
        self.interceptor.start()
        self.dns_proxy.start()
        self.connection_monitor.start()
        self.iot_sync.start()
        self.iot_local_api.start()
        self.geoip.start()
        self.network_monitor.start()
        self.anomaly_scanner.start()
        if hasattr(self.lan_shield, 'start'):
            self.lan_shield.start()
        if self.ebpf_manager and self.db.get_setting("linux_ebpf_mode", "false") == "true":
            self.ebpf_manager.start()
        
        # Start analytics reporter (opt-in only, off by default)
        self.analytics.start()
        
        # Start background updater
        threading.Thread(target=self._update_checker_loop, daemon=True).start()
        
    def _update_checker_loop(self):
        import urllib.request
        import json
        from netstrip import __version__
        while self.is_running:
            try:
                req = urllib.request.Request(
                    "https://api.github.com/repos/neohiro/Cripple-NetStrip/releases/latest",
                    headers={'User-Agent': f'Cripple/{__version__}'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    tag = data.get('tag_name', '').lstrip('v')
                    if tag and tag != __version__:
                        self.latest_version = tag
                        self.update_available = True
                        if hasattr(self, 'gui_update_callback') and self.gui_update_callback:
                            self.gui_update_callback("UPDATE_AVAILABLE")
            except Exception as e:
                logger.error(f"Failed to check for updates: {e}")
                
            # Sleep for 24 hours
            for _ in range(86400):
                if not self.is_running:
                    break
                time.sleep(1)
                
    def _blocklist_updater_loop(self):
        while self.is_running:
            self.updater.check_and_update()
            # Sleep for 1 hour between checks
            for _ in range(3600):
                if not self.is_running:
                    break
                time.sleep(1)
        
        # Hard-coded IP Kernel Blocking
        try:
            import os
            ip_blacklist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'lists', 'ip_blacklist.txt')
            if os.path.exists(ip_blacklist_path):
                with open(ip_blacklist_path, "r", encoding="utf-8") as f:
                    ips = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                if ips:
                    self.firewall.sync_ip_blocklist(ips)
                    logger.info(f"Injected {len(ips)} high-risk IPs into Windows Kernel Firewall.")
        except Exception as e:
            logger.error(f"Failed to inject IP blocklist: {e}")
        
        # Check for active local third-party DNS listeners (e.g. dnscrypt-proxy)
        detected_local_dns = self._detect_local_dns()
        
        # Set system DNS to local proxy for active interfaces
        for interface in self.platform.get_active_interfaces():
            current_upstream = self.db.get_setting("dns_upstream")
            
        # Re-apply global IPv6 block if user had it enabled in settings
        if self.db.get_setting("disable_ipv6_globally", "false") == "true":
            try:
                self.platform.disable_ipv6()
            except Exception as e:
                logger.error(f"Failed to re-apply global IPv6 block: {e}")
                
        # Re-apply global IPv4 block if user had it enabled in settings
        if self.db.get_setting("disable_ipv4_globally", "false") == "true":
            try:
                self.platform.disable_ipv4()
            except Exception as e:
                logger.error(f"Failed to re-apply global IPv4 block: {e}")

            # If the current upstream is corrupted/looping to itself, clear it
            if current_upstream == "127.127.127.127":
                current_upstream = None
                
            if detected_local_dns:
                ip, tool_name = detected_local_dns
                self.db.set_setting("local_dns_tool", tool_name)
                self.db.set_setting("local_dns_ip", ip)
                # If upstream is unset, default to the detected local proxy
                if not current_upstream:
                    self.db.set_setting("dns_upstream", ip)
            else:
                self.db.delete_setting("local_dns_tool") # Clear if no longer detected
                self.db.delete_setting("local_dns_ip")
                orig_dns = self.platform.get_original_dns(interface)
                if orig_dns and orig_dns not in ("127.127.127.127", "127.0.0.2"):
                    self.db.set_setting(f"backup_dns_{interface}", orig_dns)
                    if not current_upstream:
                        self.db.set_setting("dns_upstream", orig_dns)
                else:
                    self.db.set_setting(f"backup_dns_{interface}", "dhcp")
                    if not current_upstream:
                        self.db.set_setting("dns_upstream", "1.1.1.1") # Safe default
                
            self.platform.set_system_dns(interface, "127.127.127.127")
            
        # Trigger auto-update in background to prevent UI freeze
        # Now runs in a 1-hour loop for fast-updating threat lists
        threading.Thread(target=self._blocklist_updater_loop, daemon=True).start()
        
        self.is_running = True
        self.engine_ready = True
        
        # Start detached subprocess watchdog to ensure DNS is restored on hard crash
        import sys, os, subprocess
        if not getattr(sys, 'frozen', False) and not self.is_headless:
            # Start detached subprocess watchdog to ensure DNS is restored on hard crash
            # Hardening: Use strictly absolute paths and wipe environment variables to block DLL/PATH sideloading
            watchdog_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'watchdog.py'))
            if os.path.exists(watchdog_path):
                import subprocess
                is_frozen = getattr(sys, 'frozen', False)
                launch_cmd = [sys.executable] + sys.argv if not is_frozen else sys.argv
                cmd = [sys.executable, watchdog_path, str(os.getpid())] + launch_cmd
                try:
                    kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
                    self.watchdog_thread = subprocess.Popen(
                        cmd, 
                        env={'PATH': os.environ.get('PATH', ''), 'SYSTEMROOT': os.environ.get('SYSTEMROOT', '')}, 
                        **kwargs
                    )            
                    logger.info("Spawned detached crash recovery watchdog with relaunch capability.")
                except Exception as e:
                    logger.error(f"Failed to spawn watchdog: {e}")
        
        self.route_monitor_thread = threading.Thread(target=self._fast_route_monitor_loop, daemon=True)
        self.route_monitor_thread.start()
        
        logger.info("Cripple Engine started successfully.")
        self.broadcast_status("✅ Core Engine Initialized")
        return True

    def _detect_local_dns(self):
        """Scans loopback interfaces for active third-party UDP/TCP 53 listeners. Returns (ip, tool_name)"""
        try:
            import psutil
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr and conn.laddr.port == 53:
                    # Filter for active listeners (TCP LISTEN or UDP)
                    if conn.type == 2 or (conn.type == 1 and conn.status == 'LISTEN'):
                        ip = conn.laddr.ip
                        if ip in ("127.0.0.1", "::1", "127.0.0.2") or ip.startswith("127."):
                            # Ensure we don't accidentally detect our own proxy
                            if ip not in ("127.0.0.2", "127.127.127.127"):
                                import os
                                if conn.pid and conn.pid == os.getpid():
                                    continue # Ignore our own proxy listener!
                                    
                                process_name = "Unknown Tool"
                                try:
                                    if conn.pid:
                                        process_name = psutil.Process(conn.pid).name()
                                        if process_name.lower() in ('python.exe', 'pythonw.exe', 'python3.exe'):
                                            continue # Ignore python entirely just in case (e.g. child workers)
                                except Exception:
                                    pass
                                logger.info(f"Detected active third-party DNS proxy ({process_name}) at {ip}:53")
                                return ip, process_name
        except Exception as e:
            logger.error(f"Error scanning for local DNS: {e}")
        return None

    def stop(self):
        """Gracefully stop all subsystems and restore system state."""
        if not self.is_running:
            return
            
        logger.info("Stopping NetStrip Engine...")
        
        self.is_running = False
        self._stop_event.set()
        
        # Stop each subsystem individually — a failure in one must NOT prevent
        # critical cleanup (firewall rules, DNS restore) from running.
        for name, subsystem_stop in [
            ("interceptor", self.interceptor.stop),
            ("dns_proxy", self.dns_proxy.stop),
            ("connection_monitor", self.connection_monitor.stop),
            ("iot_sync", self.iot_sync.stop),
            ("iot_local_api", self.iot_local_api.stop),
            ("geoip", self.geoip.stop),
            ("network_monitor", self.network_monitor.stop),
            ("anomaly_scanner", self.anomaly_scanner.stop),
        ]:
            try:
                subsystem_stop()
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        
        if self.ebpf_manager:
            try:
                self.ebpf_manager.stop()
            except Exception as e:
                logger.error(f"Error stopping ebpf_manager: {e}")
        
        # Critical cleanup — must always execute
        try:
            self.firewall.clear_all_rules()
        except Exception as e:
            logger.error(f"Error clearing firewall rules: {e}")
        
        try:
            self.lan_shield.disable()
        except Exception as e:
            logger.error(f"Error disabling LAN shield: {e}")
        
        try:
            self.set_killswitch(False)
        except Exception as e:
            logger.error(f"Error disabling killswitch: {e}")
        
        # Write .clean_exit so watchdog knows this is a graceful shutdown
        try:
            import os
            from pathlib import Path
            clean_exit_path = Path.home() / ".netstrip" / ".clean_exit"
            clean_exit_path.parent.mkdir(parents=True, exist_ok=True)
            clean_exit_path.touch()
        except Exception as e:
            logger.error(f"Failed to write clean exit flag: {e}")
        
        # Restore system DNS
        try:
            for interface in self.platform.get_active_interfaces():
                original_dns = self.db.get_setting(f"backup_dns_{interface}", "dhcp")
                self.platform.restore_system_dns(interface, original_dns)
        except Exception as e:
            logger.error(f"Error restoring system DNS: {e}")
            
        # Re-enable global IPv6 so the user's internet is not permanently broken after exiting
        if self.db.get_setting("disable_ipv6_globally", "false") == "true":
            try:
                self.platform.enable_ipv6()
            except Exception as e:
                logger.error(f"Failed to restore global IPv6: {e}")
                
        # Re-enable global IPv4
        if self.db.get_setting("disable_ipv4_globally", "false") == "true":
            try:
                self.platform.enable_ipv4()
            except Exception as e:
                logger.error(f"Failed to restore global IPv4: {e}")
            
        if self.watchdog_thread:
            self.watchdog_thread.join(timeout=1.0)
        if self.route_monitor_thread:
            self.route_monitor_thread.join(timeout=1.0)
            
        logger.info("NetStrip Engine stopped.")

    def set_mode(self, level: ProtectionLevel):
        """Change the active protection mode."""
        self.classifier.set_mode(level)
        self.lan_shield.apply_mode(level)
        self.db.set_setting("protection_mode", level.name)
        
        # Load mode-specific user overrides
        mode_scope = "PARANOID" if level == ProtectionLevel.PARANOID else "STANDARD"
        rules = self.db.get_user_rules(mode_scope=mode_scope)
        if hasattr(self, 'blocklist'):
            self.blocklist.sync_user_rules(rules)
            
        def _sync_firewall(sync_rules):
            # Re-sync OS Firewall Rules for App Blocks
            self.platform.remove_all_app_block_rules()
            for r in sync_rules:
                if r['scope'] == 'app' and r['action'] == 'block' and r['note']:
                    self.platform.add_firewall_rule(
                        rule_name=f"NetStrip_AppBlock_{r['app_name']}",
                        direction="out",
                        action="block",
                        program=r['note']
                    )
        
        import threading
        threading.Thread(target=_sync_firewall, args=(rules,), daemon=True).start()
        
        if hasattr(self, 'connection_monitor') and hasattr(self.connection_monitor, 'known_connections'):
            self.connection_monitor.known_connections.clear()
            
        if level == ProtectionLevel.PARANOID:
            self.firewall.apply_paranoid_mode()
            
        logger.info(f"Mode changed to: {level.name}. Loaded {len(rules)} '{mode_scope}' user rules.")
        self.broadcast_status(f"🔰 Protection level changed to {level.name}")

    def _handle_new_connection(self, conn_data):
        """Callback from connection monitor for new connections."""
        if conn_data['action'] == ConnectionAction.ASK.value:
            self.notifier.push(conn_data)

    def _handle_malware_detected(self, conn_data):
        """Smart Shield Escalation."""
        current_mode = self.db.get_setting("protection_mode", "NORMAL")
        if current_mode != "PARANOID" and self.db.get_setting("smart_paranoid_mode", "true") == "true":
            logger.warning("ANOMALY: High threat detected. Smart Shield escalating to Paranoid Mode.")
            self.set_mode(ProtectionLevel.PARANOID)
            self.notifier.push({
                'process_name': 'Smart Shield',
                'domain': 'SYSTEM ESCALATION',
                'category': 'security',
                'action': 'block',
                'ip': 'System locked down to Paranoid Mode due to high threat anomaly.'
            })
            if self.on_smart_trigger:
                self.on_smart_trigger(conn_data)

    def set_killswitch(self, active: bool, broadcast_lan: bool = True):
        self.killswitch_active = active
        if active:
            self.platform.enable_killswitch()
            self.lan_shield.enable()
            if broadcast_lan and hasattr(self.lan_shield, 'broadcast_killswitch'):
                self.lan_shield.broadcast_killswitch()
        else:
            self.platform.disable_killswitch()
            if broadcast_lan and hasattr(self.lan_shield, 'broadcast_restore'):
                self.lan_shield.broadcast_restore()

    def _handle_geoip_change(self, old_ip: str, geo_data: dict):
        if old_ip in ('Loading...', 'Unknown', 'PARANOID MODE'):
            return
        new_ip = geo_data['ip']
        self._evaluate_network_event(f"Public IP changed from {old_ip} to {new_ip}", is_ip_flux=True)

    def _handle_network_change(self, event_data: dict):
        self._evaluate_network_event(event_data['message'], is_ip_flux=False)

    def _evaluate_network_event(self, message: str, is_ip_flux: bool = False):
        ip_flux_allowed = self.db.get_setting("ip_flux_tolerance", "false") == "true"
        
        # If it's a dynamic IP change and Flux Tolerance is ON, ignore it.
        if is_ip_flux and ip_flux_allowed:
            logger.info(f"IP Flux Tolerance active. Ignoring: {message}")
            return
            
        logger.critical(f"Network Intrusion/Anomaly Detected: {message}. ENGAGING AUTO-KILLSWITCH.")
        self.set_killswitch(True)
        
        # Send OS desktop notification
        try:
            from plyer import notification
            notification.notify(
                title="NetStrip: INTERNET KILLED",
                message=message,
                app_name="NetStrip",
                timeout=10
            )
        except Exception:
            pass

        if self.on_critical_network_event:
            self.on_critical_network_event(message)

    def _watchdog_loop(self):
        """Ensure DNS is restored, poll for Scheduled Killswitch, and clear expired Time Bombs."""
        from datetime import datetime
        last_cleanup = 0
        while self.is_running:
            try:
                # Clean up expired user rules (Time Bombs) every 10 seconds
                if time.time() - last_cleanup > 10:
                    cleaned_count = self.db.cleanup_expired_rules()
                    if cleaned_count > 0:
                        logger.info(f"Time Bomb triggered: Reverted {cleaned_count} expired app permissions.")
                        self.broadcast_status(f"💥 Time Bomb triggered: Reverted {cleaned_count} expired permissions")
                        # Sync DB rules to memory
                        if hasattr(self.blocklist, 'sync_user_rules'):
                            current_level = self.classifier.mode.name if hasattr(self.classifier, 'mode') else "STANDARD"
                            scope = "PARANOID" if current_level.upper() == "PARANOID" else "STANDARD"
                            self.blocklist.sync_user_rules(self.db.get_user_rules(mode_scope=scope))
                    last_cleanup = time.time()
                
                # Scheduled Killswitch Check
                schedule_enabled = self.db.get_setting("killswitch_schedule_enabled", "false") == "true"
                
                if schedule_enabled:
                    now = datetime.now()
                    current_time = now.strftime("%H:%M")
                    start_time = self.db.get_setting("killswitch_start", "23:00")
                    end_time = self.db.get_setting("killswitch_end", "07:00")
                    
                    # Handle overnight wrapping (e.g., 23:00 to 07:00)
                    is_scheduled = False
                    if start_time < end_time:
                        is_scheduled = start_time <= current_time <= end_time
                    else: # Wraps around midnight
                        is_scheduled = current_time >= start_time or current_time <= end_time
                    
                    if is_scheduled and not self.killswitch_active:
                        self.set_killswitch(True)
                        if self.on_critical_network_event:
                            self.on_critical_network_event("Scheduled Downtime Window Active")
            except Exception as e:
                logger.error(f"Watchdog error: {e}")
            
            self._stop_event.wait(60.0) # Poll every minute
                
    def _fast_route_monitor_loop(self):
        """Monitors for routing changes (like connecting to a new Wi-Fi) and rapidly re-applies DNS hijacking."""
        import time
        last_interfaces = self.platform.get_active_interfaces()
        while self.is_running and not self._stop_event.is_set():
            time.sleep(3)
            current_interfaces = self.platform.get_active_interfaces()
            if set(current_interfaces) != set(last_interfaces):
                logger.info("Network topology change detected, re-applying DNS hooks...")
                for interface in current_interfaces:
                    if interface not in last_interfaces:
                        self.platform.set_system_dns(interface, "127.127.127.127")
                last_interfaces = current_interfaces
            
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 53))
                current_local_ip = s.getsockname()[0]
                s.close()
                
                # If we have a tracked IP and it just changed, the routing table shifted
                if self._last_wan_local_ip and current_local_ip != self._last_wan_local_ip:
                    # Ignore loopback/disconnected shifts
                    if not current_local_ip.startswith("127."):
                        logger.warning(f"Kernel Route Shift! Default interface IP changed from {self._last_wan_local_ip} to {current_local_ip}")
                        # Immediately trigger flux response (Killswitch)
                        self._evaluate_network_event(f"Kernel Routing Shift: Interface IP changed to {current_local_ip}", is_ip_flux=True)
                
                self._last_wan_local_ip = current_local_ip
            except Exception:
                pass
                
            self._stop_event.wait(0.1) # 100 milliseconds
