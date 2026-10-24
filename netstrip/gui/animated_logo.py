import customtkinter as ctk
import math
from PIL import Image, ImageTk
import os
from netstrip.gui.theme import Colors, Animation

class AnimatedLogo(ctk.CTkCanvas):
    """Real Cripple logo with gentle pulse animation — fast, accurate, professional."""
    def __init__(self, master, width=200, height=160, bg_color=Colors.BG_PANEL, **kwargs):
        super().__init__(master, width=width, height=height, bg=bg_color, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        self._scale_x = width / 200.0
        self._scale_y = height / 160.0

        # Load real logo asset (arrow-up / arrow-down from GitHub)
        asset_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'cripple_logo.png')
        asset_path = os.path.abspath(asset_path)
        try:
            self.img = Image.open(asset_path).convert("RGBA")
        except Exception:
            # Fallback if asset missing — blank but never crash
            self.img = Image.new("RGBA", (200, 160), (0, 0, 0, 0))

        # Resize to canvas with smooth scaling
        self.img_resized = self.img.resize((width, height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(self.img_resized)

        # Center image on canvas
        self.img_id = self.create_image(width/2, height/2, image=self.photo)

        # Glow ring behind logo (bloom effect)
        self.glow_id = self.create_oval(
            width*0.12, height*0.12, width*0.88, height*0.88,
            fill="#8b5cf620", outline="#8b5cf6", width=2
        )

        self._anim_id = None
        self._running = True
        self._anim_step = 0
        self._pulse = 0.0

        self._draw_frame(0)
        self._animate()

    def _draw_frame(self, offset_phase=0):
        # Gentle bounce + glow intensity
        bounce = math.sin(self._anim_step * 0.15) * (3 * self._scale_y)
        pulse = 0.6 + 0.4 * math.sin(self._anim_step * 0.3)
        # Update glow intensity
        try:
            self.itemconfig(self.glow_id, outline="#8b5cf6" if pulse > 0.8 else "#8b5cf680",
                           fill=f"#8b5cf6{int(pulse*30):02x}")
        except Exception:
            pass
        # Subtle bounce on image
        try:
            cx = self.width / 2
            cy = self.height / 2 + bounce
            self.coords(self.img_id, cx, cy)
        except Exception:
            pass

    def stop_animation(self):
        self._running = False
        if self._anim_id:
            try:
                self.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None

    def _animate(self):
        if not self._running or not self.winfo_exists():
            return
        top = self.winfo_toplevel()
        if top:
            try:
                state = str(top.state())
                if state in ("iconic", "withdrawn") or not self.winfo_ismapped():
                    self._anim_id = self.after(250, self._animate)
                    return
            except Exception:
                pass
        self._anim_step += 1
        self._draw_frame(self._anim_step)
        self._anim_id = self.after(40, self._animate)  # 25 FPS — fast and smooth
