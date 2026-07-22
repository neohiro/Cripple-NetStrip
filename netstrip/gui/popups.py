import customtkinter as ctk
from netstrip.gui.theme import Colors, Fonts, Spacing

def check_killswitch_override(engine, parent, proceed_callback, cancel_callback=None):
    """
    Checks if the killswitch is active. If so, spawns a popup warning the user 
    that their action contradicts the killswitch and asks if they want to disable it.
    If killswitch is NOT active, it immediately fires the proceed_callback.
    """
    if not getattr(engine, 'killswitch_active', False):
        proceed_callback()
        return

    dialog = ctk.CTkToplevel(parent)
    dialog.title("Killswitch Active")
    dialog.geometry("400x250")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.attributes("-topmost", True)
    dialog.configure(fg_color=Colors.BG_DARKEST)

    # Center dialog
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 200
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 125
    dialog.geometry(f"+{x}+{y}")

    content = ctk.CTkFrame(dialog, fg_color=Colors.BG_PANEL, corner_radius=Spacing.RADIUS_MD)
    content.pack(fill="both", expand=True, padx=Spacing.LG, pady=Spacing.LG)

    ctk.CTkLabel(
        content, text="⚠️ Killswitch is Active",
        font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, Fonts.WEIGHT_BOLD),
        text_color=Colors.DANGER
    ).pack(pady=(Spacing.LG, Spacing.SM))

    ctk.CTkLabel(
        content, 
        text="The global killswitch blocks ALL traffic, overriding whitelists and settings. You must disable the killswitch to perform this action.",
        font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
        text_color=Colors.TEXT_SECONDARY,
        wraplength=320, justify="center"
    ).pack(pady=(0, Spacing.LG))

    def on_disable():
        engine.set_killswitch(False)
        dialog.destroy()
        proceed_callback()

    def on_cancel():
        dialog.destroy()
        if cancel_callback:
            cancel_callback()

    btn_row = ctk.CTkFrame(content, fg_color="transparent")
    btn_row.pack(fill="x", pady=Spacing.SM)

    ctk.CTkButton(
        btn_row, text="Cancel", width=100, height=36,
        fg_color=Colors.BG_INPUT, text_color=Colors.TEXT_PRIMARY,
        hover_color=Colors.BG_DARK,
        command=on_cancel
    ).pack(side="left", padx=Spacing.SM, expand=True)

    ctk.CTkButton(
        btn_row, text="Disable Killswitch", width=140, height=36,
        fg_color=Colors.DANGER, text_color=Colors.TEXT_PRIMARY,
        hover_color="#be123c",
        command=on_disable
    ).pack(side="right", padx=Spacing.SM, expand=True)
