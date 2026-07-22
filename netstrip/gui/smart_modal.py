"""
Smart Modal for Cripple GUI
Displays a critical alert when Smart Paranoid Mode is triggered.
"""

import customtkinter as ctk
from netstrip.gui.theme import Colors, Fonts, Spacing, Icons, CTK_BUTTON_DANGER_STYLE, CTK_BUTTON_SECONDARY_STYLE

class SmartParanoidModal(ctk.CTkToplevel):
    def __init__(self, master, engine, conn_data, **kwargs):
        super().__init__(master, **kwargs)
        self.engine = engine
        self.conn_data = conn_data
        
        self.title("CRITICAL ALERT - Smart Shield Triggered")
        self.geometry("500x320")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color=Colors.BG_DARKEST)
        
        # Center the modal
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - (500 // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (320 // 2)
        self.geometry(f"+{x}+{y}")

        self._build_ui()
        
    def _build_ui(self):
        # Header Area
        header = ctk.CTkFrame(self, fg_color=Colors.DANGER_DIM, corner_radius=0, height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header, text=f"{Icons.MALWARE} SMART SHIELD ACTIVATED",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, Fonts.WEIGHT_BOLD),
            text_color=Colors.DANGER
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Content Area
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.LG)
        
        target = self.conn_data.get('domain') or self.conn_data.get('ip', 'Unknown')
        process = self.conn_data.get('process_name', 'Unknown')
        
        ctk.CTkLabel(
            content, 
            text="Cripple intercepted a critical security event and automatically locked down the machine into Paranoid Mode.",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_PRIMARY,
            wraplength=420,
            justify="center"
        ).pack(pady=(0, Spacing.LG))
        
        # Details Box
        details = ctk.CTkFrame(content, fg_color=Colors.BG_PANEL, corner_radius=Spacing.RADIUS_SM)
        details.pack(fill="x", pady=(0, Spacing.LG))
        
        ctk.CTkLabel(details, text="Process:", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=Spacing.MD, pady=(Spacing.SM, 0))
        ctk.CTkLabel(details, text=process, font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE), text_color=Colors.TEXT_PRIMARY).grid(row=0, column=1, sticky="w", padx=Spacing.SM, pady=(Spacing.SM, 0))
        
        ctk.CTkLabel(details, text="Target:", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD), text_color=Colors.TEXT_SECONDARY).grid(row=1, column=0, sticky="w", padx=Spacing.MD, pady=(Spacing.XS, Spacing.SM))
        ctk.CTkLabel(details, text=target, font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE), text_color=Colors.DANGER).grid(row=1, column=1, sticky="w", padx=Spacing.SM, pady=(Spacing.XS, Spacing.SM))
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        ctk.CTkButton(
            btn_frame, text="Acknowledge & Disable Smart Shield",
            command=self._disable_smart_shield,
            **CTK_BUTTON_SECONDARY_STYLE
        ).pack(side="left", expand=True, padx=(0, Spacing.SM))
        
        ctk.CTkButton(
            btn_frame, text="Keep Device Locked Down",
            command=self.destroy,
            **CTK_BUTTON_DANGER_STYLE
        ).pack(side="right", expand=True, padx=(Spacing.SM, 0))

    def _disable_smart_shield(self):
        from netstrip.core.modes import ProtectionLevel
        self.engine.db.set_setting("smart_paranoid_mode", "false")
        
        # Revert mode to Normal
        self.engine.set_mode(ProtectionLevel.NORMAL)
        self.destroy()
