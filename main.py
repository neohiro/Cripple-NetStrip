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

# Early Windows Taskbar Fix
try:
    if sys.platform == 'win32':
        import ctypes
        myappid = 'NetStrip.app.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

def check_dependencies():
    missing = []
    try:
        import customtkinter
    except ImportError:
        missing.append("customtkinter")
        
    try:
        import psutil
    except ImportError:
        missing.append("psutil")
        
    try:
        import PIL
    except ImportError:
        missing.append("Pillow")
        
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

def is_embedded_system():
    """Detects if we are running on a low-resource embedded system like a Raspberry Pi."""
    import platform
    machine = platform.machine().lower()
    if machine in ('armv7l', 'aarch64', 'armv6l'):
        try:
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read().lower()
                if 'raspberry pi' in model or 'orange pi' in model or 'bananapi' in model:
                    return True
        except FileNotFoundError:
            pass
        # Fallback for generic ARM linux
        return True
    return False

def main():
    is_fallback = "--fallback-admin" in sys.argv
    is_elevated_retry = "--elevated" in sys.argv

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

    is_embedded = is_embedded_system()
    is_headless = "--service" in sys.argv or is_embedded

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
            client.sendall(b"SHOW_GUI\n")
            client.close()
        except Exception:
            pass
        print("NetStrip is already running. Showing existing GUI.")
        sys.exit(0)

    if is_embedded:
        logger.info("Embedded system mode active. GUI will not be initialized.")
        from netstrip.core.engine import NetStripEngine
        engine_instance = NetStripEngine(is_headless=is_headless)
        
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
    from netstrip.gui.app import NetStripApp
    from netstrip.gui.splash import SplashScreen
    from netstrip.core.engine import NetStripEngine
    
    # Create hidden main app immediately
    app = NetStripApp()
    
    # --- IPC Listener Thread ---
    def ipc_listener():
        while True:
            try:
                conn, addr = ipc_socket.accept()
                data = conn.recv(1024)
                if b"SHOW_GUI" in data:
                    app.after(0, app.deiconify)
                    app.after(50, lambda: app.attributes('-topmost', True))
                    app.after(100, lambda: app.attributes('-topmost', False))
                    app.after(100, app.lift)
                    app.after(100, app.focus_force)
                conn.close()
            except Exception:
                pass
                
    import threading
    threading.Thread(target=ipc_listener, daemon=True).start()
    
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
                        app.attributes('-topmost', True)
                        app.after(100, lambda: app.attributes('-topmost', False))
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
                    if hasattr(engine, 'blocklist') and not engine.blocklist.is_loading:
                        app.attributes('-alpha', 1.0)
                        on_transition_done()
                    else:
                        app.after(50, check_engine_ready)
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
    finally:
        if engine_instance:
            engine_instance.stop()

if __name__ == "__main__":
    main()
