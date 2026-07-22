from netstrip.gui.popups import check_killswitch_override
"""
Dashboard View for Cripple GUI
"""

import customtkinter as ctk
from netstrip.gui.theme import Colors, Fonts, Spacing, Icons, CTK_FRAME_STYLE
from netstrip.gui.widgets import StatCard, ModeSelector, ShieldIndicator
from netstrip.gui.utils import safe_loop, bind_copy_tooltip

class DashboardView(ctk.CTkScrollableFrame):
    def __init__(self, master, engine, **kwargs):
        super().__init__(master, fg_color=Colors.BG_DARK, **kwargs)
        self.engine = engine
        
        # New Inner Frame to contain padding so the scrollbar stays on the far right edge!
        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(fill="both", expand=True, padx=24, pady=24)
        
        # Grid layout - enforce uniform column widths so dynamic text doesn't shift the UI
        self.inner.grid_columnconfigure((0, 1), weight=1, uniform="stat_cols")
        self.inner.grid_rowconfigure(3, weight=1)
        
        # 1. Header & Shield
        self.header_frame = ctk.CTkFrame(self.inner, fg_color=Colors.BG_DARK)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, Spacing.LG))
        
        self.shield = ShieldIndicator(self.header_frame)
        self.shield.pack(side="left", padx=Spacing.MD)
        
        # Mode selector on the right
        self.mode_frame = ctk.CTkFrame(self.header_frame, fg_color=Colors.BG_DARK)
        self.mode_frame.pack(side="right", padx=Spacing.MD, pady=Spacing.MD)
        
        # System Toggle above Smart Shield
        self.system_frame = ctk.CTkFrame(self.mode_frame, fg_color=Colors.BG_DARK)
        self.system_frame.pack(fill="x", pady=(0, Spacing.XS))
        
        ctk.CTkLabel(self.system_frame, text="Block System Connections", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD), text_color=Colors.TEXT_PRIMARY).pack(side="left")
        
        self.system_toggle = ctk.CTkSwitch(
            self.system_frame, text="", width=36,
            progress_color=Colors.DANGER,
            command=self._on_system_toggle
        )
        self.system_toggle.pack(side="right")

        # Smart Shield Toggle above Mode Selector
        self.smart_frame = ctk.CTkFrame(self.mode_frame, fg_color=Colors.BG_DARK)
        self.smart_frame.pack(fill="x", pady=(0, Spacing.MD))
        
        ctk.CTkLabel(self.smart_frame, text="Smart Shield", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, Fonts.WEIGHT_BOLD), text_color=Colors.TEXT_PRIMARY).pack(side="left")
        
        self.smart_toggle = ctk.CTkSwitch(
            self.smart_frame, text="", width=36,
            progress_color=Colors.ACCENT_PRIMARY,
            command=self._on_smart_toggle
        )
        self.smart_toggle.pack(side="right")
        
        ctk.CTkLabel(self.mode_frame, text="Protection Level", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM), text_color=Colors.TEXT_SECONDARY).pack(anchor="w", pady=(0, Spacing.XS))
        self.mode_selector = ModeSelector(self.mode_frame, on_change=self._on_mode_change)
        self.mode_selector.pack(fill="x")
        
        # 2. Stats Rows (2x2 Grid)
        self.stat_traffic = StatCard(self.inner, title="Allowed | Blocked", icon=Icons.BLOCKED, color=Colors.DANGER, subtitle="Last 24h")
        self.stat_traffic.grid(row=1, column=0, sticky="ew", padx=(0, Spacing.SM), pady=(0, Spacing.SM))
        
        self.stat_queries = StatCard(self.inner, title="Total Queries", icon=Icons.CONNECTIONS, color=Colors.INFO, subtitle="Last 24h")
        self.stat_queries.grid(row=1, column=1, sticky="ew", padx=(Spacing.SM, 0), pady=(0, Spacing.SM))
        
        self.stat_active = StatCard(self.inner, title="Active Connections", icon="⚡", color=Colors.ACCENT_PRIMARY, subtitle="Currently")
        self.stat_active.grid(row=2, column=0, sticky="ew", padx=(0, Spacing.SM), pady=(0, Spacing.SM))
        
        self.stat_bandwidth = StatCard(self.inner, title="Download / Upload", icon="🖧", color=Colors.SUCCESS, subtitle="Down | Up")
        self.stat_bandwidth.grid(row=2, column=1, sticky="ew", padx=(Spacing.SM, 0), pady=(0, Spacing.SM))
        
        # Add Fading Hovertips
        try:
            from netstrip.gui.hovertip import FadingHovertip
            FadingHovertip(self.stat_traffic, "Shows the ratio of allowed vs blocked connections over the rolling 24-hour window.", hover_delay=400)
            FadingHovertip(self.stat_queries, "Total number of outbound packets intercepted and evaluated by Cripple in the last 24 hours.", hover_delay=400)
            FadingHovertip(self.stat_active, "The number of distinct applications that have made a connection recently.", hover_delay=400)
            FadingHovertip(self.system_toggle, "Toggle whether to block native Windows/OS background connections.", hover_delay=400)
            FadingHovertip(self.smart_toggle, "When enabled, Paranoid mode dynamically alerts you to background malware domains.", hover_delay=400)
        except Exception as e:
            print("Failed to attach hovertips:", e)
        
        # 3. Recent Activity List
        self.activity_frame = ctk.CTkFrame(self.inner, **CTK_FRAME_STYLE)
        self.activity_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(Spacing.LG, 0))
        
        self.activity_frame.grid_columnconfigure(0, weight=1)
        self.activity_frame.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkLabel(self.activity_frame, text="Recent Blocks", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_MD, Fonts.WEIGHT_BOLD), text_color=Colors.TEXT_PRIMARY)
        header.grid(row=0, column=0, sticky="w", padx=Spacing.MD, pady=Spacing.MD)
        
        self.activity_list = ctk.CTkFrame(self.activity_frame, fg_color=Colors.BG_DARK)
        self.activity_list.grid(row=1, column=0, sticky="nsew", padx=Spacing.XS, pady=(0, Spacing.XS))
        
        # Initialize UI state deferred to prevent startup freeze
        if hasattr(self, '_update_stats_id'): self.after_cancel(self._update_stats_id)
        self._update_stats_id = self.after(50, self._update_stats)

    def _on_smart_toggle(self):
        def proceed():
            val = "true" if self.smart_toggle.get() else "false"
            self.engine.db.set_setting("smart_paranoid_mode", val)


        is_on = self.smart_toggle.get()
        if not is_on: # They toggled it to OFF
            def on_cancel():
                self.smart_toggle.select()
            
            check_killswitch_override(self.engine, self, proceed, cancel_callback=on_cancel)
        else:
            proceed()

    def _on_system_toggle(self):
        def proceed():
            val = "true" if self.system_toggle.get() else "false"
            self.engine.db.set_setting("block_system_connections", val)


        is_on = self.system_toggle.get()
        if not is_on: # They toggled it to OFF
            def on_cancel():
                self.system_toggle.select()
            
            check_killswitch_override(self.engine, self, proceed, cancel_callback=on_cancel)
        else:
            proceed()

    def _on_mode_change(self, mode_name: str):
        from netstrip.core.modes import ProtectionLevel
        level = ProtectionLevel[mode_name.upper()]
        self.engine.set_mode(level)
        self.shield.set_state(self.engine.is_running, mode_name)

    @safe_loop(delay_ms=200)
    def _update_stats(self):
        if getattr(self, '_destroyed', False):
            return
            
        if not self.winfo_ismapped():
            self._update_stats_id = self.after(500, self._update_stats)
            return
            
        self._update_stats_id = self.after(500, self._update_stats)
        try:
            today_stats = self.engine.db.get_24h_statistics()
            if today_stats:
                try:
                    unique_allowed = self.engine.db.get_unique_allowed_today()
                except AttributeError:
                    unique_allowed = today_stats['total_allowed']
                self.stat_traffic.set_value(f"{unique_allowed:,}  |  {today_stats['total_blocked']:,}")
                self.stat_queries.set_value(f"{today_stats['total_queries']:,}")
            else:
                self.stat_traffic.set_value("0  |  0")
                self.stat_queries.set_value("0")
                
            # Active connections
            recent = getattr(self.engine, '_cached_recent', None)
            if recent is None:
                recent = self.engine.db.get_recent_connections(limit=500)
                
            is_killswitch = getattr(self.engine, 'killswitch_active', False)
            
            if is_killswitch:
                self.stat_active.set_value("0")
            else:
                # MED-4: Use cached active apps from sidebar to avoid redundant 1500 calls/sec
                active_apps = getattr(self.engine, '_cached_active_apps', set())
                self.stat_active.set_value(str(len(active_apps)))
            
            # Bandwidth (Traffic Meter) calculation
            import psutil
            import time
            current_io = psutil.net_io_counters()
            current_time = time.time()
            if not hasattr(self, '_last_io'):
                self._last_io = current_io
                self._last_io_time = current_time
                self.stat_bandwidth.set_value("0 B/s | 0 B/s")
            else:
                dt = current_time - self._last_io_time
                if dt > 0:
                    up_speed = max(0, current_io.bytes_sent - self._last_io.bytes_sent) / dt
                    down_speed = max(0, current_io.bytes_recv - self._last_io.bytes_recv) / dt
                    
                    def format_speed(bps):
                        if bps < 1024: return f"{bps:.0f} B/s"
                        elif bps < 1024 * 1024: return f"{bps/1024:.1f} KB/s"
                        else: return f"{bps/(1024*1024):.1f} MB/s"
                        
                    def format_volume(bytes_val):
                        if bytes_val < 1024: return f"{bytes_val} B"
                        elif bytes_val < 1024**2: return f"{bytes_val/1024:.1f} KB"
                        elif bytes_val < 1024**3: return f"{bytes_val/(1024**2):.1f} MB"
                        else: return f"{bytes_val/(1024**3):.2f} GB"
                        
                    self.stat_bandwidth.set_value(f"{format_speed(down_speed)} | {format_speed(up_speed)}")
                    
                    db_sent, db_recv = self.engine.db.get_24h_bandwidth()
                    if db_sent > 0 or db_recv > 0:
                        total_vol = db_sent + db_recv
                        label_suffix = "Last 24h"
                    else:
                        total_vol = current_io.bytes_sent + current_io.bytes_recv
                        label_suffix = "Since Boot"
                        
                    self.stat_bandwidth.set_subtitle(f"Vol: {format_volume(total_vol)} ({label_suffix})")
                self._last_io = current_io
                self._last_io_time = current_time
            
            # Flicker-Free Static Pool Activity List
            if not hasattr(self, '_activity_pool'):
                self._activity_pool = []
                
            blocked_only = [r for r in recent if r['action'] in ('block', 'sinkhole')][:15]
            
            if not blocked_only and not self._activity_pool:
                if not hasattr(self, 'lbl_no_blocks'):
                    self.lbl_no_blocks = ctk.CTkLabel(self.activity_list, text="No recent blocks", text_color=Colors.TEXT_TERTIARY, font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM))
                    self.lbl_no_blocks.pack(pady=Spacing.LG)
            else:
                if hasattr(self, 'lbl_no_blocks'):
                    self.lbl_no_blocks.destroy()
                    delattr(self, 'lbl_no_blocks')
                
                from netstrip.gui.theme import get_category_color
                
                # Ensure pool has enough rows (max 15)
                while len(self._activity_pool) < len(blocked_only):
                    row = ctk.CTkFrame(self.activity_list, fg_color=Colors.BG_DARK, corner_radius=0, border_width=0)
                    lbl_dot = ctk.CTkLabel(row, text="●", font=(Fonts.FAMILY_PRIMARY[0], 12))
                    lbl_dot.pack(side="left", padx=(0, Spacing.SM))
                    lbl_proc = ctk.CTkLabel(row, font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM, "bold"), text_color=Colors.TEXT_PRIMARY)
                    lbl_proc.pack(side="left")
                    lbl_domain = ctk.CTkLabel(row, font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM), text_color=Colors.TEXT_SECONDARY)
                    lbl_domain.pack(side="right")
                    self._activity_pool.append((row, lbl_dot, lbl_proc, lbl_domain))
                    row.pack(fill="x", pady=2, side="top")
                    
                # Update visible rows
                for i, r in enumerate(blocked_only):
                    row, lbl_dot, lbl_proc, lbl_domain = self._activity_pool[i]
                    if not row.winfo_ismapped():
                        row.pack(fill="x", pady=2, side="top")
                        
                    cat = r['category'] or 'unknown'
                    c_color = get_category_color(cat)
                    if lbl_dot.cget("text_color") != c_color:
                        lbl_dot.configure(text_color=c_color)
                        
                    p_name = r['process_name'] or "Unknown"
                    if lbl_proc.cget("text") != p_name:
                        lbl_proc.configure(text=p_name)
                        
                    d_text = r['domain'] or r['ip'] or ""
                    
                    privacy_on = self.engine.db.get_setting("privacy_stream_mode", "false") == "true"
                    if privacy_on:
                        from netstrip.gui.utils import mask_ip_string
                        d_text = mask_ip_string(d_text)
                    
                    if lbl_domain.cget("text") != d_text:
                        lbl_domain.configure(text=d_text)
                        
                # Hide unused rows
                for i in range(len(blocked_only), len(self._activity_pool)):
                    row = self._activity_pool[i][0]
                    if row.winfo_ismapped():
                        row.pack_forget()
                    
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Dashboard loop exception: {e}", exc_info=True)
            
        # Update shield and toggles
        try:
            current_mode = self.engine.db.get_setting("protection_mode", "NORMAL")
            self.mode_selector.set(current_mode.capitalize())
            self.shield.set_state(self.engine.is_running, current_mode.capitalize())
            
            smart_val = self.engine.db.get_setting("smart_paranoid_mode", "true")
            smart_enabled = str(smart_val).lower() == "true"
            if self.smart_toggle.get() != smart_enabled:
                self.smart_toggle.select() if smart_enabled else self.smart_toggle.deselect()
                
            system_val = self.engine.db.get_setting("block_system_connections", "false")
            system_enabled = str(system_val).lower() == "true"
            if self.system_toggle.get() != system_enabled:
                self.system_toggle.select() if system_enabled else self.system_toggle.deselect()
        except Exception as e:
            print("Dashboard loop exception 2:", e)
        
        # Removed untracked self.after call here, as it's handled at the top of the function

    def destroy(self):
        self._destroyed = True
        super().destroy()
