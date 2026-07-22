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
            bind_copy_tooltip(target_lbl, target, "Link copied!")

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
            loading_frame = ctk.CTkFrame(self._rules_scroll, fg_color=Colors.BG_PANEL)
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
            fg_color=Colors.BG_ELEVATED, corner_radius=0,
        )
        row.pack(fill="x", pady=2, padx=4)

        # Left color accent bar
        action = rule['action'] if isinstance(rule, dict) else rule[1]
        accent = Colors.SUCCESS if action == 'allow' else Colors.CAT_USER_BLOCKED
        ctk.CTkFrame(row, width=3, fg_color=accent, corner_radius=0).pack(
            side="left", fill="y",
        )

        # Content area
        content = ctk.CTkFrame(row, fg_color=Colors.BG_PANEL)
        content.pack(side="left", fill="both", expand=True, padx=Spacing.SM, pady=Spacing.SM)
        content.grid_columnconfigure(0, weight=1)

        # Pattern
        pattern = rule['pattern'] if isinstance(rule, dict) else rule[1]
        try:
            pattern = rule['pattern']
        except (KeyError, TypeError):
            pattern = str(rule)
            
        privacy_on = self.engine.db.get_setting("privacy_stream_mode", "false") == "true"
        if privacy_on:
            from netstrip.gui.utils import mask_ip_string
            pattern = mask_ip_string(pattern)
        
        pattern_lbl = ctk.CTkLabel(
            content, text=pattern,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        )
        pattern_lbl.grid(row=0, column=0, sticky="w")
        if pattern:
            bind_copy_tooltip(pattern_lbl, pattern, "Link copied!")

        # App + scope info
        try:
            app = rule['app_name'] or "All Apps"
            scope = rule['scope'] or "global"
            mode_scope = rule.get('mode_scope', 'STANDARD') if isinstance(rule, dict) else (rule['mode_scope'] if 'mode_scope' in rule.keys() else 'STANDARD')
            
            # Format the sub_text nicely
            if mode_scope == "PARANOID":
                mode_str = "🔒 PARANOID Mode Only"
            elif mode_scope == "ALL":
                mode_str = "🌐 ALL Modes"
            else:
                mode_str = "🛡️ STANDARD Mode Only"
                
            sub_text = f"{app} • {scope}  |  {mode_str}"
        except (KeyError, TypeError, IndexError):
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
            fg_color=Colors.BG_PANEL, hover_color=Colors.DANGER_DIM,
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



