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

class ClipboardTooltipManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.tip = None
        self.lbl = None
        self.hide_id = None

    def show(self, widget, message, x, y):
        import customtkinter as ctk
        if self.tip is None or not self.tip.winfo_exists():
            self.tip = ctk.CTkToplevel()
            self.tip.overrideredirect(True)
            self.tip.attributes("-topmost", True)
            self.tip.configure(fg_color=Colors.SUCCESS_DIM if hasattr(Colors, 'SUCCESS_DIM') else "#166534")
            
            self.lbl = ctk.CTkLabel(
                self.tip, text=message,
                text_color="white",
                font=("Inter", 11, "bold"),
                padx=8, pady=4
            )
            self.lbl.pack()
        else:
            self.lbl.configure(text=message)
            
        self.tip.geometry(f"+{x}+{y}")
        self.tip.deiconify()

        if self.hide_id:
            self.tip.after_cancel(self.hide_id)
        self.hide_id = self.tip.after(1500, self.tip.withdraw)

def bind_copy_tooltip(widget, text_to_copy, message=None):
    """Binds a click event to copy text and show a floating tooltip."""
    if message is None:
        message = "IP copied!" if is_ip(text_to_copy) else "Link copied!"
        
    widget.configure(cursor="hand2")
    
    def on_click(event):
        widget.clipboard_clear()
        widget.clipboard_append(str(text_to_copy))
        
        x = event.x_root + 10
        y = event.y_root + 10
        ClipboardTooltipManager.get_instance().show(widget, message, x, y)
        
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

def enable_smooth_scrolling(scrollable_frame):
    """
    Enables instant, smooth mousewheel scrolling on a CTkScrollableFrame without
    startup delay or laggy boundary checks.
    """
    def _on_mousewheel(event):
        try:
            if not scrollable_frame.winfo_exists() or not scrollable_frame.winfo_ismapped():
                return
            canvas = getattr(scrollable_frame, '_parent_canvas', None)
            if canvas:
                if hasattr(event, 'delta') and event.delta:
                    step = int(-1 * (event.delta / 40))
                    if step == 0:
                        step = -1 if event.delta > 0 else 1
                    canvas.yview_scroll(step, "units")
                elif getattr(event, 'num', None) == 4:
                    canvas.yview_scroll(-2, "units")
                elif getattr(event, 'num', None) == 5:
                    canvas.yview_scroll(2, "units")
        except Exception:
            pass

    def _bind_wheel(event=None):
        try:
            scrollable_frame.bind_all("<MouseWheel>", _on_mousewheel, add="+")
            scrollable_frame.bind_all("<Button-4>", _on_mousewheel, add="+")
            scrollable_frame.bind_all("<Button-5>", _on_mousewheel, add="+")
        except Exception:
            pass

    def _unbind_wheel(event=None):
        try:
            scrollable_frame.unbind_all("<MouseWheel>")
            scrollable_frame.unbind_all("<Button-4>")
            scrollable_frame.unbind_all("<Button-5>")
        except Exception:
            pass

    scrollable_frame.bind("<Enter>", _bind_wheel, add="+")
    scrollable_frame.bind("<Leave>", _unbind_wheel, add="+")
    canvas = getattr(scrollable_frame, '_parent_canvas', None)
    if canvas:
        canvas.bind("<Enter>", _bind_wheel, add="+")
        canvas.bind("<Leave>", _unbind_wheel, add="+")
