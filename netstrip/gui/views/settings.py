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
        
        from netstrip.gui.utils import apply_window_icon
        apply_window_icon(self)
        
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
        self._build_network_card()
        self._build_scheduler_card()
        self._build_migration_card()
        self._build_analytics_card()
        self._build_about_card()
        
        # Track switch references for state syncing
        self._switch_refs = {}
        
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
        self.lbl_update_status.configure(text="Checking GitHub API & blocklists...", text_color=Colors.TEXT_TERTIARY)
        self.btn_download_update.pack_forget()
        
        def _check():
            import urllib.request, json
            from netstrip import __version__
            from netstrip.core.updater import is_newer_version
            check_failed = False

            # Trigger blocklist auto-updater cycle
            if hasattr(self.engine, 'updater') and self.engine.updater:
                try:
                    self.engine.updater.check_and_update(force=True)
                except Exception:
                    pass

            # Check GitHub API for application release updates
            try:
                req = urllib.request.Request(
                    "https://api.github.com/repos/neohiro/Cripple-NetStrip/releases/latest",
                    headers={'User-Agent': f'Cripple/{__version__}'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    tag = data.get('tag_name', '').lstrip('v')
                    if tag and is_newer_version(tag, __version__):
                        self.engine.latest_version = tag
                        self.engine.update_available = True
                        if hasattr(self.engine, 'gui_update_callback') and self.engine.gui_update_callback:
                            try: self.engine.gui_update_callback("UPDATE_AVAILABLE")
                            except: pass
                    else:
                        self.engine.update_available = False
            except Exception:
                check_failed = True
                
            def _update_ui():
                if not getattr(self, '_destroyed', False):
                    self.btn_check_update.configure(state="normal", text="Check for Updates")
                    if check_failed and not getattr(self.engine, 'update_available', False):
                        self.lbl_update_status.configure(text="Unable to check for updates", text_color=Colors.TEXT_TERTIARY)
                    else:
                        self._refresh_update_status()
                    
            self.after(0, _update_ui)
            
        import threading
        threading.Thread(target=_check, daemon=True).start()

    def _build_general_card(self):
        card = ctk.CTkFrame(self.scroll_frame, **CTK_FRAME_STYLE)
        card.pack(fill="x", pady=(0, Spacing.MD))

        ctk.CTkLabel(
            card, text="General",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))

        # Privacy Stream Mode
        self._add_switch_row(card, "Privacy Stream Mode", 'privacy_stream_mode', tooltip_text="Use Case: Streamers who want to hide their IP addresses on screen. Masks all IPs in the GUI logs.")
        self._add_subtitle(card, "Hides all IP addresses in the GUI (useful for streamers to prevent IP leaks).")

        # Autostart toggle
        self._add_switch_row(card, "Start on Boot", 'autostart', tooltip_text="Use Case: Set-and-forget security. Ensures the firewall is running the moment the computer boots.")

        # Run as Service Only
        self._add_switch_row(card, "Run as Service Only (Headless)", 'run_as_service', tooltip_text="Use Case: Servers and non-GUI devices. Runs NetStrip silently in the background without spawning the desktop GUI.")
        self._add_subtitle(card, "Do not show GUI at login. App runs silently in the background (accessible via tray or manual start).")

        # IP Flux Tolerance
        self._add_switch_row(card, "IP Flux Tolerance", 'ip_flux_tolerance', tooltip_text="Use Case: VPN users. Prevents the firewall from panicking and locking down when your VPN changes your public IP.")
        self._add_subtitle(card, "Ignore Public IP changes for Auto-Killswitch (useful if using a VPN).")

        # Smart Shield
        self._add_switch_row(card, "Smart Shield", 'smart_paranoid_mode', tooltip_text="Use Case: Essential endpoint protection. Automatically escalates security levels when an intrusion is detected.")
        self._add_subtitle(card, "Auto-escalates to Ghost mode on malware detection, and instantly engages the Master Killswitch upon sudden VPN drops or kernel route shifts.")
        
        # Block System Connections
        self._add_switch_row(card, "Block System Connections", 'block_system_connections', tooltip_text="Use Case: Ultimate privacy. Strips redundant OS bindings (LLDP, NetBIOS, WPAD, SRV, ISATAP) and blocks background OS telemetry.")
        self._add_subtitle(card, "Disable redundant OS bindings and all background OS telemetry services globally.")
        
        # Allow in-browser DNS
        self._add_switch_row(card, "Allow in-browser DNS", 'allow_in_browser_dns', tooltip_text="Use Case: If you use Chrome/Firefox DoH features and don't want NetStrip filtering your web browsing.")
        self._add_subtitle(card, "Allows browsers to use their own DoH settings (bypasses NetStrip filtering).")

        # Bottom padding
        ctk.CTkFrame(card, fg_color=Colors.BG_PANEL, height=Spacing.SM).pack()

    def _add_subtitle(self, parent, text, pady=(2, Spacing.MD)):
        lbl = ctk.CTkLabel(
            parent, text=text,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
            text_color=Colors.TEXT_TERTIARY,
            justify="left",
            anchor="w",
            wraplength=340
        )
        lbl.pack(anchor="w", fill="x", padx=Spacing.LG, pady=pady)
        
        def _update_wrap(event):
            try:
                if lbl.winfo_exists():
                    # Wrap onto 2nd or 3rd line faster; leave ample right-margin buffer
                    new_wrap = max(180, min(event.width - (Spacing.LG * 2 + 60), 380))
                    lbl.configure(wraplength=new_wrap)
            except Exception:
                pass
        parent.bind("<Configure>", _update_wrap, add="+")
        
    def _add_title(self, parent, text, icon=None, pady=(Spacing.LG, Spacing.SM)):
        display_text = f"{icon}  {text}" if icon else text
        ctk.CTkLabel(
            parent, text=display_text,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=pady)

    # Platform compatibility map: setting_key -> set of supported platforms
    # Platforms: 'win32', 'linux', 'darwin', 'android'
    PLATFORM_SUPPORT = {
        'disable_ipv6_globally':   {'win32', 'linux', 'darwin'},
        'disable_ipv4_globally':   {'win32', 'linux', 'darwin'},
        'kernel_anomaly_scanner':  {'win32', 'linux'},
        'layer2_arp_lockdown':     {'win32', 'linux', 'darwin'},
        'mac_randomization':       {'win32', 'linux', 'darwin'},
        'harden_network_adapter':  {'win32', 'linux', 'darwin'},
        'force_doh':               {'win32', 'linux', 'darwin', 'android'},
        'linux_ebpf_mode':         {'linux'},
        'strict_inbound_shield':   {'win32', 'linux', 'darwin'},
        'inbound_lan_bypass':      {'win32', 'linux', 'darwin'},
        'inbound_notifications':   {'win32', 'linux', 'darwin', 'android'},
        'block_system_connections': {'win32', 'linux', 'darwin'},
    }

    @staticmethod
    def _get_current_platform() -> str:
        import os, sys
        if os.environ.get('NETSTRIP_ANDROID') == '1' or hasattr(sys, 'getandroidapilevel'):
            return 'android'
        return sys.platform  # 'win32', 'linux', 'darwin'

    @staticmethod
    def _platform_label(platforms: set) -> str:
        """Generate a human-readable platform availability string."""
        names = []
        if 'win32' in platforms: names.append('Windows')
        if 'linux' in platforms: names.append('Linux')
        if 'darwin' in platforms: names.append('macOS')
        if 'android' in platforms: names.append('Android')
        return ', '.join(names)

    def _add_switch_row(self, parent, label_text, setting_key, tooltip_text=None):
        # Check platform compatibility
        current_platform = self._get_current_platform()
        supported_platforms = self.PLATFORM_SUPPORT.get(setting_key)
        
        if supported_platforms is not None:
            is_supported = current_platform in supported_platforms
            # On Android: completely omit settings that aren't supported
            if current_platform == 'android' and not is_supported:
                return
        else:
            is_supported = True
        
        row = ctk.CTkFrame(parent, fg_color=Colors.BG_PANEL)
        row.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, 0))

        text_color = Colors.TEXT_PRIMARY if is_supported else Colors.TEXT_TERTIARY
        lbl = ctk.CTkLabel(
            row, text=label_text,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
            text_color=text_color,
        )
        lbl.pack(side="left")
        
        # Build tooltip — add platform availability notice for greyed-out items
        effective_tooltip = tooltip_text or ""
        if not is_supported and supported_platforms:
            platform_str = self._platform_label(supported_platforms)
            effective_tooltip = f"⚠️ Only available on: {platform_str}.\n\n{effective_tooltip}"
        
        if effective_tooltip:
            try:
                from netstrip.gui.hovertip import FadingHovertip
                FadingHovertip(lbl, effective_tooltip, hover_delay=300)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to bind hovertip: {e}")

        try:
            if setting_key == 'inbound_lan_bypass':
                default_val = 'true' if self.engine.is_headless else 'false'
            elif setting_key in ('smart_paranoid_mode', 'strict_inbound_shield', 'inbound_notifications', 
                                 'kernel_anomaly_scanner', 'layer2_arp_lockdown', 'linux_ebpf_mode'):
                default_val = 'true'
            else:
                default_val = 'false'
            
            current_val = self.engine.db.get_setting(setting_key, default_val)
            current = str(current_val).lower() == 'true'
        except Exception:
            current = setting_key in ('smart_paranoid_mode', 'strict_inbound_shield', 'inbound_notifications')
            if setting_key == 'inbound_lan_bypass' and hasattr(self, 'engine') and self.engine.is_headless:
                current = True

        if is_supported:
            switch = ctk.CTkSwitch(
                row, text="",
                progress_color=Colors.ACCENT_PRIMARY,
                button_color=Colors.TEXT_PRIMARY,
                button_hover_color=Colors.ACCENT_LIGHT,
                fg_color=Colors.BORDER_DEFAULT,
                command=lambda: self._on_switch_toggle(switch, setting_key),
            )
        else:
            # Greyed-out, non-interactive switch for unsupported platforms
            switch = ctk.CTkSwitch(
                row, text="",
                progress_color=Colors.BORDER_DEFAULT,
                button_color=Colors.TEXT_TERTIARY,
                button_hover_color=Colors.TEXT_TERTIARY,
                fg_color=Colors.BG_DARKEST,
                state="disabled",
            )
        switch.pack(side="right")
        if current and is_supported:
            switch.select()
        else:
            switch.deselect()
        self._switch_refs[setting_key] = switch

    def refresh_toggles(self):
        """Synchronize switch visuals with current DB state (called on MODE_CHANGED)."""
        if not hasattr(self, '_switch_refs'):
            return
        for key, switch in self._switch_refs.items():
            if not switch.winfo_exists():
                continue
            
            if key == 'block_system_connections':
                val = self.engine.db.get_setting(key, "false")
            elif key == 'smart_shield':
                val = self.engine.db.get_setting(key, "true")
            elif key == 'telemetry':
                val = self.engine.db.get_setting(key, "false")
            else:
                val = self.engine.db.get_setting(key, "false")
                
            current_state = switch.get()
            expected_state = 1 if val == 'true' else 0
            
            if current_state != expected_state:
                if expected_state:
                    switch.select()
                else:
                    switch.deselect()

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

            if setting_key == 'kernel_anomaly_scanner':
                if value == 'true':
                    if hasattr(self.engine, 'anomaly_scanner') and self.engine.anomaly_scanner:
                        self.engine.anomaly_scanner.start()
                else:
                    if hasattr(self.engine, 'anomaly_scanner') and self.engine.anomaly_scanner:
                        self.engine.anomaly_scanner.stop()
                        
            if setting_key == 'linux_ebpf_mode':
                if value == 'true':
                    if hasattr(self.engine, 'ebpf_manager') and self.engine.ebpf_manager:
                        self.engine.ebpf_manager.start()
                else:
                    if hasattr(self.engine, 'ebpf_manager') and self.engine.ebpf_manager:
                        self.engine.ebpf_manager.stop()
                        
            if setting_key == 'layer2_arp_lockdown':
                if value == 'false':
                    if hasattr(self.engine, 'network_monitor') and hasattr(self.engine.network_monitor, 'current_state'):
                        gw_ip = self.engine.network_monitor.current_state.get('gateway_ip')
                        if gw_ip:
                            self.engine.platform.unlock_arp(gw_ip)

            if setting_key == 'disable_ipv6_globally':
                from netstrip.platform.base import get_platform
                api = get_platform()
                if value == 'true':
                    api.disable_ipv6()
                else:
                    api.enable_ipv6()
                    
            if setting_key == 'disable_ipv4_globally':
                from netstrip.platform.base import get_platform
                api = get_platform()
                if value == 'true':
                    api.disable_ipv4()
                else:
                    api.enable_ipv4()

            if setting_key == 'analytics_opt_in':
                # Whitelist/un-whitelist the telemetry delivery domains
                telemetry_domains = ['api.github.com']
                bl = self.engine.classifier.blocklist
                if value == 'true':
                    for d in telemetry_domains:
                        bl.add_user_whitelist(d)
                else:
                    with bl.lock:
                        for d in telemetry_domains:
                            bl.whitelist.discard(d)
                if hasattr(self.engine, 'classifier'):
                    self.engine.classifier._domain_cache.clear()

            if setting_key == 'block_system_connections':
                # Flush classifier caches and harden/restore network adapter bindings
                from netstrip.platform.base import get_platform
                api = get_platform()
                is_blocking = (value == 'true')
                if hasattr(api, 'harden_network_adapters'):
                    import threading
                    threading.Thread(target=lambda: api.harden_network_adapters(enable_hardening=is_blocking), daemon=True).start()
                if hasattr(self.engine, 'classifier'):
                    self.engine.classifier._domain_cache.clear()
                    if hasattr(self.engine.classifier, '_ip_cache'):
                        self.engine.classifier._ip_cache.clear()
                if hasattr(self.engine, 'gui_update_callback') and self.engine.gui_update_callback:
                    try: self.engine.gui_update_callback("MODE_CHANGED")
                    except: pass

            if setting_key == 'mac_randomization':
                import threading
                def _apply_mac():
                    try:
                        from netstrip.core.mac_randomizer import MACRandomizer
                        randomizer = MACRandomizer(self.engine)
                        if value == 'true':
                            randomizer.randomize_active_adapter()
                        else:
                            randomizer.restore_active_adapter()
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"MAC randomization failed: {e}")
                threading.Thread(target=_apply_mac, daemon=True).start()

            if setting_key == 'harden_network_adapter':
                import threading
                def _apply_hardening():
                    try:
                        from netstrip.core.mac_randomizer import MACRandomizer
                        MACRandomizer.harden_adapter_protocols(enable=(value == 'true'))
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Adapter hardening failed: {e}")
                threading.Thread(target=_apply_hardening, daemon=True).start()

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
        
        # Disable IPv6 Globally
        self._add_switch_row(card, "Disable IPv6 Globally", 'disable_ipv6_globally', tooltip_text="Use Case: Strict IPv4 control. Forces your machine to drop complex IPv6 routing entirely so NetStrip can cleanly intercept all traffic.")
        self._add_subtitle(card, "Force all traffic onto IPv4 where NetStrip can cleanly intercept it without bypass leaks. Persistent across reboots.")

        # Disable IPv4 Globally
        self._add_switch_row(card, "Disable IPv4 Globally", 'disable_ipv4_globally', tooltip_text="Use Case: Advanced IPv6 networks. Rips IPv4 out of the OS network stack. Warning: Will break most legacy LAN connections.")
        self._add_subtitle(card, "EXPERIMENTAL: Rips IPv4 completely out of the OS network stack. Forces the machine to run exclusively on IPv6. Will break most standard LAN/WAN connections.")

        # Kernel Anomaly Scanner
        self._add_switch_row(card, "Kernel Anomaly Scanner", 'kernel_anomaly_scanner', tooltip_text="Use Case: EDR-level Security. Triggers Paranoid lockdown if a rogue VPN or rootkit Pcap driver spins up. Can whitelist known VPNs upon popup.")
        self._add_subtitle(card, "Actively scans for unauthorized NDIS filter drivers, WinPcap/libpcap raw sockets, and rogue VPN adapters that could bypass NetStrip's firewall. Escalates to Smart Shield upon detection.")

        # Layer 2 ARP Lockdown
        self._add_switch_row(card, "Layer 2 ARP Lockdown", 'layer2_arp_lockdown', tooltip_text="Use Case: Public Wi-Fi / Corporate Networks. Prevents hackers from spoofing your router's MAC address and redirecting your packets to them.")
        self._add_subtitle(card, "Enforces static MAC-to-IP pinning for your default gateway at the OS level. Mathematically prevents ARP Spoofing and Layer 2 redirection attacks without needing a custom kernel driver.")

        # MAC Address Randomization (Default OFF)
        self._add_switch_row(card, "MAC Address Randomization", 'mac_randomization', tooltip_text="Use Case: Public Wi-Fi anonymity. Changes your hardware MAC address to a random locally-administered address, preventing physical device tracking across networks.")
        self._add_subtitle(card, "Generates a random locally-administered MAC address and applies it to your active network adapter. Prevents network-level fingerprinting and hardware tracking. Requires brief adapter restart (~3s disconnect).")

        # Harden Network Adapter
        self._add_switch_row(card, "Harden Network Adapter", 'harden_network_adapter', tooltip_text="Use Case: Attack surface reduction. Disables vulnerable legacy protocols (NetBIOS, LLDP, LLMNR, mDNS, Client for Microsoft Networks, QoS) on all network adapters.")
        self._add_subtitle(card, "Strips unnecessary protocol bindings from your network adapters. Disables NetBIOS over TCP/IP, LLMNR, LLDP, mDNS responder, Client for Microsoft Networks, File and Printer Sharing, and QoS Packet Scheduler. Dramatically reduces your adapter's attack surface.")

        # Force DNS-over-HTTPS
        self._add_switch_row(card, "Force DNS-over-HTTPS (DoH)", 'force_doh', tooltip_text="Use Case: ISP blindness. Encrypts all DNS queries so your internet provider cannot see which domains you visit. Auto-enabled when no third-party DNS proxy is detected.")
        self._add_subtitle(card, "Forces all DNS resolution through encrypted HTTPS tunnels (Cloudflare, Google, Quad9, AdGuard). Falls back to DoT if DoH fails. Plaintext UDP port 53 is used only as last resort in 'auto' mode, or blocked entirely in strict mode.")


        # Linux Deep Kernel XDP Mode — shown on all platforms, greyed out on non-Linux
        self._add_switch_row(card, "Deep Kernel XDP Mode (eBPF)", 'linux_ebpf_mode', tooltip_text="Use Case: Ultimate Linux Security. Hooks into the physical NIC to drop raw socket bypasses before the Linux kernel even sees them.")
        self._add_subtitle(card, "Hooks a custom eBPF/XDP program directly into the physical Network Interface Card (NIC) driver to drop rogue Layer 2 and raw socket traffic before the Linux Kernel processes it.")

        # Strict Inbound Shield
        self._add_switch_row(card, "Strict Inbound Shield", 'strict_inbound_shield', tooltip_text="Use Case: Unsafe networks. Hard-drops all incoming connections, rendering your device invisible to network scanners.")
        self._add_subtitle(card, "Overrides OS exceptions and hard-drops all unsolicited inbound connections (silently). May break local file sharing or game servers.")

        # Allow Local LAN Inbound
        self._add_switch_row(card, "↳ Allow Local Subnet (LAN) Inbound", 'inbound_lan_bypass', tooltip_text="Use Case: Servers & Embedded systems. Lets you SSH in from your local network while still dropping inbound connections from the outside internet.")
        self._add_subtitle(card, "Bypasses the Inbound Shield for local network IPs only. Allows remote admin (SSH/RDP) without opening to WAN. Automatically defaults to ON for embedded systems/servers, but you can strictly enforce OFF to isolate them completely.")

        # Inbound Notifications
        self._add_switch_row(card, "Inbound Block Notifications", 'inbound_notifications', tooltip_text="Use Case: Auditing. Visually tells you when someone is trying to port-scan or connect to your machine.")
        self._add_subtitle(card, "Show a popup notification when an inbound connection attempt is dropped.")

        # LAN Shield Pre-Shared Key Section
        psk_card = ctk.CTkFrame(card, fg_color=Colors.BG_DARK, corner_radius=8, border_width=1, border_color=Colors.BORDER_SUBTLE)
        psk_card.pack(fill="x", padx=Spacing.LG, pady=(Spacing.MD, Spacing.SM))
        
        # Header Row: Title & Quantum Badge
        psk_hdr = ctk.CTkFrame(psk_card, fg_color="transparent")
        psk_hdr.pack(fill="x", padx=Spacing.MD, pady=(Spacing.MD, Spacing.SM))

        ctk.CTkLabel(
            psk_hdr, text="🔑  LAN Shield Pre-Shared Key",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY
        ).pack(side="left")

        # Post-Quantum Protection Badge
        pq_badge = ctk.CTkLabel(
            psk_hdr, text="  🛡️ QUANTUM-PROOF AES-256 / SHA-512  ",
            font=(Fonts.FAMILY_PRIMARY[0], 10, Fonts.WEIGHT_BOLD),
            text_color=Colors.SUCCESS,
            fg_color=Colors.SUCCESS_DIM,
            corner_radius=6,
            height=24
        )
        pq_badge.pack(side="left", padx=(Spacing.SM, 0))

        psk_val = getattr(self.engine.db, 'get_setting', lambda k, d: d)("lan_shield_psk", "Waiting for LAN Shield initialization...")

        # Key display — clean monospace entry
        psk_entry = ctk.CTkEntry(
            psk_card, font=(Fonts.FAMILY_MONO[0], Fonts.SIZE_SM),
            height=38, state="normal",
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER_DEFAULT
        )
        psk_entry.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.SM))
        psk_entry.insert(0, psk_val)
        psk_entry.configure(state="readonly")

        # Action Buttons Toolbar
        action_bar = ctk.CTkFrame(psk_card, fg_color="transparent")
        action_bar.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.SM))

        def _copy_psk():
            """Copy PSK to clipboard with visual feedback."""
            try:
                self.clipboard_clear()
                self.clipboard_append(psk_entry.get())
                btn_copy.configure(text="Copied ✓", fg_color=Colors.SUCCESS_DIM, text_color=Colors.SUCCESS)
                self.after(2000, lambda: btn_copy.configure(
                    text="📋 Copy Key", fg_color=Colors.BG_ELEVATED, text_color=Colors.TEXT_PRIMARY
                ))
            except Exception:
                pass

        def _paste_psk():
            """Paste and validate a PSK from clipboard."""
            try:
                raw = self.clipboard_get().strip()
            except Exception:
                _show_psk_status("Nothing in clipboard", is_error=True)
                return
            if len(raw) not in (44, 88) or not raw.endswith('='):
                _show_psk_status("Invalid key — must be 44-char or 88-char Quantum key", is_error=True)
                return
            try:
                from netstrip.core.crypto_utils import Fernet
                Fernet(raw.encode('utf-8'))
            except Exception:
                _show_psk_status("Invalid Quantum key format", is_error=True)
                return
            psk_entry.configure(state="normal")
            psk_entry.delete(0, "end")
            psk_entry.insert(0, raw)
            psk_entry.configure(state="readonly")
            self.engine.db.set_setting("lan_shield_psk", raw)
            try:
                if hasattr(self.engine, 'lan_shield') and self.engine.lan_shield:
                    self.engine.lan_shield._psk = raw.encode('utf-8')
                    from netstrip.core.crypto_utils import Fernet as F
                    self.engine.lan_shield._fernet = F(raw.encode('utf-8'))
            except Exception:
                pass
            _show_psk_status("Quantum Key applied ✓ — LAN Shield updated", is_error=False)

        def _regen_psk():
            """Generate a fresh 512-bit Post-Quantum Fernet key."""
            try:
                from netstrip.core.crypto_utils import Fernet
                new_key = Fernet.generate_key(native_pq=True).decode('utf-8')
                psk_entry.configure(state="normal")
                psk_entry.delete(0, "end")
                psk_entry.insert(0, new_key)
                psk_entry.configure(state="readonly")
                self.engine.db.set_setting("lan_shield_psk", new_key)
                if hasattr(self.engine, 'lan_shield') and self.engine.lan_shield:
                    self.engine.lan_shield._psk = new_key.encode('utf-8')
                    self.engine.lan_shield._fernet = Fernet(new_key.encode('utf-8'))
                _show_psk_status("New Quantum key generated (512-bit) ✓ — share with paired devices", is_error=False)
            except Exception:
                _show_psk_status("Key generation failed", is_error=True)

        btn_copy = ctk.CTkButton(
            action_bar, text="📋 Copy Key", width=110, height=32,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BG_PANEL,
            text_color=Colors.TEXT_PRIMARY,
            command=_copy_psk
        )
        btn_copy.pack(side="left", padx=(0, Spacing.SM))

        btn_paste = ctk.CTkButton(
            action_bar, text="📥 Paste Key", width=110, height=32,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BG_PANEL,
            text_color=Colors.TEXT_PRIMARY,
            command=_paste_psk
        )
        btn_paste.pack(side="left", padx=(0, Spacing.SM))

        btn_regen = ctk.CTkButton(
            action_bar, text="🔄 Generate New Key", width=160, height=32,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
            fg_color=Colors.WARNING_DIM, hover_color=Colors.WARNING,
            text_color=Colors.TEXT_PRIMARY,
            command=_regen_psk
        )
        btn_regen.pack(side="left")

        # Status label for feedback messages
        psk_status = ctk.CTkLabel(
            psk_card, text="", height=20,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
            text_color=Colors.TEXT_SECONDARY
        )
        psk_status.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.XS))

        def _show_psk_status(msg, is_error=False):
            psk_status.configure(
                text=msg,
                text_color=Colors.DANGER if is_error else Colors.SUCCESS
            )
            self.after(4000, lambda: psk_status.configure(text=""))

        self._add_subtitle(psk_card, "Pair this 512-bit Post-Quantum key across your local devices for tamper-proof, zero-trust LAN lockdown orchestration. Immune to replay attacks and quantum decryption.", pady=(0, Spacing.MD))

        # Home Automation & IoT Integrations
        self._add_title(card, "Home Automation & IoT Integrations", icon="🏠", pady=(Spacing.LG, Spacing.SM))
        
        # Webhook URL
        webhook_url_row = ctk.CTkFrame(card, fg_color=Colors.BG_PANEL)
        webhook_url_row.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, 0))
        ctk.CTkLabel(webhook_url_row, text="IoT Webhook URL (e.g. Home Assistant)", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE), text_color=Colors.TEXT_PRIMARY).pack(side="left")
        
        webhook_url_val = getattr(self.engine.db, 'get_setting', lambda k, d: d)("iot_webhook_url", "")
        webhook_url_entry = ctk.CTkEntry(webhook_url_row, width=350, font=(Fonts.FAMILY_MONO[0], Fonts.SIZE_SM))
        webhook_url_entry.pack(side="right", padx=(Spacing.MD, 0))
        webhook_url_entry.insert(0, webhook_url_val)
        
        def save_webhook_url(e):
            if hasattr(self, '_wh_url_timer'): self.after_cancel(self._wh_url_timer)
            self._wh_url_timer = self.after(1000, lambda: self.engine.db.set_setting("iot_webhook_url", webhook_url_entry.get()))
        webhook_url_entry.bind("<KeyRelease>", save_webhook_url)

        # Webhook Secret
        webhook_sec_row = ctk.CTkFrame(card, fg_color=Colors.BG_PANEL)
        webhook_sec_row.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, 0))
        ctk.CTkLabel(webhook_sec_row, text="Webhook Bearer Token / Secret (Optional)", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE), text_color=Colors.TEXT_SECONDARY).pack(side="left")
        
        webhook_sec_val = getattr(self.engine.db, 'get_setting', lambda k, d: d)("iot_webhook_secret", "")
        webhook_sec_entry = ctk.CTkEntry(webhook_sec_row, width=350, font=(Fonts.FAMILY_MONO[0], Fonts.SIZE_SM), show="*")
        webhook_sec_entry.pack(side="right", padx=(Spacing.MD, 0))
        webhook_sec_entry.insert(0, webhook_sec_val)
        
        def save_webhook_sec(e):
            if hasattr(self, '_wh_sec_timer'): self.after_cancel(self._wh_sec_timer)
            self._wh_sec_timer = self.after(1000, lambda: self.engine.db.set_setting("iot_webhook_secret", webhook_sec_entry.get()))
        webhook_sec_entry.bind("<KeyRelease>", save_webhook_sec)
        
        # Continuous Telemetry Toggle
        telemetry_row = ctk.CTkFrame(card, fg_color=Colors.BG_PANEL)
        telemetry_row.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, 0))
        ctk.CTkLabel(telemetry_row, text="Continuous Webhook Telemetry Sync", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE), text_color=Colors.TEXT_PRIMARY).pack(side="left")
        
        telemetry_var = ctk.StringVar(value=getattr(self.engine.db, 'get_setting', lambda k, d: d)("iot_telemetry_enabled", "false"))
        def toggle_telemetry():
            val = telemetry_var.get()
            self.engine.db.set_setting("iot_telemetry_enabled", val)
            
        telemetry_switch = ctk.CTkSwitch(telemetry_row, text="", variable=telemetry_var, onvalue="true", offvalue="false", command=toggle_telemetry, progress_color=Colors.SUCCESS_DIM)
        telemetry_switch.pack(side="right")
        
        # Telemetry Interval
        interval_row = ctk.CTkFrame(card, fg_color=Colors.BG_PANEL)
        interval_row.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, 0))
        ctk.CTkLabel(interval_row, text="Telemetry Sync Interval (Seconds)", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM), text_color=Colors.TEXT_SECONDARY).pack(side="left")
        
        interval_val = getattr(self.engine.db, 'get_setting', lambda k, d: d)("iot_telemetry_interval", "10.0")
        interval_entry = ctk.CTkEntry(interval_row, width=80, font=(Fonts.FAMILY_MONO[0], Fonts.SIZE_SM))
        interval_entry.pack(side="right", padx=(Spacing.MD, 28)) # Aligned under the switch slightly
        interval_entry.insert(0, interval_val)
        
        def save_interval(e):
            if hasattr(self, '_wh_int_timer'): self.after_cancel(self._wh_int_timer)
            self._wh_int_timer = self.after(1000, lambda: self.engine.db.set_setting("iot_telemetry_interval", interval_entry.get()))
        interval_entry.bind("<KeyRelease>", save_interval)
        
        # Local IoT API Sensor
        local_api_row = ctk.CTkFrame(card, fg_color=Colors.BG_PANEL)
        local_api_row.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, 0))
        ctk.CTkLabel(local_api_row, text="Local Native Sensor (mDNS/REST API for HAOS)", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE), text_color=Colors.TEXT_PRIMARY).pack(side="left")
        
        local_api_var = ctk.StringVar(value=getattr(self.engine.db, 'get_setting', lambda k, d: d)("iot_local_sensor_enabled", "false"))
        def toggle_local_api():
            val = local_api_var.get()
            self.engine.db.set_setting("iot_local_sensor_enabled", val)
            if hasattr(self.engine, 'iot_local_api') and self.engine.iot_local_api:
                if val == "true":
                    self.engine.iot_local_api.start()
                else:
                    self.engine.iot_local_api.stop()
            if hasattr(self.engine, 'on_status') and self.engine.on_status:
                self.engine.on_status(f"Local Native IoT Sensor {'Enabled' if val == 'true' else 'Disabled'}")
            
        local_api_switch = ctk.CTkSwitch(local_api_row, text="", variable=local_api_var, onvalue="true", offvalue="false", command=toggle_local_api, progress_color=Colors.SUCCESS_DIM)
        local_api_switch.pack(side="right")
        
        # Local IoT API Port
        local_port_row = ctk.CTkFrame(card, fg_color=Colors.BG_PANEL)
        local_port_row.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, 0))
        ctk.CTkLabel(local_port_row, text="Local API Port (Default: 8080)", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM), text_color=Colors.TEXT_SECONDARY).pack(side="left")
        
        local_port_val = getattr(self.engine.db, 'get_setting', lambda k, d: d)("iot_local_sensor_port", "8080")
        local_port_entry = ctk.CTkEntry(local_port_row, width=80, font=(Fonts.FAMILY_MONO[0], Fonts.SIZE_SM))
        local_port_entry.pack(side="right", padx=(Spacing.MD, 28))
        local_port_entry.insert(0, local_port_val)
        
        def save_local_port(e):
            if hasattr(self, '_local_port_timer'): self.after_cancel(self._local_port_timer)
            self._local_port_timer = self.after(1000, lambda: self.engine.db.set_setting("iot_local_sensor_port", local_port_entry.get()))
        local_port_entry.bind("<KeyRelease>", save_local_port)
        
        # Google Nest Home
        nest_row = ctk.CTkFrame(card, fg_color=Colors.BG_PANEL)
        nest_row.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, Spacing.SM))
        ctk.CTkLabel(nest_row, text="Google Nest Home Dashboard Broadcast", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE), text_color=Colors.TEXT_PRIMARY).pack(side="left")
        
        nest_var = ctk.StringVar(value=getattr(self.engine.db, 'get_setting', lambda k, d: d)("iot_nest_sensor_enabled", "false"))
        def toggle_nest():
            val = nest_var.get()
            self.engine.db.set_setting("iot_nest_sensor_enabled", val)
            
        nest_switch = ctk.CTkSwitch(nest_row, text="", variable=nest_var, onvalue="true", offvalue="false", command=toggle_nest, progress_color=Colors.SUCCESS_DIM)
        nest_switch.pack(side="right")

        self._add_subtitle(card, "Sends live JSON telemetry (Stats, Modes, Active Connections) to your Webhook endpoint to build custom Dashboards on external monitors via HAOS or Node-RED. Google Nest Home integration pushes active sensor payloads to compatible Cast displays.", pady=(0, Spacing.LG))

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

        self._btn_save_sched = ctk.CTkButton(
            row, text="Save Schedule", width=100, height=32, corner_radius=8,
            fg_color=Colors.ACCENT_PRIMARY, hover_color=Colors.ACCENT_LIGHT,
            text_color=Colors.TEXT_PRIMARY,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            command=self._save_schedule,
        )
        self._btn_save_sched.pack(side="right")

    def _save_schedule(self):
        import re
        start_val = self._start_entry.get().strip()
        end_val = self._end_entry.get().strip()
        time_pattern = r'^([01]\d|2[0-3]):[0-5]\d$'
        if not re.match(time_pattern, start_val) or not re.match(time_pattern, end_val):
            if hasattr(self, '_btn_save_sched'):
                self._btn_save_sched.configure(text="Invalid Format", fg_color=Colors.DANGER)
                self.after(2000, lambda: self._btn_save_sched.configure(text="Save Schedule", fg_color=Colors.ACCENT_PRIMARY))
            return
        self.engine.db.set_setting("killswitch_start", start_val)
        self.engine.db.set_setting("killswitch_end", end_val)
        if hasattr(self, '_btn_save_sched'):
            self._btn_save_sched.configure(text="Saved ✓", fg_color=Colors.SUCCESS_DIM)
            self.after(2000, lambda: self._btn_save_sched.configure(text="Save Schedule", fg_color=Colors.ACCENT_PRIMARY))
        if hasattr(self.engine, 'on_status') and self.engine.on_status:
            self.engine.on_status(f"Killswitch Schedule updated: {start_val} to {end_val}")

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
                # Hot-reload the engine with imported settings and rules
                if hasattr(self.engine, 'blocklist'):
                    self.engine.blocklist.load_all()
                if hasattr(self.engine, 'classifier'):
                    self.engine.classifier._domain_cache.clear()
                    if hasattr(self.engine.classifier, '_ip_cache'):
                        self.engine.classifier._ip_cache.clear()
                from tkinter import messagebox
                messagebox.showinfo("Import Successful", "Profile successfully imported and applied!")
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Import Failed", f"Failed to import profile:\n{e}")

    def _factory_reset(self):
        import customtkinter as ctk
        dialog = ctk.CTkToplevel(self)
        dialog.title('⚠ Factory Reset — Confirm')
        dialog.configure(fg_color=Colors.BG_DARKEST)
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.attributes("-topmost", True)
        dialog.resizable(False, False)
        
        # Center it reliably over the main application
        from netstrip.gui.utils import center_window, apply_window_icon
        apply_window_icon(dialog)
        center_window(dialog, 460, 270, parent=self.master)
        
        ctk.CTkLabel(dialog, text='⚠  FACTORY RESET', font=(Fonts.FAMILY_PRIMARY[0], 20, 'bold'), text_color=Colors.DANGER).pack(pady=(20, 6))
        ctk.CTkLabel(dialog, text='Are you sure? This action is irreversible.', font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, 'bold'), text_color=Colors.TEXT_PRIMARY).pack(pady=(0, 6))
        ctk.CTkLabel(dialog, text='All user rules, settings, connection logs, custom blocklists,\nand online list registrations will be permanently deleted.\nMake sure you have exported a Backup Profile first!\n\nNetStrip will restart automatically after the wipe.', font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM), text_color=Colors.TEXT_SECONDARY, justify='center').pack(pady=(0, 16))
        
        btn_frame = ctk.CTkFrame(dialog, fg_color='transparent')
        btn_frame.pack(pady=(0, 12))
        
        def on_confirm():
            dialog.destroy()
            self._do_factory_wipe()
            
        ctk.CTkButton(btn_frame, text='Cancel', width=120, height=36, fg_color=Colors.BG_ELEVATED, hover_color=Colors.BORDER_DEFAULT, text_color=Colors.TEXT_PRIMARY, command=dialog.destroy).pack(side='left', padx=10)
        ctk.CTkButton(btn_frame, text='WIPE & RESTART', width=140, height=36, fg_color=Colors.DANGER, hover_color='#f43f5e', text_color='white', font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, 'bold'), command=on_confirm).pack(side='right', padx=10)
        
    def _do_factory_wipe(self):
        # 1. Thread-safe wipe of database and cache
        try:
            self.engine.db.factory_reset()
        except Exception as e:
            logger.error(f"Factory reset DB wipe error: {e}")
            
        # 2. Clean custom blocklists and custom updater sources (preserving default bundled lists)
        try:
            import os, json
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            lists_dir = os.path.join(base_dir, 'data', 'lists')
            sources_file = os.path.join(base_dir, 'data', 'updater_sources.json')
            
            if os.path.exists(sources_file):
                with open(sources_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                original_len = len(data.get('sources', []))
                data['sources'] = [s for s in data.get('sources', []) if not s.get('name', '').startswith('Custom: ')]
                
                if len(data['sources']) < original_len:
                    with open(sources_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
                        
            if os.path.exists(lists_dir):
                for fname in os.listdir(lists_dir):
                    if fname.startswith("Custom_") or fname == "updater_state.json":
                        try:
                            os.remove(os.path.join(lists_dir, fname))
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"Failed to clean custom blocklists: {e}")
            
        # 3. Gracefully stop engine subsystems (DNS unhook, sockets unbind)
        try:
            self.engine.stop()
        except Exception as e:
            logger.error(f"Engine stop during factory wipe: {e}")
            
        # 4. Stop DB background writer
        try:
            self.engine.db.stop()
        except Exception:
            pass

        # 5. Clean IPC socket if exposed in main
        try:
            import sys
            main_mod = sys.modules.get('__main__') or sys.modules.get('main')
            if main_mod and hasattr(main_mod, '_ipc_socket') and main_mod._ipc_socket:
                main_mod._ipc_socket.close()
        except Exception:
            pass
            
        # 6. Spawn fresh restart process cleanly
        import sys, os, subprocess
        creationflags = 0
        if os.name == 'nt':
            creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            
        if getattr(sys, 'frozen', False):
            exe = sys.executable
            args = [exe] + [a for a in sys.argv[1:] if a != "--parent-pid"]
            cwd = os.path.dirname(os.path.abspath(exe))
        else:
            exe = sys.executable
            main_script = os.path.abspath(sys.argv[0])
            args = [exe, main_script] + [a for a in sys.argv[1:] if a != main_script and a != "--parent-pid"]
            cwd = os.path.dirname(main_script)
            
        if self.engine.platform.is_admin() and "--elevated" not in args:
            args.append("--elevated")
            
        try:
            subprocess.Popen(args, cwd=cwd, creationflags=creationflags, close_fds=(os.name != 'nt'))
        except Exception:
            subprocess.Popen(args, cwd=cwd, creationflags=creationflags)
        
        # Kill current process forcefully to ensure clean restart
        os._exit(0)
    def _build_analytics_card(self):
        card = ctk.CTkFrame(self.scroll_frame, **CTK_FRAME_STYLE)
        card.pack(fill="x", pady=(0, Spacing.MD))

        ctk.CTkLabel(
            card, text="Analytics",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))

        self._add_switch_row(card, "Send Anonymous Usage Statistics", 'analytics_opt_in', tooltip_text="Opt-in only. Sends minimal, non-identifying data (version, OS type, aggregate block counts) to help improve NetStrip. No IPs, domains, or personal data is ever collected.")
        self._add_subtitle(card, "Disabled by default. When enabled, sends anonymous aggregate statistics (app version, OS type, total block/allow counts) once every 24 hours. No IP addresses, domain names, DNS queries, or personally identifiable information is ever collected or transmitted.")

        # Bottom padding
        ctk.CTkFrame(card, fg_color=Colors.BG_PANEL, height=Spacing.SM).pack()

    def _build_about_card(self):
        from netstrip import __version__
        card = ctk.CTkFrame(self.scroll_frame, **CTK_FRAME_STYLE)
        card.pack(fill="x", pady=(0, Spacing.MD))

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
        credits_frame = ctk.CTkFrame(self.scroll_frame, **CTK_FRAME_STYLE)
        credits_frame.pack(fill="x", pady=(0, Spacing.MD))
        
        ctk.CTkLabel(
            credits_frame, text="OPEN SOURCE CREDITS & INTEGRATED FILTER LISTS",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(anchor="center", pady=(Spacing.MD, Spacing.XS))
        
        credits_sections = [
            ("Core Architecture & Libraries", "Python 3 • CustomTkinter (Tom Schimansky) • dnslib (PaulC) • psutil (Giampaolo Rodola)\neBPF / BCC (iovisor) • SQLite3 • Dulwich • Cryptography / Fernet • Requests"),
            ("Ad & Privacy Blocklists", "AdGuard (Base, Tracking Protection, Mobile Ads, International Registry)\nHaGeZi DNS Blocklists (Pro Plus, Ultimate, DoH/DoT Tracker, OEM Telemetry Feeds)\nOISD Big (sjhgvr) • Steven Black Hosts (Unified) • AdAway Default\nDan Pollock (someonewhocares.org) • Peter Lowe's Ad & Tracking Server List (pgl.yoyo.org)\nEasyList (Germany, Italy, Dutch, Arabic) • YousList Korean"),
            ("Security & Threat Intelligence", "URLhaus & Feodo Tracker Botnet C2 (abuse.ch) • WindowsSpyBlocker (crazy-max)\nDShield Suspicious Domains (SANS ISC) • PhishTank (phishing.army) • v2fly Domain Community"),
        ]
        
        for title, text in credits_sections:
            ctk.CTkLabel(
                credits_frame, text=title,
                font=(Fonts.FAMILY_PRIMARY[0], 10, Fonts.WEIGHT_BOLD),
                text_color=Colors.ACCENT_PRIMARY,
            ).pack(anchor="center", pady=(Spacing.XS, 0), padx=Spacing.LG)
            
            lbl_credits = ctk.CTkLabel(
                credits_frame, text=text,
                font=(Fonts.FAMILY_PRIMARY[0], 9),
                text_color=Colors.TEXT_TERTIARY,
                justify="center",
                wraplength=380
            )
            lbl_credits.pack(anchor="center", pady=(0, Spacing.XS), padx=Spacing.LG)
            
            def _update_cred_wrap(event, l=lbl_credits):
                try:
                    if l.winfo_exists():
                        l.configure(wraplength=max(180, min(event.width - 48, 420)))
                except Exception:
                    pass
            credits_frame.bind("<Configure>", _update_cred_wrap, add="+")
            
        # Bottom spacer
        ctk.CTkFrame(credits_frame, height=Spacing.SM, fg_color="transparent").pack()

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

