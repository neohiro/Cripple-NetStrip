"""
LAN Shield for NetStrip
Isolates the local network by instructing the platform firewall to block private IP ranges.
"""

import logging
from netstrip.platform.base import get_platform
from netstrip.core.modes import ProtectionLevel, get_mode

logger = logging.getLogger(__name__)

class LANShield:
    def __init__(self, engine=None):
        self.engine = engine
        self.platform = get_platform()
        self.is_active = False

    def apply_mode(self, level: ProtectionLevel):
        """Apply LAN shielding based on the selected mode and user preference."""
        mode_config = get_mode(level)
        
        if mode_config.block_lan:
            # Paranoid mode forces LAN shield on temporarily, without mutating the DB preference
            self.enable()
        else:
            # Otherwise use the user's explicit preference, defaulting to True at init
            lan_pref = self.engine.db.get_setting("lan_shield_enabled", "true")
            if lan_pref == "true":
                self.enable()
            else:
                self.disable()

    def enable(self) -> bool:
        """Enable full LAN isolation."""
        if self.is_active:
            return True
            
        success = self.platform.block_lan_traffic()
        if success:
            # Mathematical verification
            verified = self.platform.rule_exists("NetStrip_Block_LAN")
            if verified:
                self.is_active = True
                logger.info("LAN Shield enabled: Private IP ranges blocked.")
                if self.engine:
                    self.engine.broadcast_status("✅ LAN Shield Activated & Verified")
            else:
                logger.error("LAN Shield deployment failed verification!")
                if self.engine:
                    self.engine.broadcast_status("❌ LAN Shield Verification FAILED")
            
            # Allow gateway specifically if needed
            # gateway = self.platform.get_default_gateway()
            # if gateway:
            #     self.platform.unblock_ip(gateway, "NetStrip_Allow_Gateway")
                
        else:
            logger.error("Failed to enable LAN Shield.")
        return success

    def disable(self) -> bool:
        """Disable LAN isolation."""
        if self.engine and getattr(self.engine, 'killswitch_active', False):
            logger.warning("Attempted to disable LAN Shield while Killswitch is active. Denied.")
            if self.engine:
                self.engine.broadcast_status("⛔ Blocked: Killswitch overriding LAN Shield disable")
            return False

        success = self.platform.unblock_lan_traffic()
        if success:
            self.is_active = False
            logger.info("LAN Shield disabled.")
            if self.engine:
                self.engine.broadcast_status("ℹ️  LAN Shield Deactivated")
        else:
            if self.engine:
                self.engine.broadcast_status("❌ LAN Shield Deactivation FAILED")
            logger.debug("LAN Shield is already disabled or rule not found.")
        return success
