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
    Ensures smooth, fast scrolling on a CTkScrollableFrame using the centralized scroll engine.
    """
    try:
        if hasattr(scrollable_frame, '_set_scroll_increments'):
            scrollable_frame._set_scroll_increments()
    except Exception:
        pass


def get_screen_dimensions(window=None):
    """
    Get the actual primary screen width and height reliably across platforms and DPI scales.
    """
    screen_w, screen_h = 1920, 1080
    try:
        import sys
        if sys.platform.startswith("win"):
            import ctypes
            try:
                user32 = ctypes.windll.user32
                sw = user32.GetSystemMetrics(0) # SM_CXSCREEN
                sh = user32.GetSystemMetrics(1) # SM_CYSCREEN
                if sw > 0 and sh > 0:
                    screen_w, screen_h = sw, sh
            except Exception:
                pass
    except Exception:
        pass
        
    if window:
        try:
            w = window.winfo_screenwidth()
            h = window.winfo_screenheight()
            if w > 100 and h > 100:
                screen_w, screen_h = w, h
        except Exception:
            pass
            
    return screen_w, screen_h


def center_window(window, width=None, height=None, parent=None, max_w_ratio=0.92, max_h_ratio=0.90):
    """
    Universally centers any Tk / CustomTkinter window on the primary screen or over a parent window.
    Ensures dimensions fit comfortably on any display resolution (720p, 1080p, 1440p, 4K, laptops, etc.)
    and prevents off-screen placement.
    """
    try:
        window.update_idletasks()
    except Exception:
        pass

    screen_w, screen_h = get_screen_dimensions(window)

    if width is None:
        try:
            width = window.winfo_width()
            if width <= 1:
                width = window.winfo_reqwidth()
        except Exception:
            width = 400
    if height is None:
        try:
            height = window.winfo_height()
            if height <= 1:
                height = window.winfo_reqheight()
        except Exception:
            height = 300

    max_w = max(300, int(screen_w * max_w_ratio))
    max_h = max(200, int(screen_h * max_h_ratio))
    
    final_w = min(int(width), max_w)
    final_h = min(int(height), max_h)

    if parent is not None:
        try:
            parent.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            if pw > 100 and ph > 100 and px >= 0 and py >= 0:
                x = px + (pw - final_w) // 2
                y = py + (ph - final_h) // 2
                # Clamp within screen bounds
                x = max(10, min(x, screen_w - final_w - 10))
                y = max(10, min(y, screen_h - final_h - 10))
                window.geometry(f"{final_w}x{final_h}+{x}+{y}")
                return final_w, final_h, x, y
        except Exception:
            pass

    x = max(0, (screen_w - final_w) // 2)
    y = max(0, (screen_h - final_h) // 2)
    window.geometry(f"{final_w}x{final_h}+{x}+{y}")
    return final_w, final_h, x, y


_cached_logo_images = {}

def get_app_logo_image(size=(24, 24)):
    """
    Returns a CTkImage of the Cripple NetStrip logo at the specified size.
    """
    import os
    import sys
    from PIL import Image
    import customtkinter as ctk
    
    if size in _cached_logo_images:
        return _cached_logo_images[size]
        
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        logo_path = os.path.join(base_path, 'assets', 'cripple_logo.png')
        if not os.path.exists(logo_path):
            logo_path = os.path.join(base_path, 'assets', 'logo.ico')
            
        if os.path.exists(logo_path):
            pil_img = Image.open(logo_path)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
            _cached_logo_images[size] = ctk_img
            return ctk_img
    except Exception as e:
        logger.debug(f"Failed to load logo image: {e}")
    return None


def apply_window_icon(window):
    """
    Applies the Cripple NetStrip logo icon to any window or CTkToplevel modal.
    Sets Tk iconbitmap and native Windows OS window icons (small & big) in the title bar.
    """
    try:
        import os
        import sys
        
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        icon_path = os.path.join(base_path, 'assets', 'logo.ico')
        if os.path.exists(icon_path):
            try:
                window.iconbitmap(icon_path)
            except Exception:
                pass
            
            if sys.platform.startswith("win"):
                def _set_win_icon():
                    try:
                        import ctypes
                        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
                        if not hwnd:
                            hwnd = window.winfo_id()
                        hicon = ctypes.windll.user32.LoadImageW(0, icon_path, 1, 0, 0, 0x00000010)
                        if hicon and hwnd:
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon) # ICON_SMALL
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon) # ICON_BIG
                    except Exception:
                        pass
                
                # Execute immediately and also schedule after 10ms in case window wasn't fully mapped
                _set_win_icon()
                if hasattr(window, 'after'):
                    try:
                        window.after(10, _set_win_icon)
                    except Exception:
                        pass
    except Exception as e:
        logger.debug(f"Failed to apply window icon: {e}")


