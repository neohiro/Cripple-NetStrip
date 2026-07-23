"""
NetStrip - Main Entry Point
Checks privileges, starts the core engine, and launches the GUI.
"""

import sys
import os
import logging
import signal
import time

# If this process was launched successfully (e.g. as an elevated process), 
# assassinate the restricted parent process so we don't have duplicate GUIs.
if "--parent-pid" in sys.argv:
    try:
        idx = sys.argv.index("--parent-pid")
        parent_pid = int(sys.argv[idx + 1])
        os.kill(parent_pid, signal.SIGTERM)
        # Remove these from argv so they don't interfere with anything else
        sys.argv.pop(idx)
        sys.argv.pop(idx)
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Anti-Exploit Mitigation: Enforce strict DLL directory search path on Windows (LOAD_LIBRARY_SEARCH_SYSTEM32)
try:
    if sys.platform == 'win32':
        import ctypes
        myappid = 'NetStrip.app.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        ctypes.windll.kernel32.SetDefaultDllDirectories(0x00000800)
except Exception:
    pass

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

def check_dependencies():
    missing = []
    is_android = os.environ.get('NETSTRIP_ANDROID') == '1' or hasattr(sys, 'getandroidapilevel')
    
    if not is_android:
        try:
            import customtkinter
        except ImportError:
            missing.append("customtkinter")
            
        try:
            import PIL
        except ImportError:
            missing.append("Pillow")
            
    try:
        import psutil
    except ImportError:
        missing.append("psutil")
        
    try:
        import dnslib
    except ImportError:
        missing.append("dnslib")
        
    if missing:
        if "--service" not in sys.argv:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Missing Dependencies", f"Please install required dependencies: {', '.join(missing)}")
        else:
            print(f"Missing Dependencies: {', '.join(missing)}")
        sys.exit(1)

def is_server_or_embedded():
    """Detects if we are running on a server OS, or a low-resource embedded system like a Raspberry Pi."""
    import platform
    import os
    
    # Check Windows Server
    if platform.system() == 'Windows':
        if 'Server' in platform.win32_ver()[0]:
            return True
            
    # Check Linux Server (Ubuntu Server, Debian headless, etc.) or missing display
    if platform.system() == 'Linux':
        if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            return True
            
        try:
            with open('/etc/os-release', 'r') as f:
                os_release = f.read().lower()
                if 'server' in os_release:
                    return True
        except Exception:
            pass
            
    machine = platform.machine().lower()
    if machine in ('armv7l', 'aarch64', 'armv6l'):
        try:
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read().lower()
                if 'raspberry pi' in model or 'orange pi' in model or 'bananapi' in model:
                    return True
        except FileNotFoundError:
            pass
            
    # Android check
    if os.environ.get('NETSTRIP_ANDROID') == '1' or hasattr(sys, 'getandroidapilevel'):
        return True
        
    return False

def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(f"\n{'='*60}")
        print(f"  Cripple (NetStrip) v3.1.0 — CLI / Daemon")
        print(f"{'='*60}")
        print("\nBOOT VARIABLES:")
        print("  --service              Headless/daemon mode (no GUI).")
        print("  --blockinbound         Block ALL inbound connections (strict isolation).")
        print("  --allowlan             Permit LAN connections even in strict modes.")
        print("  --android              Force Android/Mobile layout for UI testing.")
        print("\nDIRECT COMMANDS (no running daemon needed):")
        print("  --set-psk <KEY>        Set LAN Shield PSK (44-char Fernet key).")
        print("  --get-psk              Display the current LAN Shield PSK.")
        print("  --set <key> <value>    Set any engine setting directly in the database.")
        print("  --get <key>            Get any engine setting from the database.")
        print("  --set-telemetry-token <PAT>  Save GitHub telemetry token.")
        print("  --export <file.json>   Export full settings/rules profile to JSON.")
        print("  --import <file.json>   Import settings/rules profile from JSON.")
        print("\nLIVE IPC COMMANDS (sent to running daemon):")
        print("  --block <domain>       Add domain to user blocklist.")
        print("  --allow <domain>       Add domain to user allowlist.")
        print("  --mode <MODE>          Switch mode: LOOSE, STANDARD, STRICT, PARANOID.")
        print("  --status               Print daemon status, mode, and active threats.")
        print("  --stats                Print 24h connection statistics.")
        print("  --allow-anomaly <name> Whitelist a kernel threat and unlock system.")
        print("  --killswitch           Engage the master killswitch (drop all traffic).")
        print("  --unkillswitch         Disengage the master killswitch.")
        print("  --ghost                Engage Ghost Mode (total network isolation).")
        print("  --unghost              Disengage Ghost Mode.")
        print("  --update-blocklists    Force an immediate blocklist refresh.")
        print("  --trust-wifi <SSID>    Mark a WiFi network as trusted for LAN Shield.")
        print("  --untrust-wifi <SSID>  Remove a WiFi network from trusted list.")
        print(f"{'='*60}\n")
        sys.exit(0)

    # --- Direct database commands (no running daemon needed) ---
    def _get_db():
        from pathlib import Path
        from netstrip.data.database import Database
        db_path = Path.home() / ".netstrip" / "netstrip.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return Database(str(db_path))

    # Handle telemetry token setup
    if "--set-telemetry-token" in sys.argv:
        try:
            idx = sys.argv.index("--set-telemetry-token")
            token = sys.argv[idx + 1]
            db = _get_db()
            db.set_setting("telemetry_github_token", token)
            db.stop()
            print(f"Telemetry token saved successfully.")
        except (IndexError, ValueError):
            print("Usage: --set-telemetry-token <GITHUB_PAT>")
        except Exception as e:
            print(f"Error saving token: {e}")
        sys.exit(0)

    # PSK management
    if "--set-psk" in sys.argv:
        try:
            idx = sys.argv.index("--set-psk")
            psk = sys.argv[idx + 1].strip()
            # Validate Fernet key format
            if len(psk) != 44 or not psk.endswith('='):
                print("Error: PSK must be a 44-character Fernet key (base64 ending with '=').")
                sys.exit(1)
            try:
                from cryptography.fernet import Fernet
                Fernet(psk.encode('utf-8'))  # Validates structure
            except Exception:
                print("Error: Invalid Fernet key format.")
                sys.exit(1)
            db = _get_db()
            db.set_setting("lan_shield_psk", psk)
            db.stop()
            print(f"LAN Shield PSK saved successfully.")
            print(f"Restart the daemon for the new key to take effect, or use the GUI which hot-reloads.")
        except IndexError:
            print("Usage: --set-psk <44-char-Fernet-key>")
        except Exception as e:
            print(f"Error saving PSK: {e}")
        sys.exit(0)

    if "--get-psk" in sys.argv:
        try:
            db = _get_db()
            psk = db.get_setting("lan_shield_psk", "")
            db.stop()
            if psk:
                print(f"LAN Shield PSK: {psk}")
                print(f"Copy this key to other Cripple instances on your LAN to pair them.")
            else:
                print("No PSK configured yet. Start the daemon once to auto-generate, or use --set-psk.")
        except Exception as e:
            print(f"Error reading PSK: {e}")
        sys.exit(0)

    # Generic settings get/set
    if "--set" in sys.argv and "--set-psk" not in sys.argv and "--set-telemetry-token" not in sys.argv:
        try:
            idx = sys.argv.index("--set")
            key = sys.argv[idx + 1]
            value = sys.argv[idx + 2]
            db = _get_db()
            db.set_setting(key, value)
            db.stop()
            print(f"Setting '{key}' = '{value}' saved.")
        except IndexError:
            print("Usage: --set <key> <value>")
        except Exception as e:
            print(f"Error: {e}")
        sys.exit(0)

    if "--get" in sys.argv and "--get-psk" not in sys.argv:
        try:
            idx = sys.argv.index("--get")
            key = sys.argv[idx + 1]
            db = _get_db()
            value = db.get_setting(key, "(not set)")
            db.stop()
            print(f"{key} = {value}")
        except IndexError:
            print("Usage: --get <key>")
        except Exception as e:
            print(f"Error: {e}")
        sys.exit(0)

    # Profile export/import
    if "--export" in sys.argv:
        try:
            idx = sys.argv.index("--export")
            filepath = sys.argv[idx + 1]
            db = _get_db()
            profile = db.export_profile()
            db.stop()
            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=2)
            print(f"Profile exported to {filepath}")
        except IndexError:
            print("Usage: --export <output.json>")
        except Exception as e:
            print(f"Error: {e}")
        sys.exit(0)

    if "--import" in sys.argv:
        try:
            idx = sys.argv.index("--import")
            filepath = sys.argv[idx + 1]
            import json
            with open(filepath, 'r', encoding='utf-8') as f:
                profile = json.load(f)
            db = _get_db()
            db.import_profile(profile)
            db.stop()
            print(f"Profile imported from {filepath}")
        except IndexError:
            print("Usage: --import <input.json>")
        except Exception as e:
            print(f"Error: {e}")
        sys.exit(0)

    is_fallback = "--fallback-admin" in sys.argv
    is_elevated_retry = "--elevated" in sys.argv

    # Install global crash reporter hook
    try:
        from netstrip.core.crash_reporter import install_global_exception_hook
        install_global_exception_hook()
    except Exception:
        pass

    from netstrip.platform.base import get_platform
    platform = get_platform()

    # If we are NOT admin, and we haven't already tried elevating...
    if not platform.is_admin() and not is_elevated_retry and not is_fallback:
        # We need to elevate IMMEDIATELY before loading heavy engine components.
        import tkinter as tk
        from tkinter import messagebox
        import subprocess
        
        # Request elevation. This will spawn a new process.
        success = platform.request_admin(os.path.abspath(__file__))
        
        if success:
            # The elevated child will kill us (parent-pid). We just wait to die.
            time.sleep(10)
            sys.exit(0)
        else:
            # User declined UAC or it failed. Continue in restricted mode. # Re-show for restricted loading
            messagebox.showwarning(
                "Elevation Declined", 
                "Cripple will run in restricted mode. Core firewall and DNS sinkhole features will be disabled or limited."
            )
    elif not is_fallback:
        pass

    setup_logging()
    logger = logging.getLogger("Cripple")
    logger.info("Starting Cripple Initialization...")

    check_dependencies()

    is_embedded = is_server_or_embedded()
    is_headless = "--service" in sys.argv or is_embedded
    
    # --- CLI Boot Overrides ---
    if "--blockinbound" in sys.argv:
        # Force strict isolation (overrides auto-server detection)
        # We don't have the engine loaded yet, so we'll pass this as a flag to engine
        pass
    if "--allowlan" in sys.argv:
        pass

    # --- IPC Single-Instance Check ---
    import socket
    IPC_PORT = 54321
    ipc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    is_primary_instance = False
    try:
        ipc_socket.bind(('127.0.0.1', IPC_PORT))
        ipc_socket.listen(1)
        is_primary_instance = True
    except OSError:
        # Another instance is already running
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', IPC_PORT))
            client.settimeout(5.0)
            
            # CLI Management Commands
            if "--block" in sys.argv:
                domain = sys.argv[sys.argv.index("--block") + 1]
                client.sendall(f"BLOCK:{domain}\n".encode())
                print(f"✓ Sent block command for {domain}")
            elif "--allow" in sys.argv:
                domain = sys.argv[sys.argv.index("--allow") + 1]
                client.sendall(f"ALLOW:{domain}\n".encode())
                print(f"✓ Sent allow command for {domain}")
            elif "--mode" in sys.argv:
                mode = sys.argv[sys.argv.index("--mode") + 1]
                client.sendall(f"MODE:{mode}\n".encode())
                print(f"✓ Mode changed to {mode.upper()}")
            elif "--allow-anomaly" in sys.argv:
                anomaly = sys.argv[sys.argv.index("--allow-anomaly") + 1]
                client.sendall(f"ALLOWANOMALY:{anomaly}\n".encode())
                print(f"✓ Whitelisted anomaly: {anomaly}")
            elif "--killswitch" in sys.argv and "--unkillswitch" not in sys.argv:
                client.sendall(b"KILLSWITCH:ON\n")
                print("✓ Master Killswitch ENGAGED — all traffic dropped")
            elif "--unkillswitch" in sys.argv:
                client.sendall(b"KILLSWITCH:OFF\n")
                print("✓ Master Killswitch DISENGAGED")
            elif "--ghost" in sys.argv and "--unghost" not in sys.argv:
                client.sendall(b"GHOST:ON\n")
                print("✓ Ghost Mode ENGAGED — total network isolation")
            elif "--unghost" in sys.argv:
                client.sendall(b"GHOST:OFF\n")
                print("✓ Ghost Mode DISENGAGED")
            elif "--update-blocklists" in sys.argv:
                client.sendall(b"UPDATE_BLOCKLISTS\n")
                print("✓ Blocklist refresh triggered")
            elif "--trust-wifi" in sys.argv:
                ssid = sys.argv[sys.argv.index("--trust-wifi") + 1]
                client.sendall(f"TRUSTWIFI:{ssid}\n".encode())
                print(f"✓ WiFi '{ssid}' marked as trusted")
            elif "--untrust-wifi" in sys.argv:
                ssid = sys.argv[sys.argv.index("--untrust-wifi") + 1]
                client.sendall(f"UNTRUSTWIFI:{ssid}\n".encode())
                print(f"✓ WiFi '{ssid}' removed from trusted list")
            elif "--status" in sys.argv:
                client.sendall(b"STATUS\n")
                response = client.recv(4096).decode()
                print(response)
            elif "--stats" in sys.argv:
                client.sendall(b"STATS\n")
                response = client.recv(4096).decode()
                print(response)
            elif "--service" in sys.argv:
                print("Daemon is already running in the background.")
                sys.exit(0)
            else:
                client.sendall(b"SHOW_GUI\n")
                print("NetStrip is already running. Showing existing GUI.")
            client.close()
        except Exception as e:
            print(f"Failed to communicate with running daemon: {e}")
        sys.exit(0)

    import threading
    engine_instance = None
    app = None

    # --- IPC Listener Thread ---
    def ipc_listener():
        while True:
            try:
                conn, addr = ipc_socket.accept()
                
                # Sanity check: Only accept local connections
                if addr[0] not in ('127.0.0.1', '::1'):
                    conn.close()
                    continue
                    
                # Sanity check: Buffer limit to prevent memory exhaustion (local DoS)
                data = conn.recv(1024)
                if len(data) > 1000:
                    conn.close()
                    continue
                    
                data = data.decode()
                import re
                
                if "SHOW_GUI" in data and app:
                    app.after(0, app.deiconify)
                    app.after(50, app.lift)
                    app.after(100, app.focus_force)
                    
                if engine_instance:
                    if data.startswith("BLOCK:"):
                        domain = data.split("BLOCK:")[1].strip()
                        if re.match(r'^[a-zA-Z0-9.\-_*]{1,253}$', domain):
                            engine_instance.db.add_user_rule(domain, "block", "global", "Added via CLI")
                            engine_instance.classifier.user_rules[domain] = "block"
                    elif data.startswith("ALLOW:"):
                        domain = data.split("ALLOW:")[1].strip()
                        if re.match(r'^[a-zA-Z0-9.\-_*]{1,253}$', domain):
                            engine_instance.db.add_user_rule(domain, "allow", "global", "Added via CLI")
                            engine_instance.classifier.user_rules[domain] = "allow"
                    elif data.startswith("MODE:"):
                        mode_str = data.split("MODE:")[1].strip().upper()
                        from netstrip.core.modes import ProtectionLevel
                        if hasattr(ProtectionLevel, mode_str):
                            engine_instance.set_mode(ProtectionLevel[mode_str])
                    elif data.startswith("ALLOWANOMALY:"):
                        anomaly = data.split("ALLOWANOMALY:")[1].strip()
                        engine_instance.db.whitelist_anomaly(anomaly)
                        logger.info(f"Whitelisted anomaly via CLI IPC: {anomaly}")
                        pending = engine_instance.db.get_setting("pending_kernel_threat", "")
                        if pending.startswith(anomaly):
                            engine_instance.db.set_setting("pending_kernel_threat", "")
                            engine_instance.set_killswitch(False)
                    elif data.startswith("KILLSWITCH:"):
                        state = data.split("KILLSWITCH:")[1].strip().upper()
                        engine_instance.set_killswitch(state == "ON")
                        logger.info(f"Killswitch {'engaged' if state == 'ON' else 'disengaged'} via CLI")
                    elif data.startswith("GHOST:"):
                        state = data.split("GHOST:")[1].strip().upper()
                        if state == "ON":
                            engine_instance.db.set_setting("ghost_mode", "true")
                            engine_instance.set_killswitch(True)
                            logger.warning("Ghost Mode engaged via CLI — total network isolation")
                        else:
                            engine_instance.db.set_setting("ghost_mode", "false")
                            engine_instance.set_killswitch(False)
                            logger.info("Ghost Mode disengaged via CLI")
                    elif data.startswith("UPDATE_BLOCKLISTS"):
                        if hasattr(engine_instance, 'updater') and engine_instance.updater:
                            engine_instance.updater.check_and_update()
                            logger.info("Blocklist update triggered via CLI")
                    elif data.startswith("TRUSTWIFI:"):
                        ssid = data.split("TRUSTWIFI:")[1].strip()
                        engine_instance.db.add_trusted_wifi(ssid)
                        logger.info(f"WiFi '{ssid}' trusted via CLI")
                    elif data.startswith("UNTRUSTWIFI:"):
                        ssid = data.split("UNTRUSTWIFI:")[1].strip()
                        engine_instance.db.remove_trusted_wifi(ssid)
                        logger.info(f"WiFi '{ssid}' untrusted via CLI")
                    elif data.startswith("STATS"):
                        try:
                            stats = engine_instance.db.get_today_stats()
                            stat_str = f"NetStrip 24h Statistics:\n"
                            stat_str += f"  Blocked:    {stats.get('blocked', 0):,}\n"
                            stat_str += f"  Allowed:    {stats.get('allowed', 0):,}\n"
                            stat_str += f"  DNS:        {stats.get('dns_queries', 0):,}\n"
                            stat_str += f"  Ads:        {stats.get('blocked_ads', 0):,}\n"
                            stat_str += f"  Trackers:   {stats.get('blocked_trackers', 0):,}\n"
                            stat_str += f"  Telemetry:  {stats.get('blocked_telemetry', 0):,}\n"
                            stat_str += f"  Malware:    {stats.get('blocked_malware', 0):,}\n"
                            conn.sendall(stat_str.encode())
                        except Exception as e:
                            conn.sendall(f"Error fetching stats: {e}\n".encode())
                    elif data.startswith("STATUS"):
                        status_str = f"NetStrip Daemon Status:\n"
                        status_str += f"  Mode:       {engine_instance.classifier.mode.name}\n"
                        status_str += f"  Killswitch: {'ACTIVE' if engine_instance.db.get_setting('killswitch_active', 'false') == 'true' else 'inactive'}\n"
                        status_str += f"  Ghost Mode: {'ACTIVE' if engine_instance.db.get_setting('ghost_mode', 'false') == 'true' else 'inactive'}\n"
                        psk = engine_instance.db.get_setting('lan_shield_psk', '')
                        status_str += f"  LAN Shield: {'paired (PSK set)' if psk else 'not configured'}\n"
                        pending = engine_instance.db.get_setting("pending_kernel_threat", "")
                        if pending:
                            status_str += f"  ⚠ LOCKDOWN: {pending}\n"
                        else:
                            status_str += "  Threats:    none detected\n"
                        conn.sendall(status_str.encode())
                conn.close()
            except Exception:
                pass
                
    threading.Thread(target=ipc_listener, daemon=True).start()

    if is_embedded:
        logger.info("Embedded system mode active. GUI will not be initialized.")
        from netstrip.core.engine import NetStripEngine
        engine_instance = NetStripEngine(is_headless=is_headless)
        
        # Apply CLI Boot Overrides natively
        if "--blockinbound" in sys.argv:
            engine_instance.db.set_setting("strict_inbound_shield", "true")
            engine_instance.db.set_setting("inbound_lan_bypass", "false")
        if "--allowlan" in sys.argv:
            engine_instance.db.set_setting("inbound_lan_bypass", "true")
        
        try:
            from netstrip.core.sound import sound_manager
            sound_manager.set_muted(True) # Disable sounds in headless mode
            
            engine_instance.start()
            
            # Since there is no Tkinter mainloop, we need our own wait loop
            while engine_instance.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received, stopping engine.")
            import pathlib
            clean_exit_path = pathlib.Path.home() / ".netstrip" / ".clean_exit"
            try:
                clean_exit_path.parent.mkdir(parents=True, exist_ok=True)
                clean_exit_path.touch()
            except: pass
        finally:
            engine_instance.stop()
            sys.exit(0)

    # Standard GUI Boot Path (used for both desktop AND --service to get tray icon)
    is_android_mode = os.environ.get('NETSTRIP_ANDROID') == '1' or hasattr(sys, 'getandroidapilevel') or '--android' in sys.argv
    
    if is_android_mode:
        from netstrip.gui.app_android import NetStripApp
    else:
        from netstrip.gui.app import NetStripApp
        
    from netstrip.gui.splash import SplashScreen
    from netstrip.core.engine import NetStripEngine
    
    # Create hidden main app immediately
    app = NetStripApp()
    
    # Suppress Tkinter's noisy callback exception reporting in headless/service mode
    if is_headless:
        app.report_callback_exception = lambda exc, val, tb: None
        
    if not is_fallback and not is_headless:
        splash = SplashScreen(app)
        app.update() # Force draw the splash screen to the OS NOW!
    else:
        splash = None
        
    start_time = time.time()
    
    import threading
    engine_instance = None
    
    def boot_thread():
        nonlocal engine_instance
        try:
            # Initialize Engine exactly ONCE in the correct privilege context
            engine_instance = NetStripEngine(is_headless=is_headless)
            
            # Apply CLI Boot Overrides natively
            if "--blockinbound" in sys.argv:
                engine_instance.db.set_setting("strict_inbound_shield", "true")
                engine_instance.db.set_setting("inbound_lan_bypass", "false")
            if "--allowlan" in sys.argv:
                engine_instance.db.set_setting("inbound_lan_bypass", "true")
                
            from netstrip.core.sound import sound_manager
            
            # Mute sounds during boot
            initial_mute_state = sound_manager.muted
            sound_manager.set_muted(True)
            
            engine_instance.start()
            
            # Defer back to main thread to build UI and finalize
            app.after(0, lambda: finalize_boot(engine_instance, initial_mute_state))
            
        except Exception as e:
            logger.error(f"Engine Boot Error: {e}")
            import traceback
            traceback.print_exc()
            app.after(0, app.destroy)
            
    def finalize_boot(engine, initial_mute_state):
        try:
            # Prepare main app for invisible rendering to prevent white flash
            app.attributes('-alpha', 0.0)
            
            # Build the heavy UI components now that engine is ready
            app.build_ui(engine)
            
            # Force Tkinter to render the widgets while fully transparent
            if not is_headless:
                app.deiconify()
            app.apply_icon()
            app.update() 
            
            def check_engine_ready():
                elapsed = time.time() - start_time
                
                def on_transition_done():
                    if not is_headless:
                        app.lift()
                        app.focus_force()
                        app.apply_icon() # Force it one more time just to be absolutely sure
                        
                        from netstrip.core.sound import sound_manager
                        sound_manager.set_muted(initial_mute_state)
                        if not initial_mute_state:
                            sound_manager.play_intro()
                    else:
                        app._show_tray_icon()
                        
                def cross_fade(splash_alpha=1.0, app_alpha=0.0):
                    if is_headless:
                        on_transition_done()
                        return
                        
                    # Faster, smoother cross-fade (step 0.1 every 10ms = ~100ms total)
                    step = 0.1
                    splash_done = True
                    app_done = True
                    
                    if splash and splash_alpha > 0.0:
                        splash_alpha -= step
                        splash.attributes('-alpha', max(0.0, splash_alpha))
                        splash_done = False
                        
                    if app_alpha < 1.0:
                        app_alpha += step
                        app.attributes('-alpha', min(1.0, app_alpha))
                        app_done = False
                        
                    if not splash_done or not app_done:
                        app.after(10, lambda: cross_fade(splash_alpha, app_alpha))
                    else:
                        if splash: splash.withdraw()
                        on_transition_done()
                        
                if is_fallback or is_headless:
                    while engine_instance.is_running:
                        try:
                            app.update()
                        except Exception:
                            pass
                        time.sleep(0.05)
                    return
    
                if hasattr(engine, 'blocklist') and not engine.blocklist.is_loading and elapsed > 2.0:
                    # Trigger the smooth cross-fade
                    cross_fade()
                else:
                    app.after(50, check_engine_ready)
                    
            check_engine_ready()
        except Exception as e:
            logger.error(f"GUI Build Error: {e}")
            
    # Start the boot process in background so splash animation can run
    threading.Thread(target=boot_thread, daemon=True).start()

    try:
        app.mainloop()
    except Exception as e:
        logger.error(f"Mainloop Error: {e}")
        if engine_instance:
            try:
                engine_instance.stop()
            except Exception:
                pass
        try:
            from netstrip.core.crash_reporter import send_crash_report
            send_crash_report(exception=e, context="mainloop")
        except Exception:
            pass
    finally:
        if engine_instance:
            try:
                engine_instance.stop()
            except Exception:
                pass

if __name__ == "__main__":
    main()
