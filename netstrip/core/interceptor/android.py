"""
Android VPN Interceptor — Reads raw IP packets from the TUN file descriptor
provided by NetStripVpnService and applies NetStrip's filtering.

Supports two modes:
  1. FULL mode — Intercepts ALL traffic (DNS + TCP/UDP). Blocked connections
     are silently dropped. Allowed connections are written back to the TUN fd
     for Android to route to the internet.
  2. DNS_ONLY mode — Only intercepts DNS queries (UDP port 53) and forwards
     them to NetStrip's internal DNS proxy. All other traffic bypasses.
"""
import os
import threading
import select
import socket
import struct
import time
import logging
from typing import Callable

from netstrip.core.interceptor.base import PacketInterceptor

logger = logging.getLogger("AndroidInterceptor")

# IP protocol numbers
PROTO_TCP = 6
PROTO_UDP = 17


class AndroidVPNInterceptor(PacketInterceptor):
    def __init__(self, callback: Callable[[str, int, str, int, str], bool], engine=None):
        super().__init__(callback)
        self.engine = engine
        self._thread = None
        self._running = False
        self._vpn_service = None
        self._fd = -1
        self._is_full_mode = True

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
        self._thread = threading.Thread(target=self._vpn_loop, daemon=True, name="VPNInterceptor")
        self._thread.start()
        logger.info("Android VPN Interceptor started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Android VPN Interceptor stopped.")

    def _vpn_loop(self):
        """Main packet processing loop — reads from TUN fd, filters, writes back."""
        # Wait for the VPN to be established and get the FD
        while self._running and self._fd <= 0:
            inst = self.NetStripVpnService.getInstance()
            if inst:
                self._fd = inst.getVpnFd()
                try:
                    self._is_full_mode = inst.isFullMode()
                except Exception:
                    self._is_full_mode = True
            if self._fd <= 0:
                time.sleep(0.5)

        if not self._running or self._fd <= 0:
            return

        mode_label = "FULL" if self._is_full_mode else "DNS_ONLY"
        logger.info(f"VPN Interceptor bound to FD: {self._fd} (mode: {mode_label})")

        try:
            while self._running:
                r, _, _ = select.select([self._fd], [], [], 1.0)
                if not r:
                    continue

                packet = os.read(self._fd, 65535)
                if not packet or len(packet) < 20:
                    continue

                # Parse IP version
                version = packet[0] >> 4
                if version == 4:
                    self._process_ipv4(packet)
                elif version == 6:
                    self._process_ipv6(packet)
                # else: drop unknown

        except Exception as e:
            logger.error(f"VPN loop error: {e}")
            import traceback
            traceback.print_exc()

    def _process_ipv4(self, packet):
        """Process an IPv4 packet from the TUN interface."""
        if len(packet) < 20:
            return

        ihl = (packet[0] & 0xF) * 4
        protocol = packet[9]
        src_ip = socket.inet_ntoa(packet[12:16])
        dst_ip = socket.inet_ntoa(packet[16:20])

        # Parse ports from TCP/UDP header
        src_port = 0
        dst_port = 0
        if len(packet) >= ihl + 4:
            src_port, dst_port = struct.unpack("!HH", packet[ihl:ihl + 4])

        proto_str = "tcp" if protocol == PROTO_TCP else "udp" if protocol == PROTO_UDP else str(protocol)

        # DNS queries (UDP port 53) — always intercept and forward to our DNS proxy
        if protocol == PROTO_UDP and dst_port == 53:
            payload = packet[ihl + 8:]
            response_payload = self._process_dns(payload)
            if response_payload:
                response_packet = self._build_ipv4_udp_response(packet, response_payload, ihl)
                try:
                    os.write(self._fd, response_packet)
                except Exception:
                    pass
            return

        # In DNS_ONLY mode, we don't filter non-DNS traffic
        if not self._is_full_mode:
            try:
                os.write(self._fd, packet)
            except Exception:
                pass
            return

        # FULL mode: Apply NetStrip filtering via the callback
        # callback returns True if the connection should be ALLOWED
        try:
            allowed = self.callback(src_ip, src_port, dst_ip, dst_port, proto_str)
        except Exception:
            allowed = True  # Fail-open: allow on error

        if allowed:
            # Write the packet back — Android will route it to the internet
            try:
                os.write(self._fd, packet)
            except Exception:
                pass
        # else: silently drop (packet is simply not written back)

    def _process_ipv6(self, packet):
        """Process an IPv6 packet from the TUN interface."""
        if len(packet) < 40:
            return

        # In DNS_ONLY mode, pass all IPv6 through
        if not self._is_full_mode:
            try:
                os.write(self._fd, packet)
            except Exception:
                pass
            return

        # FULL mode: Parse IPv6 header
        next_header = packet[6]
        src_ip = socket.inet_ntop(socket.AF_INET6, packet[8:24])
        dst_ip = socket.inet_ntop(socket.AF_INET6, packet[24:40])

        src_port = 0
        dst_port = 0
        header_len = 40
        if next_header in (PROTO_TCP, PROTO_UDP) and len(packet) >= header_len + 4:
            src_port, dst_port = struct.unpack("!HH", packet[header_len:header_len + 4])

        proto_str = "tcp" if next_header == PROTO_TCP else "udp" if next_header == PROTO_UDP else str(next_header)

        # DNS queries
        if next_header == PROTO_UDP and dst_port == 53:
            # For IPv6 DNS, we still forward to our local IPv4 DNS proxy
            payload = packet[header_len + 8:]
            response_payload = self._process_dns(payload)
            # IPv6 DNS response building is complex; for now, just drop and
            # let it fall back to IPv4 DNS resolution
            return

        try:
            allowed = self.callback(src_ip, src_port, dst_ip, dst_port, proto_str)
        except Exception:
            allowed = True

        if allowed:
            try:
                os.write(self._fd, packet)
            except Exception:
                pass

    def _process_dns(self, payload):
        """Forward a DNS payload to NetStrip's internal DNS proxy and return the response."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3.0)
            sock.sendto(payload, ("127.0.0.1", 5053))
            resp, _ = sock.recvfrom(4096)
            sock.close()
            return resp
        except Exception as e:
            logger.debug(f"DNS forwarding failed: {e}")
            return None

    def _build_ipv4_udp_response(self, req_packet, resp_payload, ihl):
        """Construct an IPv4 UDP response packet by swapping src/dst from the request."""
        # Swap IPs
        src_ip = req_packet[16:20]
        dst_ip = req_packet[12:16]

        # IP Header
        ip_header = bytearray(req_packet[:ihl])
        total_len = ihl + 8 + len(resp_payload)
        ip_header[2:4] = struct.pack("!H", total_len)
        ip_header[12:16] = src_ip
        ip_header[16:20] = dst_ip

        # Recalculate IP Checksum
        ip_header[10:12] = b'\x00\x00'
        chksum = self._calc_checksum(ip_header)
        ip_header[10:12] = struct.pack("!H", chksum)

        # UDP Header — swap ports
        udp_header = bytearray(req_packet[ihl:ihl + 8])
        src_port = req_packet[ihl + 2:ihl + 4]
        dst_port = req_packet[ihl:ihl + 2]
        udp_header[0:2] = src_port
        udp_header[2:4] = dst_port
        udp_len = 8 + len(resp_payload)
        udp_header[4:6] = struct.pack("!H", udp_len)
        udp_header[6:8] = b'\x00\x00'  # Zero checksum (valid for IPv4 UDP)

        return bytes(ip_header) + bytes(udp_header) + resp_payload

    def _calc_checksum(self, data):
        """Calculate IP header checksum."""
        if len(data) % 2 == 1:
            data += b'\0'
        s = sum(struct.unpack("!%dH" % (len(data) // 2), data))
        s = (s >> 16) + (s & 0xffff)
        s += s >> 16
        return (~s) & 0xffff
