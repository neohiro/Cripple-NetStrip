import customtkinter as ctk
from netstrip.gui.theme import Fonts, Colors

class ManualKillswitchModal(ctk.CTkToplevel):
    def __init__(self, parent, engine, callback):
        super().__init__(parent)
        self.engine = engine
        self.callback = callback
        
        self.title("WARNING: Master Killswitch")
        self.geometry("450x250")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        
        # Center modal
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (450 // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (250 // 2)
        self.geometry(f"+{x}+{y}")
        
        self._build_ui()
        self.grab_set()

    def _build_ui(self):
        frame = ctk.CTkFrame(self, fg_color=Colors.BG_ELEVATED, corner_radius=0)
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        lbl_title = ctk.CTkLabel(frame, text="⚠️ INITIATING MASTER KILLSWITCH", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, Fonts.WEIGHT_BOLD), text_color=Colors.DANGER)
        lbl_title.pack(pady=(20, 10))
        
        lbl_desc = ctk.CTkLabel(frame, text=(
            "You are about to sever all OS network connections.\n"
            "This will instantly drop all internet traffic.\n\n"
            "It is highly advised to also physically unplug your ethernet\n"
            "cable or disable your Wi-Fi adapter hardware."
        ), font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE), justify="center")
        lbl_desc.pack(pady=(0, 20))
        
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)
        
        btn_cancel = ctk.CTkButton(btn_frame, text="Cancel", fg_color=Colors.BG_INPUT, hover_color=Colors.BORDER_HOVER, text_color=Colors.TEXT_PRIMARY, command=self.on_cancel)
        btn_cancel.pack(side="left", expand=True, padx=5)
        
        btn_confirm = ctk.CTkButton(btn_frame, text="ENGAGE KILLSWITCH", fg_color=Colors.DANGER, hover_color="#991b1b", text_color="white", command=self.on_confirm)
        btn_confirm.pack(side="right", expand=True, padx=5)

    def on_cancel(self):
        self.callback(False)
        self.destroy()

    def on_confirm(self):
        self.callback(True)
        self.destroy()

class CriticalRecoveryModal(ctk.CTkToplevel):
    def __init__(self, parent, engine, message):
        super().__init__(parent)
        self.engine = engine
        
        self.title("CRITICAL: Network Intrusion Detected")
        self.geometry("500x250")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (500 // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (250 // 2)
        self.geometry(f"+{x}+{y}")
        
        self.message = message
        self._build_ui()
        self.grab_set()

    def _build_ui(self):
        frame = ctk.CTkFrame(self, fg_color=Colors.BG_ELEVATED, corner_radius=0)
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        lbl_title = ctk.CTkLabel(frame, text="🚨 AUTO-KILLSWITCH ENGAGED", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, Fonts.WEIGHT_BOLD), text_color=Colors.DANGER)
        lbl_title.pack(pady=(20, 10))
        
        lbl_desc = ctk.CTkLabel(frame, text=(
            "Cripper detected a severe network anomaly while in Paranoid Mode:\n\n"
            f"{self.message}\n\n"
            "All network traffic has been blocked to protect your system."
        ), font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE), justify="center")
        lbl_desc.pack(pady=(0, 20), padx=20)
        
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)
        
        btn_keep = ctk.CTkButton(btn_frame, text="Keep Engaged", fg_color=Colors.BG_INPUT, hover_color=Colors.BORDER_HOVER, text_color=Colors.TEXT_PRIMARY, command=self.on_keep)
        btn_keep.pack(side="left", expand=True, padx=5)
        
        btn_restore = ctk.CTkButton(btn_frame, text="Acknowledge & Restore Network", fg_color=Colors.WARNING, hover_color="#b45309", text_color="white", command=self.on_restore)
        btn_restore.pack(side="right", expand=True, padx=5)

    def on_keep(self):
        self.destroy()

    def on_restore(self):
        self.engine.set_killswitch(False)
        
        # If LAN shield was originally off, we should restore it to off if the user wanted it that way.
        # But for safety, we'll leave LAN shield on unless they manually disable it in settings.
        
        # Sync the UI switch if the parent app has the home_view loaded
        if hasattr(self.master, 'home_view'):
            try:
                self.master.home_view.sync_killswitch_state()
            except Exception:
                pass
                
        self.destroy()
