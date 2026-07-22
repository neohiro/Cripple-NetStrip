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


# ═══════════════════════════════════════════════════
#  AppRulesView — Pending Approvals + User Rules
# ═══════════════════════════════════════════════════

class AppRulesView(ctk.CTkFrame):
    """Split view: pending connections on top, user-defined rules on bottom."""

    def __init__(self, master, engine, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.engine = engine
        self._destroyed = False

        # ── Top: Pending Approvals ──────────────────────
        self._build_pending_section()

        # ── Bottom: Your Rules ──────────────────────────
        self._build_rules_section()

        # Initial data load deferred
        self.after(50, self._refresh_pending)
        self.after(50, self._refresh_rules)

    # ── Build helpers ───────────────────────────────────

    def _build_pending_section(self):
        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, Spacing.SM))

        ctk.CTkLabel(
            header, text="Pending Approvals",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        self._pending_badge = ctk.CTkLabel(
            header, text="0",
            fg_color=Colors.WARNING_DIM, text_color=Colors.WARNING,
            corner_radius=10, height=24, width=36,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS, Fonts.WEIGHT_BOLD),
        )
        self._pending_badge.pack(side="left", padx=(Spacing.SM, 0))

        # Bulk action buttons (right side)
        ctk.CTkButton(
            header, text="Block All",
            fg_color="#4a1525", hover_color="#f43f5e",
            text_color=Colors.TEXT_PRIMARY, height=30, corner_radius=8,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            command=self._block_all,
        ).pack(side="right", padx=(Spacing.XS, 0))

        ctk.CTkButton(
            header, text="Allow All",
            fg_color=Colors.SUCCESS_DIM, hover_color=Colors.SUCCESS,
            text_color=Colors.TEXT_PRIMARY, height=30, corner_radius=8,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            command=self._allow_all,
        ).pack(side="right", padx=(Spacing.XS, 0))

        # Scrollable pending list
        self._pending_scroll = ctk.CTkScrollableFrame(
            self, height=250, **CTK_FRAME_STYLE,
        )
        self._pending_scroll.pack(fill="x", pady=(0, Spacing.LG))

    def _build_rules_section(self):
        ctk.CTkLabel(
            self, text="Your Rules",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.SM))

        self._rules_scroll = ctk.CTkScrollableFrame(self, **CTK_FRAME_STYLE)
        self._rules_scroll.pack(fill="both", expand=True)

    # ── Pending refresh ─────────────────────────────────

    def _refresh_pending(self):
        if self._destroyed:
            return

        # Clear existing rows
        for w in self._pending_scroll.winfo_children():
            w.destroy()

        try:
            items = list(self.engine.notifier.pending_items)
        except Exception:
            items = []

        self._pending_badge.configure(text=str(len(items)))

        if not items:
            loading_frame = ctk.CTkFrame(self._pending_scroll, fg_color="transparent")
            loading_frame.pack(pady=Spacing.XL, expand=True)
            ctk.CTkLabel(loading_frame, text="⏳", font=(Fonts.FAMILY_PRIMARY[0], 36)).pack()
            ctk.CTkLabel(
                loading_frame, text="No pending connections",
                text_color=Colors.TEXT_TERTIARY,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            ).pack(pady=Spacing.XS)
        else:
            for item in items:
                self._create_pending_row(item)

        # Schedule next refresh
        if not self._destroyed:
            self.after(1000, self._refresh_pending)

    def _create_pending_row(self, item):
        row = ctk.CTkFrame(
            self._pending_scroll,
            fg_color=Colors.BG_ELEVATED, corner_radius=8,
        )
        row.pack(fill="x", pady=2, padx=4)
        row.grid_columnconfigure(1, weight=1)

        # Colored category dot
        cat = getattr(item, 'category', 'unknown')
        ctk.CTkLabel(
            row, text="●",
            font=(Fonts.FAMILY_PRIMARY[0], 12),
            text_color=get_category_color(cat),
        ).grid(row=0, column=0, rowspan=2, padx=(Spacing.SM, Spacing.XS), pady=Spacing.SM)

        # Process info
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.grid(row=0, column=1, rowspan=2, sticky="w", pady=Spacing.XS)

        ctk.CTkLabel(
            info, text=getattr(item, 'process_name', 'Unknown'),
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        path = getattr(item, 'process_path', '')
        if path:
            ctk.CTkLabel(
                info, text=path,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
                text_color=Colors.TEXT_TERTIARY,
            ).pack(anchor="w")

        # Target domain/IP
        target = getattr(item, 'domain', '') or getattr(item, 'ip', '') or str(getattr(item, 'target', ''))
        ctk.CTkLabel(
            row, text=target,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_SECONDARY,
        ).grid(row=0, column=2, rowspan=2, padx=Spacing.MD)

        # Allow button (Hide for Malware/Tracker to enforce strict block)
        if cat not in ['malware', 'tracker']:
            ctk.CTkButton(
                row, text="Allow",
                fg_color=Colors.SUCCESS_DIM, hover_color=Colors.SUCCESS,
                text_color=Colors.TEXT_PRIMARY,
                width=70, height=28, corner_radius=6,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
                command=lambda i=item: self._resolve_item(i, 'allow'),
            ).grid(row=0, column=3, rowspan=2, padx=(0, Spacing.XS), pady=Spacing.SM)

        # Block button
        ctk.CTkButton(
            row, text="Block",
            fg_color="#4a1525", hover_color="#f43f5e",
            text_color=Colors.TEXT_PRIMARY,
            width=70, height=28, corner_radius=6,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            command=lambda i=item: self._resolve_item(i, 'block'),
        ).grid(row=0, column=4, rowspan=2, padx=(0, Spacing.SM), pady=Spacing.SM)

    def _resolve_item(self, item, action):
        try:
            self.engine.notifier.resolve(item, action)
        except Exception:
            pass
        self._refresh_pending()
        self._refresh_rules()

    def _allow_all(self):
        try:
            self.engine.notifier.resolve_all('allow')
        except Exception:
            pass
        self._refresh_pending()
        self._refresh_rules()

    def _block_all(self):
        try:
            self.engine.notifier.resolve_all('block')
        except Exception:
            pass
        self._refresh_pending()
        self._refresh_rules()

    # ── Rules refresh ───────────────────────────────────

    def _refresh_rules(self):
        if self._destroyed:
            return

        for w in self._rules_scroll.winfo_children():
            w.destroy()

        try:
            rules = list(self.engine.db.get_user_rules())
        except Exception:
            rules = []

        if not rules:
            loading_frame = ctk.CTkFrame(self._rules_scroll, fg_color="transparent")
            loading_frame.pack(pady=Spacing.XL, expand=True)
            ctk.CTkLabel(loading_frame, text="⏳", font=(Fonts.FAMILY_PRIMARY[0], 36)).pack()
            ctk.CTkLabel(
                loading_frame, text="No rules defined yet",
                text_color=Colors.TEXT_TERTIARY,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            ).pack(pady=Spacing.XS)
            return

        for rule in rules:
            self._create_rule_row(rule)

    def _create_rule_row(self, rule):
        row = ctk.CTkFrame(
            self._rules_scroll,
            fg_color=Colors.BG_ELEVATED, corner_radius=8,
        )
        row.pack(fill="x", pady=2, padx=4)

        # Left color accent bar
        action = rule['action'] if isinstance(rule, dict) else rule[1]
        accent = Colors.SUCCESS if action == 'allow' else Colors.CAT_USER_BLOCKED
        ctk.CTkFrame(row, width=3, fg_color=accent, corner_radius=0).pack(
            side="left", fill="y",
        )

        # Content area
        content = ctk.CTkFrame(row, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=Spacing.SM, pady=Spacing.SM)
        content.grid_columnconfigure(0, weight=1)

        # Pattern
        pattern = rule['pattern'] if isinstance(rule, dict) else rule[1]
        try:
            pattern = rule['pattern']
        except (KeyError, TypeError):
            pattern = str(rule)
        ctk.CTkLabel(
            content, text=pattern,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        # App + scope info
        try:
            app = rule['app_name'] or "All Apps"
            scope = rule['scope'] or "global"
            sub_text = f"{app} • {scope}"
        except (KeyError, TypeError):
            sub_text = ""
        if sub_text:
            ctk.CTkLabel(
                content, text=sub_text,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
                text_color=Colors.TEXT_SECONDARY,
            ).grid(row=1, column=0, sticky="w")

        # Created date
        try:
            created = rule['created_at']
            if isinstance(created, str):
                dt = datetime.fromisoformat(created)
                date_str = dt.strftime("%b %d, %Y")
            else:
                date_str = str(created)
        except Exception:
            date_str = ""
        if date_str:
            ctk.CTkLabel(
                content, text=date_str,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
                text_color=Colors.TEXT_TERTIARY,
            ).grid(row=0, column=1, rowspan=2, padx=Spacing.SM)

        # Delete button
        try:
            rule_id = rule['id']
        except (KeyError, TypeError):
            rule_id = None

        ctk.CTkButton(
            content, text=Icons.TRASH,
            fg_color="transparent", hover_color=Colors.DANGER_DIM,
            width=30, height=30, corner_radius=6,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
            command=lambda rid=rule_id: self._delete_rule(rid),
        ).grid(row=0, column=2, rowspan=2, padx=(Spacing.XS, 0))

    def _delete_rule(self, rule_id):
        if rule_id is not None:
            try:
                self.engine.db.delete_user_rule(rule_id)
            except Exception:
                pass
        self._refresh_rules()

    # ── Lifecycle ───────────────────────────────────────

    def destroy(self):
        self._destroyed = True
        super().destroy()


# ═══════════════════════════════════════════════════
#  BlocklistView — Category Stats + Domain Search
# ═══════════════════════════════════════════════════

class BlocklistView(ctk.CTkFrame):
    """Blocklist stats grid and domain search interface."""

    def __init__(self, master, engine, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.engine = engine
        self._destroyed = False

        # Header
        ctk.CTkLabel(
            self, text="Blocklist Manager",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XL, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.MD))

        # Stats grid
        self._build_stats_grid()

        # Search section
        self._build_search_section()

    def _build_stats_grid(self):
        grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(0, Spacing.LG))
        grid_frame.grid_columnconfigure((0, 1), weight=1)

        try:
            metadata = getattr(self.engine.blocklist, 'sources_metadata', {})
        except Exception:
            metadata = {}

        if not metadata:
            ctk.CTkLabel(grid_frame, text="Blocklists are loading...", text_color=Colors.TEXT_TERTIARY).pack(pady=Spacing.LG)
            return

        for idx, (category, sources) in enumerate(metadata.items()):
            card = ctk.CTkFrame(grid_frame, **CTK_FRAME_STYLE)
            card.grid(
                row=idx // 2, column=idx % 2,
                sticky="ew", padx=Spacing.XS, pady=Spacing.XS,
            )

            # Colored top bar
            ctk.CTkFrame(
                card, height=3,
                fg_color=get_category_color(category),
                corner_radius=0,
            ).pack(fill="x")

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=Spacing.MD, pady=Spacing.SM)

            # Icon + label
            header_frame = ctk.CTkFrame(inner, fg_color="transparent")
            header_frame.pack(fill="x")
            ctk.CTkLabel(
                header_frame,
                text=f"{get_category_icon(category)}  {get_category_label(category).upper()}",
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
                text_color=Colors.TEXT_PRIMARY,
            ).pack(side="left")
            
            total_size = sum(s.get('size', 0) for s in sources)
            ctk.CTkLabel(
                header_frame,
                text=f"{total_size:,} domains",
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
                text_color=get_category_color(category),
            ).pack(side="right")
            
            # Sources list
            sources_frame = ctk.CTkFrame(inner, fg_color="transparent")
            sources_frame.pack(fill="x", pady=(Spacing.SM, 0))
            
            for s in sources:
                src_row = ctk.CTkFrame(sources_frame, fg_color="transparent")
                src_row.pack(fill="x", pady=1)
                ctk.CTkLabel(src_row, text=s.get('filename', 'Unknown'), font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS), text_color=Colors.TEXT_SECONDARY).pack(side="left")
                ctk.CTkLabel(src_row, text=f"Updated: {s.get('updated', 'Unknown')}", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS), text_color=Colors.TEXT_TERTIARY).pack(side="right")

    def _build_search_section(self):
        ctk.CTkLabel(
            self, text="Search Domains",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.SM))

        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.pack(fill="x", pady=(0, Spacing.SM))

        self._search_entry = ctk.CTkEntry(
            search_row, placeholder_text="Search blocklists... (e.g. telemetry)",
            **CTK_ENTRY_STYLE,
        )
        self._search_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.SM))
        self._search_entry.bind("<Return>", lambda e: self._do_search())

        ctk.CTkButton(
            search_row, text=Icons.SEARCH,
            width=40, height=36, corner_radius=8,
            fg_color=Colors.ACCENT_PRIMARY,
            hover_color=Colors.ACCENT_LIGHT,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG),
            command=self._do_search,
        ).pack(side="right")

        self._results_scroll = ctk.CTkScrollableFrame(self, **CTK_FRAME_STYLE)
        self._results_scroll.pack(fill="both", expand=True)

    def _do_search(self):
        query = self._search_entry.get().strip()

        for w in self._results_scroll.winfo_children():
            w.destroy()

        if not query:
            return

        try:
            results = self.engine.blocklist.search(query, limit=100)
        except Exception as e:
            results = []

        if not results:
            ctk.CTkLabel(
                self._results_scroll, text=f"No matches found for '{query}'",
                text_color=Colors.TEXT_TERTIARY,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            ).pack(pady=Spacing.LG)
            return

        ctk.CTkLabel(
            self._results_scroll, text=f"Showing top {len(results)} matches for '{query}':",
            text_color=Colors.TEXT_SECONDARY,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS, "italic"),
        ).pack(anchor="w", padx=Spacing.SM, pady=(0, Spacing.SM))

        for r in results:
            row = ctk.CTkFrame(
                self._results_scroll,
                fg_color=Colors.BG_ELEVATED, corner_radius=8,
            )
            row.pack(fill="x", pady=2, padx=4)

            domain = r.get('domain', 'Unknown')
            cat = r.get('category', 'unknown')

            ctk.CTkLabel(
                row, text=domain,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, "bold"),
                text_color=Colors.TEXT_PRIMARY,
            ).pack(side="left", padx=Spacing.MD, pady=Spacing.SM)

            # Quick Actions
            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.pack(side="right", padx=Spacing.SM, pady=Spacing.SM)
            
            def make_action(d=domain, act='allow'):
                self.engine.db.add_user_rule({
                    'pattern': d,
                    'action': act,
                    'scope': 'global',
                    'app_name': None,
                    'category': f'user_{act}ed',
                    'note': f"Manual {act} from search"
                })
                # Refresh blocklist memory
                rules = self.engine.db.get_user_rules()
                self.engine.blocklist.sync_user_rules(rules)
                
            ctk.CTkButton(
                btn_frame, text="Whitelist", width=60, height=22, corner_radius=4,
                fg_color=Colors.SUCCESS_DIM, hover_color=Colors.SUCCESS, text_color=Colors.TEXT_PRIMARY,
                font=(Fonts.FAMILY_PRIMARY[0], 10), command=lambda d=domain: make_action(d, 'allow')
            ).pack(side="left", padx=(0, 4))
            
            ctk.CTkLabel(
                btn_frame, text=get_category_label(cat).upper(),
                fg_color=get_category_color(cat),
                corner_radius=4, text_color="white",
                font=(Fonts.FAMILY_PRIMARY[0], 9, "bold"),
                height=22, width=80,
            ).pack(side="right")

    def destroy(self):
        self._destroyed = True
        super().destroy()


# ═══════════════════════════════════════════════════
#  LogView — Connection Log Table
# ═══════════════════════════════════════════════════

class LogView(ctk.CTkFrame):
    """Searchable, auto-refreshing connection log with category color-coding."""

    COL_WEIGHTS = (1, 2, 3, 1, 1)

    def __init__(self, master, engine, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.engine = engine
        self._destroyed = False

        # Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, Spacing.SM))

        ctk.CTkLabel(
            header_frame, text="Connection Log",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XL, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkButton(
            header_frame, text="Export Logs", width=100, height=28, corner_radius=6,
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BG_PANEL,
            text_color=Colors.TEXT_SECONDARY,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            command=self._export_logs,
        ).pack(side="right")

        # Search bar
        self._filter_entry = ctk.CTkEntry(
            self, placeholder_text="Filter logs...", **CTK_ENTRY_STYLE,
        )
        self._filter_entry.pack(fill="x", pady=(0, Spacing.SM))
        self._filter_entry.bind("<KeyRelease>", lambda e: self._refresh_logs())
        
    def _export_logs(self):
        """Exports the entire connection log to the user's Documents folder."""
        import os
        from datetime import datetime
        try:
            # Get path to Documents folder
            docs_dir = os.path.join(os.path.expanduser("~"), "Documents")
            if not os.path.exists(docs_dir):
                docs_dir = os.path.expanduser("~")
                
            filename = f"Cripple_Logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = os.path.join(docs_dir, filename)
            
            # Fetch all logs (or max 10000 to prevent massive files)
            rows = list(self.engine.db.get_recent_connections(10000))
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("Cripple Connection Log Export\n")
                f.write(f"Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 80 + "\n")
                f.write(f"{'TIME':<22} | {'PROCESS':<25} | {'DOMAIN/IP':<30} | {'CATEGORY':<12} | {'ACTION':<8}\n")
                f.write("-" * 80 + "\n")
                
                for r in reversed(rows):
                    # Format time
                    ts = r['timestamp']
                    if isinstance(ts, str):
                        time_str = ts[:19] # Cut off ms
                    else:
                        time_str = str(ts)
                        
                    proc = str(r['process_name'] or 'Unknown')[:24]
                    domain = str(r['domain'] or r['ip'] or 'Unknown')[:29]
                    cat = str(r['category'] or 'unknown').upper()
                    act = str(r['action'] or 'unknown').upper()
                    
                    f.write(f"{time_str:<22} | {proc:<25} | {domain:<30} | {cat:<12} | {act:<8}\n")
                    
            # Notify user
            # self.engine.notifier.notify(f"Logs exported successfully to Documents/{filename}")
            import tkinter.messagebox
            tkinter.messagebox.showinfo("Export Successful", f"Logs exported to:\n{filepath}")
        except Exception as e:
            import tkinter.messagebox
            tkinter.messagebox.showerror("Export Failed", f"Failed to export logs:\n{str(e)}")

        # Column headers
        hdr = ctk.CTkFrame(self, fg_color=Colors.BG_PANEL, corner_radius=8, height=36)
        hdr.pack(fill="x", pady=(0, Spacing.XS))
        for i, (label, w) in enumerate(zip(
            ["Time", "Process", "Domain/IP", "Category", "Action"],
            self.COL_WEIGHTS,
        )):
            hdr.grid_columnconfigure(i, weight=w)
            ctk.CTkLabel(
                hdr, text=label,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
                text_color=Colors.TEXT_TERTIARY,
            ).grid(row=0, column=i, sticky="w", padx=Spacing.SM, pady=Spacing.XS)

        # Scrollable body
        self._log_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._log_scroll.pack(fill="both", expand=True)

        self.after(50, self._refresh_logs)

    def _refresh_logs(self):
        if self._destroyed:
            return

        try:
            rows = list(self.engine.db.get_recent_connections(200))
        except Exception:
            rows = []

        query = self._filter_entry.get().strip().lower()
        if query:
            rows = [
                r for r in rows
                if query in (r['process_name'] or '').lower()
                or query in (r['domain'] or '').lower()
                or query in (r['ip'] or '').lower()
            ]
            
        if not hasattr(self, '_known_logs') or getattr(self, '_last_query', None) != query:
            self._last_query = query
            self._known_logs = set()
            for w in self._log_scroll.winfo_children():
                w.destroy()

        if not rows:
            if not self._known_logs:
                loading_frame = ctk.CTkFrame(self._log_scroll, fg_color="transparent")
                loading_frame.pack(pady=Spacing.XL, expand=True)
                ctk.CTkLabel(loading_frame, text="⏳", font=(Fonts.FAMILY_PRIMARY[0], 36)).pack()
                ctk.CTkLabel(
                    loading_frame, text="Listening for connections...",
                    text_color=Colors.TEXT_TERTIARY,
                    font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
                ).pack(pady=Spacing.XS)
        else:
            # Remove loading frame if it exists
            children = self._log_scroll.winfo_children()
            if not self._known_logs and children:
                for w in children:
                    w.destroy()
            
            # Rows are returned newest first. We want to insert new ones at the very top.
            # We iterate in reverse so that the newest is inserted last (at the top).
            for r in reversed(rows):
                row_id = r['id']
                if row_id not in self._known_logs:
                    self._known_logs.add(row_id)
                    row_widget = self._create_log_row(r)
                    
                    # Insert at the top
                    current_children = self._log_scroll.winfo_children()
                    if len(current_children) > 1: # >1 because row_widget is already appended by _create_log_row
                        row_widget.pack(before=current_children[0])
                        
            # Truncate old rows to keep UI snappy
            current_children = self._log_scroll.winfo_children()
            if len(current_children) > 200:
                for w in current_children[200:]:
                    w.destroy()

        if not self._destroyed:
            self.after(2000, self._refresh_logs)

    def _create_log_row(self, row):
        frame = ctk.CTkFrame(
            self._log_scroll,
            fg_color=Colors.BG_PANEL, corner_radius=8,
            border_width=1, border_color=Colors.BORDER_SUBTLE,
        )
        frame.pack(fill="x", pady=1, padx=2)
        for i, w in enumerate(self.COL_WEIGHTS):
            frame.grid_columnconfigure(i, weight=w)

        # Time
        try:
            ts = row['timestamp']
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts)
            else:
                dt = ts
            time_str = dt.strftime("%H:%M:%S")
        except Exception:
            time_str = str(row['timestamp'])[:8]

        ctk.CTkLabel(
            frame, text=time_str,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
            text_color=Colors.TEXT_TERTIARY,
        ).grid(row=0, column=0, sticky="w", padx=Spacing.SM, pady=Spacing.XS)

        # Process (with colored dot)
        proc_frame = ctk.CTkFrame(frame, fg_color="transparent")
        proc_frame.grid(row=0, column=1, sticky="w", padx=Spacing.XS, pady=Spacing.XS)
        cat = row['category'] or 'unknown'
        ctk.CTkLabel(
            proc_frame, text="●",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
            text_color=get_category_color(cat),
        ).pack(side="left", padx=(0, Spacing.XS))
        ctk.CTkLabel(
            proc_frame, text=row['process_name'] or '',
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        # Domain/IP
        domain = row['domain'] or row['ip'] or ''
        ctk.CTkLabel(
            frame, text=domain,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_SECONDARY,
        ).grid(row=0, column=2, sticky="w", padx=Spacing.SM, pady=Spacing.XS)

        # Category badge
        ctk.CTkLabel(
            frame, text=get_category_label(cat),
            fg_color=get_category_color(cat), corner_radius=6,
            text_color="white",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
            height=22,
        ).grid(row=0, column=3, padx=Spacing.SM, pady=Spacing.XS)

        # Action icon
        action = row['action'] or ''
        if action == 'allow':
            icon, color = Icons.ALLOWED, Colors.SUCCESS
        else:
            icon, color = Icons.BLOCKED, Colors.DANGER
        ctk.CTkLabel(
            frame, text=icon,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=color,
        ).grid(row=0, column=4, padx=Spacing.SM, pady=Spacing.XS)

        return frame

    def destroy(self):
        self._destroyed = True
        super().destroy()


# ═══════════════════════════════════════════════════
#  SettingsView — Configuration & About
# ═══════════════════════════════════════════════════

class SettingsView(ctk.CTkFrame):
    """Application settings: autostart, DNS upstream, and about info."""

    def __init__(self, master, engine, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.engine = engine
        self._destroyed = False

        # Header
        ctk.CTkLabel(
            self, text="Settings",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XL, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.LG))

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True)

        self._build_general_card()
        self._build_network_card()
        self._build_about_card()

    def _build_general_card(self):
        card = ctk.CTkFrame(self.scroll_frame, **CTK_FRAME_STYLE)
        card.pack(fill="x", pady=(0, Spacing.MD))

        ctk.CTkLabel(
            card, text="General",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))

        # Autostart toggle
        self._add_switch_row(card, "Start on Boot", 'autostart')

        # Minimize to tray toggle
        self._add_switch_row(card, "Minimize to Tray", 'minimize_to_tray')
        self._add_subtitle(card, "Keep Cripple running in the background when closing the window.")

        # IP Flux Tolerance
        self._add_switch_row(card, "IP Flux Tolerance", 'ip_flux_tolerance')
        self._add_subtitle(card, "Ignore Public IP changes for Auto-Killswitch (useful if using a VPN).")

        # Smart Shield
        self._add_switch_row(card, "Smart Shield", 'smart_paranoid_mode')
        self._add_subtitle(card, "Auto-escalate to Paranoid Mode when severe threats are detected.")
        
        # Block System Connections
        self._add_switch_row(card, "Block System Connections", 'block_system_connections')
        self._add_subtitle(card, "Disable all non-vital background OS services globally (can disrupt updates).")

        # Bottom padding
        ctk.CTkFrame(card, fg_color="transparent", height=Spacing.SM).pack()

    def _add_subtitle(self, parent, text):
        ctk.CTkLabel(
            parent, text=text,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
            text_color=Colors.TEXT_TERTIARY,
            justify="left"
        ).pack(anchor="w", padx=Spacing.LG, pady=(0, Spacing.SM))

    def _add_switch_row(self, parent, label_text, setting_key):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=Spacing.LG, pady=Spacing.XS)

        ctk.CTkLabel(
            row, text=label_text,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        try:
            default_val = 'true' if setting_key == 'smart_paranoid_mode' else 'false'
            current = self.engine.db.get_setting(setting_key, default_val) == 'true'
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

        row = ctk.CTkFrame(card, fg_color="transparent")
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

        self.dns_options_map = {
            "Cloudflare (1.1.1.1)": "1.1.1.1",
            "Google (8.8.8.8)": "8.8.8.8",
            "Quad9 (9.9.9.9)": "9.9.9.9",
        }
        
        # If we detected a local proxy (like dnscrypt-proxy), add it
        if dns_val.startswith("127.") and dns_val != "127.0.0.2":
            tool_name = self.engine.db.get_setting("local_dns_tool", "Detected Tool")
            self.dns_options_map[f"Local Proxy ({tool_name})"] = dns_val
        elif dns_val == "::1":
            tool_name = self.engine.db.get_setting("local_dns_tool", "Detected Tool")
            self.dns_options_map[f"Local Proxy ({tool_name})"] = dns_val
            
        # Find the key for the current value
        current_option = "Cloudflare (1.1.1.1)"
        for k, v in self.dns_options_map.items():
            if v == dns_val:
                current_option = k
                break

        self._dns_menu = ctk.CTkOptionMenu(
            row, width=200, 
            values=list(self.dns_options_map.keys()),
            fg_color=Colors.BG_INPUT,
            button_color=Colors.BG_INPUT,
            button_hover_color=Colors.BG_ELEVATED,
            dropdown_fg_color=Colors.BG_ELEVATED,
            dropdown_hover_color=Colors.BG_PANEL,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM)
        )
        self._dns_menu.pack(side="right", padx=(Spacing.SM, 0))
        self._dns_menu.set(current_option)

        ctk.CTkButton(
            row, text="Save", width=60, height=32, corner_radius=8,
            fg_color=Colors.ACCENT_PRIMARY, hover_color=Colors.ACCENT_LIGHT,
            text_color=Colors.TEXT_PRIMARY,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            command=self._save_dns,
        ).pack(side="right", padx=(Spacing.SM, 0))

        self._build_scheduler_card()
        self._build_migration_card()
        self._build_about_card()

    def _save_dns(self):
        try:
            selected_name = self._dns_menu.get()
            selected_ip = self.dns_options_map.get(selected_name, "1.1.1.1")
            self.engine.db.set_setting('dns_upstream', selected_ip)
            if hasattr(self.engine, 'on_status') and self.engine.on_status:
                self.engine.on_status(f"DNS Upstream changed to {selected_name}")
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

        row = ctk.CTkFrame(card, fg_color="transparent")
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
        card = ctk.CTkFrame(self, **CTK_FRAME_STYLE)
        card.pack(fill="x", pady=(0, Spacing.MD))

        ctk.CTkLabel(
            card, text="Backup & Migration",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        
        self._add_subtitle(card, "Export or import your complete Cripple settings and App Rules as a JSON profile.")

        row = ctk.CTkFrame(card, fg_color="transparent")
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

    def _build_about_card(self):
        card = ctk.CTkFrame(self, **CTK_FRAME_STYLE)
        card.pack(fill="x")

        ctk.CTkLabel(
            card, text="About",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))

        ctk.CTkLabel(
            card, text="Cripple v0.1.0-alpha",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.LG)

        ctk.CTkLabel(
            card, text="Intelligent Network Debloater — Strip away the noise.",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.XS, 0))

        ctk.CTkLabel(
            card, text="Built with Python & CustomTkinter",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
            text_color=Colors.TEXT_TERTIARY,
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.XS, Spacing.LG))

        self._build_credits()

    def _build_credits(self):
        credits_frame = ctk.CTkFrame(self, fg_color="transparent")
        credits_frame.pack(fill="x", side="bottom", pady=Spacing.MD)
        
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

# ═══════════════════════════════════════════════════
#  TorView — Provisional Tor Integration UI
# ═══════════════════════════════════════════════════

class TorView(ctk.CTkFrame):
    """Provisional UI for Tor app-specific routing."""

    def __init__(self, master, engine, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
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
        setup_card = ctk.CTkFrame(self, **CTK_FRAME_STYLE)
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
        row = ctk.CTkFrame(setup_card, fg_color="transparent")
        row.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.LG))
        
        self.app_entry = ctk.CTkEntry(row, placeholder_text="e.g. chrome.exe", **CTK_ENTRY_STYLE, width=200)
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
