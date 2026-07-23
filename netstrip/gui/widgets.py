"""
Custom UI Widgets for Cripple GUI
Reusable components built on top of customtkinter.
"""

import customtkinter as ctk
from netstrip.gui.theme import Colors, Fonts, Spacing, CTK_FRAME_STYLE, CTK_LABEL_STYLE, CTK_LABEL_MUTED_STYLE

class StatCard(ctk.CTkFrame):
    def __init__(self, master, title, value="0", icon="", color=Colors.ACCENT_PRIMARY, subtitle="", **kwargs):
        super().__init__(master, **{**CTK_FRAME_STYLE, **kwargs})
        self.color = color
        
        # Left-aligned container to prevent horizontal shifting/glitching on value update
        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(fill="both", expand=True, padx=Spacing.LG, pady=Spacing.LG)
        
        # Grid layout for inner
        self.inner.grid_columnconfigure(0, weight=0, minsize=50) # Fixed icon width
        self.inner.grid_columnconfigure(1, weight=1) # Flexible text area
        
        # Icon (Futuristic accent)
        self.icon_label = ctk.CTkLabel(
            self.inner, text=icon, 
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XL + 6),
            text_color=self.color,
            anchor="center"
        )
        rowspan = 3 if subtitle else 2
        self.icon_label.grid(row=0, column=0, rowspan=rowspan, sticky="nsw")
        
        # Value (Larger, more minimal)
        self.value_label = ctk.CTkLabel(
            self.inner, text=value,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XL, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY
        )
        self.value_label.grid(row=0, column=1, sticky="sw", pady=(0, 2))
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.inner, text=title.upper(),
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS, "bold"),
            text_color=Colors.TEXT_TERTIARY
        )
        self.title_label.grid(row=1, column=1, sticky="nw")
        
        if subtitle:
            self.subtitle_label = ctk.CTkLabel(
                self.inner, text=subtitle,
                font=(Fonts.FAMILY_PRIMARY[0], 10),
                text_color=self.color
            )
            self.subtitle_label.grid(row=2, column=1, sticky="w", pady=(4, 0))
            
        self._resize_timer = None
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        self._resize_timer = self.after(50, lambda: self._apply_resize(event.width))

    def _apply_resize(self, width):
        # Scale between 0.8x and 2.0x based on 250px baseline
        scale = max(0.8, min(2.0, width / 250.0))
        self._current_scale = scale
        
        # Re-apply value to calculate correct font size with new scale
        self.set_value(self.value_label.cget("text"))
        
        # Scale icon
        icon_size = int((Fonts.SIZE_XL + 4) * scale)
        self.icon_label.configure(font=(Fonts.FAMILY_PRIMARY[0], icon_size))
        
        # Scale title
        title_size = int(Fonts.SIZE_SM * scale)
        self.title_label.configure(font=(Fonts.FAMILY_PRIMARY[0], title_size, Fonts.WEIGHT_BOLD))
        
        if hasattr(self, 'subtitle_label'):
            sub_size = int(9 * scale)
            self.subtitle_label.configure(font=(Fonts.FAMILY_PRIMARY[0], sub_size))

    def set_value(self, value: str):
        val_str = str(value)
        scale = getattr(self, '_current_scale', 1.0)
        
        # Use a constant font size (SIZE_BASE) to prevent vertical bouncing 
        # and glitchy redraws when string length changes.
        scaled_size = int(Fonts.SIZE_BASE * scale)
        self.value_label.configure(text=val_str, font=(Fonts.FAMILY_PRIMARY[0], scaled_size, Fonts.WEIGHT_BOLD))

    def set_subtitle(self, subtitle: str):
        if hasattr(self, 'subtitle_label'):
            self.subtitle_label.configure(text=subtitle)


class ModeSelector(ctk.CTkFrame):
    def __init__(self, master, on_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_change = on_change
        self.current_value = "Normal"
        
        # Use standard buttons instead of CTkSegmentedButton to bypass a massive 3.6s initialization bug in CustomTkinter
        self.grid_columnconfigure((0,1,2), weight=1)
        
        self.buttons = {}
        for i, val in enumerate(["Paranoid", "Normal", "Loose"]):
            btn = ctk.CTkButton(
                self, text=val,
                command=lambda v=val: self._handle_change(v),
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD),
                fg_color=Colors.BG_PANEL,
                hover_color=Colors.BG_ELEVATED,
                text_color=Colors.TEXT_SECONDARY,
                corner_radius=4,
                height=28
            )
            btn.grid(row=0, column=i, padx=2, sticky="ew")
            self.buttons[val] = btn
            
        self.set("Normal")

    def _handle_change(self, value):
        self.set(value)
        if self.on_change:
            self.on_change(value)
            
    def get(self):
        return self.current_value
        
    def set(self, value):
        self.current_value = value
        for val, btn in self.buttons.items():
            if val == value:
                btn.configure(fg_color=Colors.ACCENT_PRIMARY, hover_color=Colors.ACCENT_LIGHT, text_color="white")
            else:
                btn.configure(fg_color=Colors.BG_PANEL, hover_color=Colors.BG_ELEVATED, text_color=Colors.TEXT_SECONDARY)
        

class ShieldIndicator(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.icon = ctk.CTkLabel(
            self, text="🛡", 
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_4XL),
            text_color=Colors.SUCCESS
        )
        self.icon.pack(pady=Spacing.MD)
        
        self.status = ctk.CTkLabel(
            self, text="Protection Active",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, Fonts.WEIGHT_BOLD),
            text_color=Colors.SUCCESS
        )
        self.status.pack()

    def set_state(self, is_active: bool, mode_name: str = "Normal"):
        if is_active:
            if mode_name == "Paranoid":
                color = Colors.MODE_PARANOID
                status = "Maximum Protection"
            elif mode_name == "Loose":
                color = Colors.MODE_LOOSE
                status = "Minimal Protection"
            else:
                color = Colors.MODE_NORMAL
                status = "Balanced Protection"
                
            self.icon.configure(text_color=color)
            self.status.configure(text=status, text_color=color)
        else:
            self.icon.configure(text_color=Colors.TEXT_TERTIARY)
            self.status.configure(text="Protection Paused", text_color=Colors.TEXT_TERTIARY)
