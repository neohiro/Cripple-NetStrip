import customtkinter as ctk
from typing import Callable, Dict
import logging

logger = logging.getLogger(__name__)

class CTkAnomalyAlert(ctk.CTkToplevel):
    """
    A custom, aggressive pop-up window that alerts the user to a Kernel Anomaly.
    Pauses the flow and forces the user to make a security decision.
    """
    def __init__(self, master, engine, anomaly_data: Dict, on_decision: Callable[[str], None], **kwargs):
        super().__init__(master, **kwargs)
        
        self.engine = engine
        self.anomaly_data = anomaly_data
        self.on_decision = on_decision
        
        self.title("CRITICAL SECURITY ALERT")
        self.geometry("500x350")
        self.resizable(False, False)
        self.attributes('-topmost', True)
        self.grab_set() # Force focus
        
        # UI Setup
        self._build_ui()
        
    def _build_ui(self):
        from netstrip.gui.theme import Colors, Fonts
        
        # Outer container with a thin info/danger border
        frame = ctk.CTkFrame(self, fg_color=Colors.BG_DARKEST, corner_radius=0, border_width=1, border_color=Colors.DANGER)
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=24)
        
        lbl_title = ctk.CTkLabel(inner, text="KERNEL INTRUSION DETECTED", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, "bold"), text_color=Colors.DANGER)
        lbl_title.pack(anchor="w", pady=(0, 10))
        
        ctk.CTkFrame(inner, fg_color=Colors.BORDER_SUBTLE, height=1).pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            inner, text="CRITICAL SECURITY EVENT INTERCEPTED.\n\n> Anomaly attempting OS layer bypass.\n> Action required immediately.",
            wraplength=450, justify="left", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE), text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(
            inner, text=f"Threat Details:\n{self.anomaly_data.get('message', 'Unknown Threat')}",
            wraplength=450, justify="left", font=("Consolas", 12), text_color=Colors.WARNING
        ).pack(anchor="w", pady=(0, 20))
        
        # Buttons
        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom")
        
        btn_top_row = ctk.CTkFrame(btn_frame, fg_color="transparent")
        btn_top_row.pack(fill="x", pady=(0, 10))
        
        ctk.CTkButton(
            btn_top_row, text=f"WHITELIST '{self.anomaly_data.get('name', 'unknown')}'",
            fg_color="transparent", border_width=1, border_color=Colors.BORDER_SUBTLE, text_color=Colors.TEXT_TERTIARY, hover_color=Colors.BG_PANEL, corner_radius=0,
            command=lambda: self._make_decision('whitelist')
        ).pack(side="left", expand=True, padx=(0, 5))
        
        ctk.CTkButton(
            btn_top_row, text="DISABLE SCANNER",
            fg_color="transparent", border_width=1, border_color=Colors.BORDER_SUBTLE, text_color=Colors.TEXT_TERTIARY, hover_color=Colors.BG_PANEL, corner_radius=0,
            command=lambda: self._make_decision('disable_scanner')
        ).pack(side="right", expand=True, padx=(5, 0))
        
        ctk.CTkButton(
            btn_frame, text="NEUTRALIZE THREAT",
            fg_color=Colors.DANGER, hover_color="#991b1b", text_color="#ffffff", corner_radius=0,
            command=lambda: self._make_decision('neutralize')
        ).pack(fill="x")
        
    def _make_decision(self, decision: str):
        self.grab_release()
        self.destroy()
        if self.on_decision:
            self.on_decision(decision)
