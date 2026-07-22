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

# ═══════════════════════════════════════════════════
#  BlocklistView
# ═══════════════════════════════════════════════════
class BlocklistView(ctk.CTkScrollableFrame):
    """Blocklist stats grid and domain search interface."""

    def __init__(self, master, engine, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PANEL, **kwargs)
        self.engine = engine
        self._destroyed = False
        self._active_category_filter = None
        self._category_ui_elements = {}

        # Header
        ctk.CTkLabel(
            self, text="Filter Manager",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XL, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.MD))
        
        # Search Bar (Top)
        self._build_search_bar()
        
        # Add Custom Rule Bar
        self._build_add_rule_bar()

        # Compact Stats Grid
        self._build_stats_grid()

        # Search Results Area
        self._build_results_area()

    def _build_add_rule_bar(self):
        add_row = ctk.CTkFrame(self, fg_color=Colors.BG_PANEL)
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
            whitelist_size = len(self.engine.blocklist.whitelist)
            app_whitelist_size = len(self.engine.blocklist.app_whitelist)
            blacklist_size = len(getattr(self.engine.blocklist, 'blacklist', {}))
            app_blacklist_size = len(getattr(self.engine.blocklist, 'app_blacklist', set()))
            
            from netstrip.core.modes import ConnectionCategory
            
            updates = {
                ConnectionCategory.USER_ALLOWED.value: whitelist_size + app_whitelist_size,
                ConnectionCategory.USER_BLOCKED.value: blacklist_size + app_blacklist_size,
            }
            
            for cat_val, (card, inner) in getattr(self, '_category_ui_elements', {}).items():
                if cat_val in updates:
                    children = inner.winfo_children()
                    if len(children) >= 2:
                        children[1].configure(text=f"{updates[cat_val]:,}")
                        
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error refreshing stats grid: {e}")

    def _build_search_bar(self):
        search_row = ctk.CTkFrame(self, fg_color=Colors.BG_PANEL)
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
        ctk.CTkLabel(
            self, text="Indexed Categories",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.SM))
        
        grid_frame = ctk.CTkFrame(self, fg_color=Colors.BG_PANEL)
        grid_frame.pack(fill="x", pady=(0, Spacing.LG))
        grid_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        try:
            metadata = getattr(self.engine.blocklist, 'sources_metadata', {})
            metadata = dict(metadata) # clone it to avoid mutating core dict
            
            # Add safe and blocked domains as pseudo-sources
            whitelist_size = len(self.engine.blocklist.whitelist)
            app_whitelist_size = len(self.engine.blocklist.app_whitelist)
            
            blacklist_size = len(getattr(self.engine.blocklist, 'blacklist', {}))
            app_blacklist_size = len(getattr(self.engine.blocklist, 'app_blacklist', set()))
            
            from netstrip.core.modes import ConnectionCategory
            
            # Always show these categories so the user knows they exist
            metadata[ConnectionCategory.USER_ALLOWED] = [
                {'filename': 'User Whitelisted Domains', 'updated': 'Now', 'size': whitelist_size},
                {'filename': 'User Allowed Apps', 'updated': 'Now', 'size': app_whitelist_size}
            ]
            
            metadata[ConnectionCategory.USER_BLOCKED] = [
                {'filename': 'User Blocked Domains', 'updated': 'Now', 'size': blacklist_size},
                {'filename': 'User Blocked Apps', 'updated': 'Now', 'size': app_blacklist_size}
            ]
            
            metadata[ConnectionCategory.ESSENTIAL] = [
                {'filename': 'Internal Essential Services', 'updated': 'Now', 'size': 5}
            ]
            
            metadata[ConnectionCategory.SYSTEM] = [
                {'filename': 'OS & Native Services', 'updated': 'Now', 'size': 6}
            ]
                
        except Exception:
            metadata = {}

        if not metadata:
            ctk.CTkLabel(grid_frame, text="Blocklists are loading...", text_color=Colors.TEXT_TERTIARY).pack(pady=Spacing.LG)
            return

        for idx, (category, sources) in enumerate(metadata.items()):
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
            
            total_size = sum(s.get('size', 0) for s in sources)
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
            
            self._category_ui_elements[category.value] = (card, inner)

            # Bindings
            def on_enter(e, cat_val=category.value):
                if self._active_category_filter != cat_val:
                    c, i = self._category_ui_elements[cat_val]
                    c.configure(fg_color=Colors.BG_ELEVATED)
                    i.configure(fg_color=Colors.BG_ELEVATED)

            def on_leave(e, cat_val=category.value):
                if self._active_category_filter != cat_val:
                    c, i = self._category_ui_elements[cat_val]
                    c.configure(fg_color=Colors.BG_PANEL)
                    i.configure(fg_color=Colors.BG_PANEL)

            def on_click(e, cat_val=category.value):
                if self._active_category_filter == cat_val:
                    self._active_category_filter = None
                else:
                    self._active_category_filter = cat_val
                
                # Update visual state of all cards
                for kv, (c, i) in self._category_ui_elements.items():
                    if kv == self._active_category_filter:
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
        self._results_container = ctk.CTkFrame(self, fg_color="transparent")
        self._results_container.pack(fill="both", expand=True)
        self._restore_empty_state()
        
        # Setup infinite scrolling variables
        self._current_results = []
        self._rendered_count = 0
        self._page_size = 50
        
        # Bind mouse wheel to check scroll position
        if hasattr(self, '_parent_canvas'):
            self.bind_all("<MouseWheel>", self._check_scroll, add="+")

    def _check_scroll(self, event=None):
        if self._destroyed or not getattr(self, '_parent_canvas', None) or not self.winfo_ismapped():
            return
        
        yview = self._parent_canvas.yview()
        # yview[1] is the bottom fractional position of the scrollbar (1.0 is bottom)
        if yview[1] >= 0.98:
            self._render_next_chunk()

    def _restore_empty_state(self):
        self._loading_label = ctk.CTkLabel(
            self._results_container, text="Search for a domain to check if it is blocked.",
            text_color=Colors.TEXT_TERTIARY,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, "italic")
        )
        self._loading_label.pack(pady=Spacing.LG)

    def _do_search(self):
        query = self._search_entry.get().strip()
        cat_filter = getattr(self, '_active_category_filter', None)

        for w in self._results_container.winfo_children():
            w.destroy()

        if not query and not cat_filter:
            self._restore_empty_state() # Restore empty state
            return

        # Show loading indicator
        txt = f"Searching for '{query}'..." if query else "Loading domains..."
        if cat_filter:
            txt += f" in category: {cat_filter.upper()}"
            
        self._loading_label = ctk.CTkLabel(
            self._results_container, text=txt,
            text_color=Colors.TEXT_TERTIARY,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, "italic")
        )
        self._loading_label.pack(pady=Spacing.LG)

        # Run search in background thread to prevent UI freezing
        import threading
        def search_task():
            try:
                # Up to 2000 results so we can scroll a lot
                results = self.engine.blocklist.search(query, limit=2000, category_filter=cat_filter)
            except Exception as e:
                results = []
            
            # Update UI on main thread safely
            if not self._destroyed:
                self.after(0, lambda: self._init_render(results, query))
                
        threading.Thread(target=search_task, daemon=True).start()

    def _init_render(self, results, query):
        if self._destroyed:
            return
            
        try:
            self._loading_label.destroy()
        except Exception:
            pass

        self._current_results = results
        self._rendered_count = 0
        self._current_query = query
        
        for w in self._results_container.winfo_children():
            w.destroy()

        if not results:
            msg = f"No matches found for '{query}'" if query else "No domains found in this category."
            ctk.CTkLabel(
                self._results_container, text=msg,
                text_color=Colors.TEXT_TERTIARY,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            ).pack(pady=Spacing.LG)
            return

        if query:
            ctk.CTkLabel(
                self._results_container, text=f"Showing top {len(results)} matches for '{query}':",
                text_color=Colors.TEXT_SECONDARY,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS, "italic"),
            ).pack(anchor="w", padx=Spacing.SM, pady=(0, Spacing.SM))

        self._render_next_chunk()

    def _render_next_chunk(self):
        if self._destroyed or not getattr(self, '_current_results', None):
            return
            
        if getattr(self, '_is_loading_chunk', False):
            return
            
        if self._rendered_count >= len(self._current_results):
            return # Done rendering
            
        self._is_loading_chunk = True
            
        chunk = self._current_results[self._rendered_count : self._rendered_count + self._page_size]
        if not chunk:
            self._is_loading_chunk = False
            return
            
        self._rendered_count += len(chunk)

        # Process the chunk in smaller batches to keep UI responsive
        def _render_batch(items, index=0):
            if self._destroyed or index >= len(items):
                self._is_loading_chunk = False
                return
                
            batch_size = 5
            for r in items[index : index + batch_size]:
                row = ctk.CTkFrame(
                    self._results_container,
                    fg_color=Colors.BG_ELEVATED, corner_radius=0,
                )
                row.pack(fill="x", pady=2, padx=4)

                domain = r.get('domain', 'Unknown')
                cat = r.get('category', 'unknown')

                domain_lbl = ctk.CTkLabel(
                    row, text=domain,
                    font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, "bold"),
                    text_color=Colors.TEXT_PRIMARY,
                )
                domain_lbl.pack(side="left", padx=Spacing.MD, pady=Spacing.SM)
                
                try:
                    from netstrip.gui.utils import bind_copy_tooltip
                    bind_copy_tooltip(domain_lbl, domain, "Link copied!")
                except Exception:
                    pass

                # Quick Actions
                btn_frame = ctk.CTkFrame(row, fg_color=Colors.BG_PANEL)
                btn_frame.pack(side="right", padx=Spacing.SM, pady=Spacing.SM)
                
                def make_action(d=domain, act='allow'):
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
                    # Refresh blocklist memory
                    rules = self.engine.db.get_user_rules(mode_scope=mode_scope)
                    if hasattr(self.engine.blocklist, 'sync_user_rules'):
                        self.engine.blocklist.sync_user_rules(rules)
                    
                    # Visual feedback
                    if hasattr(self.engine, 'on_status') and self.engine.on_status:
                        self.engine.on_status(f"{act.capitalize()}ed domain: {d}")
                        
                    # Auto-refresh the view
                    self._refresh_stats_grid()
                    self._do_search()
                    
                is_allowed = cat in ('user_allowed', 'essential')
                btn_text = "Block" if is_allowed else "Whitelist"
                btn_color = Colors.DANGER if is_allowed else Colors.SUCCESS_DIM
                btn_hover = "#be123c" if is_allowed else Colors.SUCCESS
                act_val = 'block' if is_allowed else 'allow'

                ctk.CTkButton(
                    btn_frame, text=btn_text, width=60, height=22, corner_radius=4,
                    fg_color=btn_color, hover_color=btn_hover, text_color=Colors.TEXT_PRIMARY,
                    font=(Fonts.FAMILY_PRIMARY[0], 10), command=lambda d=domain, a=act_val: make_action(d, a)
                ).pack(side="left", padx=(0, 4))
                
                ctk.CTkLabel(
                    btn_frame, text=get_category_label(cat).upper(),
                    fg_color=get_category_color(cat),
                    corner_radius=4, text_color="white",
                    font=(Fonts.FAMILY_PRIMARY[0], 9, "bold"),
                    height=22, width=80,
                ).pack(side="right")
                
            self.after(5, lambda: _render_batch(items, index + batch_size))
            
        _render_batch(chunk)

    def destroy(self):
        self._destroyed = True
        self.unbind_all("<MouseWheel>")
        super().destroy()



