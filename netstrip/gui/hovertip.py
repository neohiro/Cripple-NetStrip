import customtkinter as ctk
import time
from netstrip.gui.theme import Colors, Fonts

class TooltipManager:
    """A high-performance singleton tooltip manager that eliminates lag by reusing a single window."""
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.tip_window = None
        self.current_widget = None
        self.show_id = None
        self.hide_id = None
        self.delay_ms = 450
        
    def _create_window(self):
        if self.tip_window is None or not self.tip_window.winfo_exists():
            self.tip_window = ctk.CTkToplevel()
            self.tip_window.wm_overrideredirect(True)
            self.tip_window.attributes("-topmost", True)
            self.tip_window.withdraw()
            
            # Optional: drop shadow on Windows 11
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.tip_window.winfo_id())
                DWMWA_WINDOW_CORNER_PREFERENCE = 33
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(ctypes.c_int(2)), 4)
            except Exception:
                pass
                
            self.frame = ctk.CTkFrame(
                self.tip_window, 
                fg_color=Colors.BG_ELEVATED, 
                border_color=Colors.BORDER_SUBTLE, 
                border_width=1, 
                corner_radius=6
            )
            self.frame.pack(fill="both", expand=True)
            
            self.lbl_text = ctk.CTkLabel(
                self.frame, text="", 
                font=(Fonts.FAMILY_PRIMARY[0], 12),
                text_color=Colors.TEXT_PRIMARY,
                justify="left",
                wraplength=280
            )
            self.lbl_text.pack(padx=12, pady=8)

    def bind(self, widget, text_or_callable, delay=None):
        """Binds an attractive, zero-lag hovertip to a widget."""
        def get_text():
            return text_or_callable() if callable(text_or_callable) else text_or_callable
            
        def enter(e):
            t = get_text()
            if t:
                self.schedule_show(widget, t, delay or self.delay_ms)
                
        def leave(e):
            self.schedule_hide()
        def click(e):
            self.hide_immediate()
            
        widget.bind("<Enter>", enter, add="+")
        widget.bind("<Leave>", leave, add="+")
        widget.bind("<ButtonPress>", click, add="+")

    def schedule_show(self, widget, text, delay):
        if self.hide_id:
            widget.after_cancel(self.hide_id)
            self.hide_id = None
            
        if self.show_id:
            widget.after_cancel(self.show_id)
            
        self.current_widget = widget
        self.show_id = widget.after(delay, lambda: self.show_tip(widget, text))

    def schedule_hide(self):
        if self.show_id and self.current_widget:
            self.current_widget.after_cancel(self.show_id)
            self.show_id = None
            
        if self.tip_window and self.tip_window.winfo_ismapped() and self.current_widget:
            self.hide_id = self.current_widget.after(100, self.hide_immediate)

    def hide_immediate(self):
        if self.show_id and self.current_widget:
            self.current_widget.after_cancel(self.show_id)
            self.show_id = None
        if self.hide_id and self.current_widget:
            self.current_widget.after_cancel(self.hide_id)
            self.hide_id = None
            
        if self.tip_window and self.tip_window.winfo_exists():
            self.tip_window.withdraw()
            
    def show_tip(self, widget, text):
        if not widget.winfo_exists() or not text:
            return
            
        self._create_window()
        self.lbl_text.configure(text=text)
        
        # Position slightly below the mouse or widget center
        try:
            x = widget.winfo_rootx() + (widget.winfo_width() // 2)
            y = widget.winfo_rooty() + widget.winfo_height() + 8
        except Exception:
            return
            
        self.tip_window.update_idletasks()
        w = self.tip_window.winfo_width()
        h = self.tip_window.winfo_height()
        
        # Adjust center X
        x = x - (w // 2)
        
        # Screen bounds check
        screen_w = widget.winfo_screenwidth()
        screen_h = widget.winfo_screenheight()
        if x + w > screen_w - 10: x = screen_w - w - 10
        if x < 10: x = 10
        if y + h > screen_h - 10: y = widget.winfo_rooty() - h - 8
            
        self.tip_window.wm_geometry(f"+{x}+{y}")
        self.tip_window.deiconify()

def add_tooltip(widget, text, delay=400):
    """Convenience function to bind a lag-free tooltip."""
    TooltipManager.get_instance().bind(widget, text, delay)

class FadingHovertip:
    """Legacy wrapper for backwards compatibility"""
    def __init__(self, widget, text, hover_delay=400):
        add_tooltip(widget, text, hover_delay)


# ═══════════════════════════════════════════════════
# Global Auto-Tooltips system
# ═══════════════════════════════════════════════════

TOOLTIP_MAP = {
    # Nav Sidebar
    "Dashboard": "View network statistics and recent blocked activity.",
    "Logs": "View full history of all network connections in real-time.",
    "Filter Lists": "Manage blocklists for Ads, Trackers, Telemetry and Malware.",
    "Settings": "Configure NetStrip preferences and engine behavior.",
    "Expand Connections": "Open the live App Connections panel.",
    "Collapse Connections": "Close the live App Connections panel.",
    
    # Dashboard
    "Standard Mode": "Balanced protection blocking known trackers and malware.\nRecommended for daily use.",
    "Paranoid Mode": "Maximum security: blocks ALL unrecognized traffic unless explicitly whitelisted.",
    "Learning Mode": "Interactive mode: prompts you to approve or deny new connections as they happen.",
    
    # Settings View
    "Minimize to system tray on close": "Keeps Cripper running in the background protecting your network.",
    "Start on Boot": "Automatically launch Cripper silently when Windows starts.",
    "Block LAN Traffic": "Prevent local network devices (like smart TVs or printers) from communicating with this PC.",
    "Auto-Block Unknown": "Strict firewall behavior: any unclassified traffic is blocked by default instead of allowed.",
    "Sync Windows Firewall": "Automatically push Cripper's rules down to the native Windows Defender Firewall.",
    "Refresh Network Interfaces": "Re-scan your Wi-Fi and Ethernet adapters.",
    
    # Blocklist View
    "Refresh Blocklists": "Download the latest definitions from upstream sources (StevenBlack, OISD, etc).",
    "View Custom Rules": "Open your personal whitelist/blacklist manager.",
    "Reset Custom Rules": "Wipe all your personal overrides.",
    
    # Logs View
    "Export Logs": "Save your entire connection history to a text file in your Documents folder.",
    
    # Actions
    "Allow": "Permit this application to connect to the internet.",
    "Block": "Deny internet access for this application.",
    "Sinkhole": "Redirect this application's traffic to a safe local loopback address (fools the app into thinking it connected).",
    
    # Main App Header
    "CRIPPER: ON": "Click to toggle the manual Killswitch. When ON, you are protected.",
    "CRIPPER: OFF": "Warning: Protection is entirely bypassed.",
    "KILLSWITCH ENGAGED": "Killswitch is active. All traffic is being dropped securely by the OS.",
    "🔊": "Mute notification sounds.",
    "🔇": "Unmute notification sounds."
}

_TOOLTIPS_APPLIED = False

def apply_global_tooltips():
    """Monkey-patches CustomTkinter to automatically assign gorgeous tooltips based on widget text."""
    global _TOOLTIPS_APPLIED
    if _TOOLTIPS_APPLIED:
        return
    _TOOLTIPS_APPLIED = True

    orig_btn_init = ctk.CTkButton.__init__
    orig_sw_init = ctk.CTkSwitch.__init__
    orig_seg_init = ctk.CTkSegmentedButton.__init__
    
    def get_dynamic_tooltip(widget):
        try:
            text = widget.cget('text')
            if not isinstance(text, str): return ""
            text = text.strip()
            if text in TOOLTIP_MAP: return TOOLTIP_MAP[text]
            for key, tip in TOOLTIP_MAP.items():
                if key in text: return tip
        except Exception:
            pass
        return ""

    def patched_btn_init(self, *args, **kwargs):
        orig_btn_init(self, *args, **kwargs)
        add_tooltip(self, lambda: get_dynamic_tooltip(self))
        
    def patched_sw_init(self, *args, **kwargs):
        orig_sw_init(self, *args, **kwargs)
        add_tooltip(self, lambda: get_dynamic_tooltip(self))
        
    def patched_seg_init(self, *args, **kwargs):
        orig_seg_init(self, *args, **kwargs)
        def bind_later():
            if hasattr(self, '_buttons_dict'):
                for val, btn in self._buttons_dict.items():
                    # Bind static text for segments since they don't change text
                    tip = TOOLTIP_MAP.get(val, "")
                    if tip: add_tooltip(btn, tip)
        self.after(100, bind_later)

    ctk.CTkButton.__init__ = patched_btn_init
    ctk.CTkSwitch.__init__ = patched_sw_init
    ctk.CTkSegmentedButton.__init__ = patched_seg_init
