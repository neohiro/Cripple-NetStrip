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
from netstrip.gui.utils import safe_loop, bind_copy_tooltip, enable_smooth_scrolling


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

        # Column headers (stretches to exact pane width)
        hdr = ctk.CTkFrame(self, fg_color=Colors.BG_PANEL, corner_radius=0, height=36)
        hdr.pack(fill="x", pady=(0, 14), padx=(0, 14))
        
        for i, (label, cfg) in enumerate(zip(
            ["Time", "Process", "Domain/IP", "Category", "Action"],
            self.COL_CONFIGS,
        )):
            hdr.grid_columnconfigure(i, weight=cfg["weight"], minsize=cfg["minsize"])
            align_anchor = "center" if label in ("Category", "Action") else "w"
            ctk.CTkLabel(
                hdr, text=label,
                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD),
                text_color=Colors.TEXT_TERTIARY,
                anchor=align_anchor
            ).grid(row=0, column=i, sticky="ew" if label in ("Category", "Action") else "w", padx=Spacing.SM, pady=Spacing.XS)

        # Scrollable body
        self._log_scroll = ctk.CTkScrollableFrame(self, fg_color=Colors.BG_DARK)
        self._log_scroll.pack(fill="both", expand=True)
        enable_smooth_scrolling(self._log_scroll)

        self._last_signature = None
        self._row_pool = []
        # Rows are built lazily in chunks to prevent UI stutter

        if hasattr(self, '_refresh_logs_id'): self.after_cancel(self._refresh_logs_id)
        self._refresh_logs_id = self.after(50, self._refresh_logs)

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

    @safe_loop(delay_ms=750)
    def _refresh_logs(self):
        if getattr(self, '_destroyed', False):
            return

        if not self.winfo_ismapped():
            if hasattr(self, '_refresh_logs_id'): self.after_cancel(self._refresh_logs_id)
            self._refresh_logs_id = self.after(750, self._refresh_logs)
            return

        if getattr(self, '_is_fetching_logs', False):
            if hasattr(self, '_refresh_logs_id'): self.after_cancel(self._refresh_logs_id)
            self._refresh_logs_id = self.after(750, self._refresh_logs)
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

                    # Fast signature diffing: skip all widget manipulations if logs & filter didn't change
                    current_sig = (
                        query,
                        len(filtered_rows),
                        tuple((r['id'], str(r['timestamp']), str(r['action']), str(r['category'])) for r in filtered_rows[:15])
                    )
                    if self._last_signature == current_sig and hasattr(self, '_pool_initialized'):
                        return
                    self._last_signature = current_sig
                    self._pool_initialized = True

                    if not filtered_rows:
                        if not hasattr(self, 'loading_frame'):
                            self.loading_frame = ctk.CTkFrame(self._log_scroll, fg_color=Colors.BG_DARK)
                            self.loading_frame.pack(pady=Spacing.XL, expand=True)
                            ctk.CTkLabel(self.loading_frame, text="⏳", font=(Fonts.FAMILY_PRIMARY[0], 36)).pack()
                            ctk.CTkLabel(
                                self.loading_frame, text="Listening for connections...",
                                text_color=Colors.TEXT_TERTIARY,
                                font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
                            ).pack(pady=Spacing.XS)
                    else:
                        if hasattr(self, 'loading_frame'):
                            self.loading_frame.destroy()
                            delattr(self, 'loading_frame')

                    # In-place UI update (zero layout thrashing)
                    privacy_on = self.engine.db.get_setting("privacy_stream_mode", "false") == "true"
                    
                    def build_and_pack(index):
                        if index >= len(filtered_rows) or getattr(self, '_destroyed', False):
                            # Hide unused rows
                            for i in range(len(filtered_rows), len(self._row_pool)):
                                frame, lbls = self._row_pool[i]
                                if frame.winfo_ismapped():
                                    frame.pack_forget()
                                    
                            self._is_fetching_logs = False
                            if not getattr(self, '_destroyed', False):
                                if hasattr(self, '_refresh_logs_id'): self.after_cancel(self._refresh_logs_id)
                                self._refresh_logs_id = self.after(750, self._refresh_logs)
                            return
                            
                        # Process in small chunks to keep UI responsive
                        chunk_end = min(index + 8, len(filtered_rows))
                        for i in range(index, chunk_end):
                            if i >= len(self._row_pool):
                                frame, lbls = self._build_empty_row()
                                self._row_pool.append((frame, lbls))
                                
                            frame, lbls = self._row_pool[i]
                            
                            bg_color = Colors.BG_ELEVATED if i % 2 == 0 else Colors.BG_PANEL
                            if getattr(frame, '_last_bg', None) != bg_color:
                                frame.configure(fg_color=bg_color)
                                frame._last_bg = bg_color

                            if not frame.winfo_ismapped():
                                frame.pack(fill="x", pady=2, padx=4)
                            self._fill_row(lbls, filtered_rows[i], privacy_on)
                            
                        self.after(2, build_and_pack, chunk_end)

                    build_and_pack(0)
                except Exception as e:
                    self._is_fetching_logs = False
                    if not getattr(self, '_destroyed', False):
                        if hasattr(self, '_refresh_logs_id'): self.after_cancel(self._refresh_logs_id)
                        self._refresh_logs_id = self.after(750, self._refresh_logs)

            self.after(0, update_ui)

        threading.Thread(target=fetch_task, daemon=True).start()

    def _build_empty_row(self):
        frame = ctk.CTkFrame(
            self._log_scroll,
            fg_color=Colors.BG_PANEL, corner_radius=4, height=36,
            border_width=0, border_color=Colors.BORDER_SUBTLE,
        )
        frame.pack_propagate(False)
        for i, cfg in enumerate(self.COL_CONFIGS):
            frame.grid_columnconfigure(i, weight=cfg["weight"], minsize=cfg["minsize"])

        lbl_time = ctk.CTkLabel(frame, text="", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM), text_color=Colors.TEXT_TERTIARY, anchor="w")
        lbl_time.grid(row=0, column=0, sticky="w", padx=Spacing.SM, pady=Spacing.SM)

        proc_frame = ctk.CTkFrame(frame, fg_color="transparent")
        proc_frame.grid(row=0, column=1, sticky="w", padx=Spacing.SM, pady=Spacing.SM)
        lbl_dot = ctk.CTkLabel(proc_frame, text="●", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS))
        lbl_dot.pack(side="left", padx=(0, 4))
        lbl_proc = ctk.CTkLabel(proc_frame, text="", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD), text_color=Colors.TEXT_PRIMARY, anchor="w")
        lbl_proc.pack(side="left")

        lbl_domain = ctk.CTkLabel(frame, text="", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD), text_color=Colors.TEXT_SECONDARY, anchor="w")
        lbl_domain.grid(row=0, column=2, sticky="w", padx=Spacing.SM, pady=Spacing.SM)

        # True curved rounded pill badges with zero nested canvas overlap
        lbl_cat = ctk.CTkLabel(
            frame, text="", text_color="white",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS, Fonts.WEIGHT_BOLD),
            width=96, height=22, corner_radius=11, fg_color=Colors.BG_INPUT
        )
        lbl_cat.grid(row=0, column=3, padx=Spacing.SM, pady=Spacing.SM)

        lbl_act = ctk.CTkLabel(
            frame, text="",
            font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS, Fonts.WEIGHT_BOLD),
            width=80, height=22, corner_radius=11, fg_color=Colors.BG_INPUT
        )
        lbl_act.grid(row=0, column=4, padx=Spacing.SM, pady=Spacing.SM)

        return frame, {
            'time': lbl_time,
            'dot': lbl_dot,
            'proc': lbl_proc,
            'domain': lbl_domain,
            'cat': lbl_cat,
            'act': lbl_act
        }

    def _fill_row(self, lbls, row, privacy_on=False):
        try:
            ts = row['timestamp']
            if isinstance(ts, str):
                if ' ' in ts:
                    ts = ts.replace(' ', 'T')
                if not ts.endswith('Z') and '+' not in ts:
                    ts += '+00:00'
                d = datetime.fromisoformat(ts).astimezone()
                time_str = d.strftime("%H:%M:%S (%m-%d)")
            else:
                time_str = ts.astimezone().strftime("%H:%M:%S (%m-%d)")
        except Exception:
            try:
                time_str = str(row['timestamp'])[:14]
            except Exception:
                time_str = ""
            
        cat = row['category'] or 'unknown'
        c_color = get_category_color(cat)
        
        if getattr(lbls['time'], '_last_val', None) != time_str:
            lbls['time'].configure(text=time_str)
            lbls['time']._last_val = time_str
            
        if getattr(lbls['dot'], '_last_color', None) != c_color:
            lbls['dot'].configure(text_color=c_color)
            lbls['dot']._last_color = c_color
            
        from netstrip.core.process_utils import normalize_process_name
        raw_proc = row['process_name'] or ''
        proc_text = normalize_process_name(raw_proc)
        if len(proc_text) > 16:
            proc_text = proc_text[:13] + "..."
            
        if getattr(lbls['proc'], '_last_val', None) != proc_text:
            lbls['proc'].configure(text=proc_text)
            lbls['proc']._last_val = proc_text
            
        raw_domain = row['domain'] or row['ip'] or ''
        
        if privacy_on:
            from netstrip.gui.utils import mask_ip_string
            raw_domain = mask_ip_string(raw_domain)
            
        domain_text = raw_domain
        if len(domain_text) > 80:
            domain_text = domain_text[:77] + "..."
            
        if getattr(lbls['domain'], '_last_val', None) != domain_text:
            lbls['domain'].configure(text=domain_text)
            lbls['domain']._last_val = domain_text
            
        if getattr(lbls['domain'], '_last_raw_domain', None) != raw_domain:
            lbls['domain']._last_raw_domain = raw_domain
            if raw_domain:
                bind_copy_tooltip(lbls['domain'], raw_domain)
            
        cat_text = get_category_label(cat).upper()
        if getattr(lbls['cat'], '_last_color', None) != c_color or getattr(lbls['cat'], '_last_val', None) != cat_text:
            lbls['cat'].configure(text=cat_text, fg_color=c_color)
            lbls['cat']._last_color = c_color
            lbls['cat']._last_val = cat_text
            
        action = (row['action'] or '').lower()
        if action == 'allow':
            act_text = "ALLOW"
            act_fg = Colors.SUCCESS_DIM
            act_color = "white"
        else:
            act_text = "BLOCK"
            act_fg = "#4a1525"
            act_color = "#f43f5e"

        if getattr(lbls['act'], '_last_val', None) != act_text or getattr(lbls['act'], '_last_fg', None) != act_fg or getattr(lbls['act'], '_last_color', None) != act_color:
            lbls['act'].configure(text=act_text, fg_color=act_fg, text_color=act_color)
            lbls['act']._last_val = act_text
            lbls['act']._last_fg = act_fg
            lbls['act']._last_color = act_color

    def destroy(self):
        self._destroyed = True
        super().destroy()



