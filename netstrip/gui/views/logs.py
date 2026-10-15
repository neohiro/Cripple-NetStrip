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
from netstrip.gui.utils import safe_loop, bind_copy_tooltip, apply_treeview_scroll_patch, add_bloom_hover, add_bloom_press
import tkinter.ttk as ttk
import csv
import json


#  AppRulesView — Pending Approvals + User Rules

# ═══════════════════════════════════════════════════
#  LogView
# ═══════════════════════════════════════════════════
class LogView(ctk.CTkFrame):
    """Searchable, auto-refreshing connection log with category color-coding."""

    COL_CONFIGS = [
        {"weight": 0, "minsize": 110},  # Time
        {"weight": 0, "minsize": 160},  # Process
        {"weight": 1, "minsize": 200},  # Domain/IP (takes up available slack)
        {"weight": 0, "minsize": 120},  # Category
        {"weight": 0, "minsize": 110},  # Action
    ]

    def __init__(self, master, engine, **kwargs):
        super().__init__(master, fg_color=Colors.BG_DARK, **kwargs)
        self.engine = engine
        self._destroyed = False

        # Header Frame
        header_frame = ctk.CTkFrame(self, fg_color=Colors.BG_DARK)
        header_frame.pack(fill="x", pady=(0, Spacing.SM))

        ctk.CTkLabel(
            header_frame, text="Connection Log",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XL, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        self.btn_export = ctk.CTkButton(
            header_frame, text="Export Logs", width=100, height=28, corner_radius=6,
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BG_PANEL,
            text_color=Colors.TEXT_SECONDARY,
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            command=self._show_export_modal,
        )
        self.btn_export.pack(side="right")
        
        # Bloom hover for export button
        try:
            add_bloom_hover(self.btn_export, glow_color=Colors.ACCENT_CYAN, scale_factor=1.03)
            add_bloom_press(self.btn_export, glow_color=Colors.ACCENT_CYAN_LIGHT)
        except Exception:
            pass

        # Search bar
        self._filter_entry = ctk.CTkEntry(
            self, placeholder_text="Filter logs...", **CTK_ENTRY_STYLE,
        )
        self._filter_entry.pack(fill="x", pady=(0, Spacing.SM))
        self._filter_entry.bind("<KeyRelease>", lambda e: self._refresh_logs())

        # Apply Treeview styling
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.Treeview",
                        background=Colors.BG_PANEL,
                        foreground=Colors.TEXT_PRIMARY,
                        rowheight=36,
                        fieldbackground=Colors.BG_PANEL,
                        bordercolor=Colors.BORDER_SUBTLE,
                        borderwidth=0,
                        font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM))
        style.map('Dark.Treeview', background=[('selected', Colors.BG_ELEVATED)])
        style.configure("Dark.Treeview.Heading",
                        background=Colors.BG_DARK,
                        foreground=Colors.TEXT_SECONDARY,
                        relief="flat",
                        font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD))
        style.map("Dark.Treeview.Heading", background=[('active', Colors.BG_PANEL)])

        # Scrollable body (Native Treeview for zero lag)
        self.tree_frame = ctk.CTkFrame(self, fg_color=Colors.BG_DARK)
        self.tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(self.tree_frame, columns=("time", "proc", "domain", "cat", "act"), show="headings", style="Dark.Treeview", height=30)
        self.tree.heading("time", text="Time", anchor="w")
        self.tree.heading("proc", text="Process", anchor="w")
        self.tree.heading("domain", text="Domain/IP", anchor="w")
        self.tree.heading("cat", text="Category", anchor="w")
        self.tree.heading("act", text="Action", anchor="w")

        self.tree.column("time", width=90, minwidth=80, stretch=False)
        self.tree.column("proc", width=200, minwidth=150, stretch=True)
        self.tree.column("domain", width=280, minwidth=200, stretch=True)
        self.tree.column("cat", width=110, minwidth=100, stretch=False)
        self.tree.column("act", width=80, minwidth=70, stretch=False)

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Treeview tag colors
        for cat_name in ['AD', 'TRACKER', 'MALWARE', 'TELEMETRY', 'SYSTEM', 'SOCIAL', 'NSFW', 'UNKNOWN']:
            cat_color = get_category_color(cat_name)
            self.tree.tag_configure(cat_name, foreground=cat_color)
        self.tree.tag_configure('ALLOW', foreground=Colors.SUCCESS)
        self.tree.tag_configure('BLOCK', foreground=Colors.DANGER)

        # Apply ultra-fast 15x scrolling patch
        apply_treeview_scroll_patch(self.tree)

        self._last_signature = None

        if hasattr(self, '_refresh_logs_id'): self.after_cancel(self._refresh_logs_id)
        self._refresh_logs_id = self.after(1000, self._refresh_logs)

    def _show_export_modal(self):
        """Show a modal to select export format and options."""
        import customtkinter as ctk
        from netstrip.gui.utils import apply_window_icon
        
        modal = ctk.CTkToplevel(self)
        modal.title("Export Connection Logs")
        modal.geometry("420x380")
        modal.minsize(420, 380)
        modal.configure(fg_color=Colors.BG_DARK)
        modal.transient(self)
        modal.grab_set()
        apply_window_icon(modal)
        
        # Center on parent
        modal.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 210
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 190
        modal.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(
            modal, text="Export Connection Logs",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_LG, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(Spacing.LG, Spacing.XS))
        
        ctk.CTkLabel(
            modal, text="Choose format and options:",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_SECONDARY
        ).pack(pady=(0, Spacing.LG))
        
        # Format selection
        format_var = ctk.StringVar(value="csv")
        
        formats = [
            ("csv", "CSV (Excel/Spreadsheet)", "Best for data analysis, filtering, pivot tables"),
            ("json", "JSON (Structured Data)", "Best for programmatic processing, APIs, archival"),
            ("txt", "Text (Human Readable)", "Best for quick viewing, sharing, printing"),
        ]
        
        for fmt_val, fmt_title, fmt_desc in formats:
            row = ctk.CTkFrame(modal, fg_color=Colors.BG_PANEL, corner_radius=8)
            row.pack(fill="x", padx=Spacing.LG, pady=Spacing.SM)
            
            rb = ctk.CTkRadioButton(
                row, text="", variable=format_var, value=fmt_val,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
                fg_color=Colors.ACCENT_PRIMARY, hover_color=Colors.ACCENT_LIGHT,
                border_color=Colors.BORDER_DEFAULT,
            )
            rb.pack(side="left", padx=Spacing.MD, pady=Spacing.MD)
            
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, pady=Spacing.SM)
            
            ctk.CTkLabel(
                info_frame, text=fmt_title,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE, Fonts.WEIGHT_MEDIUM),
                text_color=Colors.TEXT_PRIMARY, anchor="w"
            ).pack(anchor="w")
            
            ctk.CTkLabel(
                info_frame, text=fmt_desc,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
                text_color=Colors.TEXT_TERTIARY, anchor="w"
            ).pack(anchor="w")
        
        # Options
        ctk.CTkLabel(
            modal, text="Options",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", padx=Spacing.LG, pady=(Spacing.MD, Spacing.XS))
        
        include_all_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            modal, text="Include all logs (up to 50,000 entries)",
            variable=include_all_var, font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_PRIMARY, fg_color=Colors.ACCENT_PRIMARY,
            hover_color=Colors.ACCENT_LIGHT, border_color=Colors.BORDER_DEFAULT,
        ).pack(anchor="w", padx=Spacing.LG, pady=Spacing.XS)
        
        privacy_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            modal, text="Mask IP addresses (Privacy Stream Mode)",
            variable=privacy_var, font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
            text_color=Colors.TEXT_PRIMARY, fg_color=Colors.ACCENT_PRIMARY,
            hover_color=Colors.ACCENT_LIGHT, border_color=Colors.BORDER_DEFAULT,
        ).pack(anchor="w", padx=Spacing.LG, pady=Spacing.XS)
        
        # Export button
        def do_export():
            fmt = format_var.get()
            limit = 50000 if include_all_var.get() else 10000
            mask_ips = privacy_var.get()
            modal.destroy()
            self._export_logs(fmt, limit, mask_ips)
        
        btn_frame = ctk.CTkFrame(modal, fg_color="transparent")
        btn_frame.pack(fill="x", padx=Spacing.LG, pady=Spacing.LG)
        
        ctk.CTkButton(
            btn_frame, text="Cancel", width=100, height=32, corner_radius=8,
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BG_PANEL,
            text_color=Colors.TEXT_SECONDARY, command=modal.destroy
        ).pack(side="left")
        
        export_btn = ctk.CTkButton(
            btn_frame, text="Export", width=100, height=32, corner_radius=8,
            fg_color=Colors.ACCENT_PRIMARY, hover_color=Colors.ACCENT_LIGHT,
            text_color=Colors.TEXT_PRIMARY, command=do_export
        )
        export_btn.pack(side="right")
        
        try:
            add_bloom_hover(export_btn, glow_color=Colors.ACCENT_PRIMARY)
            add_bloom_press(export_btn, glow_color=Colors.ACCENT_LIGHT)
        except Exception:
            pass

    def _export_logs(self, fmt="csv", limit=10000, mask_ips=False):
        """Exports the connection log in the specified format."""
        import os
        from datetime import datetime
        try:
            docs_dir = os.path.join(os.path.expanduser("~"), "Documents")
            if not os.path.exists(docs_dir):
                docs_dir = os.path.expanduser("~")
                
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if fmt == "csv":
                filename = f"Cripple_Logs_{timestamp}.csv"
            elif fmt == "json":
                filename = f"Cripple_Logs_{timestamp}.json"
            else:
                filename = f"Cripple_Logs_{timestamp}.txt"
            filepath = os.path.join(docs_dir, filename)
            
            rows = list(self.engine.db.get_recent_connections(limit))
            
            if fmt == "csv":
                self._export_csv(filepath, rows, mask_ips)
            elif fmt == "json":
                self._export_json(filepath, rows, mask_ips)
            else:
                self._export_txt(filepath, rows, mask_ips)
                    
            import tkinter.messagebox
            tkinter.messagebox.showinfo("Export Successful", f"Logs exported to:\n{filepath}")
        except Exception as e:
            import tkinter.messagebox
            tkinter.messagebox.showerror("Export Failed", f"Failed to export logs:\n{str(e)}")
    
    def _export_csv(self, filepath, rows, mask_ips):
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Process", "PID", "Domain", "IP", "Port", "Protocol", "Category", "Action", "Mode", "Direction", "Status"])
            for r in reversed(rows):
                domain = r['domain'] or r['ip'] or ''
                if mask_ips and ('.' in domain or ':' in domain):
                    domain = self._mask_ip(domain)
                writer.writerow([
                    r['timestamp'], r['process_name'], r['pid'],
                    domain, r['ip'], r['port'], r['protocol'],
                    r['category'], r['action'], r['mode'],
                    r.get('direction', ''), r.get('status', '')
                ])
    
    def _export_json(self, filepath, rows, mask_ips):
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "source": "Cripple NetStrip",
            "total_entries": len(rows),
            "logs": []
        }
        for r in reversed(rows):
            domain = r['domain'] or r['ip'] or ''
            if mask_ips and ('.' in domain or ':' in domain):
                domain = self._mask_ip(domain)
            export_data["logs"].append({
                "timestamp": r['timestamp'],
                "process_name": r['process_name'],
                "pid": r['pid'],
                "domain": domain,
                "ip": r['ip'],
                "port": r['port'],
                "protocol": r['protocol'],
                "category": r['category'],
                "action": r['action'],
                "mode": r['mode'],
                "direction": r.get('direction', ''),
                "status": r.get('status', '')
            })
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
    
    def _export_txt(self, filepath, rows, mask_ips):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("Cripple Connection Log Export\n")
            f.write(f"Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 100 + "\n")
            f.write(f"{'TIME':<22} | {'PROCESS':<28} | {'DOMAIN/IP':<35} | {'CATEGORY':<14} | {'ACTION':<10} | {'DIR':<8}\n")
            f.write("-" * 100 + "\n")
            
            for r in reversed(rows):
                ts = r['timestamp']
                if isinstance(ts, str):
                    time_str = ts[:19]
                else:
                    time_str = str(ts)
                    
                proc = str(r['process_name'] or 'Unknown')[:27]
                domain = str(r['domain'] or r['ip'] or 'Unknown')[:34]
                if mask_ips:
                    domain = self._mask_ip(domain)
                cat = str(r['category'] or 'unknown').upper()[:13]
                act = str(r['action'] or 'unknown').upper()[:9]
                direction = str(r.get('direction', ''))[:7]
                
                f.write(f"{time_str:<22} | {proc:<28} | {domain:<35} | {cat:<14} | {act:<10} | {direction:<8}\n")
    
    def _mask_ip(self, text: str) -> str:
        import re
        text = str(text)
        text = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '<HIDDEN_IP>', text)
        text = re.sub(r'\b(?:[a-fA-F0-9]{1,4}:){1,7}[a-fA-F0-9]{1,4}\b', '<HIDDEN_IP>', text)
        return text

    def _refresh_logs(self):
        if getattr(self, '_destroyed', False):
            return

        if not self.winfo_ismapped():
            if hasattr(self, '_refresh_logs_id'): self.after_cancel(self._refresh_logs_id)
            self._refresh_logs_id = self.after(1000, self._refresh_logs)
            return

        if getattr(self, '_is_fetching_logs', False):
            if hasattr(self, '_refresh_logs_id'): self.after_cancel(self._refresh_logs_id)
            self._refresh_logs_id = self.after(1000, self._refresh_logs)
            return

        self._is_fetching_logs = True

        import threading
        def fetch_task():
            try:
                rows = list(self.engine.db.get_recent_connections(50))
            except Exception:
                rows = []

            def update_ui():
                try:
                    if getattr(self, '_destroyed', False) or not self.winfo_exists():
                        return

                    query = self._filter_entry.get().strip().lower()
                    filtered_rows = rows
                    if query:
                        filtered_rows = [
                            r for r in rows
                            if query in (r['process_name'] or '').lower()
                            or query in (r['domain'] or '').lower()
                            or query in (r['ip'] or '').lower()
                        ]

                    # Fast signature diffing
                    current_sig = (
                        query,
                        len(filtered_rows),
                        tuple((r['id'], str(r['timestamp']), str(r['action']), str(r['category'])) for r in filtered_rows[:20])
                    )
                    if self._last_signature == current_sig:
                        return
                    self._last_signature = current_sig

                    # In-place UI update (zero layout thrashing and scroll-preserving)
                    privacy_on = self.engine.db.get_setting("privacy_stream_mode", "false") == "true"
                    
                    existing_children = self.tree.get_children()
                    new_len = len(filtered_rows)
                    
                    for i, r in enumerate(filtered_rows):
                        ts = r['timestamp']
                        if isinstance(ts, str):
                            time_str = ts[11:19]  # Just HH:MM:SS
                        else:
                            time_str = ts.strftime("%H:%M:%S")

                        proc = "HIDDEN" if privacy_on else str(r['process_name'] or 'Unknown')
                        domain = "HIDDEN" if privacy_on else str(r['domain'] or r['ip'] or 'Unknown')
                        cat = str(r['category'] or 'unknown').upper()
                        act = str(r['action'] or 'unknown').upper()

                        tags = (cat, act)
                        vals = (time_str, proc, domain, cat, act)
                        
                        if i < len(existing_children):
                            self.tree.item(existing_children[i], values=vals, tags=tags)
                        else:
                            self.tree.insert("", "end", values=vals, tags=tags)
                            
                    # Delete excess rows
                    if len(existing_children) > new_len:
                        self.tree.delete(*existing_children[new_len:])

                    self._is_fetching_logs = False
                    if not getattr(self, '_destroyed', False):
                        if hasattr(self, '_refresh_logs_id'): self.after_cancel(self._refresh_logs_id)
                        self._refresh_logs_id = self.after(1000, self._refresh_logs)

                except Exception as e:
                    self._is_fetching_logs = False
                    if not getattr(self, '_destroyed', False):
                        if hasattr(self, '_refresh_logs_id'): self.after_cancel(self._refresh_logs_id)
                        self._refresh_logs_id = self.after(1000, self._refresh_logs)

            self.after(0, update_ui)

        threading.Thread(target=fetch_task, daemon=True).start()



    def destroy(self):
        self._destroyed = True
        super().destroy()



