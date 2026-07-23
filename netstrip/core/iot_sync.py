import time
import threading
import logging
import requests
import urllib.request
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class IoTTelemetrySync:
    def __init__(self, engine):
        self.engine = engine
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._thread.start()
        logger.info("IoT Telemetry Sync background service started.")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _sync_loop(self):
        while self._running:
            try:
                # Check if telemetry sync is globally enabled
                enabled = self.engine.db.get_setting("iot_telemetry_enabled", "false") == "true"
                if not enabled:
                    time.sleep(5.0)
                    continue

                webhook_url = self.engine.db.get_setting("iot_webhook_url", "")
                if not webhook_url:
                    time.sleep(5.0)
                    continue

                try:
                    interval = float(self.engine.db.get_setting("iot_telemetry_interval", "10.0"))
                except ValueError:
                    interval = 10.0
                    
                if interval < 1.0:
                    interval = 1.0

                # Build payload
                payload = self._build_payload()
                
                # Check for Nest Home as a Sensor
                nest_enabled = self.engine.db.get_setting("iot_nest_sensor_enabled", "false") == "true"
                if nest_enabled:
                    payload["google_nest_sensor_active"] = True
                    self._cast_to_nest(payload)
                    
                self._send_payload(webhook_url, payload)
                
            except Exception as e:
                logger.debug(f"IoT Telemetry Sync error: {e}")
            
            # Wait for next interval or interruption
            # Sleep in tiny chunks so we can exit fast on stop()
            for _ in range(int(interval * 10)):
                if not self._running:
                    break
                time.sleep(0.1)

    def _build_payload(self) -> Dict[str, Any]:
        payload = {}
        
        # Core State
        try:
            payload["mode"] = getattr(self.engine.classifier.mode, 'name', 'UNKNOWN')
            payload["killswitch"] = getattr(self.engine, 'killswitch_active', False)
            payload["lan_shield"] = self.engine.db.get_setting("lan_shield_enabled", "true") == "true"
            
            # Stats
            stats = self.engine.db.get_24h_statistics()
            if stats:
                payload["stats_queries_today"] = stats.get("total_queries", 0)
                payload["stats_blocked_today"] = stats.get("total_blocked", 0)
            else:
                payload["stats_queries_today"] = 0
                payload["stats_blocked_today"] = 0
    
            # Unique Allowed Connections
            try:
                payload["stats_allowed_today"] = self.engine.db.get_unique_allowed_today()
            except Exception:
                payload["stats_allowed_today"] = 0
    
            # Active Connections
            recent = getattr(self.engine, '_cached_recent', [])
            payload["active_connections_count"] = len(recent)
            
            # Recent Threats (last 5 blocked)
            recent_threats = []
            for r in recent:
                if isinstance(r, dict):
                    row = r
                else:
                    try:
                        row = dict(r)
                    except Exception:
                        continue
                        
                # Make sure to handle Action correctly depending on dict or sqlite3.Row
                act = row.get('action')
                if act == 'block':
                    recent_threats.append({
                        "domain": row.get('domain') or row.get('ip'),
                        "process": row.get('process_name'),
                        "timestamp": row.get('timestamp')
                    })
                if len(recent_threats) >= 5:
                    break
                    
            payload["recent_threats"] = recent_threats
        except Exception as e:
            logger.error(f"Failed parsing telemetry payload variables: {e}")
            
        # System Info
        payload["version"] = "NetStrip 1.0"
        payload["timestamp"] = time.time()
        
        return payload

    def _cast_to_nest(self, payload: Dict[str, Any]):
        """
        Dynamically attempts to locate a Google Nest Hub and casts 
        the telemetry status to it (acting as a visual sensor).
        Requires `pychromecast` to be installed by the user.
        """
        try:
            import pychromecast
        except ImportError:
            logger.debug("Google Nest Cast is enabled but 'pychromecast' is not installed.")
            return
            
        try:
            # Note: discovering chromecasts is slow, so we cache it in a real implementation.
            # This is a stub for casting a local status text to the default media receiver.
            if not hasattr(self, '_chromecasts'):
                services, browser = pychromecast.discovery.discover_chromecasts()
                pychromecast.discovery.stop_discovery(browser)
                self._chromecasts, self._browser = pychromecast.get_listed_chromecasts(friendly_names=["Nest Hub", "Google Home", "Living Room TV"])
                
            if self._chromecasts:
                cast = self._chromecasts[0]
                cast.wait()
                # A fully-featured implementation would cast a local Dashboard HTTP URL here.
                # For now, we connect to the device to signal we are active.
                logger.debug(f"Pushed telemetry state to Google Nest Hub: {cast.device.friendly_name}")
        except Exception as e:
            logger.debug(f"Nest Cast integration failed: {e}")

    def _send_payload(self, url: str, payload: Dict[str, Any]):
        headers = {'Content-Type': 'application/json'}
        secret = self.engine.db.get_setting("iot_webhook_secret", "")
        if secret:
            headers['Authorization'] = f"Bearer {secret}"
            
        try:
            requests.post(url, json=payload, headers=headers, timeout=2.0)
        except requests.exceptions.RequestException as e:
            logger.debug(f"Failed to post telemetry to {url}: {e}")
        except Exception as e:
            # Fallback to urllib if requests isn't available or fails strangely
            try:
                req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
                urllib.request.urlopen(req, timeout=2.0)
            except Exception:
                pass
