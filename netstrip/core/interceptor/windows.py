import threading
import logging
from typing import Callable

try:
    import pydivert
except ImportError:
    pydivert = None

from netstrip.core.interceptor.base import PacketInterceptor

logger = logging.getLogger("NetStrip.WinDivert")

class WinDivertInterceptor(PacketInterceptor):
    def __init__(self, callback: Callable[[str, int, str, int, str], bool], engine=None):
        super().__init__(callback)
        self.engine = engine
        self.thread = None
        self._w = None

    def start(self):
        if not pydivert:
            logger.error("pydivert is not installed. WinDivert interception unavailable.")
            return
            
        if self.is_running:
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("WinDivert packet interception started.")

    def stop(self):
        self.is_running = False
        if self._w:
            try:
                self._w.close()
            except:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        logger.info("WinDivert packet interception stopped.")

    def _run_loop(self):
        # Intercept outbound TCP SYN (connection initialization) and outbound UDP.
        # We exclude local loopback to avoid intercepting our own DNS proxy traffic.
        filter_str = "outbound and ip and not loopback and (tcp.Syn or udp)"
        
        try:
            with pydivert.WinDivert(filter_str) as w:
                self._w = w
                for packet in w:
                    if not self.is_running:
                        break
                    
                    try:
                        dst_ip = packet.dst_addr
                        src_ip = packet.src_addr
                        
                        protocol = "TCP" if packet.tcp else "UDP" if packet.udp else "UNKNOWN"
                        
                        if packet.tcp:
                            dst_port = packet.dst_port
                            src_port = packet.src_port
                        elif packet.udp:
                            dst_port = packet.dst_port
                            src_port = packet.src_port
                        else:
                            dst_port = 0
                            src_port = 0
                            
                        # Evaluate packet via callback
                        allowed = self.callback(dst_ip, dst_port, protocol, src_port, src_ip)
                        
                        if allowed:
                            w.send(packet) # Re-inject packet into network stack
                        else:
                            # Drop the packet (do not send)
                            pass
                            
                    except Exception as e:
                        logger.error(f"Error evaluating packet: {e}")
                        # CRITICAL: If killswitch is active, failsafe = DROP to maintain block-all contract.
                        # Otherwise, failsafe = ALLOW so we don't break the internet on transient errors.
                        is_killswitch = self.engine and getattr(self.engine, 'killswitch_active', False)
                        if not is_killswitch:
                            try:
                                w.send(packet)
                            except:
                                pass
                        # else: packet is silently dropped (correct behavior under killswitch)
        except Exception as e:
            logger.error(f"WinDivert engine failed: {e}")
            self.is_running = False
