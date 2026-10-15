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

def apply_treeview_scroll_patch(tree_widget):
    """Applies ultra-fast custom scroll binding to a ttk.Treeview widget."""
    import sys
    
    def _on_mousewheel(event):
        try:
            if not tree_widget.winfo_exists():
                return
            if sys.platform.startswith("win"):
                if hasattr(event, 'delta') and event.delta:
                    step = -int((event.delta / 120) * 15)
                    if step == 0:
                        step = -1 if event.delta > 0 else 1
                    tree_widget.yview_scroll(step, "units")
                    return "break"
            elif sys.platform == "darwin":
                if hasattr(event, 'delta') and event.delta:
                    step = -int(event.delta * 8)
                    if step == 0:
                        step = -1 if event.delta > 0 else 1
                    tree_widget.yview_scroll(step, "units")
                    return "break"
        except Exception:
            pass

    def _on_linux_scroll_up(event):
        try:
            tree_widget.yview_scroll(-8, "units")
            return "break"
        except Exception:
            pass
            
    def _on_linux_scroll_down(event):
        try:
            tree_widget.yview_scroll(8, "units")
            return "break"
        except Exception:
            pass

    tree_widget.bind("<MouseWheel>", _on_mousewheel)
    tree_widget.bind("<Button-4>", _on_linux_scroll_up)
    tree_widget.bind("<Button-5>", _on_linux_scroll_down)


def get_screen_bounds(window=None):
    """
    Get the actual physical monitor width, height, and offset (left, top) in OS coordinate space.
    Returns (width, height, left, top).
    """
    import sys
    if sys.platform.startswith("win"):
        import ctypes
        from ctypes import wintypes
        try:
            if window is not None and window.winfo_exists():
                try:
                    hwnd = window.winfo_id()
                    if hwnd:
                        monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
                        class RECT(ctypes.Structure):
                            _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG), ('right', wintypes.LONG), ('bottom', wintypes.LONG)]
                        class MONITORINFO(ctypes.Structure):
                            _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', RECT), ('rcWork', RECT), ('dwFlags', wintypes.DWORD)]
                        mi = MONITORINFO()
                        mi.cbSize = ctypes.sizeof(MONITORINFO)
                        if ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(mi)):
                            mw = mi.rcMonitor.right - mi.rcMonitor.left
                            mh = mi.rcMonitor.bottom - mi.rcMonitor.top
                            if mw > 100 and mh > 100:
                                return mw, mh, mi.rcMonitor.left, mi.rcMonitor.top
                except Exception:
                    pass
            user32 = ctypes.windll.user32
            sw = user32.GetSystemMetrics(0)  # SM_CXSCREEN
            sh = user32.GetSystemMetrics(1)  # SM_CYSCREEN
            if sw > 0 and sh > 0:
                return sw, sh, 0, 0
        except Exception:
            pass

    if window is not None:
        try:
            import customtkinter as ctk
            scale = 1.0
            if hasattr(ctk, 'ScalingTracker'):
                scale = ctk.ScalingTracker.get_window_scaling(window)
            w = int(round(window.winfo_screenwidth() * scale))
            h = int(round(window.winfo_screenheight() * scale))
            if w > 100 and h > 100:
                return w, h, 0, 0
        except Exception:
            pass

    return 1920, 1080, 0, 0


def get_screen_dimensions(window=None):
    """
    Get the monitor width and height.
    Returns (width, height).
    """
    w, h, _, _ = get_screen_bounds(window)
    return w, h


def center_window(window, width=None, height=None, parent=None, max_w_ratio=0.92, max_h_ratio=0.90):
    """
    Universally centers any Tk / CustomTkinter window on the primary screen or over a parent window.
    Accounts for DPI scaling in CustomTkinter so windows are pixel-perfect centered across all resolutions.
    """
    try:
        window.update_idletasks()
    except Exception:
        pass

    # Get CustomTkinter window scaling factor
    scale = 1.0
    try:
        import customtkinter as ctk
        if hasattr(ctk, 'ScalingTracker'):
            scale = ctk.ScalingTracker.get_window_scaling(window)
    except Exception:
        scale = 1.0
    if not scale or scale <= 0:
        scale = 1.0

    screen_w, screen_h, screen_left, screen_top = get_screen_bounds(window)

    if width is None:
        try:
            actual_w = window.winfo_width()
            if actual_w <= 1:
                actual_w = window.winfo_reqwidth()
            width = int(round(actual_w / scale))
        except Exception:
            width = 400
            actual_w = int(round(width * scale))
    else:
        actual_w = int(round(width * scale))

    if height is None:
        try:
            actual_h = window.winfo_height()
            if actual_h <= 1:
                actual_h = window.winfo_reqheight()
            height = int(round(actual_h / scale))
        except Exception:
            height = 300
            actual_h = int(round(height * scale))
    else:
        actual_h = int(round(height * scale))

    max_actual_w = max(300, int(screen_w * max_w_ratio))
    max_actual_h = max(200, int(screen_h * max_h_ratio))
    
    if actual_w > max_actual_w:
        actual_w = max_actual_w
        width = int(round(actual_w / scale))
    if actual_h > max_actual_h:
        actual_h = max_actual_h
        height = int(round(actual_h / scale))

    if parent is not None:
        try:
            parent.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            if pw > 100 and ph > 100 and px >= 0 and py >= 0:
                x = px + (pw - actual_w) // 2
                y = py + (ph - actual_h) // 2
                # Clamp within screen bounds
                x = max(screen_left + 10, min(x, screen_left + screen_w - actual_w - 10))
                y = max(screen_top + 10, min(y, screen_top + screen_h - actual_h - 10))
                window.geometry(f"{width}x{height}+{x}+{y}")
                return width, height, x, y
        except Exception:
            pass

    x = screen_left + max(0, (screen_w - actual_w) // 2)
    y = screen_top + max(0, (screen_h - actual_h) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")
    return width, height, x, y


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


# ──────────────────────────────────────────────
#  Bloom Hover Effects — Premium 4K Micro-interactions
# ──────────────────────────────────────────────

_BLOOM_INSTANCES = {}

def add_bloom_hover(widget, glow_color=None, scale_factor=1.02, duration=None):
    """
    Adds a premium bloom/glow hover effect to any CTk widget.
    Creates a subtle scale + glow animation on enter, smooth reverse on leave.
    """
    import customtkinter as ctk
    from netstrip.gui.theme import Colors, Animation
    
    if duration is None:
        duration = Animation.BLOOM
    
    glow_color = glow_color or Colors.ACCENT_PRIMARY
    widget_id = id(widget)
    
    # Store original properties
    if not hasattr(widget, '_bloom_original'):
        widget._bloom_original = {
            'fg_color': widget.cget('fg_color') if 'fg_color' in widget.configure() else None,
            'border_color': widget.cget('border_color') if 'border_color' in widget.configure() else None,
            'border_width': widget.cget('border_width') if 'border_width' in widget.configure() else 0,
        }
    
    original = widget._bloom_original
    anim_state = {'step': 0, 'anim_id': None, 'active': False}
    
    def _animate_bloom(target_scale, target_glow, step=0):
        if not widget.winfo_exists():
            return
        total_steps = 12
        progress = step / total_steps
        # Ease-out cubic
        eased = 1 - (1 - progress) ** 3
        
        # Interpolate scale
        current_scale = 1.0 + (target_scale - 1.0) * eased
        # Interpolate glow intensity
        glow_intensity = target_glow * eased
        
        try:
            if current_scale != 1.0:
                # Apply subtle scale via padding/border
                if hasattr(widget, '_bloom_pad') and widget._bloom_pad:
                    pad_x = int(4 * (current_scale - 1.0) * 10)
                    pad_y = int(2 * (current_scale - 1.0) * 10)
                    widget.configure(padx=pad_x, pady=pad_y)
            
            # Apply glow border
            if glow_intensity > 0.1:
                widget.configure(
                    border_width=max(1, int(2 * glow_intensity)),
                    border_color=glow_color
                )
            elif target_glow == 0:
                widget.configure(
                    border_width=original['border_width'],
                    border_color=original['border_color'] or Colors.BORDER_SUBTLE
                )
        except Exception:
            pass
        
        if step < total_steps:
            anim_state['anim_id'] = widget.after(duration // total_steps, 
                lambda: _animate_bloom(target_scale, target_glow, step + 1))
        else:
            anim_state['active'] = False
    
    def on_enter(event):
        if anim_state['anim_id']:
            widget.after_cancel(anim_state['anim_id'])
        anim_state['active'] = True
        _animate_bloom(scale_factor, 1.0)
    
    def on_leave(event):
        if anim_state['anim_id']:
            widget.after_cancel(anim_state['anim_id'])
        _animate_bloom(1.0, 0.0)
    
    widget.bind("<Enter>", on_enter, add="+")
    widget.bind("<Leave>", on_leave, add="+")
    _BLOOM_INSTANCES[widget_id] = anim_state
    return anim_state


def add_bloom_press(widget, glow_color=None):
    """Adds a press/click bloom feedback."""
    import customtkinter as ctk
    from netstrip.gui.theme import Colors, Animation
    
    glow_color = glow_color or Colors.ACCENT_LIGHT
    original_fg = widget.cget('fg_color') if 'fg_color' in widget.configure() else None
    
    def on_press(event):
        try:
            widget.configure(fg_color=glow_color)
        except: pass
    
    def on_release(event):
        try:
            widget.after(Animation.FAST, lambda: widget.configure(fg_color=original_fg))
        except: pass
    
    widget.bind("<ButtonPress-1>", on_press, add="+")
    widget.bind("<ButtonRelease-1>", on_release, add="+")


def add_card_bloom(card_widget, glow_color=None):
    """
    Adds premium bloom effect to card/frame widgets.
    Includes subtle lift, glow border, and inner shadow simulation.
    """
    from netstrip.gui.theme import Colors, Animation
    
    glow_color = glow_color or Colors.ACCENT_PRIMARY
    original = {
        'fg_color': card_widget.cget('fg_color'),
        'border_color': card_widget.cget('border_color') if 'border_color' in card_widget.configure() else Colors.BORDER_SUBTLE,
        'border_width': card_widget.cget('border_width') if 'border_width' in card_widget.configure() else 1,
    }
    
    anim_state = {'step': 0, 'anim_id': None}
    
    def _animate(progress):
        if not card_widget.winfo_exists():
            return
        # Ease-out quart
        eased = 1 - (1 - progress) ** 4
        
        try:
            # Glow border
            if progress > 0:
                card_widget.configure(
                    border_width=max(1, int(3 * eased)),
                    border_color=glow_color
                )
            else:
                card_widget.configure(
                    border_width=original['border_width'],
                    border_color=original['border_color']
                )
        except: pass
        
        if progress < 1.0:
            anim_state['anim_id'] = card_widget.after(Animation.BLOOM // 15,
                lambda: _animate(min(1.0, progress + 0.07)))
    
    def on_enter(event):
        if anim_state['anim_id']:
            card_widget.after_cancel(anim_state['anim_id'])
        _animate(0.0)
    
    def on_leave(event):
        if anim_state['anim_id']:
            card_widget.after_cancel(anim_state['anim_id'])
        # Reverse animation
        def _reverse(progress=1.0):
            if not card_widget.winfo_exists():
                return
            eased = 1 - (1 - progress) ** 4
            try:
                if progress > 0:
                    card_widget.configure(
                        border_width=max(1, int(3 * eased)),
                        border_color=glow_color
                    )
                else:
                    card_widget.configure(
                        border_width=original['border_width'],
                        border_color=original['border_color']
                    )
            except: pass
            if progress > 0:
                card_widget.after(Animation.BLOOM // 15, lambda: _reverse(progress - 0.07))
        _reverse(1.0)
    
    card_widget.bind("<Enter>", on_enter, add="+")
    card_widget.bind("<Leave>", on_leave, add="+")
    return anim_state


