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
    dialog.transient(parent)
    dialog.grab_set()
    dialog.attributes("-topmost", True)
    dialog.configure(fg_color=Colors.BG_DARKEST)

    from netstrip.gui.utils import center_window, apply_window_icon, get_app_logo_image
    apply_window_icon(dialog)
    center_window(dialog, 400, 250, parent=parent)

    content = ctk.CTkFrame(dialog, fg_color=Colors.BG_PANEL, corner_radius=Spacing.RADIUS_MD)
    content.pack(fill="both", expand=True, padx=Spacing.LG, pady=Spacing.LG)

    header = ctk.CTkFrame(content, fg_color="transparent")
    header.pack(pady=(Spacing.LG, Spacing.SM))

    logo_img = get_app_logo_image(size=(22, 22))
    if logo_img:
        lbl_logo = ctk.CTkLabel(header, image=logo_img, text="")
        lbl_logo.pack(side="left", padx=(0, 8))

    ctk.CTkLabel(
        header, text="⚠️ Killswitch is Active",
        font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, Fonts.WEIGHT_BOLD),
        text_color=Colors.DANGER
    ).pack(side="left")

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
