import customtkinter as ctk
import math
from netstrip.gui.theme import Colors

class AnimatedLogo(ctk.CTkCanvas):
    def __init__(self, master, width=60, height=50, bg_color=Colors.BG_PANEL, **kwargs):
        super().__init__(master, width=width, height=height, bg=bg_color, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        
        # We will scale the original coords [200x150] down to the provided width/height
        scale_x = width / 200.0
        scale_y = height / 150.0
        
        self.up_poly = self.create_polygon(
            [70*scale_x, 120*scale_y, 70*scale_x, 60*scale_y, 50*scale_x, 60*scale_y, 
             85*scale_x, 20*scale_y, 120*scale_x, 60*scale_y, 100*scale_x, 60*scale_y, 100*scale_x, 120*scale_y],
            fill=Colors.ACCENT_PRIMARY, outline="", smooth=False
        )
        self.down_poly = self.create_polygon(
            [100*scale_x, 30*scale_y, 100*scale_x, 90*scale_y, 80*scale_x, 90*scale_y, 
             115*scale_x, 130*scale_y, 150*scale_x, 90*scale_y, 130*scale_x, 90*scale_y, 130*scale_x, 30*scale_y],
            fill=Colors.SUCCESS, outline="", smooth=False
        )
        
        self._animation_step = 0
        self._scale_y = scale_y
        self._animate()

    def _animate(self):
        if not self.winfo_exists():
            return
            
        self._animation_step += 0.05
        # Bounce animation using sine wave, scaled
        up_offset = math.sin(self._animation_step) * (5 * self._scale_y)
        down_offset = math.cos(self._animation_step) * (5 * self._scale_y)
        
        scale_x = self.width / 200.0
        scale_y = self.height / 150.0
        
        self.coords(
            self.up_poly,
            70*scale_x, (120*scale_y) + up_offset, 70*scale_x, (60*scale_y) + up_offset, 50*scale_x, (60*scale_y) + up_offset, 
            85*scale_x, (20*scale_y) + up_offset, 120*scale_x, (60*scale_y) + up_offset, 100*scale_x, (60*scale_y) + up_offset, 100*scale_x, (120*scale_y) + up_offset
        )
        
        self.coords(
            self.down_poly,
            100*scale_x, (30*scale_y) + down_offset, 100*scale_x, (90*scale_y) + down_offset, 80*scale_x, (90*scale_y) + down_offset, 
            115*scale_x, (130*scale_y) + down_offset, 150*scale_x, (90*scale_y) + down_offset, 130*scale_x, (90*scale_y) + down_offset, 130*scale_x, (30*scale_y) + down_offset
        )
        
        # 16ms for ~60fps smooth animation
        self.after(16, self._animate)
