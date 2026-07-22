"""
Cripper GUI Views — App Rules, Blocklist, Logs, Settings.
Fully functional views with auto-refresh, color-coding, and error handling.
"""

import customtkinter as ctk
from datetime import datetime
from netstrip.gui.theme import (
    Colors, Fonts, Spacing, Icons,
    CTK_FRAME_STYLE, CTK_ENTRY_STYLE, CTK_SWITCH_STYLE,
    get_category_color, get_category_label, get_category_icon,
)


#  AppRulesView — Pending Approvals + User Rules


class DNSSelectorModal(ctk.CTkToplevel):
    def __init__(self, master, dns_options_map, current_val, on_select_callback):
        super().__init__(master)
        self.title("Select DNS Upstream")
        self.geometry("400x500")
        self.minsize(400, 500)
        self.configure(fg_color=Colors.BG_DARK)
        self.transient(master)
        self.grab_set()
        
        self.dns_options_map = dns_options_map
        self.on_select_callback = on_select_callback
        
        # Search bar
        search_frame = ctk.CTkFrame(self, fg_color=Colors.BG_PANEL)
        search_frame.pack(fill="x", padx=Spacing.LG, pady=Spacing.LG)
        
        self.search_entry = ctk.CTkEntry(
            search_frame, placeholder_text="Search DNS providers...",
            fg_color=Colors.BG_INPUT, text_color=Colors.TEXT_PRIMARY,
            border_color=Colors.BORDER_DEFAULT, border_width=1,
            height=36, corner_radius=8
        )
        self.search_entry.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)
        self.search_entry.bind("<KeyRelease>", self._filter_list)
        
        # Scrollable list of providers
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=Colors.BG_DARK)
        self.scroll_frame.pack(fill="both", expand=True, padx=Spacing.LG, pady=(0, Spacing.LG))
        
        self.buttons = []
        self._populate_list(list(self.dns_options_map.keys()))
        
        # Center window
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() // 2) - (400 // 2)
        y = master.winfo_rooty() + (master.winfo_height() // 2) - (500 // 2)
        self.geometry(f"+{x}+{y}")
        self.search_entry.focus_set()

    def _filter_list(self, event=None):
        query = self.search_entry.get().lower()
        filtered = [k for k in self.dns_options_map.keys() if query in k.lower() or query in self.dns_options_map[k].lower()]
        self._populate_list(filtered)

    def _populate_list(self, items):
        for btn in self.buttons:
            btn.destroy()
        self.buttons.clear()
        
        for name in items:
            btn = ctk.CTkButton(
                self.scroll_frame, text=name, anchor="w",
                fg_color=Colors.BG_PANEL, text_color=Colors.TEXT_PRIMARY,
                hover_color=Colors.BG_ELEVATED, height=36, corner_radius=8,
                command=lambda n=name: self._select_item(n)
            )
            btn.pack(fill="x", pady=2)
            self.buttons.append(btn)
            
    def _select_item(self, name):
        self.on_select_callback(name)
        self.destroy()

# ═══════════════════════════════════════════════════
#  SettingsView

# ═══════════════════════════════════════════════════
class SettingsView(ctk.CTkFrame):
    """Application settings: autostart, DNS upstream, and about info."""

    def __init__(self, master, engine, **kwargs):
        super().__init__(master, fg_color=Colors.BG_DARK, **kwargs)
        self.engine = engine
        self._destroyed = False

        # Header
        ctk.CTkLabel(
            self, text="Settings",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XL, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.LG))

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=Colors.BG_DARK)
        self.scroll_frame.pack(fill="both", expand=True)

        self._build_general_card()
        self._build_network_card()
        self._build_scheduler_card()
        self._build_migration_card()
        self._build_about_card()

    def _build_general_card(self):
        card = ctk.CTkFrame(self.scroll_frame, **CTK_FRAME_STYLE)
        card.pack(fill="x", pady=(0, Spacing.MD))

        ctk.CTkLabel(
            card, text="General",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))

        # Privacy Stream Mode
        self._add_switch_row(card, "Privacy Stream Mode", 'privacy_stream_mode')
        self._add_subtitle(card, "Hides all IP addresses in the GUI (useful for streamers to prevent IP leaks).")

        # Autostart toggle
        self._add_switch_row(card, "Start on Boot", 'autostart')

        # Minimize to tray toggle
        self._add_switch_row(card, "Minimize to Tray", 'minimize_to_tray')
        self._add_subtitle(card, "Keep Cripper running in the background when closing the window.")

        # Run as Service Only
        self._add_switch_row(card, "Run as Service Only (Headless)", 'run_as_service')
        self._add_subtitle(card, "Do not show GUI at login. App runs silently in the background (accessible via tray or manual start).")

        # IP Flux Tolerance
        self._add_switch_row(card, "IP Flux Tolerance", 'ip_flux_tolerance')
        self._add_subtitle(card, "Ignore Public IP changes for Auto-Killswitch (useful if using a VPN).")

        # Smart Shield
        self._add_switch_row(card, "Smart Shield", 'smart_paranoid_mode')
        self._add_subtitle(card, "Auto-escalates to Paranoid mode on malware detection, and instantly engages the Master Killswitch upon sudden VPN drops or kernel route shifts.")
        
        # Block System Connections
        self._add_switch_row(card, "Block System Connections", 'block_system_connections')
        self._add_subtitle(card, "Disable all non-vital background OS services globally (can disrupt updates).")
        
        # Allow in-browser DNS
        self._add_switch_row(card, "Allow in-browser DNS", 'allow_in_browser_dns')
        self._add_subtitle(card, "Allows browsers to use their own DoH settings (bypasses NetStrip filtering).")

        # Bottom padding
        ctk.CTkFrame(card, fg_color=Colors.BG_PANEL, height=Spacing.SM).pack()

    def _add_subtitle(self, parent, text):
        ctk.CTkLabel(
            parent, text=text,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
            text_color=Colors.TEXT_TERTIARY,
            justify="left"
        ).pack(anchor="w", padx=Spacing.LG, pady=(2, Spacing.MD))

    def _add_switch_row(self, parent, label_text, setting_key):
        row = ctk.CTkFrame(parent, fg_color=Colors.BG_PANEL)
        row.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, 0))

        ctk.CTkLabel(
            row, text=label_text,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        try:
            default_val = 'true' if setting_key == 'smart_paranoid_mode' else 'false'
            current_val = self.engine.db.get_setting(setting_key, default_val)
            current = str(current_val).lower() == 'true'
        except Exception:
            current = setting_key == 'smart_paranoid_mode'

        switch = ctk.CTkSwitch(
            row, text="",
            progress_color=Colors.ACCENT_PRIMARY,
            button_color=Colors.TEXT_PRIMARY,
            button_hover_color=Colors.ACCENT_LIGHT,
            fg_color=Colors.BORDER_DEFAULT,
            command=lambda: self._on_switch_toggle(switch, setting_key),
        )
        switch.pack(side="right")
        if current:
            switch.select()

    def _on_switch_toggle(self, switch, setting_key):
        try:
            value = 'true' if switch.get() else 'false'
            self.engine.db.set_setting(setting_key, value)
            
            if setting_key == 'run_as_service' and value == 'true':
                toplevel = self.winfo_toplevel()
                toplevel.withdraw()
                toplevel._show_tray_icon()
                if hasattr(self.engine, 'on_status') and self.engine.on_status:
                    self.engine.on_status("Switched to background service mode")
                return

            if setting_key == 'disable_ipv6_globally':
                from netstrip.platform.base import get_platform
                api = get_platform()
                if value == 'true':
                    api.disable_ipv6()
                else:
                    api.enable_ipv6()
                    
            readable_name = setting_key.replace('_', ' ').title()
            status = "Enabled" if value == 'true' else "Disabled"
            if hasattr(self.engine, 'on_status') and self.engine.on_status:
                self.engine.on_status(f"{readable_name} has been {status}")
        except Exception:
            pass

    def _build_network_card(self):
        card = ctk.CTkFrame(self.scroll_frame, **CTK_FRAME_STYLE)
        card.pack(fill="x", pady=(0, Spacing.MD))

        ctk.CTkLabel(
            card, text="Network",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        
        # Disable IPv6 globally
        self._add_switch_row(card, "Disable IPv6 Globally", 'disable_ipv6_globally')
        self._add_subtitle(card, "Force all traffic onto IPv4 where NetStrip can cleanly intercept it without bypass leaks. Persistent across reboots.")

        row = ctk.CTkFrame(card, fg_color=Colors.BG_PANEL)
        row.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.LG))

        ctk.CTkLabel(
            row, text="DNS Upstream",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        try:
            dns_val = self.engine.db.get_setting('dns_upstream', '1.1.1.1')
        except Exception:
            dns_val = '1.1.1.1'

        from netstrip.core.dns_proxy import DNS_UPSTREAM_OPTIONS
        # DNS_UPSTREAM_OPTIONS maps IP -> "IP (Name)"
        # We need a reverse map for the dropdown: "IP (Name)" -> IP
        self.dns_options_map = {v: k for k, v in DNS_UPSTREAM_OPTIONS.items()}
        
        # If we detected a local proxy (like dnscrypt-proxy), add it as an option
        local_tool = self.engine.db.get_setting("local_dns_tool")
        local_ip = self.engine.db.get_setting("local_dns_ip", "127.0.0.1")
        if local_tool:
            self.dns_options_map[f"Local Proxy ({local_tool})"] = local_ip
            
        # Find the key for the current value
        current_option = list(self.dns_options_map.keys())[0]
        for k, v in self.dns_options_map.items():
            if v == dns_val:
                current_option = k
                break

        self.current_dns_label = ctk.CTkLabel(
            row, text=current_option,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
            text_color=Colors.ACCENT_PRIMARY,
            width=200, anchor="e"
        )
        self.current_dns_label.pack(side="right", padx=(Spacing.LG, Spacing.SM))
        
        ctk.CTkButton(
            row, text="Select DNS...", width=120, height=32, corner_radius=8,
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BG_INPUT,
            text_color=Colors.TEXT_PRIMARY,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            command=self._open_dns_selector,
        ).pack(side="right", padx=(Spacing.SM, 0))




    def _open_dns_selector(self):
        try:
            dns_val = self.engine.db.get_setting('dns_upstream', '1.1.1.1')
        except:
            dns_val = '1.1.1.1'
        DNSSelectorModal(self.winfo_toplevel(), self.dns_options_map, dns_val, self._save_dns)

    def _save_dns(self, selected_name):
        try:
            self.current_dns_label.configure(text=selected_name)
            selected_ip = self.dns_options_map.get(selected_name, selected_name.strip())
            self.engine.db.set_setting('dns_upstream', selected_ip)
            if hasattr(self.engine, 'on_status') and self.engine.on_status:
                self.engine.on_status(f"DNS Upstream changed to {selected_ip}")
        except Exception:
            pass

    def _build_scheduler_card(self):
        card = ctk.CTkFrame(self.scroll_frame, **CTK_FRAME_STYLE)
        card.pack(fill="x", pady=(0, Spacing.MD))

        ctk.CTkLabel(
            card, text="Killswitch Scheduler",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.XS))
        
        self._add_subtitle(card, "Automatically engage the Master Killswitch during a daily downtime window.")

        self._add_switch_row(card, "Enable Scheduler", 'killswitch_schedule_enabled')

        row = ctk.CTkFrame(card, fg_color=Colors.BG_PANEL)
        row.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, Spacing.LG))

        ctk.CTkLabel(row, text="Start (HH:MM):", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM), text_color=Colors.TEXT_SECONDARY).pack(side="left")
        self._start_entry = ctk.CTkEntry(row, width=60, **CTK_ENTRY_STYLE)
        self._start_entry.pack(side="left", padx=Spacing.SM)
        self._start_entry.insert(0, self.engine.db.get_setting("killswitch_start", "23:00"))

        ctk.CTkLabel(row, text="End (HH:MM):", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM), text_color=Colors.TEXT_SECONDARY).pack(side="left", padx=(Spacing.LG, 0))
        self._end_entry = ctk.CTkEntry(row, width=60, **CTK_ENTRY_STYLE)
        self._end_entry.pack(side="left", padx=Spacing.SM)
        self._end_entry.insert(0, self.engine.db.get_setting("killswitch_end", "07:00"))

        ctk.CTkButton(
            row, text="Save Schedule", width=100, height=32, corner_radius=8,
            fg_color=Colors.ACCENT_PRIMARY, hover_color=Colors.ACCENT_LIGHT,
            text_color=Colors.TEXT_PRIMARY,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            command=self._save_schedule,
        ).pack(side="right")

    def _save_schedule(self):
        self.engine.db.set_setting("killswitch_start", self._start_entry.get())
        self.engine.db.set_setting("killswitch_end", self._end_entry.get())

    def _build_migration_card(self):
        card = ctk.CTkFrame(self.scroll_frame, **CTK_FRAME_STYLE)
        card.pack(fill="x", pady=(0, Spacing.MD))

        ctk.CTkLabel(
            card, text="Backup & Migration",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        
        self._add_subtitle(card, "Export or import your complete Cripper settings and App Rules as a JSON profile.")

        row = ctk.CTkFrame(card, fg_color=Colors.BG_PANEL)
        row.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.LG))

        ctk.CTkButton(
            row, text="Export Profile", width=120, height=32, corner_radius=8,
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BORDER_DEFAULT,
            text_color=Colors.TEXT_PRIMARY, border_width=1, border_color=Colors.BORDER_SUBTLE,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            command=self._export_profile,
        ).pack(side="left", padx=(0, Spacing.SM))

        ctk.CTkButton(
            row, text="Import Profile", width=120, height=32, corner_radius=8,
            fg_color=Colors.ACCENT_PRIMARY, hover_color=Colors.ACCENT_LIGHT,
            text_color=Colors.TEXT_PRIMARY,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            command=self._import_profile,
        ).pack(side="left")

        ctk.CTkButton(
            row, text="Factory Reset", width=120, height=32, corner_radius=8,
            fg_color="#4a1525", hover_color=Colors.DANGER,
            text_color=Colors.TEXT_PRIMARY,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
            command=self._factory_reset,
        ).pack(side="right")

    def _export_profile(self):
        import tkinter.filedialog as fd
        import os
        init_dir = os.path.expanduser("~/Documents")
        path = fd.asksaveasfilename(
            initialdir=init_dir,
            title="Export Cripper Profile",
            defaultextension=".json",
            filetypes=[("JSON Profile", "*.json"), ("All Files", "*.*")]
        )
        if path:
            try:
                self.engine.db.export_profile(path)
                from tkinter import messagebox
                messagebox.showinfo("Export Successful", f"Profile successfully exported to:\n{path}")
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Export Failed", f"Failed to export profile:\n{e}")

    def _import_profile(self):
        import tkinter.filedialog as fd
        import os
        init_dir = os.path.expanduser("~/Documents")
        path = fd.askopenfilename(
            initialdir=init_dir,
            title="Import Cripper Profile",
            filetypes=[("JSON Profile", "*.json"), ("All Files", "*.*")]
        )
        if path:
            try:
                self.engine.db.import_profile(path)
                from tkinter import messagebox
                messagebox.showinfo("Import Successful", "Profile successfully imported! Some settings may require a restart to apply.")
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Import Failed", f"Failed to import profile:\n{e}")

    def _factory_reset(self):
        import customtkinter as ctk
        dialog = ctk.CTkToplevel(self)
        dialog.title('Factory Reset')
        dialog.geometry('400x200')
        dialog.transient(self.master)
        dialog.grab_set()
        
        # Center it
        dialog.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - 400) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - 200) // 2
        dialog.geometry(f'+{x}+{y}')
        
        ctk.CTkLabel(dialog, text='WARNING: Factory Reset', font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, 'bold'), text_color=Colors.DANGER).pack(pady=(20, 10))
        ctk.CTkLabel(dialog, text='This will permanently delete ALL your App Rules, settings,\nand connection history. Please ensure you have exported a\nBackup Profile first!\n\nThe application will restart after wiping data.', text_color=Colors.TEXT_SECONDARY).pack(pady=(0, 20))
        
        btn_frame = ctk.CTkFrame(dialog, fg_color='transparent')
        btn_frame.pack()
        
        def on_confirm():
            dialog.destroy()
            self._do_factory_wipe()
            
        ctk.CTkButton(btn_frame, text='Cancel', width=100, fg_color=Colors.BG_ELEVATED, hover_color=Colors.BORDER_DEFAULT, command=dialog.destroy).pack(side='left', padx=10)
        ctk.CTkButton(btn_frame, text='WIPE DATA', width=100, fg_color=Colors.DANGER, hover_color='#f43f5e', command=on_confirm).pack(side='right', padx=10)
        
    def _do_factory_wipe(self):
        try:
            conn = self.engine.db._get_connection()
            conn.execute('DELETE FROM user_rules')
            conn.execute('DELETE FROM settings')
            conn.execute('DELETE FROM connection_log')
            conn.execute('DELETE FROM statistics')
            try: conn.execute('DELETE FROM dns_cache')
            except: pass
            conn.commit()
            conn.execute('VACUUM')
        except Exception as e:
            print('Wipe failed:', e)
            
        import sys, os
        os.execv(sys.executable, ['python'] + sys.argv)

    def _build_about_card(self):
        card = ctk.CTkFrame(self.scroll_frame, fg_color=Colors.BG_PANEL, corner_radius=14, border_width=1, border_color=Colors.BORDER_SUBTLE)
        card.pack(fill="x")

        ctk.CTkLabel(
            card, text="About",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))

        ctk.CTkLabel(
            card, text="Cripper v0.1.0-alpha",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG)

        ctk.CTkLabel(
            card, text="Intelligent Network Debloater — Strip away the noise.",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.XS, 0))

        ctk.CTkLabel(
            card, text="© 2026 FrenzyPenguin Media",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_TERTIARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.XS, Spacing.LG))

        ctk.CTkLabel(
            card, text="Built with Python & CustomTkinter",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
            text_color=Colors.TEXT_TERTIARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.XS, Spacing.LG))

        self._build_credits()

    def _build_credits(self):
        credits_frame = ctk.CTkFrame(self.scroll_frame, fg_color=Colors.BG_PANEL)
        credits_frame.pack(fill="x", pady=Spacing.MD)
        
        credits_text = (
            "POWERED BY & CREDITS TO OPEN SOURCE:\n"
            "Python 3 • CustomTkinter (Tom Schimansky) • dnslib (PaulC) • psutil (Giampaolo Rodola)\n"
            "BCC (iovisor) • SQLite3 • AdGuard Blocklists • oisd (sjhgvr) • Steven Black Hosts • HaGeZi\n"
            "WindowsSpyBlocker (crazy-max) • URLHaus (abuse.ch)"
        )
        
        ctk.CTkLabel(
            credits_frame, text=credits_text,
            font=(Fonts.FAMILY_PRIMARY[0], 9), # Micro-font
            text_color=Colors.TEXT_TERTIARY,
            justify="center"
        ).pack(anchor="center")

    def destroy(self):
        self._destroyed = True
        super().destroy()

#  TorView — Provisional Tor Integration UI

class TorView(ctk.CTkFrame):
    """Provisional UI for Tor app-specific routing."""

    def __init__(self, master, engine, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PANEL, **kwargs)
        self.engine = engine
        
        # Header
        ctk.CTkLabel(
            self, text="Tor Integration (Preview)",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XL, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.MD))
        
        # Warning Card
        warning_card = ctk.CTkFrame(self, fg_color=Colors.WARNING_DIM, corner_radius=Spacing.RADIUS_MD)
        warning_card.pack(fill="x", pady=(0, Spacing.LG))
        
        ctk.CTkLabel(
            warning_card,
            text="⚠ UDP traffic (like standard DNS queries or game data) is NOT routed through Tor. Only TCP traffic can be proxied.",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
            text_color=Colors.WARNING,
            wraplength=700,
            justify="left"
        ).pack(padx=Spacing.LG, pady=Spacing.MD, anchor="w")
        
        # Setup Card
        setup_card = ctk.CTkFrame(self, fg_color=Colors.BG_PANEL, corner_radius=14, border_width=1, border_color=Colors.BORDER_SUBTLE)
        setup_card.pack(fill="x", pady=(0, Spacing.MD))
        
        ctk.CTkLabel(
            setup_card, text="Per-App Proxying",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        
        ctk.CTkLabel(
            setup_card, 
            text="Assign specific applications to route their TCP traffic exclusively through the Tor network.\n(Note: This requires the Tor client to be running locally on port 9050. Full Windows transparent proxying driver integration is under development.)",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_SECONDARY,
            justify="left"
        ).pack(anchor="w", padx=Spacing.LG, pady=(0, Spacing.LG))
        
        # Add app row
        row = ctk.CTkFrame(setup_card, fg_color=Colors.BG_PANEL)
        row.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.LG))
        
        self.app_entry = ctk.CTkEntry(row, placeholder_text="e.g. chrome.exe", width=200)
        self.app_entry.pack(side="left")
        
        ctk.CTkButton(
            row, text="Add to Tor Routing",
            fg_color=Colors.ACCENT_PRIMARY, hover_color=Colors.ACCENT_LIGHT,
            text_color=Colors.TEXT_PRIMARY,
            command=self._add_tor_app
        ).pack(side="left", padx=Spacing.SM)
        
    def _add_tor_app(self):
        # Placeholder for Tor app adding logic
        pass

