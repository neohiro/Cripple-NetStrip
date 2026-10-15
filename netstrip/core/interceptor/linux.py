import logging
import threading
import subprocess
import socket
import struct
from typing import Callable
from netstrip.core.interceptor.base import PacketInterceptor

logger = logging.getLogger("NetStrip.LinuxNFQueue")

class LinuxNFQueueInterceptor(PacketInterceptor):
    """
    Linux NFQueue zero-leak interceptor.
    Dynamically inserts an iptables rule to route outbound traffic to NFQueue 1.
    """
    def __init__(self, callback: Callable[[str, int, str, int, str], bool], engine=None):
        super().__init__(callback)
        self.engine = engine
        self._nfqueue = None
        self._nfqueue_thread = None

    def start(self):
        if self.is_running:
            return
            
        try:
            from netfilterqueue import NetfilterQueue
        except ImportError:
            logger.error("NetfilterQueue library not found. Install it with: pip install NetfilterQueue")
            return
            
        # Insert iptables rule for intercepting outbound TCP traffic
        try:
            subprocess.run(["iptables", "-I", "OUTPUT", "-p", "tcp", "--syn", "-j", "NFQUEUE", "--queue-num", "1"], check=True, capture_output=True)
            logger.info("Inserted iptables NFQUEUE rule.")
        except Exception as e:
            logger.error(f"Failed to insert iptables NFQUEUE rule: {e}")
            return

        self._nfqueue = NetfilterQueue()
        self._nfqueue.bind(1, self._packet_callback)

        self.is_running = True
        self._nfqueue_thread = threading.Thread(target=self._nfqueue.run, daemon=True)
        self._nfqueue_thread.start()
        logger.info("Linux NFQueue packet interception started.")

    def _packet_callback(self, pkt):
        payload = pkt.get_payload()
        if len(payload) < 20:
            pkt.accept()
            return
            
        # Parse IPv4 Header
        ip_header = payload[:20]
        iph = struct.unpack('!BBHHHBBH4s4s', ip_header)
        version_ihl = iph[0]
        ihl = version_ihl & 0xF
        iph_length = ihl * 4
        
        protocol = iph[6]
        src_ip = socket.inet_ntoa(iph[8])
        dst_ip = socket.inet_ntoa(iph[9])
        
        if protocol == 6: # TCP
            tcp_header = payload[iph_length:iph_length+20]
            tcph = struct.unpack('!HHLLBBHHH', tcp_header)
            src_port = tcph[0]
            dst_port = tcph[1]
            
            allowed = self.callback(dst_ip, dst_port, "TCP", src_port, src_ip)
            if allowed:
                pkt.accept()
            else:
                pkt.drop()
        else:
            pkt.accept()

    def stop(self):
        if not self.is_running:
            return
            
        self.is_running = False
        if self._nfqueue:
            self._nfqueue.unbind()
            
        # Remove iptables rule
        try:
            subprocess.run(["iptables", "-D", "OUTPUT", "-p", "tcp", "--syn", "-j", "NFQUEUE", "--queue-num", "1"], capture_output=True)
            logger.info("Removed iptables NFQUEUE rule.")
        except Exception as e:
            logger.error(f"Failed to remove iptables NFQUEUE rule: {e}")
            
        logger.info("Linux NFQueue packet interception stopped.")
