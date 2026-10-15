import customtkinter as ctk
import math
from netstrip.gui.theme import Colors, Animation

class AnimatedLogo(ctk.CTkCanvas):
    """Premium animated logo with bloom glow effects for 4K displays."""
    def __init__(self, master, width=200, height=160, bg_color=Colors.BG_PANEL, **kwargs):
        super().__init__(master, width=width, height=height, bg=bg_color, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        
        self._scale_x = width / 200.0
        self._scale_y = height / 160.0
        
        # Main logo shape - shield with circuit pattern
        self.shield_path = self.create_polygon(
            [0]*14, fill=Colors.ACCENT_PRIMARY, outline="", smooth=True
        )
        self.circuit_lines = []
        for _ in range(6):
            line = self.create_line(0, 0, 0, 0, fill=Colors.ACCENT_CYAN, width=2, capstyle="round")
            self.circuit_lines.append(line)
        
        # Glow layers for bloom effect
        self.glow_layers = []
        for i in range(3):
            glow = self.create_polygon([0]*14, fill="", outline="", smooth=True)
            self.glow_layers.append(glow)
        
        self._animation_step = 0
        self._running = True
        self._anim_id = None
        self._pulse_phase = 0
        self._bloom_intensity = 0
        self._target_bloom = 0
        
        self._draw_frame(0)
        self._animate()

    def _draw_frame(self, bounce_offset):
        sx = self._scale_x
        sy = self._scale_y
        cx = self.width / 2
        cy = self.height / 2
        
        # Shield shape points (rounded shield)
        shield_pts = [
            cx, cy - 70*sy + bounce_offset,      # Top center
            cx + 50*sx, cy - 40*sy + bounce_offset,  # Top right
            cx + 65*sx, cy + 10*sy + bounce_offset,  # Mid right
            cx + 45*sx, cy + 55*sy + bounce_offset,  # Lower right
            cx, cy + 80*sy + bounce_offset,       # Bottom point
            cx - 45*sx, cy + 55*sy + bounce_offset,  # Lower left
            cx - 65*sx, cy + 10*sy + bounce_offset,  # Mid left
            cx - 50*sx, cy - 40*sy + bounce_offset,  # Top left
        ]
        flat_pts = [coord for pt in zip(shield_pts[::2], shield_pts[1::2]) for coord in pt]
        
        self.coords(self.shield_path, *flat_pts)
        
        # Circuit lines - animated pulse
        pulse = math.sin(self._pulse_phase) * 0.5 + 0.5
        
        # Horizontal circuit lines
        self.coords(self.circuit_lines[0], 
            cx - 40*sx, cy - 10*sy + bounce_offset, cx + 40*sx, cy - 10*sy + bounce_offset)
        self.coords(self.circuit_lines[1], 
            cx - 35*sx, cy + 20*sy + bounce_offset, cx + 35*sx, cy + 20*sy + bounce_offset)
        # Vertical center line
        self.coords(self.circuit_lines[2], 
            cx, cy - 30*sy + bounce_offset, cx, cy + 60*sy + bounce_offset)
        # Small accent dots
        self.coords(self.circuit_lines[3], 
            cx - 20*sx, cy - 10*sy + bounce_offset, cx - 20*sx, cy - 10*sy + bounce_offset)
        self.coords(self.circuit_lines[4], 
            cx + 20*sx, cy + 20*sy + bounce_offset, cx + 20*sx, cy + 20*sy + bounce_offset)
        self.coords(self.circuit_lines[5], 
            cx, cy + 45*sy + bounce_offset, cx, cy + 45*sy + bounce_offset)
        
        # Bloom glow layers - expanding/contracting
        for i, glow in enumerate(self.glow_layers):
            bloom_scale = 1.0 + (self._bloom_intensity * 0.15) + (i * 0.08)
            glow_pts = []
            for x, y in zip(shield_pts[::2], shield_pts[1::2]):
                gx = cx + (x - cx) * bloom_scale
                gy = cy + (y - cy) * bloom_scale
                glow_pts.extend([gx, gy])
            self.coords(glow, *glow_pts)
            # Glow color with intensity
            glow_colors = [Colors.ACCENT_PRIMARY, Colors.ACCENT_CYAN, Colors.ACCENT_LIGHT]
            intensity = max(0, self._bloom_intensity - i * 0.3)
            if intensity > 0:
                self.itemconfig(glow, outline=glow_colors[i], width=int(2 + intensity * 4))

    def stop_animation(self):
        self._running = False
        if self._anim_id:
            try: self.after_cancel(self._anim_id)
            except: pass
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
            except: pass
        
        # Main bounce animation
        self._animation_step = (self._animation_step + 0.12) % (2 * math.pi)
        bounce = math.sin(self._animation_step) * (10 * self._scale_y)
        
        # Pulse phase for circuit lines
        self._pulse_phase = (self._pulse_phase + 0.08) % (2 * math.pi)
        
        # Bloom effect - breathes slowly
        self._target_bloom = 0.5 + 0.5 * math.sin(self._animation_step * 0.3)
        self._bloom_intensity += (self._target_bloom - self._bloom_intensity) * 0.1
        
        self._draw_frame(bounce)
        self._anim_id = self.after(Animation.NORMAL, self._animate)
