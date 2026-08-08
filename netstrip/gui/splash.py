"""
NetStrip - High-Performance Instant Splash Screen
Ultra-lightweight, zero-dependency native Tkinter splash screen for sub-50ms startup.
"""

import tkinter as tk
import math
import time
import random
import os
import sys

class SplashScreen(tk.Toplevel):
    """
    Ultra-responsive native Tkinter Splash Screen.
    Loads instantly without heavy third-party GUI or image libraries.
    """
    def __init__(self, master=None, *args, **kwargs):
        if master is None:
            self._standalone_root = tk.Tk()
            self._standalone_root.withdraw()
            super().__init__(self._standalone_root, *args, **kwargs)
        else:
            self._standalone_root = None
            super().__init__(master, *args, **kwargs)

        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.after(1200, lambda: self._safe_remove_topmost())


        # Styling
        self.bg_color = "#0B0E14"
        self.border_color = "#1E293B"
        self.accent_blue = "#3B82F6"
        self.accent_cyan = "#38BDF8"
        self.accent_green = "#10B981"
        self.text_primary = "#F8FAFC"
        self.text_secondary = "#94A3B8"
        self.text_muted = "#475569"
        self.track_color = "#161D2B"

        self.configure(bg=self.bg_color)

        # Center on primary monitor
        self.w = 440
        self.h = 370
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - self.w) // 2)
        y = max(0, (sh - self.h) // 2)
        self.geometry(f"{self.w}x{self.h}+{x}+{y}")

        # Canvas for rich hardware-accelerated drawing
        self.canvas = tk.Canvas(
            self, width=self.w, height=self.h,
            bg=self.bg_color, highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Subtle modern outer border
        self.canvas.create_rectangle(1, 1, self.w - 2, self.h - 2, outline=self.border_color, width=1)

        # Draw Animated Shield Logo (Center X: 220, Base Y: 35)
        self.logo_cx = 220
        self.logo_base_y = 35
        self._anim_step = 0
        self._running = True
        self._last_custom_update = 0

        # Up arrow (Blue)
        self.up_poly = self.canvas.create_polygon(
            self._get_up_coords(0),
            fill=self.accent_blue, outline="", smooth=False
        )
        # Down arrow (Emerald)
        self.down_poly = self.canvas.create_polygon(
            self._get_down_coords(0),
            fill=self.accent_green, outline="", smooth=False
        )

        # Glowing accent lines on shield
        self.glow_line = self.canvas.create_line(
            self.logo_cx - 40, self.logo_base_y + 60,
            self.logo_cx + 40, self.logo_base_y + 60,
            fill=self.accent_cyan, width=1
        )

        # Title & Badge
        self.canvas.create_text(
            self.logo_cx - 22, 190,
            text="Cripple - NetStrip",
            fill=self.text_primary,
            font=("Segoe UI", 18, "bold")
        )
        self.canvas.create_text(
            self.logo_cx + 105, 187,
            text="v3.3.9",
            fill=self.accent_cyan,
            font=("Segoe UI", 9, "bold")
        )

        # Status text
        self.status_id = self.canvas.create_text(
            self.logo_cx, 225,
            text="Initializing core engine...",
            fill=self.text_secondary,
            font=("Segoe UI", 10)
        )

        # Rounded Capsule Progress Bar
        self.bar_x1 = 55
        self.bar_y1 = 255
        self.bar_x2 = self.w - 55
        self.bar_y2 = 265
        self.bar_width = self.bar_x2 - self.bar_x1

        # Background track
        self.canvas.create_rectangle(
            self.bar_x1, self.bar_y1, self.bar_x2, self.bar_y2,
            fill=self.track_color, outline=""
        )

        # Fill bar
        self._target_progress = 0.0
        self._current_progress = 0.0
        self.progress_bar = self.canvas.create_rectangle(
            self.bar_x1, self.bar_y1, self.bar_x1, self.bar_y2,
            fill=self.accent_blue, outline=""
        )

        # Shimmer highlight on progress bar
        self.shimmer = self.canvas.create_rectangle(
            self.bar_x1, self.bar_y1, self.bar_x1, self.bar_y2,
            fill=self.accent_cyan, outline=""
        )

        # Subtitle / Shield status
        self.canvas.create_text(
            self.logo_cx, 288,
            text="Intelligent Network Debloater & DNS Sinkhole",
            fill=self.text_muted,
            font=("Segoe UI", 8)
        )

        # Footer Copyright
        self.canvas.create_text(
            self.logo_cx, 340,
            text="© 2026 FrenzyPenguin Media",
            fill=self.text_muted,
            font=("Segoe UI", 8)
        )

        # Initialize loading phrases
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

        # Start animations
        self._anim_id = None
        self._cycle_id = None
        self._smooth_prog_id = None
        self._animate()
        self._cycle_id = self.after(800, self._cycle_loading_text)
        self._smooth_prog_id = self.after(20, self._smooth_progress_tick)

        # Force draw NOW so window is visible immediately
        try:
            self.update()
        except Exception:
            pass

    def _safe_remove_topmost(self):
        try:
            if self.winfo_exists():
                self.attributes('-topmost', False)
        except Exception:
            pass

    def _get_up_coords(self, offset):
        cx = self.logo_cx
        cy = self.logo_base_y + offset
        scale_x = 0.85
        scale_y = 0.85
        return [
            cx - 25 * scale_x, cy + 115 * scale_y,
            cx - 25 * scale_x, cy + 60 * scale_y,
            cx - 45 * scale_x, cy + 60 * scale_y,
            cx - 10 * scale_x, cy + 20 * scale_y,
            cx + 25 * scale_x, cy + 60 * scale_y,
            cx + 5 * scale_x, cy + 60 * scale_y,
            cx + 5 * scale_x, cy + 115 * scale_y
        ]

    def _get_down_coords(self, offset):
        cx = self.logo_cx
        cy = self.logo_base_y + offset
        scale_x = 0.85
        scale_y = 0.85
        return [
            cx + 5 * scale_x, cy + 30 * scale_y,
            cx + 5 * scale_x, cy + 85 * scale_y,
            cx - 15 * scale_x, cy + 85 * scale_y,
            cx + 20 * scale_x, cy + 125 * scale_y,
            cx + 55 * scale_x, cy + 85 * scale_y,
            cx + 35 * scale_x, cy + 85 * scale_y,
            cx + 35 * scale_x, cy + 30 * scale_y
        ]

    def _animate(self):
        if not self._running or not self.winfo_exists():
            return

        self._anim_step += 0.06
        up_offset = math.sin(self._anim_step) * 4.0
        down_offset = math.cos(self._anim_step) * 4.0

        try:
            self.canvas.coords(self.up_poly, *self._get_up_coords(up_offset))
            self.canvas.coords(self.down_poly, *self._get_down_coords(down_offset))

            # Pulse glow line
            glow_x = self.logo_cx + math.sin(self._anim_step * 1.5) * 20
            self.canvas.coords(
                self.glow_line,
                glow_x - 30, self.logo_base_y + 60 + (up_offset * 0.5),
                glow_x + 30, self.logo_base_y + 60 + (up_offset * 0.5)
            )
        except Exception:
            pass

        if self._running:
            self._anim_id = self.after(25, self._animate)

    def _smooth_progress_tick(self):
        """Interpolates the progress bar smoothly towards target progress."""
        if not self._running or not self.winfo_exists():
            return

        diff = self._target_progress - self._current_progress
        if abs(diff) > 0.001:
            self._current_progress += diff * 0.15
            fill_x = self.bar_x1 + (self.bar_width * max(0.0, min(1.0, self._current_progress)))
            try:
                self.canvas.coords(self.progress_bar, self.bar_x1, self.bar_y1, fill_x, self.bar_y2)
                
                # Shimmer effect
                shimmer_x1 = max(self.bar_x1, fill_x - 20)
                self.canvas.coords(self.shimmer, shimmer_x1, self.bar_y1, fill_x, self.bar_y2)
            except Exception:
                pass

        if self._running:
            self._smooth_prog_id = self.after(20, self._smooth_progress_tick)

    def update_status(self, text: str, progress_val: float):
        """Update loading status message and target progress value."""
        self._last_custom_update = time.time()
        self._target_progress = max(self._target_progress, float(progress_val))
        if self.winfo_exists():
            try:
                self.canvas.itemconfigure(self.status_id, text=text)
                self.update_idletasks()
            except Exception:
                pass

    def _cycle_loading_text(self):
        if not self._running or not self.winfo_exists():
            return

        if time.time() - self._last_custom_update > 2.5:
            try:
                self.canvas.itemconfigure(self.status_id, text=self._phrases[self._phrase_idx])
                self._phrase_idx = (self._phrase_idx + 1) % len(self._phrases)
                if self._target_progress < 0.85:
                    self._target_progress += 0.04
            except Exception:
                pass

        if self._running:
            self._cycle_id = self.after(1400, self._cycle_loading_text)

    def stop_animation(self):
        """Stops all running timers and loops."""
        self._running = False
        for aid in (self._anim_id, self._cycle_id, self._smooth_prog_id):
            if aid:
                try:
                    self.after_cancel(aid)
                except Exception:
                    pass
        self._anim_id = None
        self._cycle_id = None
        self._smooth_prog_id = None

    def fade_out(self, callback=None, step=0, total_steps=8):
        """Smoothly fades out splash screen alpha before calling completion callback."""
        if step == 0:
            self.stop_animation()
            # Force progress to 100%
            self._current_progress = 1.0
            fill_x = self.bar_x1 + self.bar_width
            try:
                self.canvas.coords(self.progress_bar, self.bar_x1, self.bar_y1, fill_x, self.bar_y2)
                self.canvas.itemconfigure(self.status_id, text="Ready!")
                self.update()
            except Exception:
                pass

        if not self.winfo_exists():
            if callback:
                callback()
            return

        progress = min(1.0, float(step) / float(total_steps))
        eased = (1.0 - math.cos(progress * math.pi)) / 2.0
        alpha = max(0.0, 1.0 - eased)

        try:
            self.attributes('-alpha', alpha)
        except Exception:
            pass

        if step < total_steps:
            self.after(20, lambda: self.fade_out(callback, step + 1, total_steps))
        else:
            try:
                self.withdraw()
            except Exception:
                pass
            if callback:
                callback()

    def destroy(self):
        self.stop_animation()
        try:
            super().destroy()
        except Exception:
            pass
        if self._standalone_root:
            try:
                self._standalone_root.destroy()
            except Exception:
                pass
            self._standalone_root = None

