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
                        
                    # Reload core memory
                    self.engine.blocklist.load_all()
                    
                    if not self._destroyed:
                        self.after(0, lambda: self._refresh_stats_grid(f"Added permanent blocklist: {name}"))
                        
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
        
    def _refresh_stats_grid(self, msg=None):
        if msg and hasattr(self.engine, 'on_status') and self.engine.on_status:
            self.engine.on_status(msg)
            
        try:
            metadata = getattr(self.engine.blocklist, 'sources_metadata', {})
            stats = getattr(self.engine.blocklist, 'stats', {})
            domain_map = getattr(self.engine.blocklist, 'domain_map', {})
            
            whitelist_size = len(self.engine.blocklist.whitelist)
            app_whitelist_size = len(self.engine.blocklist.app_whitelist)
            blacklist_size = len(getattr(self.engine.blocklist, 'blacklist', {}))
            app_blacklist_size = len(getattr(self.engine.blocklist, 'app_blacklist', set()))
            
            from netstrip.core.modes import ConnectionCategory
            
            for cat_enum, (card, inner, lbl_count) in getattr(self, '_category_ui_elements', {}).items():
                cat_val = getattr(cat_enum, 'value', str(cat_enum))
                sources = metadata.get(cat_enum) or metadata.get(cat_val) or []
                cnt = sum(s.get('size', 0) for s in sources)
                if not cnt and stats:
                    cnt = stats.get(cat_enum) or stats.get(cat_val) or (stats.get('ads') if cat_val == 'ad' else 0) or 0
                if not cnt and domain_map:
                    cnt = sum(1 for c in domain_map.values() if c == cat_enum or getattr(c, 'value', str(c)) == cat_val)
                    
                if cat_enum == ConnectionCategory.USER_ALLOWED or cat_val == 'user_allowed':
                    cnt += whitelist_size + app_whitelist_size
                elif cat_enum == ConnectionCategory.USER_BLOCKED or cat_val == 'user_blocked':
                    cnt += blacklist_size + app_blacklist_size
                        
                cnt = int(cnt or 0)
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

        metadata = getattr(self.engine.blocklist, 'sources_metadata', {})
        stats = getattr(self.engine.blocklist, 'stats', {})
        domain_map = getattr(self.engine.blocklist, 'domain_map', {})
        whitelist_size = len(self.engine.blocklist.whitelist)
        app_whitelist_size = len(self.engine.blocklist.app_whitelist)
        blacklist_size = len(getattr(self.engine.blocklist, 'blacklist', {}))
        app_blacklist_size = len(getattr(self.engine.blocklist, 'app_blacklist', set()))

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
            
            if category == ConnectionCategory.USER_ALLOWED:
                total_size = whitelist_size + app_whitelist_size
            elif category == ConnectionCategory.USER_BLOCKED:
                total_size = blacklist_size + app_blacklist_size
            else:
                sources = metadata.get(category, [])
                total_size = sum(s.get('size', 0) for s in sources)
                if total_size == 0 and stats:
                    total_size = stats.get(category, 0)
                if total_size == 0 and domain_map:
                    total_size = sum(1 for c in domain_map.values() if c == category)

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



