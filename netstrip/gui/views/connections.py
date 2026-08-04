"""
Persistent Connections Sidebar for Cripple GUI.
Displays a live list of connections grouped by app name, target, classification color, and allow/block toggle.
"""

import customtkinter as ctk
from netstrip.gui.theme import Colors, Fonts, Spacing, Icons, get_category_color, get_category_label
from netstrip.core.engine import NetStripEngine
from netstrip.gui.icon_manager import IconManager
import os


from netstrip.gui.components.sidebar_components import ConnectionRow, AppGroupFrame
from netstrip.gui.utils import safe_loop
from netstrip.gui.popups import check_killswitch_override

class ConnectionsView(ctk.CTkFrame):
    def __init__(self, master, engine: NetStripEngine, **kwargs):
        super().__init__(master, fg_color=Colors.BG_DARK, corner_radius=0, **kwargs)
        self.engine = engine
        self._destroyed = False
        
        home_dir = os.path.expanduser("~")
        config_dir = os.path.join(home_dir, ".NetStrip")
        self.icon_manager = IconManager(config_dir)
        
        # Grid layout for sidebar
        self.grid_rowconfigure(3, weight=1) # List area
        self.grid_rowconfigure(4, weight=0) # LAN toggle row
        self.grid_columnconfigure(0, weight=1)
        
        # Legend (Now at the very top, row 0)
        legend_frame = ctk.CTkFrame(self, fg_color="transparent")
        legend_frame.grid(row=0, column=0, sticky="ew", padx=Spacing.LG, pady=(Spacing.MD, 0))
        ctk.CTkLabel(legend_frame, text="Legend: ", font=(Fonts.FAMILY_PRIMARY[0], 10, "bold"), text_color=Colors.TEXT_SECONDARY).pack(side="left")
        
        categories = [
            ('Ad', Colors.CAT_AD), ('Tracker', Colors.CAT_TRACKER), ('Telemetry', Colors.CAT_TELEMETRY), ('Malware', Colors.CAT_MALWARE),
            ('Essential', Colors.CAT_ESSENTIAL), ('Allowed', Colors.CAT_USER_ALLOWED), ('Unknown', Colors.CAT_UNKNOWN), ('LAN', Colors.CAT_LAN)
        ]
        
        legend_grid = ctk.CTkFrame(legend_frame, fg_color="transparent")
        legend_grid.pack(side="left")
        
        for i, (name, color) in enumerate(categories):
            row = i // 4
            col = i % 4
            cell = ctk.CTkFrame(legend_grid, fg_color="transparent")
            cell.grid(row=row, column=col, padx=(4, 8), pady=1, sticky="w")
            ctk.CTkLabel(cell, text="●", text_color=color, font=(Fonts.FAMILY_PRIMARY[0], 10)).pack(side="left", padx=(0, 2))
            ctk.CTkLabel(cell, text=name, text_color=Colors.TEXT_TERTIARY, font=(Fonts.FAMILY_PRIMARY[0], 10)).pack(side="left")

        # Header (Now row 1)
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=1, column=0, sticky="ew", padx=Spacing.LG, pady=(Spacing.MD, Spacing.SM))
        
        ctk.CTkLabel(
            header_frame, 
            text="App Connections", 
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY
        ).pack(side="left")

        self.hide_inactive = False

        # Sort & Filter Bar (Now row 2)
        sf_frame = ctk.CTkFrame(self, fg_color="transparent")
        sf_frame.grid(row=2, column=0, sticky="ew", padx=Spacing.LG, pady=(0, Spacing.SM))
        
        from netstrip.gui.components.selection_modal import TouchOptionMenu
        
        self.sort_var = ctk.StringVar(value="Sort by: Recent")
        self.opt_sort = TouchOptionMenu(
            sf_frame, title="Sort Connections", values=["Sort by: Recent", "Sort by: Active", "Sort by: Name (A-Z)"], 
            variable=self.sort_var, width=130, height=26,
            font=(Fonts.FAMILY_PRIMARY[0], 11),
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BORDER_DEFAULT,
            command=self._on_sort_filter_change
        )
        self.opt_sort.pack(side="left")
        
        self.filter_var = ctk.StringVar(value="Filter: All")
        self.opt_filter = TouchOptionMenu(
            sf_frame, title="Filter Connections", values=["Filter: All", "Filter: Allowed", "Filter: Blocked", "Filter: DNS/Local"], 
            variable=self.filter_var, width=130, height=26,
            font=(Fonts.FAMILY_PRIMARY[0], 11),
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BORDER_DEFAULT,
            command=self._on_sort_filter_change
        )
        self.opt_filter.pack(side="left", padx=Spacing.SM)
        
        self.btn_reset = ctk.CTkButton(
            sf_frame, text="Reset", width=50, height=26,
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BORDER_DEFAULT,
            command=self._reset_filters,
            font=(Fonts.FAMILY_PRIMARY[0], 11), text_color=Colors.TEXT_TERTIARY
        )
        self.btn_reset.pack(side="left", padx=Spacing.SM)
        
        self._all_expanded = False
        self.btn_expand_all = ctk.CTkButton(
            sf_frame, text="Expand All", width=80, height=26,
            fg_color=Colors.BG_INPUT, hover_color=Colors.ACCENT_PRIMARY,
            command=self._toggle_expand_all,
            font=(Fonts.FAMILY_PRIMARY[0], 11, "bold"), text_color=Colors.TEXT_PRIMARY
        )
        self.btn_expand_all.pack(side="right")
        
        # List Area
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, 
            fg_color=Colors.BG_DARK,
            corner_radius=0
        )
        self.scroll_frame.grid(row=3, column=0, sticky="nsew", padx=Spacing.SM)
        
        self.app_groups = {} # process_name -> AppGroupFrame
        self.last_update_id = 0
        
        # LAN Shield Toggle at bottom
        self.lan_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.lan_frame.grid(row=4, column=0, sticky="ew", padx=Spacing.LG, pady=Spacing.MD)
        
        ctk.CTkLabel(self.lan_frame, text="LAN Shield", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD), text_color=Colors.TEXT_PRIMARY).pack(side="left")
        
        self.lan_toggle = ctk.CTkSwitch(
            self.lan_frame, text="", width=36,
            progress_color=Colors.CAT_LAN,
            command=self._on_lan_toggle
        )
        self.lan_toggle.pack(side="right")
        
        # Initialize toggle state from DB
        if self.engine.db.get_setting("lan_shield_enabled", "true") == "true":
            self.lan_toggle.select()
        
        self._refresh_loop()

    def _on_lan_toggle(self):
        def proceed():
            val = self.lan_toggle.get() == 1
            self.engine.db.set_setting("lan_shield_enabled", "true" if val else "false")
            
            if val:
                self.engine.lan_shield.enable()
            else:
                self.engine.lan_shield.disable()


        # We only care if they are trying to toggle it OFF
        is_on = self.lan_toggle.get() == 1
        if not is_on: # They toggled it to OFF
            def on_cancel():
                # Revert visual
                self.lan_toggle.select()
            
            check_killswitch_override(self.engine, self, proceed, cancel_callback=on_cancel)
        else:
            proceed()

    def _is_mouse_inside(self) -> bool:
        try:
            x, y = self.winfo_pointerxy()
            widget_x = self.winfo_rootx()
            widget_y = self.winfo_rooty()
            widget_w = self.winfo_width()
            widget_h = self.winfo_height()
            return (widget_x <= x <= widget_x + widget_w) and (widget_y <= y <= widget_y + widget_h)
        except Exception:
            return False

    def _on_sort_filter_change(self, choice=None):
        self._refresh_loop()
        
    @safe_loop(delay_ms=200)
    def _refresh_loop(self):
        if getattr(self, '_destroyed', False):
            return
        # Skip heavy refresh during active window resize to prevent artifacts
        if getattr(self, '_resize_paused', False):
            return
            
        # Fetch recent connections in background thread to prevent UI micro-stutters
        def fetch():
            try:
                conns = self.engine.db.get_recent_connections(limit=500, unique_only=True)
                sys_val = self.engine.db.get_setting("block_system_connections", "false")
                
                def process_ui():
                    if getattr(self, '_destroyed', False) or not self.winfo_exists():
                        return
                    self.engine._cached_recent = conns
                    self._process_connections(conns, sys_val)
                self.after(0, process_ui)
            except Exception:
                pass
                
        import threading
        threading.Thread(target=fetch, daemon=True).start()

    def _process_connections(self, conns, sys_val):
        try:
            db_cache = {"block_system_connections": sys_val}
            
            if len(conns) > 0:
                # Process newest first, limit to 50 per app to prevent UI widget thrashing
                app_conn_counts = {}
                for i, row_data in enumerate(conns):
                    conn_dict = dict(row_data)
                    p_name = conn_dict.get('process_name', 'Unknown')
                    
                    # Normalize names early for counting
                    domain_ip = str(conn_dict.get('domain') or conn_dict.get('ip') or '')
                    if p_name and p_name.lower() in ('cripple.exe', 'cripple (internal)', 'netstrip', 'netstrip (internal)'):
                        p_name = 'Cripple (Internal)'
                    elif p_name and p_name.lower() in ('python.exe', 'python3.exe', 'pythonw.exe', 'language_server.exe'):
                        if any(x in domain_ip for x in ('github', 'urlhaus', 'oisd.nl', 'stevenblack', 'ip-api.com', 'ipify.org', 'yoyo.org', 'adaway.org', 'energized.pro', 'someonewhocares', 'v2fly', 'adguard')):
                            p_name = 'Cripple (Internal)'
                    elif p_name == 'Unknown (DNS)' or conn_dict.get('rport') in (53, 853):
                        if any(x in domain_ip for x in ('github', 'urlhaus', 'oisd.nl', 'stevenblack', 'ip-api.com', 'ipify.org', 'yoyo.org', 'adaway.org', 'energized.pro', 'someonewhocares', 'v2fly', 'adguard')):
                            p_name = 'Cripple (Internal)'
                        else:
                            p_name = 'DNS'
                            
                    if app_conn_counts.get(p_name, 0) >= 50:
                        continue
                        
                    app_conn_counts[p_name] = app_conn_counts.get(p_name, 0) + 1
                    
                    p_path = conn_dict.get('process_path', '')
                    
                    if p_name == 'DNS':
                        conn_dict['category'] = 'dns'
                        
                    # Live re-evaluate category and action based on current mode and blocklist rules
                    domain_ip = conn_dict.get('domain') or conn_dict.get('ip')
                    if domain_ip:
                        from netstrip.core.modes import ConnectionCategory, ConnectionAction
                        
                        original_cat = conn_dict.get('category', 'unknown')
                        try:
                            cat = ConnectionCategory(original_cat)
                        except ValueError:
                            cat = ConnectionCategory.UNKNOWN
                            
                        # Run the domain through the classifier ONLY if we don't have a label yet
                        if cat == ConnectionCategory.UNKNOWN:
                            live_cat = self.engine.classifier.classify_domain(domain_ip, p_name)
                            if live_cat == ConnectionCategory.UNKNOWN:
                                live_cat, _ = self.engine.classifier.classify_ip(conn_dict.get('ip'), 0, p_name)
                            if live_cat != ConnectionCategory.UNKNOWN:
                                cat = live_cat
                        
                        # Apply EXPLICIT user rule overrides only.
                        # We check the whitelist/blacklist sets directly instead of calling
                        # is_blocked() again, which would re-run the full classification cascade
                        # and overwrite built-in categories (e.g. ESSENTIAL → USER_ALLOWED).
                        domain_lower = domain_ip.lower().rstrip('.')
                        bl = self.engine.classifier.blocklist
                        if domain_lower in bl.whitelist or (p_name and p_name in bl.app_whitelist):
                            cat = ConnectionCategory.USER_ALLOWED
                        elif domain_lower in bl.blacklist or (p_name and p_name in bl.app_blacklist):
                            cat = ConnectionCategory.USER_BLOCKED
                        
                        action = self.engine.classifier.mode.get_action_for_category(cat, self.engine.db)
                        
                        if getattr(self.engine, 'killswitch_active', False):
                            action = ConnectionAction.BLOCK
                        
                        conn_dict['action'] = action.value
                        conn_dict['category'] = cat.value if cat != ConnectionCategory.UNKNOWN else p_name
                        
                        # Apply identity tag
                        identity = self.engine.blocklist.get_identity(domain_ip)
                        if identity:
                            conn_dict['identity'] = identity
                    
                    if p_name not in self.app_groups:
                        # Create new group
                        import time
                        group = AppGroupFrame(self.scroll_frame, p_name, p_path, self.engine, self.icon_manager)
                        self.app_groups[p_name] = group
                        group.set_expanded(getattr(self, 'is_expanded', False))
                        if self._all_expanded and not group.is_expanded:
                            group._toggle_expand()
                        
                    # Add connection to group
                    self.app_groups[p_name].add_connection(conn_dict, self.hide_inactive)
                    
            if not conns and not hasattr(self, 'lbl_empty'):
                self.lbl_empty = ctk.CTkLabel(self.scroll_frame, text="No app connections tracked yet.\n\nWaiting for traffic...", text_color=Colors.TEXT_TERTIARY)
                self.lbl_empty.pack(pady=40)
            elif conns and hasattr(self, 'lbl_empty'):
                self.lbl_empty.destroy()
                delattr(self, 'lbl_empty')
                    
            # Sorting logic
            sort_val = self.sort_var.get()
            groups = list(self.app_groups.values())
            
            if sort_val == "Sort by: Name (A-Z)":
                groups.sort(key=lambda g: g.process_name.lower())
            elif sort_val == "Sort by: Active":
                groups.sort(key=lambda g: len(g.rows), reverse=True)
            elif sort_val == "Sort by: Recent":
                # Dynamic stable sort:
                # 1. Get the most recent connection time for this app
                # 2. Bucket the time into 5-second chunks (prevents micro-jittering/flickering)
                # 3. Secondary sort by app name for perfect stability within the bucket
                def get_sort_key(g):
                    import time
                    if not g.rows: return (0, g.process_name)
                    latest = max(getattr(r, 'last_updated', 0) for r in g.rows.values())
                    bucket = round(latest / 5.0) * 5
                    return (bucket, g.process_name.lower())
                    
                groups.sort(key=get_sort_key, reverse=True)
                
            current_filter = self.filter_var.get()
            
            # Extract currently packed AppGroupFrames in order
            current_packed = [c for c in self.scroll_frame.winfo_children() if isinstance(c, AppGroupFrame) and getattr(c, '_is_packed', True)]
            
            # Update internal visibility first without packing/unpacking
            for group in groups:
                if hasattr(group, 'refresh_global_state'):
                    group.refresh_global_state()
                group.apply_filter(self.hide_inactive, current_filter)
                
            # Now repack only if the visible order does not match the desired sorted order
            visible_groups = [g for g in groups if g.visible_count > 0]
            
            # Force DNS to the very bottom, as it is a less visible internal system group
            dns_group = next((g for g in visible_groups if g.process_name == 'DNS'), None)
            if dns_group:
                visible_groups.remove(dns_group)
                visible_groups.append(dns_group)
                
            if current_packed != visible_groups:
                # Unpack groups that are no longer visible
                for group in current_packed:
                    if group not in visible_groups:
                        group.pack_forget()
                        group._is_packed = False
                
                # Seamlessly re-order the remaining groups without flickering
                prev = None
                for group in visible_groups:
                    if not getattr(group, '_is_packed', False):
                        group.pack(fill="x", padx=Spacing.XS, pady=Spacing.SM)
                        group._is_packed = True
                        
                    if prev:
                        group.pack(after=prev)
                    else:
                        others = [g for g in visible_groups if g != group and getattr(g, '_is_packed', False)]
                        if others:
                            group.pack(before=others[0])
                            
                    prev = group
                        
            # Export active apps for dashboard to avoid redundant classification
            active_apps = set()
            for group in groups:
                if any(row.conn_data.get('action') == 'allow' for row in group.rows.values()):
                    active_apps.add(group.process_name)
            self.engine._cached_active_apps = active_apps
                        
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error updating sidebar: {e}", exc_info=True)

        # Update LAN toggle state
        lan_enabled = self.engine.db.get_setting("lan_shield_enabled", "true") == "true"
        if lan_enabled and not self.lan_toggle.get():
            self.lan_toggle.select()
        elif not lan_enabled and self.lan_toggle.get():
            self.lan_toggle.deselect()
            
        if not self._destroyed:
            if hasattr(self, '_refresh_after_id'):
                self.after_cancel(self._refresh_after_id)
            self._refresh_after_id = self.after(500, self._refresh_loop)

    def _reset_filters(self):
        self.sort_var.set("Sort by: Recent")
        self.filter_var.set("Filter: All")
        self.hide_inactive = False
        self._on_sort_filter_change()
        
    def _toggle_expand_all(self):
        if getattr(self, '_is_expanding_all', False):
            return # Prevent double clicks
            
        self._all_expanded = not self._all_expanded
        btn_text = "Collapse All" if self._all_expanded else "Expand All"
        self.btn_expand_all.configure(text=btn_text)
        
        # Instantly snap scroll view to top when collapsing all to avoid empty void from batch shrinking
        if not self._all_expanded:
            try: self.scroll_frame._parent_canvas.yview_moveto(0)
            except Exception: pass
        
        groups_to_update = list(self.app_groups.values())
        self._is_expanding_all = True
        
        def _update_next(index=0):
            if not self.winfo_exists() or index >= len(groups_to_update):
                self._is_expanding_all = False
                return
                
            # Process up to 5 groups per UI cycle to balance speed vs freezing
            batch_size = 5
            for i in range(index, min(index + batch_size, len(groups_to_update))):
                group = groups_to_update[i]
                if getattr(group, '_is_packed', False):
                    if group.is_expanded != self._all_expanded:
                        group._toggle_expand()
                else:
                    # Keep state synced for hidden groups but don't force UI redraws
                    group.is_expanded = self._all_expanded
                    if group.is_expanded:
                        group.btn_expand.configure(text="Collapse ▲", fg_color=Colors.BG_DARK, text_color=Colors.TEXT_SECONDARY)
                    else:
                        group.btn_expand.configure(text="Expand ▼", fg_color=Colors.BG_INPUT, text_color=Colors.TEXT_PRIMARY)
                    
            # Yield to UI loop
            self.after(2, lambda: _update_next(index + batch_size))
            
        _update_next()

    def set_expanded(self, expanded: bool):
        self.is_expanded = expanded
        for group in self.app_groups.values():
            group.set_expanded(expanded)

    def destroy(self):
        self._destroyed = True
        super().destroy()
