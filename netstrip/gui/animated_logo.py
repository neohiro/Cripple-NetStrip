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
        self._running = True
        self._anim_id = None
        
        # Draw initial resting frame
        self._draw_frame(0, 0)
        
        # Ensure it starts animating
        self._animate()

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
            
        top = self.winfo_toplevel()
        if top:
            try:
                state = str(top.state())
                if state in ("iconic", "withdrawn") or not self.winfo_ismapped():
                    # Pause animation if window is hidden, check again in 250ms
                    self._anim_id = self.after(250, self._animate)
                    return
            except Exception:
                pass
                
        self._animation_step = (self._animation_step + 0.15) % (2 * math.pi)
        
        # Dynamic Bounce animation using sine wave (increased amplitude to 12)
        up_offset = math.sin(self._animation_step) * (12 * self._scale_y)
        down_offset = math.cos(self._animation_step) * (12 * self._scale_y)
        
        self._draw_frame(up_offset, down_offset)
        
        # Capped framerate strictly to 25 FPS (40ms) to ensure GPU stability
        self._anim_id = self.after(40, self._animate)
