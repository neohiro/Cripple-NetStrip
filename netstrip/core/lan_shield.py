"""
LAN Shield for NetStrip
Isolates the local network by instructing the platform firewall to block private IP ranges.
"""

import logging
import socket
import threading
import json
import time
from cryptography.fernet import Fernet
from netstrip.platform.base import get_platform
from netstrip.core.modes import ProtectionLevel, get_mode

logger = logging.getLogger(__name__)

class LANShield:
    def __init__(self, engine=None):
        self.engine = engine
        self.platform = get_platform()
        self.is_active = False
        self._listener_thread = None
        self._running = False
        self._psk = self._init_psk()
        self._fernet = Fernet(self._psk) if self._psk else None
        
    def _init_psk(self):
        if not self.engine:
            return None
        psk = self.engine.db.get_setting("lan_shield_psk", "")
        if not psk:
            psk = Fernet.generate_key().decode('utf-8')
            self.engine.db.set_setting("lan_shield_psk", psk)
        return psk.encode('utf-8')

    def start(self):
        if self._running or not self._fernet: return
        self._running = True
        self._listener_thread = threading.Thread(target=self._listen_for_broadcasts, daemon=True)
        self._listener_thread.start()

    def stop(self):
        self._running = False
        # Thread will exit natively since it's a daemon or wait for timeout

    def _listen_for_broadcasts(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind to 0.0.0.0 on port 54321
        try:
            sock.bind(("", 54321))
            sock.settimeout(2.0)
        except Exception as e:
            logger.error(f"LAN Shield listener failed to bind: {e}")
            return

        while self._running:
            try:
                data, addr = sock.recvfrom(4096)
                if data.startswith(b"NetStrip:ANOMALY:"):
                    encrypted_payload = data[len(b"NetStrip:ANOMALY:"):]
                    try:
                        decrypted = self._fernet.decrypt(encrypted_payload, ttl=60) # 60 sec TTL replay prevention
                        payload = json.loads(decrypted.decode('utf-8'))
                        # Validate the payload
                        if payload.get('type') == 'LAN_THREAT_BROADCAST':
                            logger.critical(f"LAN SHIELD: Received Encrypted Threat Broadcast from {addr[0]}! Initiating local lockdown...")
                            # Trigger local lockdown
                            if self.engine:
                                # Run in separate thread to prevent blocking
                                threading.Thread(target=self.engine.trigger_threat_escalation, args=({'process_name': 'LAN Shield Remote Broadcast', 'domain': 'LAN_THREAT', 'note': payload.get('note', 'Remote Host Compromised')},)).start()
                    except Exception as e:
                        logger.debug(f"LAN Shield dropped invalid/expired encrypted broadcast: {e}")
            except socket.timeout:
                continue
            except Exception as e:
                logger.debug(f"LAN Shield listener error: {e}")

    def broadcast_anomaly(self, anomaly_data: dict):
        if not self._fernet: return
        try:
            payload = {
                'type': 'LAN_THREAT_BROADCAST',
                'timestamp': time.time(),
                'note': anomaly_data.get('note', 'Unknown Threat')
            }
            encrypted = self._fernet.encrypt(json.dumps(payload).encode('utf-8'))
            msg = b"NetStrip:ANOMALY:" + encrypted
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(msg, ("255.255.255.255", 54321))
            sock.close()
            logger.info("LAN Shield: Successfully broadcasted encrypted E2E threat warning to LAN clients.")
        except Exception as e:
            logger.error(f"Failed to broadcast LAN threat: {e}")

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
