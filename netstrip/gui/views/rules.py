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
from netstrip.gui.utils import safe_loop, bind_copy_tooltip


#  AppRulesView — Pending Approvals + User Rules

# ═══════════════════════════════════════════════════
#  AppRulesView
# ═══════════════════════════════════════════════════
class AppRulesView(ctk.CTkFrame):
    """Split view: pending connections on top, user-defined rules on bottom."""

    def __init__(self, master, engine, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PANEL, **kwargs)
        self.engine = engine
        self._destroyed = False

        # ── Top: Pending Approvals ──────────────────────
        self._build_pending_section()

        # ── Bottom: Your Rules ──────────────────────────
        self._build_rules_section()

        # Initial data load deferred
        if hasattr(self, '_pending_after_id'): self.after_cancel(self._pending_after_id)
        self._pending_after_id = self.after(50, self._refresh_pending)
        if hasattr(self, '_rules_after_id'): self.after_cancel(self._rules_after_id)
        self._rules_after_id = self.after(50, self._refresh_rules)

    # ── Build helpers ───────────────────────────────────

    def _build_pending_section(self):
        # Header row
        header = ctk.CTkFrame(self, fg_color=Colors.BG_PANEL)
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
            text_color=Colors.TEXT_PRIMARY, height=30, corner_radius=0,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            command=self._block_all,
        ).pack(side="right", padx=(Spacing.XS, 0))

        ctk.CTkButton(
            header, text="Allow All",
            fg_color=Colors.SUCCESS_DIM, hover_color=Colors.SUCCESS,
            text_color=Colors.TEXT_PRIMARY, height=30, corner_radius=0,
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

    @safe_loop(delay_ms=1000)
    def _refresh_pending(self):
        if getattr(self, '_destroyed', False):
            return
            
        if not self.winfo_ismapped():
            if hasattr(self, '_pending_after_id'): self.after_cancel(self._pending_after_id)
            self._pending_after_id = self.after(1000, self._refresh_pending)
            return

        if not hasattr(self, '_pending_rows'):
            self._pending_rows = {}

        try:
            items = list(self.engine.notifier.pending_items)
        except Exception:
            items = []

        self._pending_badge.configure(text=str(len(items)))
        current_targets = set(item.target for item in items)
        
        # Remove old rows
        for target in list(self._pending_rows.keys()):
            if target not in current_targets:
                self._pending_rows[target].destroy()
                del self._pending_rows[target]

        if not items and not self._pending_rows:
            if not hasattr(self, 'lbl_no_pending'):
                loading_frame = ctk.CTkFrame(self._pending_scroll, fg_color=Colors.BG_PANEL)
                loading_frame.pack(pady=Spacing.XL, expand=True)
                ctk.CTkLabel(loading_frame, text="⏳", font=(Fonts.FAMILY_PRIMARY[0], 36)).pack()
                ctk.CTkLabel(
                    loading_frame, text="No pending connections",
                    text_color=Colors.TEXT_TERTIARY,
                    font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
                ).pack(pady=Spacing.XS)
                self.lbl_no_pending = loading_frame
        else:
            if hasattr(self, 'lbl_no_pending'):
                self.lbl_no_pending.destroy()
                delattr(self, 'lbl_no_pending')
                
            for item in items:
                if item.target not in self._pending_rows:
                    row = self._create_pending_row(item)
                    self._pending_rows[item.target] = row

        # Schedule next refresh
        if not getattr(self, '_destroyed', False):
            if hasattr(self, '_pending_after_id'): self.after_cancel(self._pending_after_id)
            self._pending_after_id = self.after(1000, self._refresh_pending)

    def _create_pending_row(self, item):
        row = ctk.CTkFrame(
            self._pending_scroll,
            fg_color=Colors.BG_ELEVATED, corner_radius=0,
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
        info = ctk.CTkFrame(row, fg_color=Colors.BG_PANEL)
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
        
        privacy_on = self.engine.db.get_setting("privacy_stream_mode", "false") == "true"
        if privacy_on:
            from netstrip.gui.utils import mask_ip_string
            target = mask_ip_string(target)
        target_lbl = ctk.CTkLabel(
            row, text=target,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_SECONDARY,
        )
        target_lbl.grid(row=0, column=2, rowspan=2, padx=Spacing.MD)
        if target:
            bind_copy_tooltip(target_lbl, target)

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

        return row

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

    # ── Rules refresh with widget recycling & signature diffing ────────

    def _refresh_rules(self):
        if getattr(self, '_destroyed', False):
            return

        try:
            rules = list(self.engine.db.get_user_rules())
        except Exception:
            rules = []

        # Fast signature diffing to skip redundant repainting
        privacy_on = self.engine.db.get_setting("privacy_stream_mode", "false") == "true"
        sig = (privacy_on, [(r.get('id'), r.get('pattern'), r.get('action'), r.get('app_name'), r.get('scope'), r.get('mode_scope')) if isinstance(r, dict) else (r[0], r[1], r[2], r[3], r[4]) for r in rules])
        if getattr(self, '_last_rules_sig', None) == sig:
            return
        self._last_rules_sig = sig

        if not hasattr(self, '_rule_widgets_pool'):
            self._rule_widgets_pool = []

        if not rules:
            for w_tuple in self._rule_widgets_pool:
                w_tuple[0].pack_forget()
            if not hasattr(self, 'lbl_no_rules'):
                loading_frame = ctk.CTkFrame(self._rules_scroll, fg_color=Colors.BG_PANEL)
                loading_frame.pack(pady=Spacing.XL, expand=True)
                ctk.CTkLabel(loading_frame, text="⏳", font=(Fonts.FAMILY_PRIMARY[0], 36)).pack()
                ctk.CTkLabel(
                    loading_frame, text="No rules defined yet",
                    text_color=Colors.TEXT_TERTIARY,
                    font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
                ).pack(pady=Spacing.XS)
                self.lbl_no_rules = loading_frame
            return
        else:
            if hasattr(self, 'lbl_no_rules'):
                self.lbl_no_rules.destroy()
                delattr(self, 'lbl_no_rules')

        # Grow pool if needed
        while len(self._rule_widgets_pool) < len(rules):
            row = ctk.CTkFrame(self._rules_scroll, fg_color=Colors.BG_ELEVATED, corner_radius=0)
            accent = ctk.CTkFrame(row, width=3, corner_radius=0)
            accent.pack(side="left", fill="y")

            content = ctk.CTkFrame(row, fg_color=Colors.BG_PANEL)
            content.pack(side="left", fill="both", expand=True, padx=Spacing.SM, pady=Spacing.SM)
            content.grid_columnconfigure(0, weight=1)

            pattern_lbl = ctk.CTkLabel(
                content, text="",
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE, Fonts.WEIGHT_BOLD),
                text_color=Colors.TEXT_PRIMARY,
            )
            pattern_lbl.grid(row=0, column=0, sticky="w")

            sub_lbl = ctk.CTkLabel(
                content, text="",
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
                text_color=Colors.TEXT_SECONDARY,
            )
            sub_lbl.grid(row=1, column=0, sticky="w")

            date_lbl = ctk.CTkLabel(
                content, text="",
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
                text_color=Colors.TEXT_TERTIARY,
            )
            date_lbl.grid(row=0, column=1, rowspan=2, padx=Spacing.SM)

            del_btn = ctk.CTkButton(
                content, text=Icons.TRASH,
                fg_color=Colors.BG_PANEL, hover_color=Colors.DANGER_DIM,
                width=30, height=30, corner_radius=6,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
            )
            del_btn.grid(row=0, column=2, rowspan=2, padx=(Spacing.XS, 0))

            self._rule_widgets_pool.append((row, accent, content, pattern_lbl, sub_lbl, date_lbl, del_btn))

        # Update and map active rows in place
        for i, rule in enumerate(rules):
            row, accent, content, pattern_lbl, sub_lbl, date_lbl, del_btn = self._rule_widgets_pool[i]

            action = rule.get('action') if isinstance(rule, dict) else rule[1]
            accent_color = Colors.SUCCESS if action == 'allow' else Colors.CAT_USER_BLOCKED
            accent.configure(fg_color=accent_color)

            # Pattern
            pattern = rule.get('pattern') if isinstance(rule, dict) else rule[1]
            if privacy_on:
                from netstrip.gui.utils import mask_ip_string
                display_pattern = mask_ip_string(str(pattern))
            else:
                display_pattern = str(pattern)

            pattern_lbl.configure(text=display_pattern)
            if pattern:
                bind_copy_tooltip(pattern_lbl, str(pattern))

            # App + scope
            try:
                app = rule.get('app_name') or "All Apps"
                scope = rule.get('scope') or "global"
                mode_scope = rule.get('mode_scope', 'STANDARD') if isinstance(rule, dict) else (rule['mode_scope'] if 'mode_scope' in rule.keys() else 'STANDARD')
                
                if mode_scope in ("PARANOID", "GHOST"):
                    mode_str = "👻 GHOST Mode Only"
                elif mode_scope == "ALL":
                    mode_str = "🌐 ALL Modes"
                else:
                    mode_str = "🔰 NORMAL / LOOSE Mode Only"
                    
                sub_text = f"{app} • {scope}  |  {mode_str}"
            except Exception:
                sub_text = ""
            sub_lbl.configure(text=sub_text)

            # Created date
            try:
                created = rule.get('created_at', '')
                if isinstance(created, str) and created:
                    dt = datetime.fromisoformat(created)
                    date_str = dt.strftime("%b %d, %Y")
                else:
                    date_str = str(created) if created else ""
            except Exception:
                date_str = ""
            date_lbl.configure(text=date_str)

            # Delete button
            rule_id = rule.get('id') if isinstance(rule, dict) else rule[0]
            del_btn.configure(command=lambda rid=rule_id: self._delete_rule(rid))

            if not row.winfo_ismapped():
                row.pack(fill="x", pady=2, padx=4)

        # Unmap surplus rows
        for j in range(len(rules), len(self._rule_widgets_pool)):
            surplus_row = self._rule_widgets_pool[j][0]
            if surplus_row.winfo_ismapped():
                surplus_row.pack_forget()

    def _delete_rule(self, rule_id):
        if rule_id is not None:
            try:
                self.engine.db.delete_user_rule(rule_id)
            except Exception:
                pass
        self._last_rules_sig = None
        self._refresh_rules()

    # ── Lifecycle ───────────────────────────────────────

    def destroy(self):
        self._destroyed = True
        super().destroy()



