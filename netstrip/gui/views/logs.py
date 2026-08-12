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
from netstrip.gui.utils import safe_loop, bind_copy_tooltip, apply_treeview_scroll_patch
import tkinter.ttk as ttk


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
            import tkinter.messagebox
            tkinter.messagebox.showinfo("Export Successful", f"Logs exported to:\n{filepath}")
        except Exception as e:
            import tkinter.messagebox
            tkinter.messagebox.showerror("Export Failed", f"Failed to export logs:\n{str(e)}")

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



