"""
GUI Utilities for NetStrip
"""

import functools
import logging
import traceback
from netstrip.gui.theme import Colors

logger = logging.getLogger(__name__)

def safe_loop(delay_ms=None):
    """
    Decorator for Tkinter loop callbacks.
    Catches any unhandled exceptions to prevent the loop from silently crashing and dying forever.
    If delay_ms is provided, it attempts to reschedule the loop even on failure.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if hasattr(self, '_destroyed') and self._destroyed:
                return
                
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in UI loop '{func.__name__}': {e}")
                logger.debug(traceback.format_exc())
                
                # Try to reschedule if we have a delay and we aren't destroyed
                if delay_ms and hasattr(self, 'after') and not getattr(self, '_destroyed', False):
                    try:
                        self.after(delay_ms, getattr(self, func.__name__))
                    except Exception as reschedule_err:
                        logger.error(f"Failed to reschedule UI loop '{func.__name__}': {reschedule_err}")
        return wrapper
    return decorator

def is_ip(text: str) -> bool:
    if not text: return False
    text = str(text)
    # Basic IPv4
    if re.match(r'^(?:\d{1,3}\.){3}\d{1,3}$', text): return True
    # Basic IPv6
    if re.match(r'^(?:[a-fA-F0-9]{1,4}:){1,7}[a-fA-F0-9]{1,4}$', text): return True
    return False

def bind_copy_tooltip(widget, text_to_copy, message=None):
    """Binds a click event to copy text and show a floating tooltip."""
    import customtkinter as ctk
    
    if message is None:
        message = "IP copied!" if is_ip(text_to_copy) else "Link copied!"
        
    widget.configure(cursor="hand2")
    
    def on_click(event):
        widget.clipboard_clear()
        widget.clipboard_append(str(text_to_copy))
        
        # Debounce: Destroy existing tooltip if one exists for this widget
        if hasattr(widget, '_active_tooltip') and widget._active_tooltip.winfo_exists():
            widget._active_tooltip.destroy()
            
        # Create a tiny floating toplevel without window decorations
        tip = ctk.CTkToplevel()
        widget._active_tooltip = tip
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        # Some OS need transparent color key to remove background, but we'll just style it
        tip.configure(fg_color=Colors.SUCCESS_DIM if hasattr(Colors, 'SUCCESS_DIM') else "#166534")
        
        x = event.x_root + 10
        y = event.y_root + 10
        tip.geometry(f"+{x}+{y}")
        
        lbl = ctk.CTkLabel(
            tip, text=message,
            text_color="white",
            font=("Inter", 11, "bold"),
            padx=8, pady=4
        )
        lbl.pack()
        
        # Destroy after 1.5s
        tip.after(1500, tip.destroy)
        
    widget.bind("<Button-1>", on_click)

import re

def mask_ip_string(text: str) -> str:
    """Masks IPv4 and IPv6 addresses in a string for Privacy Stream Mode."""
    if not text:
        return text
        
    text = str(text)
    # Mask IPv4
    text = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '<HIDDEN_IP>', text)
    # Mask common IPv6 patterns
    text = re.sub(r'\b(?:[a-fA-F0-9]{1,4}:){1,7}[a-fA-F0-9]{1,4}\b', '<HIDDEN_IP>', text)
    return text
