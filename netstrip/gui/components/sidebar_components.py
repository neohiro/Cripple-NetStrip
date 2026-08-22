from netstrip.gui.popups import check_killswitch_override
import customtkinter as ctk
from netstrip.gui.theme import Colors, Fonts, Spacing, get_category_color
from netstrip.core.engine import NetStripEngine
from netstrip.gui.icon_manager import IconManager
from netstrip.gui.utils import mask_ip_string
from netstrip.core.classifier import ConnectionCategory

class ConnectionRow(ctk.CTkFrame):
    def __init__(self, master, conn_data: dict, engine: NetStripEngine, **kwargs):
        super().__init__(master, fg_color=Colors.BG_DARK, corner_radius=0, **kwargs)
        self.engine = engine
        self.conn_data = conn_data
        
        import time
        self.last_updated = time.time()
        
        self._bg_rect = ctk.CTkFrame(self, fg_color=Colors.BG_DARK, corner_radius=0)
        self._bg_rect.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._bg_rect.lower()
        
        # Grid layout for the row
        self.grid_columnconfigure(2, weight=1) # Target pushes toggle to right
        self.grid_columnconfigure(3, weight=0) # Toggle switch
        self.is_expanded = False
        
        # 1. Color Code Dot
        category = conn_data.get('category', 'unknown')
        color = get_category_color(category)
        
        self.color_dot = ctk.CTkFrame(self, width=8, height=8, corner_radius=4, fg_color=color)
        self.color_dot.grid(row=0, column=0, padx=(Spacing.SM, Spacing.XS), pady=2)
        
        # 2. Target Domain/IP with Direction Arrow
        direction = conn_data.get('direction', 'outbound')
        arrow = "▼ " if direction == 'inbound' else "▲ "
        target = conn_data.get('domain') or conn_data.get('ip', 'Unknown')
        
        self.privacy_mode = self.engine.db.get_setting("privacy_stream_mode", "false") == "true"
        if self.privacy_mode:
            target = mask_ip_string(target)
            
        if str(conn_data.get('protocol')).upper() == 'DNS':
            target += " [DNS]"
            
        # Add GeoIP info
        try:
            from netstrip.core.geoip import OfflineGeoIP
            geoip_engine = OfflineGeoIP.get_instance()
            raw_ip = conn_data.get('remote_ip') or conn_data.get('ip')
            if raw_ip:
                loc = geoip_engine.get_full_location(raw_ip)
                if loc:
                    target = f"[{loc}] {target}"
        except Exception:
            pass
        
        self.target_label = ctk.CTkLabel(
            self,
            text=f"{arrow}{target}",
            font=(Fonts.FAMILY_PRIMARY[0], 11),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        self.target_label.grid(row=0, column=2, sticky="w", pady=1)
        
        try:
            from netstrip.gui.utils import bind_copy_tooltip
            raw_target = conn_data.get('domain') or conn_data.get('ip', 'Unknown')
            bind_copy_tooltip(self.target_label, raw_target)
        except Exception:
            pass
        
        # 3. Network Status
        status = conn_data.get('status', 'UNKNOWN')
        if status == 'NONE':
            status = 'ACTIVE'
            
        status_text = "" if status == 'UNKNOWN' else f"[{status}]"
        self.status_label = ctk.CTkLabel(
            self,
            text=status_text,
            font=(Fonts.FAMILY_PRIMARY[0], 9),
            text_color=Colors.TEXT_TERTIARY
        )
        self.status_label.grid(row=0, column=3, padx=Spacing.SM)

        # 4. Action Buttons
        action = conn_data.get('action', 'allow')
        
        self.btn_allow = ctk.CTkButton(
            self, text="Allow", width=40, height=20, corner_radius=4,
            fg_color=Colors.SUCCESS_DIM if action == 'allow' else "transparent",
            hover_color=Colors.SUCCESS, text_color=Colors.TEXT_PRIMARY if action == 'allow' else Colors.TEXT_SECONDARY,
            font=(Fonts.FAMILY_PRIMARY[0], 10),
            command=lambda: self._on_action('allow')
        )
        self.btn_allow.grid(row=0, column=4, padx=(0, 2))
        
        self.btn_block = ctk.CTkButton(
            self, text="Block", width=40, height=20, corner_radius=4,
            fg_color="#4a1525" if action == 'block' else "transparent",
            hover_color="#f43f5e", text_color=Colors.TEXT_PRIMARY if action == 'block' else Colors.TEXT_SECONDARY,
            font=(Fonts.FAMILY_PRIMARY[0], 10),
            command=lambda: self._on_action('block')
        )
        self.btn_block.grid(row=0, column=5, padx=(2, Spacing.XS))
        
        # PRE-ALLOCATE DETAILS FRAME (CRITICAL FOR PERFORMANCE)
        self.details_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.lbl_details = ctk.CTkLabel(
            self.details_frame, text="",
            font=(Fonts.FAMILY_PRIMARY[0], 10),
            text_color=Colors.TEXT_TERTIARY,
            justify="left", anchor="w"
        )
        self.lbl_details.pack(side="left", fill="x", expand=True)
            
    def set_expanded(self, expanded: bool):
        self.is_expanded = expanded
        if not expanded:
            self.details_frame.grid_remove()
        else:
            self.details_frame.grid(row=1, column=0, columnspan=6, sticky="ew", padx=(30, 0), pady=(0, 4))
            self._update_unified_label()

    def _update_unified_label(self):
        if not getattr(self, 'is_expanded', False) or not hasattr(self, 'lbl_details') or not self.lbl_details.winfo_exists():
            return
            
        protocol = self.conn_data.get('protocol', 'TCP')
        rport = self.conn_data.get('rport', '')
        ip = str(self.conn_data.get('ip') or '')
        
        if getattr(self, 'privacy_mode', False):
            ip = mask_ip_string(ip)
            
        pid = self.conn_data.get('pid', '?')
        category = str(self.conn_data.get('category', 'unknown')).upper()
        identity = self.conn_data.get('identity')
        
        special_label = ""
        if rport == 443 and ip.startswith("10."):
            special_label = " (VPN DoH)"
        elif ip == "127.0.0.1" or ip == "::1":
            special_label = " (Loopback)"
        elif self.conn_data.get('category') == 'dns':
            special_label = " (DNS)"
            
        if category == 'UNKNOWN':
            process_name = str(self.conn_data.get('process_name', 'UNKNOWN')).upper()
            if identity:
                category = str(identity).upper()
            elif process_name != 'UNKNOWN':
                category = process_name
                
        cat_str = f"[{category}]"
        if identity and identity.upper() != category:
            cat_str += f" Identity: {identity}"
            
        original_exe = str(self.conn_data.get('original_exe', ''))
        proc_name = str(self.conn_data.get('process_name', ''))
        exe_str = ""
        if original_exe and original_exe != proc_name and original_exe != "Unknown":
            exe_str = f"  |  exe: {original_exe}"
            
        details = f"↳ PID: {pid}{exe_str}  |  {protocol}  |  {ip}:{rport}{special_label}  |  {cat_str}"
        
        if getattr(self, '_last_details', None) != details:
            self.lbl_details.configure(text=details)
            self._last_details = details
            
    def update_data(self, conn_data: dict):
        import time
        self.last_updated = time.time()
        self.is_new_traffic = False
        new_id = conn_data.get('max_id') or conn_data.get('id', 0)
        old_id = self.conn_data.get('max_id') or self.conn_data.get('id', 0) if hasattr(self, 'conn_data') else 0
        if hasattr(self, 'conn_data') and new_id > old_id:
            self.is_new_traffic = True
            
        self.conn_data = conn_data
        
        # Check if privacy mode changed
        new_privacy = self.engine.db.get_setting("privacy_stream_mode", "false") == "true"
        if new_privacy != getattr(self, 'privacy_mode', False):
            self.privacy_mode = new_privacy
            target = conn_data.get('domain') or conn_data.get('ip', 'Unknown')
            if self.privacy_mode:
                target = mask_ip_string(target)
            if str(conn_data.get('protocol')).upper() == 'DNS':
                target += " [DNS]"
            direction = conn_data.get('direction', 'outbound')
            arrow = "▼ " if direction == 'inbound' else "▲ "
            self.target_label.configure(text=f"{arrow}{target}")
            
        status = conn_data.get('status', 'UNKNOWN')
        if status == 'NONE':
            status = 'ACTIVE'
        status_text = "" if status == 'UNKNOWN' else f"[{status}]"
        if getattr(self, '_last_status_text', None) != status_text:
            self.status_label.configure(text=status_text)
            self._last_status_text = status_text
        
        # Ensure category color dot stays updated
        category = conn_data.get('category', 'unknown')
        cat_color = get_category_color(category)
        if hasattr(self, 'color_dot'):
            if getattr(self, '_last_cat_color', None) != cat_color:
                self.color_dot.configure(fg_color=cat_color)
                self._last_cat_color = cat_color
            
        self._update_unified_label()
        
        action = conn_data.get('action', 'allow')
        if getattr(self, '_last_action', None) != action:
            self._last_action = action
            if action == 'allow':
                self.btn_allow.configure(fg_color=Colors.SUCCESS_DIM, text_color=Colors.TEXT_PRIMARY)
                self.btn_block.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
            elif action in ('block', 'sinkhole'):
                self.btn_block.configure(fg_color="#4a1525", text_color=Colors.TEXT_PRIMARY)
                self.btn_allow.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
            else: # ask / unknown
                self.btn_allow.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
                self.btn_block.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
                
        # Trigger pulse animation for EVERY active incoming traffic update
        if getattr(self, 'is_new_traffic', False):
            self._trigger_pulse(action)

    def _trigger_pulse(self, action="allow"):
        if not hasattr(self, '_is_pulsing') or not self._is_pulsing:
            self._is_pulsing = True
            pulse_color = Colors.SUCCESS if action == 'allow' else Colors.DANGER
            self.target_label.configure(text_color=pulse_color)
            
            steps = ["#143c22", "#102a18", "#0b1910"] if action == 'allow' else ["#450a0a", "#300707", "#1a0404"]
            
            self._bg_rect.configure(fg_color=steps[0])
            
            def fade(step_idx=1):
                try:
                    if not self.winfo_exists(): return
                    if step_idx < len(steps):
                        self._bg_rect.configure(fg_color=steps[step_idx])
                        self.after(80, lambda: fade(step_idx + 1))
                    else:
                        self._is_pulsing = False
                        self.target_label.configure(text_color=Colors.TEXT_SECONDARY)
                        # Restore the solid zebra tint instead of transparency
                        self.set_zebra(getattr(self, '_last_zebra_is_even', True))
                except Exception:
                    pass
                    
            try:
                self.after(100, fade)
            except Exception:
                pass

    def _on_action(self, new_action: str):
        def proceed():
            # Update UI instantly
            if new_action == 'allow':
                self.btn_allow.configure(fg_color=Colors.SUCCESS_DIM, text_color=Colors.TEXT_PRIMARY)
                self.btn_block.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
            else:
                self.btn_block.configure(fg_color="#4a1525", text_color=Colors.TEXT_PRIMARY)
                self.btn_allow.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
                
            target = self.conn_data.get('domain') or self.conn_data.get('ip')
            process_name = self.conn_data.get('process_name')
            
            # Save the rule mapped to the current mode scope
            current_mode = self.engine.classifier.mode.name
            mode_scope = "PARANOID" if current_mode == "PARANOID" else "STANDARD"
            
            self.engine.db.add_user_rule({
                'pattern': target,
                'action': new_action,
                'scope': 'global',
                'app_name': process_name,
                'category': 'user_allowed' if new_action == 'allow' else 'user_blocked',
                'note': f"Manual toggle from sidebar",
                'mode_scope': mode_scope
            })
            
            # Sync memory instantly for this mode scope
            if hasattr(self.engine.blocklist, 'sync_user_rules'):
                self.engine.blocklist.sync_user_rules(self.engine.db.get_user_rules(mode_scope=mode_scope))
                
            # Dispatch event so Blocklist tab instantly updates counters
            if hasattr(self.engine, 'on_status_update'):
                self.engine.on_status_update("rules_changed")


        if new_action == 'allow':
            check_killswitch_override(self.engine, self, proceed)
        else:
            proceed()

    def set_zebra(self, is_even: bool):
        # Solid tint colors (never "transparent") — transparency causes CTk to
        # redraw rounded corners mid-scroll which shows up as horizontal line
        # artifacts in expanded lists.
        self._last_zebra_is_even = is_even
        self.zebra_color = "#0a0a12" if is_even else "#0d1017"
        if not getattr(self, '_is_pulsing', False):
            if getattr(self, '_last_zebra', None) != self.zebra_color:
                self._bg_rect.configure(fg_color=self.zebra_color)
                self._last_zebra = self.zebra_color

    def apply_bulk_state(self, bulk_action: str):
        """
        Lightweight per-row visual sync for Allow All / Block All / Neutral.
        Pure UI update: no database writes, no rule re-syncs, no modals.
        The live classifier re-evaluates real actions on the next poll tick.
        """
        if not getattr(self, 'winfo_exists', lambda: True)():
            return
        try:
            if bulk_action == 'allow':
                self.conn_data['action'] = 'allow'
                self.btn_allow.configure(fg_color=Colors.SUCCESS_DIM, text_color=Colors.TEXT_PRIMARY)
                self.btn_block.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
                self._last_action = 'allow'
            elif bulk_action == 'block':
                self.conn_data['action'] = 'block'
                self.btn_block.configure(fg_color="#4a1525", text_color=Colors.TEXT_PRIMARY)
                self.btn_allow.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
                self._last_action = 'block'
            else:
                # Neutral: clear explicit visuals; next poll repaints from the
                # live classification result.
                self.conn_data['action'] = ''
                self.btn_allow.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
                self.btn_block.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
                self._last_action = ''
        except Exception:
            pass

class AppGroupFrame(ctk.CTkFrame):
    def __init__(self, master, process_name: str, process_path: str, engine: NetStripEngine, icon_manager: IconManager, **kwargs):
        super().__init__(master, fg_color=Colors.BG_DARK, **kwargs)
        self.process_name = process_name
        self.process_path = process_path
        self.engine = engine
        self.icon_manager = icon_manager
        self.rows = {} # target -> ConnectionRow
        
        self.grid_columnconfigure(0, weight=1)
        
        # UI Setup
        self.header = ctk.CTkFrame(
            self, height=30, corner_radius=6, 
            fg_color=Colors.BG_PANEL, border_color=Colors.BORDER_SUBTLE, border_width=1
        )
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.pack_propagate(False)
        self.header.bind("<Button-1>", self._toggle_expand)
        
        # Container for individual connection rows
        self.rows_container = ctk.CTkFrame(self, fg_color=Colors.BG_DARK, corner_radius=0)
        # Icon container
        self.icon_bg = ctk.CTkFrame(self.header, width=20, height=20, corner_radius=10, fg_color=Colors.ACCENT_PRIMARY)
        self.icon_bg.pack(side="left", padx=(0, Spacing.XS))
        self.icon_bg.pack_propagate(False)
        self.icon_bg.bind("<Button-1>", self._toggle_expand)
        
        self.icon_label = ctk.CTkLabel(
            self.icon_bg, text="", 
            font=(Fonts.FAMILY_PRIMARY[0], 10, Fonts.WEIGHT_BOLD),
            text_color=Colors.BG_DARKEST
        )
        self.icon_label.place(relx=0.5, rely=0.5, anchor="center")
        self.icon_label.bind("<Button-1>", self._toggle_expand)
        
        # Load Icon
        self._set_icon()
        
        # App Name Label
        is_unknown = process_name.startswith("Unknown")
        self.lbl_name = ctk.CTkLabel(
            self.header, 
            text=process_name, 
            font=(Fonts.FAMILY_PRIMARY[0], 11, "italic" if is_unknown else Fonts.WEIGHT_BOLD),
            text_color=Colors.TEXT_TERTIARY if is_unknown else Colors.TEXT_PRIMARY
        )
        self.lbl_name.pack(side="left")
        self.lbl_name.bind("<Button-1>", self._toggle_expand)

        # Flashing traffic light indicator (green for allowed traffic, red for blocked)
        self.traffic_dot = ctk.CTkLabel(
            self.header, text="●", font=(Fonts.FAMILY_PRIMARY[0], 11),
            text_color=Colors.TEXT_TERTIARY
        )
        self.traffic_dot.pack(side="left", padx=(Spacing.XS, Spacing.XS))
        self.traffic_dot.bind("<Button-1>", self._toggle_expand)
        
        self.btn_expand = ctk.CTkButton(
            self.header, text="Expand ▼", width=75, height=22,
            font=(Fonts.FAMILY_PRIMARY[0], 10, "bold"),
            fg_color=Colors.BG_INPUT, text_color=Colors.TEXT_PRIMARY,
            hover_color=Colors.ACCENT_PRIMARY, corner_radius=6,
            command=self._toggle_expand
        )
        self.btn_expand.pack(side="right", padx=Spacing.XS)
        
        # Check current global status
        self._global_action_state = None
        is_paranoid = getattr(getattr(self.engine, 'classifier', None), 'mode', None)
        is_paranoid = is_paranoid and is_paranoid.name.upper() == "PARANOID"
        has_explicit_allow = False
        
        if hasattr(self.engine, 'blocklist'):
            if process_name in self.engine.blocklist.app_whitelist:
                self._global_action_state = 'allow'
                has_explicit_allow = True
            elif process_name in self.engine.blocklist.app_blacklist:
                self._global_action_state = 'block'
                
        if is_paranoid and not has_explicit_allow and self._global_action_state != 'block':
            try:
                rules = list(self.engine.db.get_user_rules(mode_scope="PARANOID"))
                has_partial_allow = any(r['app_name'] == process_name and r['action'] == 'allow' and r['scope'] == 'global' for r in rules)
                if not has_partial_allow:
                    self._global_action_state = 'block' # Simulated visual default
            except Exception:
                pass
                
        # Bulk Actions
        self.btn_block_all = ctk.CTkButton(
            self.header, text="Block All", width=50, height=20, corner_radius=4,
            fg_color="#f43f5e" if self._global_action_state == 'block' else "transparent", 
            hover_color="#f43f5e", 
            text_color=Colors.TEXT_PRIMARY if self._global_action_state == 'block' else Colors.TEXT_SECONDARY,
            font=(Fonts.FAMILY_PRIMARY[0], 10),
            command=lambda: self._toggle_global_action('block')
        )
        self.btn_block_all.pack(side="right", padx=(2, Spacing.SM))
        
        self.btn_allow_all = ctk.CTkButton(
            self.header, text="Allow All", width=50, height=20, corner_radius=4,
            fg_color=Colors.SUCCESS if self._global_action_state == 'allow' else "transparent", 
            hover_color=Colors.SUCCESS, 
            text_color=Colors.TEXT_PRIMARY if self._global_action_state == 'allow' else Colors.TEXT_SECONDARY,
            font=(Fonts.FAMILY_PRIMARY[0], 10),
            command=lambda: self._toggle_global_action('allow')
        )
        self.btn_allow_all.pack(side="right", padx=2)
        
        # Inactive Label
        self.lbl_inactive = ctk.CTkLabel(
            self.header, text="", font=(Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_XS),
            text_color=Colors.TEXT_TERTIARY
        )
        self.lbl_inactive.pack(side="right", padx=(0, Spacing.XS))
        
        # 15 Min Time Bomb Button
        self.btn_timebomb = ctk.CTkButton(
            self.header, text="🕛 15 Min", width=60, height=20,
            font=(Fonts.FAMILY_PRIMARY[0], 10),
            fg_color="transparent", text_color=Colors.TEXT_TERTIARY,
            hover_color=Colors.BG_INPUT,
            command=self._on_time_bomb
        )
        # Not packed initially since group starts collapsed
        
        # Container for connection rows
        self.rows_container = ctk.CTkFrame(self, fg_color="transparent")
        self.rows_container.grid_columnconfigure(0, weight=1)
        
        self.rows = {} # target -> ConnectionRow
        self.is_expanded = False
        
        # Start collapsed by default
        self.btn_expand.configure(text="Expand ▼")
        
        # Render the correct initial toggle state immediately (system block
        # red-light, Ghost implicit block, persisted allow/block) so the state
        # is correct at program start and not only after the first UI poll.
        self.visible_count = 0
        self.refresh_global_state()

    def _toggle_expand(self, event=None):
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.rows_container.grid(row=1, column=0, sticky="ew", pady=(0, 4))
            self.btn_expand.configure(text="Collapse ▲", fg_color=Colors.BG_DARK, text_color=Colors.TEXT_SECONDARY)
        else:
            self.rows_container.grid_forget()
            self.btn_expand.configure(text="Expand ▼", fg_color=Colors.BG_INPUT, text_color=Colors.TEXT_PRIMARY)

    def _on_time_bomb(self):
        def proceed():
            from datetime import datetime, timedelta
            # Add 15 minutes rule
            expires = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            
            current_mode = self.engine.classifier.mode.name
            mode_scope = "PARANOID" if current_mode == "PARANOID" else "STANDARD"
            
            self.engine.db.add_user_rule({
                'pattern': '*',
                'action': 'allow',
                'scope': 'app',
                'app_name': self.process_name,
                'category': 'user_allowed',
                'note': 'Temporary 15 min access',
                'expires_at': expires,
                'mode_scope': mode_scope
            })
            
            if hasattr(self.engine.blocklist, 'sync_user_rules'):
                self.engine.blocklist.sync_user_rules(self.engine.db.get_user_rules(mode_scope=mode_scope))
                if hasattr(self.engine, 'on_status_update'):
                    self.engine.on_status_update("rules_changed")
                
            # Give visual feedback
            self.btn_timebomb.configure(text="? Granted", text_color=Colors.SUCCESS)
            self.after(2000, lambda: self.btn_timebomb.configure(text="?? 15 Min", text_color=Colors.TEXT_TERTIARY))


        check_killswitch_override(self.engine, self, proceed)
    def _set_icon(self):
        def _apply_raw_image(img):
            from PIL import ImageTk
            pil_img = img.cget("light_image")
            if pil_img:
                photo = ImageTk.PhotoImage(pil_img.resize((24, 24)), master=self.winfo_toplevel())
                self._icon_image_ref = photo # Prevent GC
                self.icon_label.configure(image="", text="") # Clear CTkImage wrapper
                self.icon_label._label.configure(image=photo) # Set raw tk.PhotoImage directly
                self.icon_bg.configure(fg_color="transparent")

        # Pass a callback to update UI if it downloads in the background
        def on_loaded():
            def _apply():
                try:
                    if not self.winfo_exists(): return
                    img = self.icon_manager.get_icon(self.process_path, self.process_name)
                    if img:
                        _apply_raw_image(img)
                except Exception:
                    pass
            try:
                self.after(0, _apply)
            except Exception:
                pass
        
        img = self.icon_manager.get_icon(self.process_path, self.process_name, callback=on_loaded)
        if img:
            _apply_raw_image(img)
        else:
            # Deterministic fallback glyph: system/OS daemons get a gear,
            # everything else gets its first letter.
            from netstrip.core.process_utils import is_system_process
            if is_system_process(self.process_name):
                self.icon_label.configure(text="⚙", image="")
                self.icon_bg.configure(fg_color=Colors.BG_ELEVATED)
                self.icon_label.configure(text_color=Colors.TEXT_SECONDARY)
            elif self.process_name and self.process_name.startswith("Unknown"):
                first_letter = self.process_name[0].upper() if self.process_name else "?"
                self.icon_label.configure(text=first_letter, image="")
                self.icon_bg.configure(fg_color=Colors.BG_DARK)
                self.icon_label.configure(text_color=Colors.TEXT_TERTIARY)
            else:
                first_letter = self.process_name[0].upper() if self.process_name else "?"
                self.icon_label.configure(text=first_letter, image="")
                self.icon_bg.configure(fg_color=Colors.ACCENT_PRIMARY)


    def _trigger_pulse(self, action="allow"):
        if not hasattr(self, '_is_pulsing') or not self._is_pulsing:
            self._is_pulsing = True
            
            steps = ["#143c22", "#102a18", "#0b1910"] if action == 'allow' else ["#450a0a", "#300707", "#1a0404"]
            
            self.header.configure(fg_color=steps[0])
            
            def fade(step_idx=1):
                try:
                    if not self.winfo_exists(): return
                    if step_idx < len(steps):
                        self.header.configure(fg_color=steps[step_idx])
                        self.after(80, lambda: fade(step_idx + 1))
                    else:
                        self._is_pulsing = False
                except Exception:
                    pass
                    
            try:
                self.after(100, fade)
            except Exception:
                pass

    def _flash_traffic_light(self, action="allow"):
        if not hasattr(self, 'traffic_dot') or not self.traffic_dot.winfo_exists():
            return
        
        flash_color = Colors.SUCCESS if action == 'allow' else Colors.DANGER
        self.traffic_dot.configure(text_color=flash_color)
        
        def reset():
            try:
                if self.winfo_exists() and hasattr(self, 'traffic_dot'):
                    self.traffic_dot.configure(text_color=Colors.TEXT_TERTIARY)
            except Exception:
                pass
                
        self.after(300, reset)

    def add_connection(self, conn_data: dict, hide_inactive: bool):
        target = conn_data.get('domain') or conn_data.get('ip')
        is_new = False
        if target in self.rows:
            self.rows[target].update_data(conn_data)
            is_new = getattr(self.rows[target], 'is_new_traffic', False)
        else:
            row = ConnectionRow(self.rows_container, conn_data, self.engine)
            self.rows[target] = row
            is_new = True
            # Infinite Uptime Optimization: max 50 rows per app group
            if len(self.rows) > 50:
                # Find the oldest row by timestamp (using getattr to handle missing attributes safely)
                oldest_target = min(
                    self.rows.keys(), 
                    key=lambda k: getattr(self.rows[k], 'conn_data', {}).get('timestamp', 0)
                )
                old_row = self.rows.pop(oldest_target)
                old_row.destroy()
                
        if is_new:
            action = conn_data.get('action', 'allow')
            self._trigger_pulse(action)
            self._flash_traffic_light(action)
            if target in self.rows:
                try:
                    self.rows[target]._trigger_pulse(action)
                except Exception:
                    pass
            
        # The system block visual override is handled in refresh_global_state during the UI loop
    def _toggle_global_action(self, target_action: str):
        # Prevent double-click stacking which previously froze the GUI thread
        if getattr(self, '_is_toggling', False):
            return
        self._is_toggling = True

        def proceed():
            # Determine if we are turning the action ON or OFF (Explicit 3-State Toggle)
            if self._global_action_state == target_action:
                # Toggle OFF -> Set explicit Neutral state (both buttons transparent, individual evaluation active)
                new_state = 'neutral'
                db_action = 'neutral'
            else:
                # Toggle ON -> Set state
                new_state = target_action
                db_action = target_action

            self._global_action_state = new_state

            # Update button visuals immediately
            if new_state == 'block':
                self.btn_block_all.configure(fg_color="#f43f5e", text_color=Colors.TEXT_PRIMARY)
                self.btn_allow_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
            elif new_state == 'allow':
                self.btn_allow_all.configure(fg_color=Colors.SUCCESS, text_color=Colors.TEXT_PRIMARY)
                self.btn_block_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
            else: # 'neutral' / both off
                self.btn_block_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
                self.btn_allow_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)

            # Apply instant visual feedback to child rows WITHOUT touching the
            # database per-row (the old per-row `_on_action` cascade wrote a
            # global rule + re-synced the whole blocklist for every single row,
            # freezing the UI for minutes on large app groups).
            rows_snapshot = list(self.rows.values())
            def _apply_row_visuals():
                for row in rows_snapshot:
                    try:
                        row.apply_bulk_state(db_action)
                    except Exception:
                        pass
            try:
                self.after(0, _apply_row_visuals)
            except Exception:
                pass

            # Heavy I/O (OS firewall netsh calls, SQLite writes, rule re-sync)
            # runs on a background thread so the UI never blocks.
            import threading
            def heavy_work():
                try:
                    # Update OS Firewall
                    rule_name = f"NetStrip_AppBlock_{self.process_name}"
                    if new_state == 'block' and self.process_path:
                        self.engine.platform.add_firewall_rule(
                            rule_name=rule_name,
                            direction="out",
                            action="block",
                            program=self.process_path
                        )
                    else:
                        self.engine.platform.remove_firewall_rule(rule_name=rule_name)

                    # Update Database
                    current_mode = self.engine.classifier.mode.name
                    mode_scope = "PARANOID" if current_mode.upper() in ("GHOST", "PARANOID") else "STANDARD"

                    # First remove any existing global app rule for this app under the current mode scope
                    try:
                        conn = self.engine.db._get_connection()
                        conn.execute("DELETE FROM user_rules WHERE scope='app' AND app_name=? AND (mode_scope=? OR mode_scope='ALL')", (self.process_name, mode_scope))
                        conn.commit()
                    except Exception:
                        pass

                    if db_action != 'neutral':
                        # Store explicit rule (allow or block). Neutral needs no
                        # persisted rule: absence of an explicit app rule means
                        # individual evaluation is restored automatically.
                        self.engine.db.add_user_rule({
                            'pattern': '*',
                            'action': db_action,
                            'scope': 'app',
                            'app_name': self.process_name,
                            'category': 'user_allowed' if db_action == 'allow' else 'user_blocked',
                            'note': self.process_path,
                            'mode_scope': mode_scope
                        })

                    # Sync memory instantly for this mode scope
                    if hasattr(self.engine.blocklist, 'sync_user_rules'):
                        self.engine.blocklist.sync_user_rules(self.engine.db.get_user_rules(mode_scope=mode_scope))
                    status_cb = getattr(self.engine, 'on_status_update', None)
                    if status_cb:
                        status_cb("rules_changed")
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Bulk toggle failed for {self.process_name}: {e}")
                finally:
                    self._is_toggling = False

            threading.Thread(target=heavy_work, daemon=True).start()

        if target_action == 'allow' and self._global_action_state != 'allow':
            check_killswitch_override(self.engine, self, proceed)
        else:
            proceed()

    def refresh_global_state(self):
        # Check current global status
        self._global_action_state = None
        self._implicit_block = False
        self._system_blocked = False
        is_paranoid = getattr(getattr(self.engine, 'classifier', None), 'mode', None)
        is_paranoid = is_paranoid and is_paranoid.name.upper() in ("GHOST", "PARANOID")
        has_explicit_allow = False
        
        if hasattr(self.engine, 'blocklist'):
            if self.process_name in self.engine.blocklist.app_whitelist:
                self._global_action_state = 'allow'
                has_explicit_allow = True
            elif self.process_name in self.engine.blocklist.app_blacklist:
                self._global_action_state = 'block'
            elif self.process_name in getattr(self.engine.blocklist, 'app_neutral', set()):
                self._global_action_state = 'neutral'
                
        # Implicit mode default ONLY applies if user has no explicit rule (state is None)
        if self._global_action_state is None and is_paranoid and not has_explicit_allow:
            try:
                rules = list(self.engine.db.get_user_rules(mode_scope="PARANOID"))
                has_partial_allow = any(r['app_name'] == self.process_name and r['action'] == 'allow' and r['scope'] == 'global' for r in rules)
                if not has_partial_allow:
                    self._implicit_block = True  # Paranoid default — visual indicator only
            except Exception:
                pass

        # System block indicator applies unless user explicitly allowed
        sys_blocked = self.engine.db.get_setting("block_system_connections", "false") == "true"
        if sys_blocked and not has_explicit_allow:
            from netstrip.core.process_utils import is_system_process
            is_system = False
            if is_system_process(self.process_name):
                is_system = True
            elif len(self.rows) > 0 and all(r.conn_data.get('category') in ('system', ConnectionCategory.SYSTEM.value, 'telemetry', 'tracker', 'ad', 'malware') or r.conn_data.get('action') == 'block' for r in self.rows.values()):
                is_system = True
                
            if is_system:
                self._global_action_state = 'block'
                self._system_blocked = True
                
        # Update button visuals (Explicit User Preference ALWAYS takes priority!)
        from netstrip.gui.theme import Colors
        if self._global_action_state == 'block':
            self.btn_block_all.configure(fg_color="#f43f5e", text_color=Colors.TEXT_PRIMARY)
            self.btn_allow_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
        elif self._global_action_state == 'allow':
            self.btn_allow_all.configure(fg_color=Colors.SUCCESS, text_color=Colors.TEXT_PRIMARY)
            self.btn_block_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
        elif self._global_action_state == 'neutral':
            # User explicitly turned off both toggles — both transparent!
            self.btn_block_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
            self.btn_allow_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
        elif self._system_blocked:
            # Block System Connections is active for this system process -> Block All lights up RED!
            self.btn_block_all.configure(fg_color="#f43f5e", text_color=Colors.TEXT_PRIMARY)
            self.btn_allow_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
        elif self._implicit_block:
            self.btn_block_all.configure(fg_color="#4a1525", text_color=Colors.TEXT_SECONDARY)
            self.btn_allow_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
        else:
            self.btn_block_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
            self.btn_allow_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)

    def apply_filter(self, hide_inactive: bool, active_filter: str = "All"):
        import time
        now = time.time()
        
        # Calculate inactive time
        if self.rows:
            last_active = max(getattr(row, 'last_updated', now) for row in self.rows.values())
            inactive_secs = int(now - last_active)
            if inactive_secs >= 60:
                self.lbl_inactive.configure(text=f"Inactive")
            else:
                self.lbl_inactive.configure(text="")
        else:
            self.lbl_inactive.configure(text="")
            
        # Get and prune rows
        valid_rows = []
        for target, row in list(self.rows.items()):
            # Prune if inactive for 2 minutes (120 seconds) to save Tkinter memory
            if now - getattr(row, 'last_updated', now) > 120:
                old_row = self.rows.pop(target)
                old_row.destroy()
                continue
            
            status = row.conn_data.get('status', 'UNKNOWN')
            is_active = status in ('ESTABLISHED', 'SYN_SENT', 'LISTEN', 'ACTIVE', 'NONE', 'UNKNOWN')
            
            valid_rows.append((row, is_active))
            
        current_packed = [c for c in self.rows_container.winfo_children() if getattr(c, '_is_packed', False)]
        
        visible_rows = []
        for row, is_active in valid_rows:
            action = row.conn_data.get('action', 'allow')
            category = row.conn_data.get('category', 'unknown')
            
            filter_hidden = False
            if active_filter == "Filter: Allowed" and action != 'allow':
                filter_hidden = True
            elif active_filter == "Filter: Blocked" and action != 'block':
                filter_hidden = True
            elif active_filter == "Filter: System":
                from netstrip.core.process_utils import is_system_process
                if row.conn_data.get('category') not in ('system', ConnectionCategory.SYSTEM.value) and not is_system_process(row.conn_data.get('process_name')):
                    filter_hidden = True
            elif active_filter == "Filter: DNS/Local" and category not in ('dns', 'lan'):
                filter_hidden = True
                
            if not filter_hidden and not (hide_inactive and not is_active):
                visible_rows.append(row)
                
        # Now sync packed state
        if current_packed != visible_rows:
            # Unpack all old rows that are no longer visible
            for row in current_packed:
                if row not in visible_rows:
                    row.grid_forget()
                    row._is_packed = False
                    
            # Repack seamlessly in new order
            for idx, row in enumerate(visible_rows):
                row.set_zebra(idx % 2 == 0)
                row.grid(row=idx, column=0, sticky="ew", pady=0)
                row._is_packed = True
                
        else:
            # Update zebras if order is same but maybe some colors were reset
            for idx, row in enumerate(visible_rows):
                row.set_zebra(idx % 2 == 0)
                
        self.visible_count = len(visible_rows)

    def set_expanded(self, expanded: bool):
        self.is_expanded_ui = expanded
        if expanded:
            if not hasattr(self, 'lbl_path') or not getattr(self.lbl_path, 'winfo_exists', lambda: False)():
                self.lbl_path = ctk.CTkButton(
                    self.header, text=self.process_path, 
                    font=(Fonts.FAMILY_PRIMARY[0], 9), text_color=Colors.TEXT_TERTIARY,
                    fg_color="transparent", hover_color=Colors.BG_DARK,
                    height=20, corner_radius=4, anchor="w",
                    command=self._copy_path
                )
            self.lbl_path.pack(side="left", padx=Spacing.MD)
            self.btn_timebomb.pack(side="right", padx=(0, Spacing.SM))
        else:
            if hasattr(self, 'lbl_path') and getattr(self.lbl_path, 'winfo_exists', lambda: False)():
                self.lbl_path.pack_forget()
            self.btn_timebomb.pack_forget()
                
        rows_list = list(self.rows.values())
        def _update_rows(index=0):
            if not self.winfo_exists() or index >= len(rows_list):
                return
            batch_size = 20
            for i in range(index, min(index + batch_size, len(rows_list))):
                if hasattr(rows_list[i], 'set_expanded'):
                    rows_list[i].set_expanded(expanded)
            try:
                self.after(2, lambda: _update_rows(index + batch_size))
            except Exception:
                pass
        _update_rows()

    def _copy_path(self):
        if not self.process_path:
            return
        self.clipboard_clear()
        self.clipboard_append(self.process_path)
        if hasattr(self, 'lbl_path') and self.lbl_path.winfo_exists():
            original_text = self.process_path
            self.lbl_path.configure(text="Path copied!", text_color=Colors.SUCCESS)
            self.after(1500, lambda: self.lbl_path.configure(text=original_text, text_color=Colors.TEXT_TERTIARY) if hasattr(self, 'lbl_path') and self.lbl_path.winfo_exists() else None)

