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
        # Header
        header = ctk.CTkFrame(self, fg_color="#8B0000", corner_radius=0)
        header.pack(fill="x", pady=0)
        
        ctk.CTkLabel(
            header, text="⚠️ KERNEL INTRUSION DETECTED",
            font=("Arial", 18, "bold"), text_color="white"
        ).pack(pady=10)
        
        # Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            body, text="NetStrip has detected a critical anomaly attempting to bypass the firewall at the OS layer.",
            wraplength=450, justify="left", font=("Arial", 14)
        ).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(
            body, text=f"Threat Details:\n{self.anomaly_data.get('message', 'Unknown Threat')}",
            wraplength=450, justify="left", font=("Consolas", 12), text_color="#FF4500"
        ).pack(anchor="w", pady=(0, 20))
        
        # Buttons
        btn_frame = ctk.CTkFrame(body, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=10)
        
        ctk.CTkButton(
            btn_frame, text="NEUTRALIZE THREAT (Recommended)",
            fg_color="#8B0000", hover_color="#A52A2A", font=("Arial", 12, "bold"),
            command=lambda: self._make_decision('neutralize')
        ).pack(fill="x", pady=5)
        
        ctk.CTkButton(
            btn_frame, text=f"Whitelist Anomaly '{self.anomaly_data.get('name', 'unknown')}'",
            fg_color="transparent", border_width=1, text_color="gray", hover_color="#333333",
            command=lambda: self._make_decision('whitelist')
        ).pack(fill="x", pady=5)
        
        ctk.CTkButton(
            btn_frame, text="Disable Kernel Scanner Globally",
            fg_color="transparent", text_color="gray", hover_color="#333333",
            command=lambda: self._make_decision('disable_scanner')
        ).pack(fill="x")
        
    def _make_decision(self, decision: str):
        self.grab_release()
        self.destroy()
        if self.on_decision:
            self.on_decision(decision)
