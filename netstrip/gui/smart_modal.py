"""
Smart Modal for Cripple GUI
Displays a critical alert when Smart Ghost Mode is triggered.
"""

import customtkinter as ctk
from netstrip.gui.theme import Colors, Fonts, Spacing, Icons, CTK_BUTTON_DANGER_STYLE, CTK_BUTTON_SECONDARY_STYLE

class SmartParanoidModal(ctk.CTkToplevel):
    def __init__(self, master, engine, conn_data, **kwargs):
        super().__init__(master, **kwargs)
        self.engine = engine
        self.conn_data = conn_data
        
        self.title("CRITICAL ALERT - Smart Shield Triggered")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color=Colors.BG_DARKEST)
        from netstrip.gui.utils import center_window, apply_window_icon, get_app_logo_image
        apply_window_icon(self)
        center_window(self, 500, 320, parent=master)

        self._build_ui()
        
    def _build_ui(self):
        from netstrip.gui.utils import get_app_logo_image
        # Outer container with a thin info/danger border
        frame = ctk.CTkFrame(self, fg_color=Colors.BG_DARKEST, bg_color=Colors.BG_DARKEST, corner_radius=8, border_width=1, border_color=Colors.DANGER)
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=24)
        
        # Header with Cripple logo and title
        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        
        logo_img = get_app_logo_image(size=(24, 24))
        if logo_img:
            lbl_logo = ctk.CTkLabel(header, image=logo_img, text="")
            lbl_logo.pack(side="left", padx=(0, 10))
            
        lbl_title = ctk.CTkLabel(header, text="SMART SHIELD ACTIVATED", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, "bold"), text_color=Colors.DANGER)
        lbl_title.pack(side="left")
        
        ctk.CTkFrame(inner, fg_color=Colors.BORDER_SUBTLE, height=1).pack(fill="x", pady=(0, 20))
        
        target = self.conn_data.get('domain') or self.conn_data.get('ip', 'Unknown')
        process = self.conn_data.get('process_name', 'Unknown')
        
        lbl_desc = ctk.CTkLabel(inner, text=(
            "CRITICAL SECURITY EVENT INTERCEPTED.\n\n"
            "> Threat detected automatically.\n"
            "> Forcing lock-down to GHOST mode...\n\n"
            f"Process: {process}\nTarget: {target}"
        ), font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE), justify="left", text_color=Colors.TEXT_SECONDARY)
        lbl_desc.pack(anchor="w", pady=(0, 20))
        
        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        btn_disable = ctk.CTkButton(
            btn_frame, text="DISABLE SMART SHIELD", fg_color="transparent", border_width=1, border_color=Colors.BORDER_SUBTLE,
            hover_color=Colors.BG_PANEL, text_color=Colors.TEXT_TERTIARY, bg_color=Colors.BG_DARKEST, corner_radius=8, command=self._disable_smart_shield
        )
        btn_disable.pack(side="left", expand=True, padx=(0, 5))
        
        btn_keep = ctk.CTkButton(
            btn_frame, text="KEEP LOCKED DOWN", fg_color=Colors.DANGER, 
            hover_color="#991b1b", text_color="white", bg_color=Colors.BG_DARKEST, corner_radius=8, command=self.destroy
        )
        btn_keep.pack(side="right", expand=True, padx=(5, 0))

    def _disable_smart_shield(self):
        from netstrip.core.modes import ProtectionLevel
        self.engine.db.set_setting("smart_paranoid_mode", "false")
        
        # Revert mode to Normal
        self.engine.set_mode(ProtectionLevel.NORMAL)
        self.destroy()

# Alias
SmartGhostModal = SmartParanoidModal
