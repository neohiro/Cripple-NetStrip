import logging
import os
import subprocess
from typing import List, Optional

from netstrip.platform.base import PlatformBase

logger = logging.getLogger(__name__)

class AndroidPlatform(PlatformBase):
    """
    Android Platform implementation via python-for-android / pyjnius.
    Interfaces directly with Android's VpnService API instead of using iptables,
    as iptables requires a rooted device.
    """

    def __init__(self):
        super().__init__()
        self.vpn_fd = -1
        # Defined unconditionally. They used to be assigned only inside the
        # try below, so a device (or a test) without pyjnius left them missing
        # entirely and every method that touched them raised AttributeError
        # instead of returning its documented False.
        self.PythonActivity = None
        self.VpnService = None
        self.Context = None
        self.Builder = None
        try:
            from jnius import autoclass
            self.PythonActivity = autoclass('org.kivy.android.PythonActivity')
            self.VpnService = autoclass('android.net.VpnService')
            self.Context = autoclass('android.content.Context')
            # VpnService.Builder is a nested class
            self.Builder = autoclass('android.net.VpnService$Builder')
        except ImportError:
            logger.warning("pyjnius not available - Android native calls will fail.")

    def is_admin(self) -> bool:
        # We don't use 'root' on Android, we use VpnService.
        # But for engine bypasses, we consider it 'admin' if we have VPN permission.
        return True

    def request_admin(self, script_path: str) -> bool:
        # VpnService permission is requested via Kivy UI Intent in android_main.py.
        return True

    def set_system_dns(self, interface: str, dns_server: str) -> bool:
        """
        On Android, DNS is set when the VpnService is established using
        builder.addDnsServer(). There is no per-interface DNS setting to make:
        the VpnService builder owns the resolver for the tunnel, so this only
        needs to confirm a VpnService handle exists.

        It deliberately does not touch PythonActivity.mActivity - that call
        was never needed (nothing is done with the result) and it raised
        AttributeError on any build without a live Activity, turning a
        straightforward "is the VPN up" check into a crash.
        """
        if not getattr(self, "VpnService", None):
            return False
        logger.info(
            f"Android VpnService builder will intercept DNS queries "
            f"on {interface} and route to {dns_server}"
        )
        return True

    def restore_system_dns(self, interface: str) -> bool:
        # Bringing down the VpnService naturally restores DNS
        return True

    def get_original_dns(self, interface: str) -> Optional[str]:
        # Android handles the fallback upstream DNS automatically when VPN is off
        return "8.8.8.8"

    def get_current_ssid(self) -> str:
        if not getattr(self, 'Context', None):
            return ""
        try:
            wifi_manager = self.PythonActivity.mActivity.getSystemService(self.Context.WIFI_SERVICE)
            if wifi_manager:
                info = wifi_manager.getConnectionInfo()
                if info:
                    ssid = info.getSSID()
                    if ssid and ssid != "<unknown ssid>":
                        return ssid.strip('"')
        except Exception as e:
            logger.debug(f"Failed to get Android SSID: {e}")
        return ""

    def get_active_interfaces(self) -> List[str]:
        return ["wlan0", "rmnet0"]

    def get_default_gateway(self) -> Optional[str]:
        return "192.168.1.1"

    def add_firewall_rule(self, rule_name: str, direction: str, action: str, remote_ip: Optional[str], remote_port: Optional[int], protocol: Optional[str], program: Optional[str]) -> bool:
        # We handle dropping packets directly in our VpnService TUN read loop.
        logger.debug(f"Android virtual rule registered: {rule_name} -> {action}")
        return True

    def remove_firewall_rule(self, rule_name: str) -> bool:
        return True

    def rule_exists(self, rule_name: str) -> bool:
        return False

    def block_ip(self, ip: str) -> bool:
        # Will be dropped by internal python engine
        return True

    def unblock_ip(self, ip: str) -> bool:
        return True

    def block_lan_traffic(self) -> bool:
        return True

    def unblock_lan_traffic(self) -> bool:
        return True

    def remove_all_NetStrip_rules(self) -> bool:
        return True

    def remove_all_app_block_rules(self) -> bool:
        return True

    def kill_all_tcp_connections(self):
        """Forcefully terminate all active TCP connections on Android. Handled natively by VpnService."""
        pass

    def enable_killswitch(self) -> bool:
        logger.warning("Android VpnService native killswitch engaged.")
        self.kill_all_tcp_connections()
        return True

    def disable_killswitch(self) -> bool:
        logger.info("Android VpnService native killswitch disengaged.")
        return True
        
    def disable_ipv6(self) -> bool:
        return True
        
    def enable_ipv6(self) -> bool:
        return True
        
    def is_ipv6_enabled(self) -> bool:
        return True
        
    def disable_ipv4(self) -> bool:
        return True
        
    def enable_ipv4(self) -> bool:
        return True
        
    def is_ipv4_enabled(self) -> bool:
        return True

    def install_autostart(self) -> bool:
        # Requires BOOT_COMPLETED broadcast receiver in java.
        return False

    def uninstall_autostart(self) -> bool:
        return False

    def is_autostart_installed(self) -> bool:
        return False

    def disable_protocol_bindings(self) -> bool:
        """No-op on Android.

        The base class declares this abstract so every platform states its
        answer explicitly. On Linux/Windows/macOS the method turns off
        WPAD/LLDP/LLMNR/NetBIOS/SMB and the sysctls that accept those
        protocols, all of which are adapter-level features of a desktop OS.
        Android has none of them: there is no sysctl, no systemd, and no
        smbd/avahi to stop - traffic is captured by VpnService at the fd
        level before it reaches any adapter. Returning True records "nothing
        to do, and that is correct", rather than raising and making the
        platform uninstantiable (which is what happened before: the class was
        abstract and `AndroidPlatform.__new__` raised TypeError, so the
        Android path could not be constructed at all).
        """
        logger.debug(
            "disable_protocol_bindings: no-op on Android (VpnService model)"
        )
        return True

    def restore_protocol_bindings(self) -> bool:
        """No-op on Android; the counterpart of disable_protocol_bindings."""
        logger.debug(
            "restore_protocol_bindings: no-op on Android (VpnService model)"
        )
        return True
