import customtkinter as ctk
from netstrip.gui.theme import Colors, Fonts
from netstrip.gui.animated_logo import AnimatedLogo

class SplashScreen(ctk.CTkToplevel):
    def __init__(self, master=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        # Remove topmost after a short delay so that firewall prompts can be visible
        self.after(1000, lambda: self.attributes('-topmost', False))
        self.configure(fg_color=Colors.BG_DARKEST)
        
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
        
        # Center the splash screen reliably across all resolutions and DPI scalings
        from netstrip.gui.utils import center_window, apply_window_icon
        apply_window_icon(self)
        center_window(self, 400, 400)
        
        self._cycle_id = None
        # Start dynamic loading animation
        self._cycle_id = self.after(500, self._cycle_loading_text)
        
    def stop_animation(self):
        """Stops all background timers and canvas animations."""
        if hasattr(self, '_cycle_id') and self._cycle_id:
            try:
                self.after_cancel(self._cycle_id)
            except Exception:
                pass
            self._cycle_id = None
        if hasattr(self, 'logo') and self.logo:
            try:
                self.logo.stop_animation()
            except Exception:
                pass

    def update_status(self, text, progress_val):
        """Update the loading text and progress bar."""
        import time
        self._last_custom_update = time.time()
        if self.winfo_exists():
            try:
                self.status_label.configure(text=text)
                self.progress.set(progress_val)
                self.update_idletasks()
            except Exception:
                pass
            
    def _cycle_loading_text(self):
        if not self.winfo_exists():
            return
            
        import time
        import random
        # If we received a live progress update within the last 3.0 seconds, don't overwrite it
        if time.time() - getattr(self, '_last_custom_update', 0) < 3.0:
            self._cycle_id = self.after(500, self._cycle_loading_text)
            return

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
        
        try:
            self.status_label.configure(text=self._phrases[self._phrase_idx])
            self._phrase_idx = (self._phrase_idx + 1) % len(self._phrases)
            
            # Slightly advance progress bar artificially if below 0.9
            current_prog = self.progress.get()
            if current_prog < 0.9:
                self.progress.set(current_prog + 0.05)
        except Exception:
            pass
            
        self._cycle_id = self.after(1500, self._cycle_loading_text)

    def fade_out(self, callback=None, step=0, total_steps=10):
        """Fade out the splash screen smoothly before destroying it."""
        if step == 0:
            self.stop_animation()

        if not self.winfo_exists():
            if callback:
                callback()
            return
            
        import math
        progress = min(1.0, float(step) / float(total_steps))
        eased = (1.0 - math.cos(progress * math.pi)) / 2.0
        alpha = max(0.0, 1.0 - eased)
        
        try:
            self.attributes('-alpha', alpha)
        except Exception:
            pass
            
        if step < total_steps:
            self.after(25, lambda: self.fade_out(callback, step + 1, total_steps))
        else:
            try:
                self.withdraw()
            except Exception:
                pass
            if callback:
                callback()

