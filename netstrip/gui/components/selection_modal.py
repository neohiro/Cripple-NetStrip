"""
Touch-friendly Selection Modal for Mobile-first UX.
Replaces standard dropdown menus with a large, centered modal overlay
for selecting options.
"""

import customtkinter as ctk
from netstrip.gui.theme import Colors, Fonts, Spacing

class SelectionModal(ctk.CTkToplevel):
    def __init__(self, master, title: str, options: list, current_value: str, callback=None, **kwargs):
        """
        :param master: Parent window
        :param title: Title of the modal
        :param options: List of string options
        :param current_value: The currently selected option
        :param callback: Function to call with the selected option: callback(selected_string)
        """
        super().__init__(master, **kwargs)
        self.callback = callback
        
        self.title("")
        self.attributes("-topmost", True)
        self.overrideredirect(True) # Remove OS window decorations
        self.configure(fg_color=Colors.BG_DARK)
        
        # Determine size based on options (max 400px height)
        height = min(400, 60 + len(options) * 50 + 20)
        width = 300
        
        # Center the modal over the parent window
        self.update_idletasks()
        try:
            x = master.winfo_rootx() + (master.winfo_width() // 2) - (width // 2)
            y = master.winfo_rooty() + (master.winfo_height() // 2) - (height // 2)
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            self.geometry(f"{width}x{height}")
            
        self._build_ui(title, options, current_value)
        
        # Grab focus
        self.focus_force()
        self.grab_set()
        
        # Close on outside click
        self.bind("<FocusOut>", self._on_focus_out)
        
    def _build_ui(self, title, options, current_value):
        # Outer frame with border
        main_frame = ctk.CTkFrame(self, fg_color=Colors.BG_PANEL, corner_radius=14, border_width=1, border_color=Colors.BORDER_SUBTLE)
        main_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Header
        header = ctk.CTkFrame(main_frame, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.MD, pady=Spacing.MD)
        
        ctk.CTkLabel(header, text=title, font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, "bold"), text_color=Colors.TEXT_PRIMARY).pack(side="left")
        
        btn_close = ctk.CTkButton(header, text="✕", width=28, height=28, fg_color="transparent", hover_color=Colors.BG_INPUT, text_color=Colors.TEXT_SECONDARY, command=self.destroy)
        btn_close.pack(side="right")
        
        # Scrollable area for options if there are many
        scroll = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=Spacing.SM, pady=(0, Spacing.SM))
        
        for opt in options:
            is_selected = (opt == current_value)
            
            btn_fg = Colors.BG_INPUT if is_selected else "transparent"
            text_color = Colors.ACCENT_PRIMARY if is_selected else Colors.TEXT_PRIMARY
            hover = Colors.BG_ELEVATED
            
            btn = ctk.CTkButton(
                scroll,
                text=opt,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
                fg_color=btn_fg,
                text_color=text_color,
                hover_color=hover,
                anchor="w",
                height=40,
                corner_radius=8,
                command=lambda o=opt: self._select_option(o)
            )
            btn.pack(fill="x", pady=2)

    def _select_option(self, option):
        if self.callback:
            self.callback(option)
        self.destroy()
        
    def _on_focus_out(self, event):
        # Destroy if lost focus to main app
        if event.widget == self:
            self.destroy()

class TouchOptionMenu(ctk.CTkButton):
    """
    A drop-in replacement for CTkOptionMenu that looks like a button
    but opens a SelectionModal on click.
    """
    def __init__(self, master, title="Select Option", values=None, variable=None, command=None, **kwargs):
        self.modal_title = title
        self.values = values or []
        self.variable = variable
        self.command_callback = command
        
        # Initialize as a button
        super().__init__(
            master, 
            text=self._get_current_value(),
            command=self._open_modal,
            **kwargs
        )
        
    def _get_current_value(self):
        if self.variable:
            return self.variable.get()
        return self.values[0] if self.values else "Select..."
        
    def _open_modal(self):
        SelectionModal(
            self.winfo_toplevel(),
            title=self.modal_title,
            options=self.values,
            current_value=self._get_current_value(),
            callback=self._on_select
        )
        
    def _on_select(self, selected):
        if self.variable:
            self.variable.set(selected)
        self.configure(text=selected)
        if self.command_callback:
            self.command_callback(selected)
