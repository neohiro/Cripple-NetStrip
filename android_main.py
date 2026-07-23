import os
import sys
import threading
import time

# Ensure we are treated as Android
os.environ['NETSTRIP_ANDROID'] = '1'

# We import kivy to build the basic UI
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
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
        super().__init__(orientation='vertical', padding=20, spacing=20, **kwargs)
        self.status_label = Label(text="NetStrip Android initializing...", font_size='20sp', size_hint=(1, 0.8))
        self.add_widget(self.status_label)
        
        self.btn = Button(text="Start NetStrip Shield", size_hint=(1, 0.2))
        self.btn.bind(on_press=self.request_vpn)
        self.add_widget(self.btn)

    def request_vpn(self, instance):
        if VpnService:
            self.status_label.text = "Requesting VPN Permission..."
            # Ask Android for VPN permission
            intent = VpnService.prepare(PythonActivity.mActivity)
            if intent is not None:
                PythonActivity.mActivity.startActivityForResult(intent, 0)
                # Wait for user to accept... then we can start the service
                Clock.schedule_once(self.check_and_start, 2.0)
            else:
                # Already have permission
                self.start_engine()
        else:
            self.status_label.text = "Error: jnius / VpnService not found!"

    def check_and_start(self, dt):
        # We assume they accepted for this skeleton. In a real app we'd catch onActivityResult
        self.start_engine()

    def start_engine(self):
        self.status_label.text = "NetStrip Core Engine is Running in Background."
        self.btn.disabled = True
        
        # Add a button to trust the current WiFi
        self.trust_btn = Button(text="Trust Current WiFi", size_hint=(1, 0.2))
        self.trust_btn.bind(on_press=self.toggle_trust_wifi)
        self.add_widget(self.trust_btn)
        
        # Start Engine in background thread
        import main
        sys.argv = ["main.py", "--service", "--blockinbound"] # Run headless
        threading.Thread(target=self._run_main, daemon=True).start()
        
        # Periodically update the trust button text
        Clock.schedule_interval(self.update_trust_btn, 5.0)

    def _run_main(self):
        import main
        self._engine = main.main()

    def update_trust_btn(self, dt):
        if not hasattr(self, '_engine') or not self._engine: return
        try:
            ssid = self._engine.platform.get_current_ssid()
            if not ssid:
                self.trust_btn.text = "No WiFi connected"
                self.trust_btn.disabled = True
                return
                
            self.trust_btn.disabled = False
            trusted = self._engine.db.get_trusted_wifis()
            if ssid in trusted:
                self.trust_btn.text = f"Untrust WiFi ({ssid})"
            else:
                self.trust_btn.text = f"Trust WiFi ({ssid})"
        except Exception:
            pass

    def toggle_trust_wifi(self, instance):
        if not hasattr(self, '_engine') or not self._engine: return
        ssid = self._engine.platform.get_current_ssid()
        if not ssid: return
        
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
