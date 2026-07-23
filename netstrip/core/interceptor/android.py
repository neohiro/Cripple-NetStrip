import os
import threading
import select
import logging
from typing import Callable

from netstrip.core.interceptor.base import PacketInterceptor

logger = logging.getLogger("AndroidInterceptor")

class AndroidVPNInterceptor(PacketInterceptor):
    def __init__(self, callback: Callable[[str, int, str, int, str], bool], engine=None):
        super().__init__(callback)
        self.engine = engine
        self._thread = None
        self._running = False
        self._vpn_service = None
        self._fd = -1
        
        try:
            from jnius import autoclass
            self.NetStripVpnService = autoclass('org.cripple.netstrip.NetStripVpnService')
        except ImportError:
            self.NetStripVpnService = None
            logger.error("Failed to load NetStripVpnService via pyjnius.")

    def start(self):
        if not self.NetStripVpnService:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._vpn_loop, daemon=True)
        self._thread.start()
        logger.info("Android VPN Interceptor started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            
        # Optional: We could call stopVpn() here, but the Service lifecycle
        # might be managed externally by android_main.py. We'll leave it as is.
        logger.info("Android VPN Interceptor stopped.")

    def _vpn_loop(self):
        import time
        # Wait for the VPN to be established and get the FD
        while self._running and self._fd <= 0:
            inst = self.NetStripVpnService.getInstance()
            if inst:
                self._fd = inst.getVpnFd()
            if self._fd <= 0:
                time.sleep(0.5)
                
        if not self._running or self._fd <= 0:
            return
            
        logger.info(f"VPN Interceptor bound to FD: {self._fd}")
        
        # We can use os.read and os.write on this fd directly
        import socket
        import struct
        
        try:
            while self._running:
                # We use select to not block indefinitely
                r, _, _ = select.select([self._fd], [], [], 1.0)
                if not r:
                    continue
                    
                packet = os.read(self._fd, 4096)
                if not packet:
                    continue
                    
                # Basic IPv4 Header Parsing
                # Byte 0: Version (4 bits) + IHL (4 bits)
                version = packet[0] >> 4
                if version != 4:
                    continue # Ignore IPv6 for now
                    
                ihl = (packet[0] & 0xF) * 4
                protocol = packet[9]
                
                # We only care about UDP (17) for DNS
                if protocol != 17:
                    continue
                    
                # UDP Header Parsing
                udp_header = packet[ihl:ihl+8]
                src_port, dst_port, udp_len, udp_checksum = struct.unpack("!HHHH", udp_header)
                
                # We only care about DNS queries destined for our dummy IP 10.0.0.1:53
                if dst_port != 53:
                    continue
                    
                payload = packet[ihl+8:]
                
                src_ip = socket.inet_ntoa(packet[12:16])
                dst_ip = socket.inet_ntoa(packet[16:20])
                
                # Process the DNS payload
                response_payload = self._process_dns(payload)
                if response_payload:
                    # Construct IPv4 and UDP response
                    response_packet = self._build_ipv4_udp_response(packet, response_payload, ihl)
                    os.write(self._fd, response_packet)
                    
        except Exception as e:
            logger.error(f"VPN loop error: {e}")
            import traceback
            traceback.print_exc()
            
    def _process_dns(self, payload):
        # We can reuse the engine's DNSProxy logic if needed, 
        # but the simplest way is to send it to our local DNS server port 5053
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            sock.sendto(payload, ("127.0.0.1", 5053))
            resp, _ = sock.recvfrom(4096)
            sock.close()
            return resp
        except Exception as e:
            logger.error(f"DNS forwarding failed: {e}")
            return None

    def _build_ipv4_udp_response(self, req_packet, resp_payload, ihl):
        import struct
        
        # Swap IPs
        src_ip = req_packet[16:20]
        dst_ip = req_packet[12:16]
        
        # IP Header
        ip_header = bytearray(req_packet[:ihl])
        # Total Length
        total_len = ihl + 8 + len(resp_payload)
        ip_header[2:4] = struct.pack("!H", total_len)
        # Swap IPs
        ip_header[12:16] = src_ip
        ip_header[16:20] = dst_ip
        
        # Recalculate IP Checksum
        ip_header[10:12] = b'\x00\x00'
        chksum = self._calc_checksum(ip_header)
        ip_header[10:12] = struct.pack("!H", chksum)
        
        # UDP Header
        udp_header = bytearray(req_packet[ihl:ihl+8])
        # Swap Ports
        src_port = req_packet[ihl+2:ihl+4]
        dst_port = req_packet[ihl:ihl+2]
        udp_header[0:2] = src_port
        udp_header[2:4] = dst_port
        # UDP Length
        udp_len = 8 + len(resp_payload)
        udp_header[4:6] = struct.pack("!H", udp_len)
        # UDP Checksum (0 = ignore checksum for IPv4 UDP)
        udp_header[6:8] = b'\x00\x00' 
        
        return bytes(ip_header) + bytes(udp_header) + resp_payload

    def _calc_checksum(self, data):
        import struct
        if len(data) % 2 == 1:
            data += b'\0'
        s = sum(struct.unpack("!%dH" % (len(data) // 2), data))
        s = (s >> 16) + (s & 0xffff)
        s += s >> 16
        return (~s) & 0xffff
