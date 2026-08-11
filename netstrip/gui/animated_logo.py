import customtkinter as ctk
import math
from netstrip.gui.theme import Colors

class AnimatedLogo(ctk.CTkCanvas):
    def __init__(self, master, width=60, height=50, bg_color=Colors.BG_PANEL, **kwargs):
        super().__init__(master, width=width, height=height, bg=bg_color, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        
        # We will scale the original coords [200x150] down to the provided width/height
        self._scale_x = width / 200.0
        self._scale_y = height / 150.0
        
        self.up_poly = self.create_polygon(
            [0,0, 0,0, 0,0, 0,0, 0,0, 0,0, 0,0],
            fill=Colors.ACCENT_PRIMARY, outline="", smooth=False
        )
        self.down_poly = self.create_polygon(
            [0,0, 0,0, 0,0, 0,0, 0,0, 0,0, 0,0],
            fill=Colors.SUCCESS, outline="", smooth=False
        )
        
        self._animation_step = 0
        self._running = False
        self._anim_id = None
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        # Draw initial resting frame
        self._draw_frame(0, 0)

    def _draw_frame(self, up_offset, down_offset):
        sx = self._scale_x
        sy = self._scale_y
        
        self.coords(
            self.up_poly,
            70*sx, (120*sy) + up_offset, 70*sx, (60*sy) + up_offset, 50*sx, (60*sy) + up_offset, 
            85*sx, (20*sy) + up_offset, 120*sx, (60*sy) + up_offset, 100*sx, (60*sy) + up_offset, 100*sx, (120*sy) + up_offset
        )
        
        self.coords(
            self.down_poly,
            100*sx, (30*sy) + down_offset, 100*sx, (90*sy) + down_offset, 80*sx, (90*sy) + down_offset, 
            115*sx, (130*sy) + down_offset, 150*sx, (90*sy) + down_offset, 130*sx, (90*sy) + down_offset, 130*sx, (30*sy) + down_offset
        )

    def _on_enter(self, event):
        self._running = True
        if not self._anim_id:
            self._animate()

    def _on_leave(self, event):
        self._running = False
        self.stop_animation()
        self._animation_step = 0
        self._draw_frame(0, 0)

    def stop_animation(self):
        """Stop animation loop and cancel pending timer."""
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
            
        self._animation_step = (self._animation_step + 0.15) % (2 * math.pi)
        
        # Bounce animation using sine wave, scaled
        up_offset = math.sin(self._animation_step) * (5 * self._scale_y)
        down_offset = math.cos(self._animation_step) * (5 * self._scale_y)
        
        self._draw_frame(up_offset, down_offset)
        
        # Reduced framerate for better UI stability
        self._anim_id = self.after(30, self._animate)
