import customtkinter as ctk
from netstrip.gui.theme import Colors, Fonts
from netstrip.gui.animated_logo import AnimatedLogo

class SplashScreen(ctk.CTkToplevel):
    def __init__(self, master=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(fg_color=Colors.BG_DARKEST)
        
        # Center the splash screen
        width = 400
        height = 300
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Explicitly set the icon on the splash screen as well to guarantee it doesn't default to the feather
        try:
            import os, sys
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            icon_path = os.path.join(base_path, 'assets', 'logo.ico')
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                hicon = ctypes.windll.user32.LoadImageW(0, icon_path, 1, 0, 0, 0x00000010)
                if hicon:
                    ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon) # ICON_SMALL
                    ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon) # ICON_BIG
        except Exception:
            pass
        
        # Animated Canvas for Logo
        self.logo = AnimatedLogo(self, width=200, height=150, bg_color=Colors.BG_DARKEST)
        self.logo.pack(pady=(40, 20))
        
        self.logo_label = ctk.CTkLabel(
            self, text="Cripple - NetStrip",
            font=(Fonts.FAMILY_PRIMARY[0], 28, "bold"),
            text_color=Colors.TEXT_PRIMARY
        )
        self.logo_label.pack()
        
        self.status_label = ctk.CTkLabel(
            self, text="Initializing core engine...",
            font=(Fonts.FAMILY_PRIMARY[0], 12),
            text_color=Colors.TEXT_TERTIARY
        )
        self.status_label.pack(pady=10)
        
        self.progress = ctk.CTkProgressBar(self, width=250, progress_color=Colors.ACCENT_PRIMARY)
        self.progress.pack(pady=10)
        self.progress.set(0)
        
        self.copyright_label = ctk.CTkLabel(
            self, text="© 2026 FrenzyPenguin Media",
            font=(Fonts.FAMILY_PRIMARY[0], 10),
            text_color=Colors.TEXT_TERTIARY
        )
        self.copyright_label.pack(side="bottom", pady=10)
        
        # Start dynamic loading animation
        self.after(500, self._cycle_loading_text)
        
    def update_status(self, text, progress_val):
        """Update the loading text and progress bar."""
        if self.winfo_exists():
            self.status_label.configure(text=text)
            self.progress.set(progress_val)
            self.update()
            
    def _cycle_loading_text(self):
        if not self.winfo_exists():
            return
            
        import random
        if not hasattr(self, '_phrases'):
            self._phrases = [
                "Initializing deep packet inspection...",
                "Loading threat intelligence lists...",
                "Calibrating DNS sinkhole...",
                "Establishing zero-leak interceptor...",
                "Synchronizing firewall rules...",
                "Warming up the Cripple Engine...",
                "Mapping telemetry endpoints...",
                "Connecting to secure upstream DNS...",
                "Parsing behavioral app profiles...",
                "Arming the manual killswitch...",
                "Validating LAN passthrough routes...",
                "Initializing local SQLite database...",
                "Booting the background monitor...",
                "Loading visual layout engines...",
                "Ensuring memory safety bounds..."
            ]
            random.shuffle(self._phrases)
            self._phrase_idx = 0
        
        # Don't overwrite if it's a specific engine broadcast
        current = self.status_label.cget("text")
        if current.endswith("..."):
            self.status_label.configure(text=self._phrases[self._phrase_idx])
            self._phrase_idx = (self._phrase_idx + 1) % len(self._phrases)
            
        # Slightly advance progress bar artificially
        current_prog = self.progress.get()
        if current_prog < 0.9:
            self.progress.set(current_prog + 0.05)
            
        self.after(1500, self._cycle_loading_text)

    def fade_out(self, callback=None):
        """Fade out the splash screen before destroying it."""
        if not self.winfo_exists():
            if callback:
                callback()
            return
            
        alpha = self.attributes('-alpha')
        if alpha > 0.05:
            alpha -= 0.05
            self.attributes('-alpha', alpha)
            self.after(20, self.fade_out, callback)
        else:
            self.withdraw()
            if callback:
                callback()

