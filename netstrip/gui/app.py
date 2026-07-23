"""
Main GUI Application for NetStrip
"""

import customtkinter as ctk
import sys
from netstrip.gui.hovertip import apply_global_tooltips

# Apply global auto-tooltips monkey-patch
apply_global_tooltips()

# Monkey-patch CustomTkinter Scrollable Frame to scroll 3x faster
original_mouse_wheel_all = ctk.CTkScrollableFrame._mouse_wheel_all

def fast_mouse_wheel_all(self, event):
    if self._check_if_valid_scroll(event.widget):
        if sys.platform.startswith("win"):
            if self._shift_pressed:
                if self._parent_canvas.xview() != (0.0, 1.0):
                    self._parent_canvas.xview("scroll", -int(event.delta / 4), "units")
            else:
                if self._parent_canvas.yview() != (0.0, 1.0):
                    self._parent_canvas.yview("scroll", -int(event.delta / 4), "units")
        elif sys.platform == "darwin":
            if self._shift_pressed:
                if self._parent_canvas.xview() != (0.0, 1.0):
                    self._parent_canvas.xview("scroll", -int(event.delta * 2), "units")
            else:
                if self._parent_canvas.yview() != (0.0, 1.0):
                    self._parent_canvas.yview("scroll", -int(event.delta * 2), "units")
        else:
            if self._shift_pressed:
                if self._parent_canvas.xview() != (0.0, 1.0):
                    self._parent_canvas.xview("scroll", -int(event.delta / 4), "units")
            else:
                if self._parent_canvas.yview() != (0.0, 1.0):
                    self._parent_canvas.yview("scroll", -int(event.delta / 4), "units")

def fast_check_if_valid_scroll(self, widget):
    canvas_str = str(self._parent_canvas)
    widget_str = str(widget)
    return widget_str == canvas_str or widget_str.startswith(canvas_str + ".")

ctk.CTkScrollableFrame._mouse_wheel_all = fast_mouse_wheel_all
ctk.CTkScrollableFrame._check_if_valid_scroll = fast_check_if_valid_scroll
import logging
from netstrip.gui.theme import Colors, Fonts, Icons, Spacing
from netstrip.gui.dashboard import DashboardView
from netstrip.gui.connections_sidebar import ConnectionsSidebar
from netstrip.gui.views import AppRulesView, BlocklistView, LogView, SettingsView
from netstrip.gui.smart_modal import SmartParanoidModal
from netstrip.gui.killswitch_modal import ManualKillswitchModal, CriticalRecoveryModal
from netstrip.core.engine import NetStripEngine

class DraggableSash(ctk.CTkFrame):
    def __init__(self, master, engine, right_frame, **kwargs):
        super().__init__(master, width=6, cursor="sb_h_double_arrow", fg_color=Colors.BORDER_SUBTLE, **kwargs)
        self.engine = engine
        self.right_frame = right_frame
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", lambda e: self.configure(fg_color=Colors.TEXT_SECONDARY))
        self.bind("<Leave>", lambda e: self.configure(fg_color=Colors.BORDER_SUBTLE))
        self._drag_timer = None
        
    def _on_press(self, event):
        self._start_x = event.x_root
        self._initial_width = self.right_frame.winfo_width()
        self.configure(fg_color=Colors.ACCENT_PRIMARY)
        if not hasattr(self, 'ghost_line'):
            self.ghost_line = ctk.CTkFrame(self.master, width=4, fg_color=Colors.ACCENT_PRIMARY, corner_radius=0)
        self.ghost_line.place(x=self.winfo_x(), y=self.winfo_y(), height=self.winfo_height())
        self.ghost_line.lift()
        
    def _on_drag(self, event):
        dx = event.x_root - self._start_x
        new_width = self._initial_width - dx
        if 250 < new_width < 1200:
            new_x = self.winfo_x() + dx
            if hasattr(self, 'ghost_line'):
                self.ghost_line.place(x=new_x)
            
    def _on_release(self, event):
        self.configure(fg_color=Colors.BORDER_SUBTLE)
        if hasattr(self, 'ghost_line'):
            self.ghost_line.place_forget()
        dx = event.x_root - self._start_x
        new_width = self._initial_width - dx
        if 250 < new_width < 1200:
            self.master.grid_columnconfigure(3, weight=0, minsize=new_width)
            self.engine.db.set_setting("sidebar_width", str(new_width))

logger = logging.getLogger(__name__)

class NetStripApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw() # Hide immediately to prevent white window flash during init

        # Setup Window
        self.title("NetStrip — Intelligent Network Debloater")
        self.geometry("1500x800")
        self.configure(fg_color=Colors.BG_DARKEST)
        
        # Fix Taskbar icon grouping on Windows globally for this process
        try:
            import ctypes
            myappid = 'NetStrip.app.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        self.apply_icon()
        
        # Prevent black rendering artifacts on window restore
        self.bind("<Map>", lambda e: self.after(10, self.update_idletasks))
        self.bind("<Configure>", self._on_window_resize)
        self._resize_timer = None

    def apply_icon(self):
        try:
            import os
            import sys
            from PIL import Image
            
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                
            icon_path = os.path.join(base_path, 'assets', 'logo.ico')
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
                self._icon_image = Image.open(icon_path)
                
                import ctypes
                myappid = 'NetStrip.app.1.0'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                
                # Also set the small and large icons explicitly using ctypes for taskbar and alt-tab
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                hicon = ctypes.windll.user32.LoadImageW(0, icon_path, 1, 0, 0, 0x00000010)
                if hicon:
                    ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon) # ICON_SMALL
                    ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon) # ICON_BIG
        except Exception as e:
            pass

    def _on_window_resize(self, event):
        # Only act on top-level window resize events, not child widget reconfigs
        if event.widget is not self:
            return
            
        if not getattr(self, '_is_resizing', False):
            self._is_resizing = True
            if hasattr(self, 'connections_list'):
                self.connections_list._resize_paused = True
                
        # Debounce: cancel any pending resize-end callback and reset
        if self._resize_timer is not None:
            self.after_cancel(self._resize_timer)
        self._resize_timer = self.after(200, self._on_resize_end)

    def _on_resize_end(self):
        self._resize_timer = None
        self._is_resizing = False
        
        # Restore scroll frames
        if hasattr(self, 'connections_list'):
            self.connections_list._resize_paused = False

    def build_ui(self, engine: NetStripEngine):
        self.engine = engine
        ctk.set_appearance_mode("dark")

        # Register notification badge callback
        self.engine.notifier.on_count_changed = self._update_pending_badge
        self.engine.on_smart_trigger = self._show_smart_modal
        self.engine.on_critical_network_event = self._show_critical_recovery_modal
        if self._update_geoip_ui not in self.engine.geoip.callbacks:
            self.engine.geoip.callbacks.append(self._update_geoip_ui)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        if getattr(self.engine, 'is_headless', False):
            # Headless Mode: Skip heavy UI widget construction and polling loops
            self.withdraw()
            self.engine.set_status_callback(self._show_status)
            return

        self._build_ui()
        
        # Register status callback
        self.engine.set_status_callback(self._show_status)

    def _show_status(self, msg: str):
        def _update():
            try:
                if hasattr(self, 'status_label'):
                    self.status_label.configure(text=msg)
                    if hasattr(self, '_status_timer'):
                        self.after_cancel(self._status_timer)
                    self._status_timer = self.after(5000, lambda: self.status_label.configure(text=""))
                
                # If app is hidden/minimized to tray or headless, send a system notification
                if getattr(self, '_tray_icon', None):
                    if not self.winfo_ismapped() or getattr(self.engine, 'is_headless', False):
                        # Don't spam notifications for minor updates, only important ones
                        if "blocked" in msg.lower() or "mode changed" in msg.lower() or "threat" in msg.lower() or "whitelist" in msg.lower() or "killswitch" in msg.lower() or "anomaly" in msg.lower():
                            self._tray_icon.notify(msg, "NetStrip Status")
            except Exception:
                pass
        self.after(0, _update)

    def _build_ui(self):
        # 3-column layout, 3 rows: Top Bar | (Nav Sidebar | Main Content | Connections Sidebar) | Status Bar
        self.grid_rowconfigure(0, weight=0) # Top Bar
        self.grid_rowconfigure(1, weight=1) # Main
        self.grid_rowconfigure(2, weight=0) # Status Bar
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        
        try:
            saved_width = int(self.engine.db.get_setting("sidebar_width", "500"))
        except Exception:
            saved_width = 500
            
        self.grid_columnconfigure(2, weight=0, minsize=6) # Sash
        self.grid_columnconfigure(3, weight=0, minsize=saved_width) # Right sidebar
        
        # Top Bar
        self.top_bar = ctk.CTkFrame(self, fg_color=Colors.BG_PANEL, corner_radius=0, height=45)
        self.top_bar.grid(row=0, column=0, columnspan=4, sticky="ew")
        self.top_bar.grid_propagate(False)
        self.top_bar.grid_columnconfigure(1, weight=1)

        self.lbl_geoip = ctk.CTkLabel(self.top_bar, text="🌐 Loading GeoIP...", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM), text_color=Colors.TEXT_SECONDARY)
        self.lbl_geoip.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.top_bar.grid_rowconfigure(0, weight=1)
        
        self.btn_sound_toggle = ctk.CTkButton(
            self.top_bar, text="🔊", font=(Fonts.FAMILY_PRIMARY[0], 22), width=40, height=40,
            fg_color="transparent", hover_color=Colors.BG_ELEVATED, text_color=Colors.TEXT_PRIMARY,
            command=self._toggle_sound
        )
        self.btn_sound_toggle.grid(row=0, column=1, padx=10, sticky="e")
        
        self.btn_killswitch = ctk.CTkButton(
            self.top_bar, text="CRIPPLE: ON", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, "bold"),
            fg_color=Colors.SUCCESS_DIM, hover_color=Colors.SUCCESS, text_color="white", corner_radius=4, height=28,
            command=self._manual_killswitch_click
        )
        self.btn_killswitch.grid(row=0, column=2, padx=20, pady=8, sticky="e")
        
        try:
            from netstrip.gui.hovertip import FadingHovertip
            FadingHovertip(self.btn_killswitch, "Click to toggle Killswitch mode. When ON, all traffic is securely dropped by the OS packet filter.", hover_delay=400)
            FadingHovertip(self.btn_sound_toggle, "Toggle notification and alert sounds.", hover_delay=400)
        except Exception:
            pass

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=Colors.BG_PANEL,
                                     border_width=0)
        self.sidebar.grid(row=1, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(8, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        # Logo
        from netstrip.gui.animated_logo import AnimatedLogo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        
        # Add the requested quote
        ctk.CTkLabel(logo_frame, text="Blocking over a million domains,\nupdated daily!",
                     font=(Fonts.FAMILY_PRIMARY[0], 9, "italic"),
                     justify="center", text_color=Colors.TEXT_TERTIARY).pack(anchor="center", pady=(0, 10))
        
        self.persistent_logo = AnimatedLogo(logo_frame, width=180, height=120, bg_color=Colors.BG_PANEL)
        self.persistent_logo.pack(anchor="center", pady=(0, 5))
        
        ctk.CTkLabel(logo_frame, text="CRIPPLE",
                     font=("Segoe UI Black", 38, "bold"),
                     text_color=Colors.TEXT_PRIMARY).pack(anchor="center")
        ctk.CTkLabel(logo_frame, text="Network Debloater",
                     font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
                     text_color=Colors.TEXT_TERTIARY).pack(anchor="center")
        
        # Add copyright at the very bottom of the sidebar
        copyright_lbl = ctk.CTkLabel(
            self.sidebar, text="© 2026 FrenzyPenguin Media", 
            font=(Fonts.FAMILY_PRIMARY[0], 10), text_color=Colors.TEXT_TERTIARY
        )
        copyright_lbl.grid(row=8, column=0, pady=20, sticky="s")
        ctk.CTkLabel(logo_frame, text="DNS filter & sinkhole",
                     font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
                     text_color=Colors.TEXT_TERTIARY).pack(anchor="center")
        ctk.CTkLabel(logo_frame, text="Firewall add-on",
                     font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
                     text_color=Colors.TEXT_TERTIARY).pack(anchor="center")

        # Separator
        ctk.CTkFrame(self.sidebar, height=1, fg_color=Colors.BORDER_SUBTLE).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(8, 12))

        # Nav buttons
        self.nav_btns = []
        self.badge_label = None
        self._add_nav_btn(2, "Dashboard", Icons.DASHBOARD, DashboardView)
        self._add_nav_btn(3, "Logs", Icons.LOGS, LogView)
        self._add_nav_btn(4, "Filter Lists", Icons.BLOCKLIST, BlocklistView)
        self._add_nav_btn(5, "Settings", Icons.SETTINGS, SettingsView)

        # Expand button
        self.btn_expand = ctk.CTkButton(
            self.sidebar, text="◀ Expand Connections", 
            font=(Fonts.FAMILY_PRIMARY[0], 12, "bold"), 
            fg_color=Colors.BG_ELEVATED, 
            hover_color=Colors.BG_PANEL,
            text_color=Colors.TEXT_PRIMARY,
            corner_radius=8,
            height=32,
            command=self._toggle_sidebar_expand
        )
        self.btn_expand.grid(row=8, column=0, pady=20, padx=20, sticky="ew")

        # Version
        from netstrip import __version__
        self.version_label = ctk.CTkLabel(self.sidebar, text=f"{__version__}",
                     font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
                     text_color=Colors.TEXT_TERTIARY,
                     cursor="hand2")
        self.version_label.grid(row=9, column=0, pady=(0, 16))
        
        def _nav_to_settings(e):
            self._select_nav_by_text("Settings")
            
            def _scroll_to_top():
                from netstrip.gui.views.settings import SettingsView
                settings_view = self._cached_views.get(SettingsView)
                if settings_view and hasattr(settings_view, 'scroll_frame') and hasattr(settings_view.scroll_frame, '_parent_canvas'):
                    try:
                        settings_view.scroll_frame._parent_canvas.yview_moveto(0)
                    except: pass
                    
            self.after(50, _scroll_to_top)
            
        self.version_label.bind("<Button-1>", _nav_to_settings)

        # Register callback for engine events
        self.engine.gui_update_callback = self._on_engine_event
        if getattr(self.engine, 'update_available', False):
            self._on_engine_event("UPDATE_AVAILABLE")

        # Main content (middle pane)
        self.main_frame = ctk.CTkFrame(self, fg_color=Colors.BG_DARK, corner_radius=0)
        self.main_frame.grid(row=1, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Sash
        self.sash = DraggableSash(self, self.engine, None)
        self.sash.grid(row=1, column=2, sticky="ns")

        # Right Sidebar (Persistent App Connections List)
        self.right_sidebar = ctk.CTkFrame(self, corner_radius=0, fg_color=Colors.BG_PANEL, border_width=1, border_color=Colors.BORDER_SUBTLE)
        self.right_sidebar.grid(row=1, column=3, sticky="nsew")
        self.sash.right_frame = self.right_sidebar
        
        # Status Bar
        self.status_bar = ctk.CTkFrame(self, height=24, corner_radius=0, fg_color=Colors.BG_DARKEST)
        self.status_bar.grid(row=2, column=0, columnspan=4, sticky="ew")
        self.status_bar.grid_propagate(False)
        self.status_label = ctk.CTkLabel(
            self.status_bar, text="",
            font=(Fonts.FAMILY_PRIMARY[0], 11),
            text_color=Colors.TEXT_TERTIARY
        )
        self.status_label.pack(side="left", padx=16)
        
        self.right_sidebar.grid_rowconfigure(0, weight=1)
        self.right_sidebar.grid_columnconfigure(0, weight=1)
        
        # Instantiate heavy components BEFORE the splash screen fades out
        self._deferred_init()

    def _deferred_init(self):
        # Instantiate the ConnectionsSidebar widget inside the right sidebar
        self.connections_list = ConnectionsSidebar(self.right_sidebar, self.engine)
        self.connections_list.pack(fill="both", expand=True)

        self.current_view = None
        self._cached_views = {}
        self._select_nav(self.nav_btns[0])
        
        # Lazy pre-load disabled: views are instantiated on-demand when clicked
        pass

    def _preload_next_view(self, index):
        pass

    def _toggle_sidebar_expand(self):
        from netstrip.core.sound import sound_manager
        sound_manager.play_click()
        if not hasattr(self, '_sidebar_expanded'):
            self._sidebar_expanded = False
            
        self._sidebar_expanded = not self._sidebar_expanded
        
        if self._sidebar_expanded:
            self.main_frame.grid_remove()
            self.sash.grid_remove()
            self.right_sidebar.grid(row=1, column=1, columnspan=3, sticky="nsew")
            self.connections_list.set_expanded(True)
            self.btn_expand.configure(text="Collapse Sidebar ▶", font=(Fonts.FAMILY_PRIMARY[0], 12, "bold"))
        else:
            self.right_sidebar.grid(row=1, column=3, columnspan=1, sticky="nsew")
            self.sash.grid(row=1, column=2, sticky="ns")
            self.main_frame.grid()
            self.connections_list.set_expanded(False)
            self.btn_expand.configure(text="◀ Expand Sidebar", font=(Fonts.FAMILY_PRIMARY[0], 12, "bold"))

    def _add_nav_btn(self, row, text, icon, view_class):
        btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=40)
        btn_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
        btn_frame.grid_columnconfigure(0, weight=1)

        btn = ctk.CTkButton(
            btn_frame,
            text=f"  {icon}   {text}",
            anchor="w", height=38,
            corner_radius=Spacing.RADIUS_SM,
            fg_color="transparent",
            text_color=Colors.TEXT_SECONDARY,
            hover_color=Colors.BG_ELEVATED,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD),
            command=lambda t=text: self._select_nav_by_text(t)
        )
        btn.grid(row=0, column=0, sticky="ew")
        btn._view_class = view_class
        btn._text_val = text
        self.nav_btns.append(btn)

    def _update_pending_badge(self, count: int):
        try:
            if self.badge_label:
                if count > 0:
                    self.badge_label.configure(text=str(count))
                    self.badge_label.grid(row=0, column=1, padx=(0, 8))
                else:
                    self.badge_label.grid_forget()
        except Exception:
            pass

    def _select_nav_by_text(self, text):
        for btn in self.nav_btns:
            if btn._text_val == text:
                self._select_nav(btn)
                break

    def _select_nav(self, selected_btn):
        from netstrip.core.sound import sound_manager
        sound_manager.play_click()
        for btn in self.nav_btns:
            btn.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
        selected_btn.configure(fg_color=Colors.BG_ELEVATED, text_color=Colors.ACCENT_PRIMARY)

        if self.current_view:
            self.current_view.grid_remove() # Hide the old view instead of destroying it

        view_class = selected_btn._view_class
        
        # Immediate UI feedback
        if not hasattr(self, '_tab_loading_overlay'):
            self._tab_loading_overlay = ctk.CTkFrame(self.main_frame, fg_color=Colors.BG_DARK)
            ctk.CTkLabel(self._tab_loading_overlay, text="Loading Tab...", font=(Fonts.FAMILY_PRIMARY[0], 20)).place(relx=0.5, rely=0.5, anchor="center")
            
        self._tab_loading_overlay.grid(row=0, column=0, sticky="nsew")
        self.update_idletasks() # Force UI update immediately
        
        def _build_and_show():
            if view_class not in self._cached_views:
                self._cached_views[view_class] = view_class(self.main_frame, self.engine)
            self._tab_loading_overlay.grid_remove()
            self.current_view = self._cached_views[view_class]
            
            if view_class.__name__ == 'DashboardView':
                self.current_view.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
            else:
                self.current_view.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
            
        self.after(20, _build_and_show)

    def _show_smart_modal(self, conn_data):
        # Must run in main thread
        self.after(0, lambda: SmartParanoidModal(self, self.engine, conn_data))

    def _update_geoip_ui(self, old_ip: str, geo_data: dict):
        def update_ui():
            privacy_on = self.engine.db.get_setting("privacy_stream_mode", "false") == "true"
            if privacy_on:
                text = "🌐 [STREAMER PRIVACY MODE ENABLED]"
                copy_val = "Hidden for privacy"
            else:
                text = f"{geo_data.get('flag', '🌐')} {geo_data.get('city', 'Unknown')}, {geo_data.get('country', 'Unknown')}  |  {geo_data.get('ip', 'Unknown')}"
                copy_val = geo_data.get('ip', 'Unknown')
                
            self.lbl_geoip.configure(text=text)
            try:
                from netstrip.gui.utils import bind_copy_tooltip
                bind_copy_tooltip(self.lbl_geoip, copy_val, "Copied!")
            except Exception:
                pass
        self.after(0, update_ui)

    def _toggle_sound(self):
        from netstrip.core.sound import sound_manager
        sound_manager.set_muted(not sound_manager.muted)
        self.btn_sound_toggle.configure(text="🔇" if sound_manager.muted else "🔊")
        if not sound_manager.muted:
            sound_manager.play_click()

    def _manual_killswitch_click(self):
        current_state = self.btn_killswitch.cget("text")
        
        if current_state == "CRIPPLE: ON":
            # State 1 -> 2: Engage Killswitch
            try:
                self.after(0, lambda: ManualKillswitchModal(self, self.engine, self._execute_manual_killswitch))
            except Exception:
                self._execute_manual_killswitch(True) # Fallback to engaging without warning
        elif current_state == "KILLSWITCH ENGAGED":
            # State 2 -> 3: Cripple OFF (Bypass)
            try:
                self._show_bypass_warning()
            except Exception:
                self.engine.set_killswitch(False)
                self.engine.firewall.clear_all_rules()
                self.btn_killswitch.configure(text="CRIPPLE: OFF (BYPASS)", fg_color=Colors.WARNING)
        else:
            # State 3 -> 1: Cripple ON
            self.engine.set_killswitch(False)
            self.btn_killswitch.configure(text="CRIPPLE: ON", fg_color=Colors.SUCCESS_DIM)

    def _execute_manual_killswitch(self, confirmed: bool):
        if confirmed:
            self.engine.set_killswitch(True)
            self.btn_killswitch.configure(text="KILLSWITCH ENGAGED", fg_color="#7f1d1d")

    def _show_bypass_warning(self):
        # Quick inline warning modal for bypassing Cripple entirely
        modal = ctk.CTkToplevel(self)
        modal.title("WARNING: BYPASS MODE")
        modal.geometry("450x200")
        modal.attributes("-topmost", True)
        
        lbl_title = ctk.CTkLabel(modal, text="🚨 WARNING: ENDPOINT UNPROTECTED", font=Fonts.h3(), text_color=Colors.WARNING)
        lbl_title.pack(pady=(20, 10))
        
        lbl_desc = ctk.CTkLabel(modal, text="Switching to OFF will clear all Cripple firewall rules and DNS.\nYour PC will be raw and unprotected.", font=Fonts.body())
        lbl_desc.pack(pady=10)
        
        btn_frame = ctk.CTkFrame(modal, fg_color="transparent")
        btn_frame.pack()
        
        ctk.CTkButton(btn_frame, text="Cancel", command=modal.destroy, fg_color=Colors.BG_INPUT, hover_color=Colors.BORDER_HOVER, text_color=Colors.TEXT_PRIMARY).pack(side="left", padx=5)
        
        def confirm_bypass():
            self.engine.set_killswitch(False)
            self.engine.firewall.clear_all_rules()
            self.btn_killswitch.configure(text="CRIPPLE: OFF (BYPASS)", fg_color=Colors.WARNING)
            modal.destroy()
            
        ctk.CTkButton(btn_frame, text="Proceed to OFF", command=confirm_bypass, fg_color=Colors.WARNING, text_color="white").pack(side="left", padx=5)

    def _show_critical_recovery_modal(self, message: str):
        try:
            self.after(0, lambda: CriticalRecoveryModal(self, self.engine, message))
        except Exception as e:
            logger.error(f"Failed to spawn recovery modal: {e}")
        self.after(0, lambda: self.btn_killswitch.configure(text="KILLSWITCH ENGAGED", fg_color="#7f1d1d"))

    def _perform_clean_exit(self):
        import pathlib
        clean_exit_path = pathlib.Path.home() / ".netstrip" / ".clean_exit"
        try:
            clean_exit_path.parent.mkdir(parents=True, exist_ok=True)
            clean_exit_path.touch()
        except Exception as e:
            logger.error(f"Failed to write clean exit flag: {e}")
        self.withdraw()
        self.update()
        self.quit()

    def _on_closing(self):
        val = self.engine.db.get_setting("run_as_service", "false")
        if str(val).lower() == "true":
            self.withdraw()
            self._show_tray_icon()
        else:
            self._perform_clean_exit()

    def _show_tray_icon(self):
        try:
            import pystray
            import threading
    
            if getattr(self, '_tray_icon', None) is not None:
                return
        except Exception as e:
            # Pystray requires a display server (X11/Wayland/Explorer).
            # If we fail here, we are on a truly headless OS or broken environment.
            self._tray_icon = None
            return

        def on_show(icon, item):
            icon.stop()
            self._tray_icon = None
            self.after(0, self.deiconify)

        def on_quit(icon, item):
            icon.stop()
            self._tray_icon = None
            self.after(0, self._perform_clean_exit)

        def is_killswitch_active(item):
            return getattr(self.engine, 'killswitch_active', False)

        def toggle_killswitch(icon, item):
            current = is_killswitch_active(item)
            self.engine.set_killswitch(not current)
            def update_ui():
                if hasattr(self, 'btn_killswitch'):
                    if getattr(self.engine, 'killswitch_active', False):
                        self.btn_killswitch.configure(text="KILLSWITCH ENGAGED", fg_color="#7f1d1d")
                    else:
                        self.btn_killswitch.configure(text="CRIPPLE: ACTIVE", fg_color=Colors.SUCCESS_DIM)
            self.after(0, update_ui)

        def is_paranoid_active(item):
            mode = getattr(getattr(self.engine, 'classifier', None), 'mode', None)
            return mode and mode.name == "PARANOID"

        def toggle_paranoid(icon, item):
            if is_paranoid_active(item):
                self.engine.classifier.set_mode("STANDARD")
            else:
                self.engine.classifier.set_mode("PARANOID")

        def is_lan_shield_active(item):
            return self.engine.db.get_setting("lan_shield_enabled", "true") == "true"

        def toggle_lan_shield(icon, item):
            current = is_lan_shield_active(item)
            new_val = "false" if current else "true"
            self.engine.db.set_setting("lan_shield_enabled", new_val)
            if new_val == "true":
                self.engine.platform.block_lan_traffic()
            else:
                self.engine.platform.unblock_lan_traffic()

        def review_anomaly(icon, item):
            threat = self.engine.db.get_setting("pending_kernel_threat")
            if threat:
                try:
                    name, msg = threat.split('|', 1)
                except ValueError:
                    name, msg = "unknown", threat
                anomaly_data = {'name': name, 'message': msg, 'type': 'adapter'}
                
                def _tray_decision(decision):
                    self.engine.db.set_setting("pending_kernel_threat", "")
                    if decision == 'neutralize':
                        if self.engine.anomaly_scanner:
                            self.engine.anomaly_scanner._neutralize_adapter(name)
                            self.engine.anomaly_scanner._neutralize_pcap()
                    elif decision == 'whitelist':
                        self.engine.db.whitelist_anomaly(name)
                    elif decision == 'disable_scanner':
                        self.engine.db.set_setting("kernel_anomaly_scanner", "false")
                        if self.engine.anomaly_scanner:
                            self.engine.anomaly_scanner.stop()
                
                from netstrip.gui.views.anomaly_alert import CTkAnomalyAlert
                self.after(0, lambda: CTkAnomalyAlert(self, self.engine, anomaly_data, _tray_decision))

        def get_menu_items():
            items = [pystray.MenuItem('Show Cripple', on_show, default=True)]
            
            # Dynamic Threat Button
            threat = self.engine.db.get_setting("pending_kernel_threat")
            if threat:
                items.append(pystray.MenuItem('⚠️ Review Kernel Anomaly', review_anomaly))
                
            items.extend([
                pystray.MenuItem('Master Killswitch', toggle_killswitch, checked=is_killswitch_active),
                pystray.MenuItem('Paranoid Mode', toggle_paranoid, checked=is_paranoid_active),
                pystray.MenuItem('LAN Shield', toggle_lan_shield, checked=is_lan_shield_active),
                pystray.MenuItem('Quit', on_quit)
            ])
            return items

        menu = pystray.Menu(get_menu_items)

        self._tray_icon = pystray.Icon("NetStrip", getattr(self, '_icon_image'), "Cripple", menu)
        
        # pystray blocks, so run it in a thread
        threading.Thread(target=self._tray_icon.run, daemon=True).start()

    def _on_engine_event(self, event_name: str, *args, **kwargs):
        def _handle_event():
            if event_name == "UPDATE_AVAILABLE":
                if not getattr(self, '_update_glow_active', False):
                    self._update_glow_active = True
                    self._animate_update_glow()
            elif event_name == "MODE_CHANGE":
                pass # Can add specific mode change logic here if needed
        self.after(0, _handle_event)
                
    def _animate_update_glow(self, step=0, increasing=True):
        if not getattr(self, '_update_glow_active', False) or not self.winfo_exists():
            return
            
        # Pulse between TEXT_TERTIARY (#6b7280) and a glowing yellow (#facc15)
        try:
            import colorsys
            r1, g1, b1 = int('6b', 16), int('72', 16), int('80', 16)
            r2, g2, b2 = int('fa', 16), int('cc', 16), int('15', 16)
            
            ratio = step / 20.0
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            
            self.version_label.configure(text_color=color)
            
            if increasing:
                step += 1
                if step >= 20: increasing = False
            else:
                step -= 1
                if step <= 0: increasing = True
                
            self.after(50, lambda: self._animate_update_glow(step, increasing))
        except Exception:
            pass

