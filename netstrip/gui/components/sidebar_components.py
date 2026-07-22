from netstrip.gui.popups import check_killswitch_override
import customtkinter as ctk
from netstrip.gui.theme import Colors, Fonts, Spacing, Icons, get_category_color, get_category_label
from netstrip.core.engine import NetStripEngine
from netstrip.gui.icon_manager import IconManager
from netstrip.gui.utils import safe_loop, bind_copy_tooltip, mask_ip_string
import os
import time

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
            bind_copy_tooltip(self.target_label, raw_target, "Link copied!")
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
        if hasattr(self, 'conn_data') and conn_data.get('id', 0) > self.conn_data.get('id', 0):
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
            
            steps = ["#143c22", "#102a18", "#0b1910", "transparent"] if action == 'allow' else ["#450a0a", "#300707", "#1a0404", "transparent"]
            
            self._bg_rect.configure(fg_color=steps[0])
            self.target_label.configure(text_color=Colors.TEXT_PRIMARY)
            
            def fade(step_idx=1):
                if not self.winfo_exists(): return
                try:
                    if step_idx < len(steps):
                        self._bg_rect.configure(fg_color=steps[step_idx])
                        self.after(120, lambda: fade(step_idx + 1))
                    else:
                        self._is_pulsing = False
                        self.target_label.configure(text_color=Colors.TEXT_SECONDARY)
                except Exception:
                    pass
                    
            self.after(200, fade)

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


        if new_action == 'allow':
            check_killswitch_override(self.engine, self, proceed)
        else:
            proceed()

    def set_zebra(self, is_even: bool):
        # Slightly tint the background
        self.zebra_color = Colors.BG_DARK if is_even else "transparent"
        if not getattr(self, '_is_pulsing', False):
            if getattr(self, '_last_zebra', None) != self.zebra_color:
                self._bg_rect.configure(fg_color=self.zebra_color)
                self._last_zebra = self.zebra_color

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
        
        self.rows = {} # target -> ConnectionRow
        self.is_expanded = False
        
        # Start collapsed by default
        self.btn_expand.configure(text="Expand ▼")

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
                img = self.icon_manager.get_icon(self.process_path, self.process_name)
                if img:
                    _apply_raw_image(img)
            try:
                self.after(0, _apply)
            except Exception:
                pass
        
        img = self.icon_manager.get_icon(self.process_path, self.process_name, callback=on_loaded)
        if img:
            _apply_raw_image(img)
        else:
            pname = self.process_name.lower() if self.process_name else ""
            if pname in ("python.exe", "NetStrip.exe", "pythonw.exe", "NetStrip", "cripper (internal)"):
                self.icon_label.place_forget()
                self.icon_bg.configure(fg_color=Colors.BG_DARK)
                from netstrip.gui.animated_logo import AnimatedLogo
                self.NetStrip_logo = AnimatedLogo(self.icon_bg, width=24, height=24, bg_color=Colors.BG_DARK)
                self.NetStrip_logo.place(relx=0.5, rely=0.5, anchor="center")
                self.NetStrip_logo.bind("<Button-1>", self._toggle_expand)
            else:
                first_letter = self.process_name[0].upper() if self.process_name else "?"
                self.icon_label.configure(text=first_letter, image="")
                if self.process_name and self.process_name.startswith("Unknown"):
                    self.icon_bg.configure(fg_color=Colors.BG_DARK)
                    self.icon_label.configure(text_color=Colors.TEXT_TERTIARY)
                else:
                    self.icon_bg.configure(fg_color=Colors.ACCENT_PRIMARY)


    def _trigger_pulse(self, action="allow"):
        if not hasattr(self, '_is_pulsing') or not self._is_pulsing:
            self._is_pulsing = True
            
            steps = ["#143c22", "#102a18", "#0b1910", "transparent"] if action == 'allow' else ["#450a0a", "#300707", "#1a0404", "transparent"]
            
            self.header.configure(fg_color=steps[0])
            
            def fade(step_idx=1):
                if not self.winfo_exists(): return
                try:
                    if step_idx < len(steps):
                        self.header.configure(fg_color=steps[step_idx])
                        self.after(120, lambda: fade(step_idx + 1))
                    else:
                        self._is_pulsing = False
                except Exception:
                    pass
                    
            self.after(200, fade)
            
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
                oldest_target = next(iter(self.rows))
                old_row = self.rows.pop(oldest_target)
                old_row.destroy()
                
        if is_new:
            action = conn_data.get('action', 'allow')
            self._trigger_pulse(action)
            self.rows[target]._trigger_pulse(action)
        
    def _toggle_global_action(self, target_action: str):
        def proceed():
            # Determine if we are turning the action ON or OFF
            if self._global_action_state == target_action:
                # Toggle OFF
                new_state = None
                db_action = 'remove'
            else:
                # Toggle ON
                new_state = target_action
                db_action = target_action
                
            self._global_action_state = new_state
            
            # Update button visuals
            if new_state == 'block':
                self.btn_block_all.configure(fg_color="#f43f5e", text_color=Colors.TEXT_PRIMARY)
                self.btn_allow_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
            elif new_state == 'allow':
                self.btn_allow_all.configure(fg_color=Colors.SUCCESS, text_color=Colors.TEXT_PRIMARY)
                self.btn_block_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
            else:
                self.btn_block_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
                self.btn_allow_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
                
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
            mode_scope = "PARANOID" if current_mode == "PARANOID" else "STANDARD"
            
            # First remove any existing global app rule for this mode
            try:
                conn = self.engine.db._get_connection()
                conn.execute("DELETE FROM user_rules WHERE scope='app' AND app_name=? AND mode_scope=?", (self.process_name, mode_scope))
                conn.commit()
            except:
                pass
                
            if db_action != 'remove':
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
                
            # Apply action to all existing child rows
            # If removing a rule, we want to re-evaluate them (by just deleting the row, it will re-populate on next update)
            if db_action == 'remove':
                for target, row in list(self.rows.items()):
                    row.destroy()
                self.rows.clear()
                self.visible_count = 0
            else:
                for target, row in self.rows.items():
                    try:
                        row._on_action(db_action)
                    except:
                        pass


        if target_action == 'allow' and self._global_action_state != 'allow':
            check_killswitch_override(self.engine, self, proceed)
        else:
            proceed()


    def refresh_global_state(self):
        # Check current global status
        self._global_action_state = None
        is_paranoid = getattr(getattr(self.engine, 'classifier', None), 'mode', None)
        is_paranoid = is_paranoid and is_paranoid.name.upper() == "PARANOID"
        has_explicit_allow = False
        
        if hasattr(self.engine, 'blocklist'):
            if self.process_name in self.engine.blocklist.app_whitelist:
                self._global_action_state = 'allow'
                has_explicit_allow = True
            elif self.process_name in self.engine.blocklist.app_blacklist:
                self._global_action_state = 'block'
                
        if is_paranoid and not has_explicit_allow and self._global_action_state != 'block':
            try:
                rules = list(self.engine.db.get_user_rules(mode_scope="PARANOID"))
                has_partial_allow = any(r['app_name'] == self.process_name and r['action'] == 'allow' and r['scope'] == 'global' for r in rules)
                if not has_partial_allow:
                    self._global_action_state = 'block' # Simulated visual default
            except Exception:
                pass
                
        # Update button visuals
        from netstrip.gui.theme import Colors
        if self._global_action_state == 'block':
            self.btn_block_all.configure(fg_color="#f43f5e", text_color=Colors.TEXT_PRIMARY)
            self.btn_allow_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
        elif self._global_action_state == 'allow':
            self.btn_allow_all.configure(fg_color=Colors.SUCCESS, text_color=Colors.TEXT_PRIMARY)
            self.btn_block_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
        else:
            self.btn_block_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
            self.btn_allow_all.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)

    def apply_filter(self, hide_inactive: bool, active_filter: str = "All"):
        self.visible_count = 0
        import time
        now = time.time()
        
        # We need a list to safely delete during iteration
        targets = list(self.rows.keys())
        
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
            
        for target in targets:
            row = self.rows[target]
            
            # Prune if inactive for 2 minutes (120 seconds) to save Tkinter memory
            if now - getattr(row, 'last_updated', now) > 120:
                old_row = self.rows.pop(target)
                old_row.destroy()
                continue
                
            status = row.conn_data.get('status', 'UNKNOWN')
            action = row.conn_data.get('action', 'allow')
            category = row.conn_data.get('category', 'unknown')
            
            # For UDP, status is often NONE or UNKNOWN in psutil
            is_active = status in ('ESTABLISHED', 'SYN_SENT', 'LISTEN', 'ACTIVE', 'NONE', 'UNKNOWN')
            
            # Check filter category
            filter_hidden = False
            if active_filter == "Filter: Allowed" and action != 'allow':
                filter_hidden = True
            elif active_filter == "Filter: Blocked" and action != 'block':
                filter_hidden = True
            elif active_filter == "Filter: DNS/Local" and category not in ('dns', 'lan'):
                filter_hidden = True
                
            if filter_hidden or (hide_inactive and not is_active):
                if getattr(row, '_is_packed', True): # Assume packed initially if unknown
                    row.pack_forget()
                    row._is_packed = False
            else:
                row.set_zebra(self.visible_count % 2 == 0)
                if not getattr(row, '_is_packed', False):
                    row.pack(fill="x", pady=0)
                    row._is_packed = True
                self.visible_count += 1
                
        # Remove the self.pack() / pack_forget() logic from here.
        # It is now strictly managed by connections_sidebar.py to guarantee proper sorting.

    def set_expanded(self, expanded: bool):
        self.is_expanded_ui = expanded
        if expanded:
            # Add full process path
            self.lbl_path = ctk.CTkButton(
                self.header, text=self.process_path, 
                font=(Fonts.FAMILY_PRIMARY[0], 9), text_color=Colors.TEXT_TERTIARY,
                fg_color="transparent", hover_color=Colors.BG_DARK,
                height=20, corner_radius=4, anchor="w",
                command=self._copy_path
            )
            self.lbl_path.pack(side="left", padx=Spacing.MD)
            
            # Show 15 min button when sidebar is expanded
            self.btn_timebomb.pack(side="right", padx=(0, Spacing.SM))
        else:
            if hasattr(self, 'lbl_path'):
                self.lbl_path.destroy()
            self.btn_timebomb.pack_forget()
                
        for row in self.rows.values():
            row.set_expanded(expanded)

    def _copy_path(self):
        if not self.process_path:
            return
        self.clipboard_clear()
        self.clipboard_append(self.process_path)
        if hasattr(self, 'lbl_path') and self.lbl_path.winfo_exists():
            original_text = self.process_path
            self.lbl_path.configure(text="Path copied!", text_color=Colors.SUCCESS)
            self.after(1500, lambda: self.lbl_path.configure(text=original_text, text_color=Colors.TEXT_TERTIARY) if hasattr(self, 'lbl_path') and self.lbl_path.winfo_exists() else None)

