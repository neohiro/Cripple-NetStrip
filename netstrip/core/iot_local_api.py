import logging
import threading
import socket
import time
from typing import Optional

from flask import Flask, jsonify

logger = logging.getLogger("NetStrip.IoTLocalAPI")

class IoTLocalAPI:
    def __init__(self, engine):
        self.engine = engine
        self.app = Flask(__name__)
        self.port = 8080
        self.server_thread: Optional[threading.Thread] = None
        self.zeroconf = None
        self._is_running = False

        # Disable annoying flask startup logs
        logging.getLogger('werkzeug').setLevel(logging.ERROR)

        @self.app.route("/metrics", methods=["GET"])
        def get_metrics():
            if not self.engine:
                return jsonify({"status": "starting"}), 503
                
            try:
                stats = self.engine.db.get_statistics()
                mode = self.engine.classifier.mode.name if self.engine.classifier and self.engine.classifier.mode else "UNKNOWN"
                active_conns = len(self.engine.connection_monitor.active_connections) if self.engine.connection_monitor else 0
                
                payload = {
                    "app": "NetStrip",
                    "mode": mode,
                    "killswitch_active": self.engine.killswitch_active,
                    "lan_shield_active": self.engine.lan_shield.enabled if self.engine.lan_shield else False,
                    "stats": {
                        "total_queries": stats.get("total_queries", 0),
                        "total_blocked": stats.get("total_blocked", 0),
                        "total_allowed": stats.get("total_allowed", 0)
                    },
                    "active_connections": active_conns,
                    "timestamp": time.time()
                }
                return jsonify(payload)
            except Exception as e:
                logger.error(f"Error serving IoT metrics: {e}")
                return jsonify({"error": str(e)}), 500

    def start(self):
        enabled = self.engine.db.get_setting("iot_local_sensor_enabled", "false") == "true"
        if not enabled:
            return

        try:
            self.port = int(self.engine.db.get_setting("iot_local_sensor_port", "8080"))
        except ValueError:
            self.port = 8080

        logger.info(f"Starting IoT Local API on port {self.port}...")
        self._is_running = True

        # Start Flask server
        self.server_thread = threading.Thread(
            target=lambda: self.app.run(host="0.0.0.0", port=self.port, debug=False, use_reloader=False),
            daemon=True,
            name="IoT_Local_API"
        )
        self.server_thread.start()

        # Start Zeroconf mDNS broadcast
        self._start_mdns()

    def _start_mdns(self):
        try:
            from zeroconf import ServiceInfo, Zeroconf
            
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            except Exception:
                local_ip = "127.0.0.1"
            finally:
                s.close()
                
            hostname = socket.gethostname()
            
            self.zeroconf = Zeroconf()
            
            # Broadcast as a generic HTTP service that Home Assistant can scan
            info = ServiceInfo(
                "_http._tcp.local.",
                f"NetStrip Sensor ({hostname})._http._tcp.local.",
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties={"path": "/metrics", "version": "1.0", "app": "NetStrip"},
                server=f"{hostname}.local.",
            )
            
            self.zeroconf.register_service(info)
            logger.info(f"Registered mDNS service _http._tcp.local. for NetStrip Sensor on {local_ip}:{self.port}")
            
        except ImportError:
            logger.warning("zeroconf not installed, mDNS discovery will not work.")
        except Exception as e:
            logger.error(f"Failed to start mDNS broadcast: {e}")

    def stop(self):
        if self._is_running:
            logger.info("Stopping IoT Local API...")
            self._is_running = False
            if self.zeroconf:
                try:
                    self.zeroconf.close()
                except Exception:
                    pass
            # Flask's built in server cannot be easily stopped from a thread
            # Since it's a daemon thread, it will die with the process.
