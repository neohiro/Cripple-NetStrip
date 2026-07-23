"""
NetStrip Android Entry Point — Kivy UI launcher for the Android APK.

Supports two VPN modes:
  1. Native VPN (default) — NetStrip occupies Android's VPN slot and filters
     ALL traffic (DNS + TCP/UDP). No other VPN app needed.
  2. Companion Mode — NetStrip runs DNS filtering only on 127.0.0.1:5353,
     designed to work alongside another VPN app (RethinkDNS, AdGuard, etc.)
     that handles the actual tunnel and points DNS to 127.0.0.1:5353.
"""

import os
import sys
import threading
import time

# Ensure we are treated as Android
os.environ['NETSTRIP_ANDROID'] = '1'

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock

try:
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent = autoclass('android.content.Intent')
    VpnService = autoclass('android.net.VpnService')
except ImportError:
    # Fallback for testing on desktop
    PythonActivity = None
    VpnService = None


class NetStripAndroidUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=20, spacing=12, **kwargs)
        self._engine = None
        self._vpn_mode = "FULL"  # Default: native VPN

        # Title
        self.title_label = Label(
            text="[b]Cripple — NetStrip[/b]",
            markup=True, font_size='24sp',
            size_hint=(1, 0.12)
        )
        self.add_widget(self.title_label)

        # Status
        self.status_label = Label(
            text="Select VPN mode and tap Start",
            font_size='16sp', size_hint=(1, 0.15)
        )
        self.add_widget(self.status_label)

        # VPN Mode Toggle
        mode_row = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.1))

        self.btn_full = ToggleButton(
            text="Native VPN", group="vpn_mode", state="down",
            font_size='14sp'
        )
        self.btn_full.bind(on_press=lambda i: self._set_mode("FULL"))

        self.btn_companion = ToggleButton(
            text="Companion Mode", group="vpn_mode",
            font_size='14sp'
        )
        self.btn_companion.bind(on_press=lambda i: self._set_mode("DNS_ONLY"))

        mode_row.add_widget(self.btn_full)
        mode_row.add_widget(self.btn_companion)
        self.add_widget(mode_row)

        # Mode description
        self.mode_desc = Label(
            text="Routes ALL traffic through NetStrip.\nNo other VPN app needed.",
            font_size='12sp', size_hint=(1, 0.12),
            halign='center'
        )
        self.mode_desc.bind(size=self.mode_desc.setter('text_size'))
        self.add_widget(self.mode_desc)

        # Start button
        self.btn_start = Button(
            text="Start NetStrip Shield", size_hint=(1, 0.13),
            font_size='18sp'
        )
        self.btn_start.bind(on_press=self.request_vpn)
        self.add_widget(self.btn_start)

        # Trust WiFi button (hidden until engine starts)
        self.trust_btn = Button(
            text="Trust Current WiFi", size_hint=(1, 0.1),
            font_size='14sp', opacity=0, disabled=True
        )
        self.trust_btn.bind(on_press=self.toggle_trust_wifi)
        self.add_widget(self.trust_btn)

        # Info label
        self.info_label = Label(
            text="Native VPN: NetStrip is your device's VPN — filters everything.\n"
                 "Companion: Use with another VPN app pointing DNS to 127.0.0.1:5353.",
            font_size='11sp', size_hint=(1, 0.15),
            halign='center', color=(0.6, 0.6, 0.6, 1)
        )
        self.info_label.bind(size=self.info_label.setter('text_size'))
        self.add_widget(self.info_label)

    def _set_mode(self, mode):
        self._vpn_mode = mode
        if mode == "FULL":
            self.mode_desc.text = "Routes ALL traffic through NetStrip.\nNo other VPN app needed."
        else:
            self.mode_desc.text = "DNS filtering only — use alongside another VPN app\npointing DNS to 127.0.0.1:5353."

    def request_vpn(self, instance):
        if VpnService:
            self.status_label.text = "Requesting VPN Permission..."
            intent = VpnService.prepare(PythonActivity.mActivity)
            if intent is not None:
                PythonActivity.mActivity.startActivityForResult(intent, 0)
                Clock.schedule_once(self.check_and_start, 2.0)
            else:
                self.start_engine()
        else:
            self.status_label.text = "Error: jnius / VpnService not found!"

    def check_and_start(self, dt):
        self.start_engine()

    def start_engine(self):
        mode_label = "Native VPN" if self._vpn_mode == "FULL" else "Companion (DNS Only)"
        self.status_label.text = f"NetStrip Engine Running — {mode_label}"
        self.btn_start.disabled = True
        self.btn_full.disabled = True
        self.btn_companion.disabled = True

        # Start Java VpnService with the selected mode
        try:
            context = PythonActivity.mActivity
            service_intent = Intent(context, autoclass('org.cripple.netstrip.NetStripVpnService'))
            if self._vpn_mode == "FULL":
                service_intent.setAction("START_FULL")
            else:
                service_intent.setAction("START_DNS_ONLY")
            context.startService(service_intent)
        except Exception as e:
            self.status_label.text = f"Failed to start Java VPN: {e}"
            return

        # Show trust WiFi button
        self.trust_btn.opacity = 1
        self.trust_btn.disabled = False

        # Start Engine in background thread
        sys.argv = ["main.py", "--service", "--blockinbound"]
        threading.Thread(target=self._run_main, daemon=True).start()

        Clock.schedule_interval(self.update_trust_btn, 5.0)

    def _run_main(self):
        import main
        self._engine = main.main()

    def update_trust_btn(self, dt):
        if not self._engine:
            return
        if getattr(self, '_is_updating_trust', False):
            return
        self._is_updating_trust = True

        def _fetch_bg():
            try:
                ssid = self._engine.platform.get_current_ssid()
                trusted = self._engine.db.get_trusted_wifis() if ssid else []

                def _update_ui(dt):
                    try:
                        if not ssid:
                            self.trust_btn.text = "No WiFi connected"
                            self.trust_btn.disabled = True
                        else:
                            self.trust_btn.disabled = False
                            if ssid in trusted:
                                self.trust_btn.text = f"Untrust WiFi ({ssid})"
                            else:
                                self.trust_btn.text = f"Trust WiFi ({ssid})"
                    except Exception:
                        pass
                    finally:
                        self._is_updating_trust = False
                Clock.schedule_once(_update_ui, 0)
            except Exception:
                self._is_updating_trust = False

        threading.Thread(target=_fetch_bg, daemon=True).start()

    def toggle_trust_wifi(self, instance):
        if not self._engine:
            return
        ssid = self._engine.platform.get_current_ssid()
        if not ssid:
            return

        trusted = self._engine.db.get_trusted_wifis()
        if ssid in trusted:
            self._engine.db.remove_trusted_wifi(ssid)
            self.trust_btn.text = f"Trust WiFi ({ssid})"
        else:
            self._engine.db.add_trusted_wifi(ssid)
            self.trust_btn.text = f"Untrust WiFi ({ssid})"


class NetStripAndroidApp(App):
    def build(self):
        return NetStripAndroidUI()


if __name__ == '__main__':
    NetStripAndroidApp().run()
