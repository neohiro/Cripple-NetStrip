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
        # Outer container with a thin danger border for futuristic accent
        frame = ctk.CTkFrame(self, fg_color=Colors.BG_DARKEST, corner_radius=0, border_width=1, border_color=Colors.DANGER)
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=24)
        
        lbl_title = ctk.CTkLabel(inner, text="SYSTEM LOCKDOWN INITIATED", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, "bold"), text_color=Colors.DANGER)
        lbl_title.pack(anchor="w", pady=(0, 10))
        
        # Subtle separator
        ctk.CTkFrame(inner, fg_color=Colors.BORDER_SUBTLE, height=1).pack(fill="x", pady=(0, 20))
        
        lbl_desc = ctk.CTkLabel(inner, text=(
            "SEVERING ALL OS NETWORK CONNECTIONS.\n\n"
            "> Dropping all internet traffic...\n"
            "> Blocking all active ports...\n\n"
            "Hardware intervention (unplugging ethernet) is recommended."
        ), font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE), justify="left", text_color=Colors.TEXT_SECONDARY)
        lbl_desc.pack(anchor="w", pady=(0, 20))
        
        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        btn_cancel = ctk.CTkButton(
            btn_frame, text="ABORT", fg_color="transparent", border_width=1, border_color=Colors.BORDER_SUBTLE, 
            hover_color=Colors.BG_PANEL, text_color=Colors.TEXT_TERTIARY, corner_radius=0, command=self.on_cancel
        )
        btn_cancel.pack(side="left", expand=True, padx=(0, 5))
        
        btn_confirm = ctk.CTkButton(
            btn_frame, text="ENGAGE", fg_color=Colors.DANGER, 
            hover_color="#991b1b", text_color="#ffffff", corner_radius=0, command=self.on_confirm
        )
        btn_confirm.pack(side="right", expand=True, padx=(5, 0))

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
        # Outer container with a thin info/danger border
        frame = ctk.CTkFrame(self, fg_color=Colors.BG_DARKEST, corner_radius=0, border_width=1, border_color=Colors.WARNING)
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=24)
        
        lbl_title = ctk.CTkLabel(inner, text="AUTO-KILLSWITCH ENGAGED", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, "bold"), text_color=Colors.WARNING)
        lbl_title.pack(anchor="w", pady=(0, 10))
        
        ctk.CTkFrame(inner, fg_color=Colors.BORDER_SUBTLE, height=1).pack(fill="x", pady=(0, 20))
        
        lbl_msg = ctk.CTkLabel(inner, text=f"> Watchdog Event:\n{self.message}", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE), justify="left", text_color=Colors.TEXT_SECONDARY)
        lbl_msg.pack(anchor="w", pady=(0, 20))
        
        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        btn_keep = ctk.CTkButton(
            btn_frame, text="MAINTAIN LOCKDOWN", fg_color="transparent", border_width=1, border_color=Colors.BORDER_SUBTLE,
            hover_color=Colors.BG_PANEL, text_color=Colors.TEXT_TERTIARY, corner_radius=0, command=self.on_keep
        )
        btn_keep.pack(side="left", expand=True, padx=(0, 5))
        
        btn_restore = ctk.CTkButton(
            btn_frame, text="ACKNOWLEDGE", fg_color=Colors.WARNING, 
            hover_color="#b45309", text_color="white", corner_radius=0, command=self.on_restore
        )
        btn_restore.pack(side="right", expand=True, padx=(5, 0))

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
