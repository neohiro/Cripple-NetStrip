"""
Cripple GUI Views — App Rules, Blocklist, Logs, Settings.
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

        self._build_updates_card()
        self._build_general_card()
        
    def _build_updates_card(self):
        from netstrip import __version__
        card = ctk.CTkFrame(self.scroll_frame, **CTK_FRAME_STYLE)
        card.pack(fill="x", pady=(0, Spacing.MD))

        ctk.CTkLabel(
            card, text="Updates",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        
        status_frame = ctk.CTkFrame(card, fg_color="transparent")
        status_frame.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.MD))
        
        self.lbl_current_version = ctk.CTkLabel(
            status_frame, text=f"Current Version: v{__version__}",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_SECONDARY
        )
        self.lbl_current_version.pack(side="left")
        
        self.lbl_update_status = ctk.CTkLabel(
            status_frame, text="Checking...",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, "bold"),
            text_color=Colors.TEXT_TERTIARY
        )
        self.lbl_update_status.pack(side="right")
        
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.LG))
        
        self.btn_check_update = ctk.CTkButton(
            btn_frame, text="Check for Updates",
            width=140, height=32, corner_radius=6,
            fg_color=Colors.BG_INPUT, hover_color=Colors.BG_ELEVATED,
            text_color=Colors.TEXT_PRIMARY,
            command=self._manual_update_check
        )
        self.btn_check_update.pack(side="left")
        
        self.btn_download_update = ctk.CTkButton(
            btn_frame, text="Download Update (Browser)",
            width=200, height=32, corner_radius=6,
            fg_color=Colors.SUCCESS_DIM, hover_color=Colors.SUCCESS,
            text_color=Colors.TEXT_PRIMARY,
            command=lambda: __import__('webbrowser').open("https://github.com/neohiro/Cripple-NetStrip/releases/latest")
        )
        self.btn_download_update.pack(side="right")
        self.btn_download_update.pack_forget() # Hidden by default
        
        self._refresh_update_status()
        
    def _refresh_update_status(self):
        if getattr(self.engine, 'update_available', False):
            self.lbl_update_status.configure(text=f"New version available: v{self.engine.latest_version}", text_color="#facc15")
            self.btn_download_update.pack(side="right")
        else:
            self.lbl_update_status.configure(text="Up to date", text_color=Colors.SUCCESS)
            self.btn_download_update.pack_forget()
            
    def _manual_update_check(self):
        self.btn_check_update.configure(state="disabled", text="Checking...")
        self.lbl_update_status.configure(text="Checking GitHub API...", text_color=Colors.TEXT_TERTIARY)
        self.btn_download_update.pack_forget()
        
        def _check():
            import urllib.request, json
            from netstrip import __version__
            try:
                req = urllib.request.Request(
                    "https://api.github.com/repos/neohiro/Cripple-NetStrip/releases/latest",
                    headers={'User-Agent': f'Cripple/{__version__}'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    tag = data.get('tag_name', '').lstrip('v')
                    if tag and tag != __version__:
                        self.engine.latest_version = tag
                        self.engine.update_available = True
                        if hasattr(self.engine, 'gui_update_callback') and self.engine.gui_update_callback:
                            try: self.engine.gui_update_callback("UPDATE_AVAILABLE")
                            except: pass
            except Exception:
                pass
                
            def _update_ui():
                if not self._destroyed:
                    self.btn_check_update.configure(state="normal", text="Check for Updates")
                    self._refresh_update_status()
                    
            self.after(0, _update_ui)
            
        import threading
        threading.Thread(target=_check, daemon=True).start()
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

            if setting_key == 'privacy_stream_mode':
                toplevel = self.winfo_toplevel()
                if hasattr(toplevel, '_update_geoip_ui'):
                    geo = getattr(self.engine.geoip, 'last_geo_data', {}) if hasattr(self.engine, 'geoip') else {}
                    toplevel._update_geoip_ui("", geo)

            if setting_key == 'autostart':
                from netstrip.platform.base import get_platform
                api = get_platform()
                if value == 'true':
                    api.install_autostart()
                else:
                    api.uninstall_autostart()
                    
            if setting_key == 'allow_in_browser_dns':
                import threading
                def reload_task():
                    try:
                        self.engine.blocklist.load_all()
                    except Exception:
                        pass
                threading.Thread(target=reload_task, daemon=True).start()

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
        
        self._add_subtitle(card, "Export or import your complete Cripple settings and App Rules as a JSON profile.")

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
            title="Export Cripple Profile",
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
            title="Import Cripple Profile",
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
        dialog.title('⚠ Factory Reset — Confirm')
        dialog.geometry('460x260')
        dialog.configure(fg_color=Colors.BG_DARKEST)
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.attributes("-topmost", True)
        dialog.resizable(False, False)
        
        # Center it
        dialog.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - 460) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - 260) // 2
        dialog.geometry(f'+{x}+{y}')
        
        ctk.CTkLabel(dialog, text='⚠  FACTORY RESET', font=(Fonts.FAMILY_PRIMARY[0], 20, 'bold'), text_color=Colors.DANGER).pack(pady=(24, 8))
        ctk.CTkLabel(dialog, text='Are you sure? This action is irreversible.', font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, 'bold'), text_color=Colors.TEXT_PRIMARY).pack(pady=(0, 6))
        ctk.CTkLabel(dialog, text='All user rules, settings, connection logs, custom blocklists,\nand online list registrations will be permanently deleted.\nMake sure you have exported a Backup Profile first!\n\nCripple will restart automatically after the wipe.', font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM), text_color=Colors.TEXT_SECONDARY, justify='center').pack(pady=(0, 20))
        
        btn_frame = ctk.CTkFrame(dialog, fg_color='transparent')
        btn_frame.pack()
        
        def on_confirm():
            dialog.destroy()
            self._do_factory_wipe()
            
        ctk.CTkButton(btn_frame, text='Cancel', width=120, height=36, fg_color=Colors.BG_ELEVATED, hover_color=Colors.BORDER_DEFAULT, text_color=Colors.TEXT_PRIMARY, command=dialog.destroy).pack(side='left', padx=10)
        ctk.CTkButton(btn_frame, text='WIPE & RESTART', width=140, height=36, fg_color=Colors.DANGER, hover_color='#f43f5e', text_color='white', font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, 'bold'), command=on_confirm).pack(side='right', padx=10)
        
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
            
        try:
            import os, json
            from netstrip.core.engine import NetStripEngine
            
            # Reconstruct lists_dir and sources_file path
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            lists_dir = os.path.join(base_dir, 'data', 'lists')
            sources_file = os.path.join(base_dir, 'data', 'updater_sources.json')
            
            # 1. Clean updater_sources.json
            if os.path.exists(sources_file):
                with open(sources_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                original_len = len(data.get('sources', []))
                data['sources'] = [s for s in data.get('sources', []) if not s.get('name', '').startswith('Custom: ')]
                
                if len(data['sources']) < original_len:
                    with open(sources_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
                        
            # 2. Delete custom downloaded txt files and cache
            if os.path.exists(lists_dir):
                for fname in os.listdir(lists_dir):
                    if "Custom_" in fname or fname == "NetStrip_cache.json" or fname == "updater_state.json":
                        try:
                            os.remove(os.path.join(lists_dir, fname))
                        except:
                            pass
        except Exception as e:
            print("Failed to clean custom blocklists:", e)
            
        import sys, os, subprocess
        creationflags = 0
        if os.name == 'nt':
            creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            
        if getattr(sys, 'frozen', False):
            # PyInstaller exe restart
            subprocess.Popen([sys.executable] + sys.argv[1:], creationflags=creationflags)
        else:
            # Python script restart
            subprocess.Popen([sys.executable] + sys.argv, creationflags=creationflags)
        
        # Kill current process forcefully to ensure clean restart without hanging threads
        os._exit(0)

    def _build_about_card(self):
        from netstrip import __version__
        card = ctk.CTkFrame(self.scroll_frame, fg_color=Colors.BG_PANEL, corner_radius=14, border_width=1, border_color=Colors.BORDER_SUBTLE)
        card.pack(fill="x")

        ctk.CTkLabel(
            card, text="About",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))

        ctk.CTkLabel(
            card, text=f"Cripple v{__version__}",
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

