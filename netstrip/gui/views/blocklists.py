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
from netstrip.gui.utils import enable_smooth_scrolling


#  AppRulesView — Pending Approvals + User Rules

# ═══════════════════════════════════════════════════
#  BlocklistView
# ═══════════════════════════════════════════════════
class BlocklistView(ctk.CTkFrame):
    """Blocklist stats grid and domain search interface."""

    def __init__(self, master, engine, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PANEL, **kwargs)
        self.engine = engine
        self._destroyed = False
        self._active_category_filter = None
        self._category_ui_elements = {}

        # Main scrollable container for the entire tab
        self._main_scroll = ctk.CTkScrollableFrame(self, fg_color=Colors.BG_PANEL)
        self._main_scroll.pack(fill="both", expand=True)
        enable_smooth_scrolling(self._main_scroll)

        # Header Row
        header_row = ctk.CTkFrame(self._main_scroll, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, Spacing.MD))

        ctk.CTkLabel(
            header_row, text="Filter Manager",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XL, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")
        
        self._btn_update = ctk.CTkButton(
            header_row, text=f"{Icons.SHIELD} Update Blocklists",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
            fg_color=Colors.ACCENT_PRIMARY,
            hover_color=Colors.ACCENT_LIGHT,
            height=32,
            corner_radius=6,
            command=self._on_manual_update_click,
        )
        self._btn_update.pack(side="right")
        
        self._update_status_lbl = ctk.CTkLabel(
            header_row, text="",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
            text_color=Colors.TEXT_SECONDARY,
        )
        self._update_status_lbl.pack(side="right", padx=Spacing.MD)
        
        # Search Bar (Top)
        self._build_search_bar()
        
        # Add Custom Rule Bar
        self._build_add_rule_bar()

        # Compact Stats Grid (Indexed Categories)
        self._build_stats_grid()

        # Online Threat Feeds & Sources Manager
        self._build_sources_section()

        # Search Results Area with dedicated inner scrollbar
        self._build_results_area()
        
        # Bind Map event to refresh stats grid when tab becomes visible
        self.bind("<Map>", lambda e: self._refresh_stats_grid() if e.widget is self else None)
        
        # Register blocklist reload listener
        if hasattr(self.engine.blocklist, 'add_loaded_callback'):
            self.engine.blocklist.add_loaded_callback(self._on_blocklist_data_reloaded)
            
        # Start periodic poll to update counts as background blocklist loading completes
        self._poll_loading()

    def _on_manual_update_click(self):
        if getattr(self.engine.updater, 'is_updating', False):
            return
        self._btn_update.configure(state="disabled", text="Updating...")
        self._update_status_lbl.configure(text="Connecting to blocklist mirrors...")
        
        def on_progress(current, total, name):
            if not self._destroyed:
                def update_prog():
                    self._update_status_lbl.configure(text=f"Syncing {current}/{total}: {name[:24]}...")
                self.after(0, update_prog)

        def on_complete(updated_count):
            if not self._destroyed:
                def update_ui():
                    self._btn_update.configure(state="normal", text=f"{Icons.SHIELD} Update Blocklists")
                    self._update_status_lbl.configure(text=f"Updated ({updated_count} lists synced)")
                    self._refresh_stats_grid()
                    self._do_search()
                self.after(0, update_ui)
                
        self.engine.updater.check_and_update(force=True, on_complete=on_complete, on_progress=on_progress)

    def _on_blocklist_data_reloaded(self):
        if getattr(self, '_destroyed', False):
            return
        try:
            self.after(0, self._on_blocklist_data_reloaded_ui)
        except Exception:
            pass

    def _on_blocklist_data_reloaded_ui(self):
        if getattr(self, '_destroyed', False):
            return
        self._refresh_stats_grid()
        if self._active_category_filter or (hasattr(self, '_search_entry') and self._search_entry.get().strip()):
            self._do_search()

    def _poll_loading(self):
        if getattr(self, '_destroyed', False):
            return

        self._refresh_stats_grid()

        if getattr(self.engine.blocklist, 'is_loading', False):
            self.after(500, self._poll_loading)

    def _build_add_rule_bar(self):
        add_row = ctk.CTkFrame(self._main_scroll, fg_color=Colors.BG_PANEL)
        add_row.pack(fill="x", pady=(0, Spacing.LG))
        
        self._action_var = ctk.StringVar(value="Block")
        self._action_seg = ctk.CTkSegmentedButton(
            add_row, values=["Block", "Allow"], variable=self._action_var,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
            selected_color=Colors.DANGER, selected_hover_color="#be123c",
            unselected_color=Colors.BG_ELEVATED, unselected_hover_color=Colors.BG_DARK,
            height=40
        )
        self._action_seg.pack(side="left", padx=(0, Spacing.SM))

        def on_action_change(*args):
            if self._action_var.get() == "Block":
                self._action_seg.configure(selected_color=Colors.DANGER, selected_hover_color="#be123c")
                btn_add.configure(text="Add Block", fg_color=Colors.DANGER, hover_color="#be123c")
                self._add_entry.configure(placeholder_text="Add domain to block or paste a .txt list URL")
            else:
                self._action_seg.configure(selected_color=Colors.SUCCESS_DIM, selected_hover_color=Colors.SUCCESS)
                btn_add.configure(text="Add Allow", fg_color=Colors.SUCCESS_DIM, hover_color=Colors.SUCCESS)
                self._add_entry.configure(placeholder_text="Add domain to whitelist")
                
        self._action_var.trace_add("write", on_action_change)

        self._add_entry = ctk.CTkEntry(
            add_row, placeholder_text="Add domain to block or paste a .txt list URL",
            height=40,
            **CTK_ENTRY_STYLE,
        )
        self._add_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.SM))
        self._add_entry.bind("<Return>", lambda e: self._add_custom_rule())

        btn_add = ctk.CTkButton(
            add_row, text="Add Block",
            width=100, height=40, corner_radius=0,
            fg_color=Colors.DANGER,
            hover_color="#be123c",
            text_color=Colors.TEXT_PRIMARY,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
            command=self._add_custom_rule,
        )
        btn_add.pack(side="right")

    def _add_custom_rule(self):
        pattern = self._add_entry.get().strip()
        if not pattern:
            return
            
        action = "block" if self._action_var.get() == "Block" else "allow"

        # Check if it is a URL to an online list
        if pattern.startswith("http://") or pattern.startswith("https://"):
            self._add_entry.delete(0, 'end')
            if hasattr(self.engine, 'on_status') and self.engine.on_status:
                self.engine.on_status(f"Downloading new online list...")
                
            import threading
            import urllib.request
            import os, json
            
            def download_list():
                try:
                    req = urllib.request.Request(pattern, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=15) as response:
                        content = response.read()
                        
                    name = pattern.split("/")[-1]
                    if not name or name == "hosts":
                        name = pattern.split("/")[-2] + "_list"
                        
                    # Intelligent Category Scanning
                    detected_category = "user_blocked"
                    if action == "block":
                        url_lower = pattern.lower()
                        # Comprehensive Heuristic Keywords
                        kw_telemetry = ["telemetry", "spy", "metrics", "winoffice", "analytics", "diagnostic", "data-collection", "logger", "crash"]
                        kw_tracker = ["tracker", "tracking", "track", "pixel", "fingerprint", "beacon", "stat", "audience"]
                        kw_malware = ["malware", "phish", "ransom", "botnet", "c2", "command-and-control", "crypto", "miner", "exploit", "scam", "fraud", "virus", "trojan", "malicious"]
                        kw_system = ["system", "os", "native", "windows", "apple", "linux", "ubuntu", "debian", "android", "ios", "microsoft", "mac"]
                        
                        # Layer 1: URL Heuristics
                        if any(k in url_lower for k in kw_telemetry):
                            detected_category = "telemetry"
                        elif any(k in url_lower for k in kw_tracker):
                            detected_category = "tracker"
                        elif any(k in url_lower for k in kw_malware):
                            detected_category = "malware"
                        elif any(k in url_lower for k in kw_system):
                            detected_category = "system"
                        else:
                            # Layer 2: Content/Header Heuristics
                            try:
                                header_sample = content[:1000].decode('utf-8', errors='ignore').lower()
                                if any(k in header_sample for k in kw_telemetry):
                                    detected_category = "telemetry"
                                elif any(k in header_sample for k in kw_tracker):
                                    detected_category = "tracker"
                                elif any(k in header_sample for k in kw_malware):
                                    detected_category = "malware"
                                elif any(k in header_sample for k in kw_system):
                                    detected_category = "system"
                            except Exception:
                                pass
                                
                    final_category = "whitelist" if action == "allow" else detected_category
                        
                    # Save to updater_sources.json
                    sources_file = os.path.join(self.engine.blocklist.lists_dir, '..', 'updater_sources.json')
                    if os.path.exists(sources_file):
                        with open(sources_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                        new_source = {
                            "name": "Custom: " + name,
                            "url": pattern,
                            "format": "domains" if ".txt" in pattern else "hosts",
                            "category": final_category,
                            "enabled": True
                        }
                        data.setdefault('sources', []).append(new_source)
                        
                        with open(sources_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2)
                            
                    # Save the downloaded file directly to lists dir
                    safe_name = new_source['name'].replace(' ', '_').replace('/', '_').replace(':', '')
                    file_prefix = f"{final_category}_" if action == "block" else "whitelist_"
                    target_file = os.path.join(self.engine.blocklist.lists_dir, f"{file_prefix}{safe_name}.txt")
                    with open(target_file, 'wb') as f:
                        f.write(content)
                        
                    # Reload core memory with new source
                    self.engine.blocklist.load_all()
                    
                    if not self._destroyed:
                        def on_success():
                            self._refresh_stats_grid(f"Added permanent blocklist: {name}")
                            sources = self.engine.blocklist.get_updater_sources()
                            count = len(sources) if sources else 36
                            if not self._sources_expanded:
                                self._btn_toggle_sources.configure(text=f"▼ Show Online Feeds ({count})")
                            else:
                                self._populate_sources_list()
                            if self._active_category_filter or (hasattr(self, '_search_entry') and self._search_entry.get().strip()):
                                self._do_search()
                        self.after(0, on_success)
                        
                except Exception as e:
                    if hasattr(self.engine, 'on_status') and self.engine.on_status:
                        self.engine.on_status(f"Failed to add online list: {e}")
            
            threading.Thread(target=download_list, daemon=True).start()
            return

        # Simple validation: clean up domain
        pattern = pattern.lower().replace('http://', '').replace('https://', '').split('/')[0]

        # Add to DB
        mode_scope = "PARANOID" if self.engine.classifier.mode.name.upper() == "PARANOID" else "STANDARD"
        self.engine.db.add_user_rule({
            'pattern': pattern,
            'action': action,
            'scope': 'global',
            'category': f'user_{action}ed',
            'note': 'Added from Lists tab',
            'mode_scope': mode_scope
        })

        # Sync Blocklist memory
        if hasattr(self.engine.blocklist, 'sync_user_rules'):
            self.engine.blocklist.sync_user_rules(self.engine.db.get_user_rules(mode_scope=mode_scope))

        self._add_entry.delete(0, 'end')
        
        # Show feedback
        if hasattr(self.engine, 'on_status') and self.engine.on_status:
            self.engine.on_status(f"Added custom {action} rule for {pattern}")
            
        self._refresh_stats_grid()
            
        self._search_entry.delete(0, 'end')
        self._search_entry.insert(0, pattern)
        self._do_search()
        
    def _get_category_count(self, cat_enum):
        from netstrip.core.modes import ConnectionCategory
        cat_val = getattr(cat_enum, 'value', str(cat_enum)).lower()
        if cat_val.startswith('connectioncategory.'):
            cat_val = cat_val.split('.')[-1].lower()

        if cat_enum == ConnectionCategory.USER_ALLOWED or cat_val == 'user_allowed':
            whitelist_size = len(getattr(self.engine.blocklist, 'whitelist', set()))
            app_whitelist_size = len(getattr(self.engine.blocklist, 'app_whitelist', set()))
            return whitelist_size + app_whitelist_size

        if cat_enum == ConnectionCategory.USER_BLOCKED or cat_val == 'user_blocked':
            blacklist_size = len(getattr(self.engine.blocklist, 'blacklist', {}))
            app_blacklist_size = len(getattr(self.engine.blocklist, 'app_blacklist', set()))
            return blacklist_size + app_blacklist_size

        stats = getattr(self.engine.blocklist, 'stats', {})
        metadata = getattr(self.engine.blocklist, 'sources_metadata', {})

        cnt = 0
        for k, v in stats.items():
            k_val = getattr(k, 'value', str(k)).lower()
            if k_val.startswith('connectioncategory.'):
                k_val = k_val.split('.')[-1].lower()
            if k == cat_enum or k_val == cat_val or (k_val in ('ad', 'ads') and cat_val in ('ad', 'ads')):
                cnt += v

        if cnt == 0 and metadata:
            for k, sources in metadata.items():
                k_val = getattr(k, 'value', str(k)).lower()
                if k_val.startswith('connectioncategory.'):
                    k_val = k_val.split('.')[-1].lower()
                if k == cat_enum or k_val == cat_val or (k_val in ('ad', 'ads') and cat_val in ('ad', 'ads')):
                    cnt += sum(s.get('size', 0) for s in sources if isinstance(s, dict))

        if cnt == 0:
            domain_map = getattr(self.engine.blocklist, 'domain_map', {})
            if domain_map:
                cnt = sum(
                    1 for v in domain_map.values()
                    if (v == cat_enum or getattr(v, 'value', str(v)).lower().split('.')[-1] == cat_val)
                )

        return cnt

    def _refresh_stats_grid(self, msg=None):
        if msg and hasattr(self.engine, 'on_status') and self.engine.on_status:
            self.engine.on_status(msg)
            
        try:
            for cat_enum, (card, inner, lbl_count) in getattr(self, '_category_ui_elements', {}).items():
                cnt = self._get_category_count(cat_enum)
                lbl_count.configure(text=f"{cnt:,}")
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error refreshing stats grid: {e}")

    def _build_search_bar(self):
        search_row = ctk.CTkFrame(self._main_scroll, fg_color=Colors.BG_PANEL)
        search_row.pack(fill="x", pady=(0, Spacing.LG))

        self._search_entry = ctk.CTkEntry(
            search_row, placeholder_text="Search indexed domains... (e.g. doubleclick.net)",
            height=40,
            **CTK_ENTRY_STYLE,
        )
        self._search_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.SM))
        self._search_entry.bind("<Return>", lambda e: self._do_search())

        btn_search = ctk.CTkButton(
            search_row, text=Icons.SEARCH,
            width=44, height=40, corner_radius=0,
            fg_color=Colors.ACCENT_PRIMARY,
            hover_color=Colors.ACCENT_LIGHT,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG),
            command=self._do_search,
        )
        btn_search.pack(side="right")

    def _build_stats_grid(self):
        self._stats_container = ctk.CTkFrame(self._main_scroll, fg_color="transparent")
        self._stats_container.pack(fill="x", pady=0)
        
        ctk.CTkLabel(
            self._stats_container, text="Indexed Categories",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.SM))
        
        grid_frame = ctk.CTkFrame(self._stats_container, fg_color=Colors.BG_PANEL)
        grid_frame.pack(fill="x", pady=(0, Spacing.LG))
        grid_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        from netstrip.core.modes import ConnectionCategory
        
        categories_to_display = [
            ConnectionCategory.AD,
            ConnectionCategory.TRACKER,
            ConnectionCategory.TELEMETRY,
            ConnectionCategory.MALWARE,
            ConnectionCategory.SYSTEM,
            ConnectionCategory.UPDATE,
            ConnectionCategory.SECURITY,
            ConnectionCategory.ESSENTIAL,
            ConnectionCategory.USER_ALLOWED,
            ConnectionCategory.USER_BLOCKED,
        ]

        for idx, category in enumerate(categories_to_display):
            card = ctk.CTkFrame(grid_frame, **CTK_FRAME_STYLE)
            card.grid(
                row=idx // 4, column=idx % 4,
                sticky="ew", padx=Spacing.XS, pady=Spacing.XS,
            )
            card.configure(cursor="hand2")

            # Colored top bar
            ctk.CTkFrame(
                card, height=3,
                fg_color=get_category_color(category),
                corner_radius=0,
            ).pack(fill="x")

            inner = ctk.CTkFrame(card, fg_color=Colors.BG_PANEL)
            inner.pack(fill="both", expand=True, padx=Spacing.SM, pady=Spacing.SM)

            # Icon + label
            lbl_title = ctk.CTkLabel(
                inner,
                text=f"{get_category_icon(category)} {get_category_label(category).upper()}",
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
                text_color=Colors.TEXT_PRIMARY,
            )
            lbl_title.pack(anchor="w")
            
            total_size = self._get_category_count(category)

            lbl_count = ctk.CTkLabel(
                inner,
                text=f"{total_size:,}",
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, Fonts.WEIGHT_BOLD),
                text_color=get_category_color(category),
            )
            lbl_count.pack(anchor="w", pady=(2, 0))
            
            lbl_desc = ctk.CTkLabel(
                inner,
                text="domains loaded",
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
                text_color=Colors.TEXT_TERTIARY,
            )
            lbl_desc.pack(anchor="w")
            
            self._category_ui_elements[category] = (card, inner, lbl_count)

            # Bindings
            def on_enter(e, cat_enum=category):
                if self._active_category_filter != cat_enum.value:
                    c, i, _ = self._category_ui_elements[cat_enum]
                    c.configure(fg_color=Colors.BG_ELEVATED)
                    i.configure(fg_color=Colors.BG_ELEVATED)

            def on_leave(e, cat_enum=category):
                if self._active_category_filter != cat_enum.value:
                    c, i, _ = self._category_ui_elements[cat_enum]
                    c.configure(fg_color=Colors.BG_PANEL)
                    i.configure(fg_color=Colors.BG_PANEL)

            def on_click(e, cat_enum=category):
                if self._active_category_filter == cat_enum.value:
                    self._active_category_filter = None
                else:
                    self._active_category_filter = cat_enum.value
                
                # Update visual state of all cards
                for kv_enum, (c, i, _) in self._category_ui_elements.items():
                    if kv_enum.value == self._active_category_filter:
                        c.configure(fg_color="#1e1e2d") # Bright active highlight
                        i.configure(fg_color="#1e1e2d")
                    else:
                        c.configure(fg_color=Colors.BG_PANEL)
                        i.configure(fg_color=Colors.BG_PANEL)
                
                self._do_search()

            for widget in (card, inner, lbl_title, lbl_count, lbl_desc):
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)
                widget.bind("<Button-1>", on_click)

    def _build_sources_section(self):
        """Construct the interactive online threat feeds & blocklist sources manager."""
        self._sources_container = ctk.CTkFrame(self._main_scroll, fg_color="transparent")
        self._sources_container.pack(fill="x", pady=(0, Spacing.LG))

        header_frame = ctk.CTkFrame(self._sources_container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, Spacing.SM))

        ctk.CTkLabel(
            header_frame, text="Threat Intelligence & Online Feeds",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        self._sources_expanded = False
        self._btn_toggle_sources = ctk.CTkButton(
            header_frame, text="▼ Show Online Feeds (36)",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS, Fonts.WEIGHT_BOLD),
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BG_PANEL,
            text_color=Colors.TEXT_PRIMARY,
            height=28, width=180, corner_radius=6,
            command=self._toggle_sources_view
        )
        self._btn_toggle_sources.pack(side="right")

        self._sources_list_frame = ctk.CTkScrollableFrame(
            self._sources_container, fg_color=Colors.BG_DARK,
            height=280, corner_radius=6, border_width=1, border_color=Colors.BORDER_SUBTLE
        )
        enable_smooth_scrolling(self._sources_list_frame)

    def _toggle_sources_view(self):
        if self._sources_expanded:
            self._sources_list_frame.pack_forget()
            sources = self.engine.blocklist.get_updater_sources()
            count = len(sources) if sources else 36
            self._btn_toggle_sources.configure(text=f"▼ Show Online Feeds ({count})")
            self._sources_expanded = False
        else:
            self._sources_list_frame.pack(fill="x", pady=(Spacing.XS, 0))
            self._populate_sources_list()
            self._btn_toggle_sources.configure(text="▲ Hide Online Feeds")
            self._sources_expanded = True

    def _populate_sources_list(self):
        sources = self.engine.blocklist.get_updater_sources()
        from netstrip.core.modes import ConnectionCategory
        from netstrip.gui.theme import get_category_color, get_category_label, get_category_icon

        if not hasattr(self, '_sources_row_pool'):
            self._sources_row_pool = []

        if not sources:
            for item in self._sources_row_pool:
                item['frame'].pack_forget()
            if not hasattr(self, '_lbl_no_sources'):
                self._lbl_no_sources = ctk.CTkLabel(
                    self._sources_list_frame, text="No online sources configured.",
                    font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, "italic"),
                    text_color=Colors.TEXT_TERTIARY
                )
            self._lbl_no_sources.pack(pady=Spacing.MD)
            return
        else:
            if hasattr(self, '_lbl_no_sources'):
                self._lbl_no_sources.destroy()
                delattr(self, '_lbl_no_sources')

        # Grow pool if needed
        while len(self._sources_row_pool) < len(sources):
            idx = len(self._sources_row_pool)
            row_bg = "#181824" if idx % 2 == 0 else "#14141f"
            row = ctk.CTkFrame(self._sources_list_frame, fg_color=row_bg, corner_radius=6, height=42)
            row.pack_propagate(False)

            left_frame = ctk.CTkFrame(row, fg_color="transparent")
            left_frame.pack(side="left", fill="both", expand=True, padx=Spacing.SM)

            dot_lbl = ctk.CTkLabel(
                left_frame, text="●", font=(Fonts.FAMILY_PRIMARY[0], 12),
                text_color=Colors.SUCCESS, width=16
            )
            dot_lbl.pack(side="left", padx=(0, Spacing.XS))

            info_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True)

            name_lbl = ctk.CTkLabel(
                info_frame, text="",
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
                text_color=Colors.TEXT_PRIMARY,
                anchor="w"
            )
            name_lbl.pack(anchor="w")

            sub_lbl = ctk.CTkLabel(
                info_frame, text="",
                font=(Fonts.FAMILY_PRIMARY[0], 10),
                text_color=Colors.TEXT_TERTIARY,
                anchor="w"
            )
            sub_lbl.pack(anchor="w")

            badge = ctk.CTkLabel(
                row, text="",
                font=(Fonts.FAMILY_PRIMARY[0], 10, Fonts.WEIGHT_BOLD),
                fg_color=Colors.BG_ELEVATED,
                corner_radius=8,
                height=22,
                width=90
            )
            badge.pack(side="left", padx=Spacing.MD)

            switch_var = ctk.BooleanVar(value=True)
            switch = ctk.CTkSwitch(
                row, text="", variable=switch_var,
                width=45, height=22,
                **CTK_SWITCH_STYLE
            )
            switch.pack(side="right", padx=Spacing.MD)

            self._sources_row_pool.append({
                'frame': row,
                'dot_lbl': dot_lbl,
                'name_lbl': name_lbl,
                'sub_lbl': sub_lbl,
                'badge': badge,
                'switch_var': switch_var,
                'switch': switch
            })

        for idx, src in enumerate(sources):
            item = self._sources_row_pool[idx]
            name = src.get('name', 'Unknown Source')
            url = src.get('url', '')
            cat_str = src.get('category', 'ad')
            enabled = src.get('enabled', True)
            is_local = src.get('is_local', False)
            local_size = src.get('local_size', 0)

            row_bg = "#181824" if idx % 2 == 0 else "#14141f"
            item['frame'].configure(fg_color=row_bg)

            status_dot_color = Colors.SUCCESS if (enabled and is_local) else (Colors.WARNING if enabled else Colors.TEXT_TERTIARY)
            item['dot_lbl'].configure(text_color=status_dot_color)

            item['name_lbl'].configure(
                text=name,
                text_color=Colors.TEXT_PRIMARY if enabled else Colors.TEXT_TERTIARY
            )

            url_short = url[:65] + "..." if len(url) > 65 else url
            size_str = f" • {local_size / 1024:.1f} KB" if (is_local and local_size > 0) else ""
            item['sub_lbl'].configure(text=f"{url_short}{size_str}")

            try:
                norm_cat = "ad" if cat_str == "ads" else cat_str
                cat_enum = ConnectionCategory(norm_cat)
            except Exception:
                cat_enum = ConnectionCategory.UNKNOWN

            cat_color = get_category_color(cat_enum)
            cat_label = get_category_label(cat_enum)
            cat_icon = get_category_icon(cat_enum)

            item['badge'].configure(
                text=f" {cat_icon} {cat_label.upper()} ",
                text_color=cat_color
            )

            item['switch_var'].set(enabled)

            def make_toggle_handler(src_name=name, var=item['switch_var'], n_lbl=item['name_lbl'], d_lbl=item['dot_lbl']):
                def on_toggle():
                    val = var.get()
                    self.engine.blocklist.toggle_updater_source(src_name, val)
                    n_lbl.configure(text_color=Colors.TEXT_PRIMARY if val else Colors.TEXT_TERTIARY)
                    d_lbl.configure(text_color=Colors.SUCCESS if val else Colors.TEXT_TERTIARY)
                    if hasattr(self.engine, 'on_status') and self.engine.on_status:
                        self.engine.on_status(f"{'Enabled' if val else 'Disabled'} feed: {src_name}")
                return on_toggle

            item['switch'].configure(command=make_toggle_handler())

            if not item['frame'].winfo_ismapped():
                item['frame'].pack(fill="x", pady=2, padx=4)

        for j in range(len(sources), len(self._sources_row_pool)):
            if self._sources_row_pool[j]['frame'].winfo_ismapped():
                self._sources_row_pool[j]['frame'].pack_forget()

        # Isolate scroll events on the sources list frame so mouse wheel does not scroll the outer tab
        self._isolate_sources_scroll()

    def _isolate_sources_scroll(self):
        """Bind mouse wheel events to scroll only the inner sources list and halt propagation."""
        def _on_wheel(event):
            try:
                canvas = getattr(self._sources_list_frame, '_parent_canvas', None)
                if canvas:
                    if event.delta:
                        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    elif event.num == 4:
                        canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        canvas.yview_scroll(1, "units")
            except Exception:
                pass
            return "break"

        def _bind_all(widget):
            try:
                widget.bind("<MouseWheel>", _on_wheel)
                widget.bind("<Button-4>", _on_wheel)
                widget.bind("<Button-5>", _on_wheel)
            except Exception:
                pass
            try:
                for child in widget.winfo_children():
                    _bind_all(child)
            except Exception:
                pass

        _bind_all(self._sources_list_frame)
        if hasattr(self._sources_list_frame, '_parent_canvas'):
            _bind_all(self._sources_list_frame._parent_canvas)

    def _build_results_area(self):
        self._results_container = ctk.CTkFrame(self._main_scroll, fg_color="transparent")
        self._results_container.pack(fill="both", expand=True, pady=(Spacing.SM, Spacing.MD))

        hdr_row = ctk.CTkFrame(self._results_container, fg_color="transparent")
        hdr_row.pack(fill="x", pady=(0, Spacing.XS))
        
        self._lbl_results_title = ctk.CTkLabel(
            hdr_row, text="Matching Filter List Entries",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        )
        self._lbl_results_title.pack(side="left")
        
        self._lbl_results_count = ctk.CTkLabel(
            hdr_row, text="",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_TERTIARY,
        )
        self._lbl_results_count.pack(side="right")

        # Scrollable inner results list with dedicated scrollbar
        self._results_scroll = ctk.CTkScrollableFrame(
            self._results_container, fg_color=Colors.BG_DARK,
            height=440, corner_radius=6, border_width=1, border_color=Colors.BORDER_SUBTLE
        )
        self._results_scroll.pack(fill="both", expand=True)
        enable_smooth_scrolling(self._results_scroll)
        
        self._loaded_results = []
        self._results_row_pool = []
        self._has_more = False
        self._is_fetching = False
        self._page_size = 50
        
        # Load more button container
        self._load_more_frame = ctk.CTkFrame(self._results_scroll, fg_color="transparent")
        self._btn_load_more = ctk.CTkButton(
            self._load_more_frame, text="Load More Domains...",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BG_PANEL,
            text_color=Colors.TEXT_SECONDARY, height=32, corner_radius=6,
            command=self._load_next_page
        )
        self._btn_load_more.pack(pady=Spacing.MD)

        # Hook canvas scroll listener for smooth infinite scrolling
        try:
            canvas = getattr(self._results_scroll, '_parent_canvas', None)
            if canvas:
                def _on_canvas_scroll(event=None):
                    if getattr(self, '_destroyed', False):
                        return
                    try:
                        _, y_bottom = canvas.yview()
                        if y_bottom > 0.88 and getattr(self, '_has_more', False) and not getattr(self, '_is_fetching', False):
                            self._load_next_page()
                    except Exception:
                        pass
                canvas.bind("<MouseWheel>", _on_canvas_scroll, add="+")
                canvas.bind("<Configure>", _on_canvas_scroll, add="+")
        except Exception:
            pass
            
        self._restore_empty_state()

    def _get_or_create_row(self, index):
        while len(self._results_row_pool) <= index:
            row = ctk.CTkFrame(self._results_scroll, fg_color=Colors.BG_ELEVATED, corner_radius=6, height=36)
            row.pack_propagate(False)
            
            domain_lbl = ctk.CTkLabel(
                row, text="", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, "bold"),
                text_color=Colors.TEXT_PRIMARY, anchor="w"
            )
            domain_lbl.pack(side="left", padx=Spacing.MD)
            
            cat_badge = ctk.CTkLabel(
                row, text="", font=(Fonts.FAMILY_PRIMARY[0], 10, "bold"),
                corner_radius=11, height=22, width=96
            )
            cat_badge.pack(side="left", padx=Spacing.SM)
            
            btn = ctk.CTkButton(
                row, text="", width=75, height=24, corner_radius=6,
                font=(Fonts.FAMILY_PRIMARY[0], 10, "bold"), text_color=Colors.TEXT_PRIMARY
            )
            btn.pack(side="right", padx=Spacing.MD)
            
            self._results_row_pool.append({
                'frame': row,
                'domain_lbl': domain_lbl,
                'cat_badge': cat_badge,
                'btn': btn
            })
        return self._results_row_pool[index]

    def _restore_empty_state(self):
        self._has_more = False
        self._is_fetching = False
        if hasattr(self, '_load_more_frame') and self._load_more_frame.winfo_ismapped():
            self._load_more_frame.pack_forget()
            
        for item in self._results_row_pool:
            if item['frame'].winfo_ismapped():
                item['frame'].pack_forget()
                
        if hasattr(self, '_lbl_results_count'):
            self._lbl_results_count.configure(text="")

        if not hasattr(self, '_empty_lbl') or not self._empty_lbl.winfo_exists():
            self._empty_lbl = ctk.CTkLabel(
                self._results_scroll, text="Search for a domain or click an Indexed Category to explore filter lists.",
                text_color=Colors.TEXT_TERTIARY,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, "italic")
            )
        self._empty_lbl.pack(pady=Spacing.LG)

    def _do_search(self):
        query = self._search_entry.get().strip()
        cat_filter = getattr(self, '_active_category_filter', None)

        self._current_search_id = getattr(self, '_current_search_id', 0) + 1
        current_search_id = self._current_search_id

        # Keep stats container visible at top
        if hasattr(self, '_stats_container') and not self._stats_container.winfo_ismapped():
            self._stats_container.pack(fill="x", pady=(0, Spacing.SM))

        if not query and not cat_filter:
            self._restore_empty_state()
            return

        self._loaded_results = []
        self._has_more = True
        self._is_fetching = True

        import threading
        def search_task():
            try:
                results = self.engine.blocklist.search(query, limit=self._page_size, category_filter=cat_filter, offset=0)
            except Exception:
                results = []
            
            if not self._destroyed and getattr(self, '_current_search_id', 0) == current_search_id:
                self.after(0, lambda: self._handle_first_page(results, query, current_search_id))
                
        threading.Thread(target=search_task, daemon=True).start()

    def _handle_first_page(self, results, query, search_id):
        if self._destroyed or getattr(self, '_current_search_id', 0) != search_id:
            return

        self._is_fetching = False
        self._loaded_results = list(results)
        self._has_more = len(results) >= self._page_size

        if hasattr(self, '_empty_lbl') and self._empty_lbl.winfo_exists():
            self._empty_lbl.pack_forget()

        # Unpack all old pool items beyond current results
        for i in range(len(results), len(self._results_row_pool)):
            if self._results_row_pool[i]['frame'].winfo_ismapped():
                self._results_row_pool[i]['frame'].pack_forget()

        self._render_batch(0, len(results))
        self._update_footer_and_count()

    def _load_next_page(self):
        if self._is_fetching or not self._has_more or self._destroyed:
            return

        self._is_fetching = True
        query = self._search_entry.get().strip()
        cat_filter = getattr(self, '_active_category_filter', None)
        current_search_id = getattr(self, '_current_search_id', 0)
        current_offset = len(self._loaded_results)

        if hasattr(self, '_btn_load_more'):
            self._btn_load_more.configure(text="Loading more...", state="disabled")

        import threading
        def load_task():
            try:
                more_results = self.engine.blocklist.search(
                    query, limit=self._page_size, category_filter=cat_filter, offset=current_offset
                )
            except Exception:
                more_results = []

            if not self._destroyed and getattr(self, '_current_search_id', 0) == current_search_id:
                self.after(0, lambda: self._handle_next_page(more_results, current_search_id))

        threading.Thread(target=load_task, daemon=True).start()

    def _handle_next_page(self, more_results, search_id):
        if self._destroyed or getattr(self, '_current_search_id', 0) != search_id:
            return

        self._is_fetching = False
        start_idx = len(self._loaded_results)
        self._loaded_results.extend(more_results)
        self._has_more = len(more_results) >= self._page_size

        self._render_batch(start_idx, len(self._loaded_results))
        self._update_footer_and_count()

    def _render_batch(self, start_idx, end_idx):
        from netstrip.core.modes import ConnectionCategory
        from netstrip.gui.theme import get_category_color, get_category_label, get_category_icon

        # Hide load more while packing new rows
        if hasattr(self, '_load_more_frame') and self._load_more_frame.winfo_ismapped():
            self._load_more_frame.pack_forget()

        for i in range(start_idx, end_idx):
            item = self._get_or_create_row(i)
            r = self._loaded_results[i]
            domain = r.get('domain', 'Unknown')
            cat = r.get('category', 'unknown')
            
            # Dynamic row background color for alternating contrast
            bg_color = "#181824" if i % 2 == 0 else "#14141f"
            item['frame'].configure(fg_color=bg_color)
            item['domain_lbl'].configure(text=domain)
            
            try:
                cat_enum = ConnectionCategory(cat)
            except ValueError:
                cat_enum = ConnectionCategory.UNKNOWN
                
            cat_color = get_category_color(cat_enum)
            cat_label = get_category_label(cat_enum)
            cat_icon = get_category_icon(cat_enum)
            
            item['cat_badge'].configure(
                text=f" {cat_icon} {cat_label.upper()} ",
                text_color=cat_color,
                fg_color=Colors.BG_ELEVATED
            )
            
            is_allowed = cat in ('user_allowed', 'essential')
            btn_text = "Block" if is_allowed else "Whitelist"
            btn_color = Colors.DANGER if is_allowed else Colors.SUCCESS_DIM
            btn_hover = "#be123c" if is_allowed else Colors.SUCCESS
            act_val = 'block' if is_allowed else 'allow'

            def make_action(d=domain, act=act_val):
                mode_scope = "PARANOID" if self.engine.classifier.mode.name.upper() == "PARANOID" else "STANDARD"
                self.engine.db.add_user_rule({
                    'pattern': d,
                    'action': act,
                    'scope': 'global',
                    'app_name': None,
                    'category': f'user_{act}ed',
                    'note': f"Manual {act} from search",
                    'mode_scope': mode_scope
                })
                rules = self.engine.db.get_user_rules(mode_scope=mode_scope)
                if hasattr(self.engine.blocklist, 'sync_user_rules'):
                    self.engine.blocklist.sync_user_rules(rules)
                if hasattr(self.engine, 'on_status') and self.engine.on_status:
                    self.engine.on_status(f"{act.capitalize()}ed domain: {d}")
                self._refresh_stats_grid()
                self._do_search()

            item['btn'].configure(
                text=btn_text, fg_color=btn_color, hover_color=btn_hover,
                command=make_action
            )
            
            if not item['frame'].winfo_ismapped():
                item['frame'].pack(fill="x", pady=2, padx=4)

    def _update_footer_and_count(self):
        count = len(self._loaded_results)
        if hasattr(self, '_lbl_results_count'):
            more_suffix = "+" if self._has_more else ""
            self._lbl_results_count.configure(text=f"Showing {count:,}{more_suffix} results")

        if self._has_more:
            if hasattr(self, '_btn_load_more'):
                self._btn_load_more.configure(text="Load More Domains...", state="normal")
            if hasattr(self, '_load_more_frame'):
                self._load_more_frame.pack(fill="x", pady=Spacing.SM)
        else:
            if hasattr(self, '_load_more_frame') and self._load_more_frame.winfo_ismapped():
                self._load_more_frame.pack_forget()

    def destroy(self):
        self._destroyed = True
        super().destroy()



