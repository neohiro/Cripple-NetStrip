"""
Notification Popup for NetStrip
Toast-style popup for connection decisions.
"""

import customtkinter as ctk
from netstrip.gui.theme import Colors, Fonts, Spacing

class NotificationPopup(ctk.CTkToplevel):
    def __init__(self, master, conn_data, on_resolve, **kwargs):
        super().__init__(master, **kwargs)
        self.conn_data = conn_data
        self.on_resolve = on_resolve
        
        self.title("Cripple - Unknown Connection")
        self.geometry("400x160")
        self.resizable(False, False)
        # self.overrideredirect(True) # Remove window decorations for true toast style
        self.attributes("-topmost", True)
        
        # Position at bottom right (simplified logic)
        # screen_width = self.winfo_screenwidth()
        # screen_height = self.winfo_screenheight()
        # self.geometry(f"+{screen_width - 420}+{screen_height - 200}")
        
        self.configure(fg_color=Colors.BG_ELEVATED)
        
        # Process name
        ctk.CTkLabel(self, text=conn_data.get('process_name', 'Unknown App'), font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, Fonts.WEIGHT_BOLD)).pack(pady=(Spacing.MD, 0))
        
        # Domain/IP
        target = conn_data.get('domain') or conn_data.get('ip')
        ctk.CTkLabel(self, text=f"Wants to connect to: {target}", text_color=Colors.TEXT_SECONDARY).pack(pady=Spacing.XS)
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=Spacing.LG, pady=Spacing.MD)
        
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        allow_btn = ctk.CTkButton(btn_frame, text="Allow Always", fg_color=Colors.SUCCESS_DIM, hover_color=Colors.SUCCESS, command=lambda: self._resolve('allow'))
        allow_btn.grid(row=0, column=0, padx=Spacing.SM)
        
        block_btn = ctk.CTkButton(btn_frame, text="Block Always", fg_color=Colors.DANGER_DIM, hover_color=Colors.DANGER, command=lambda: self._resolve('block'))
        block_btn.grid(row=0, column=1, padx=Spacing.SM)
        
        # Auto-timeout logic can be added here
        
    def _resolve(self, action):
        self.on_resolve(self.conn_data, action)
        self.destroy()
