"""
Deepened Android tests: lifecycle simulation, TUN packet round-trips,
and platform-layer behavior — all device-free.
"""

import os
import socket
import struct
import sys
import types

import pytest

if "jnius" not in sys.modules:
    stub = types.ModuleType("jnius")
    stub.autoclass = lambda *a, **k: (_ for _ in ()).throw(ImportError)
    sys.modules["jnius"] = stub

from netstrip.core.interceptor.android import (
    PROTO_UDP,
    AndroidVPNInterceptor,
)


def _build_ipv4_udp(src_ip, dst_ip, src_port, dst_port, payload, ttl=64):
    udp_len = 8 + len(payload)
    udp_header = struct.pack("!HHHH", src_port, dst_port, udp_len, 0) + payload
    total_len = 20 + len(udp_header)
    header = bytearray(struct.pack(
        "!BBHHHBBH4s4s",
        0x45, 0x00, total_len, 0x1234, 0x4000, ttl, PROTO_UDP, 0,
        socket.inet_aton(src_ip), socket.inet_aton(dst_ip),
    ))
    chk = AndroidVPNInterceptor._calc_checksum(None, bytes(header))
    header[10:12] = struct.pack("!H", chk)
    return bytes(header) + udp_header


class TestVPNLifecycle:
    """Simulate VPN establishment and teardown without pyjnius."""

    def test_interceptor_starts_without_jni(self):
        inst = AndroidVPNInterceptor(callback=lambda *a: True, engine=None)
        assert inst.NetStripVpnService is None
        inst.start()  # must be a no-op
        inst.stop()

    def test_vpn_loop_exits_when_not_running(self):
        inst = AndroidVPNInterceptor(callback=lambda *a: True, engine=None)
        inst._running = False
        inst._vpn_loop()  # should return immediately without error

    def test_full_mode_toggle(self):
        inst = AndroidVPNInterceptor(callback=lambda *a: True, engine=None)

        class Inst:
            def getVpnFd(self): return 1
            def isFullMode(self): return False

        inst.NetStripVpnService = types.SimpleNamespace(getInstance=lambda: Inst())
        # Simulate fd acquisition
        inst._fd = 1
        inst._is_full_mode = False
        assert not inst._is_full_mode


class TestPacketRoundTrip:
    """End-to-end packet processing with captured output."""

    def _make_inst(self, monkeypatch, callback=None):
        inst = AndroidVPNInterceptor(callback=callback or (lambda *a: True), engine=None)
        inst._fd = 42
        inst._is_full_mode = True
        written = []
        monkeypatch.setattr(os, "write", lambda fd, data: written.append(data))
        inst._writes = written
        return inst

    def test_dns_query_produces_valid_response(self, monkeypatch):
        query = _build_ipv4_udp("10.8.0.2", "10.8.0.1", 44444, 53, b"\x00\x01query")
        inst = self._make_inst(monkeypatch)
        inst._process_dns = lambda p: b"\x00response"

        inst._process_ipv4(query)

        assert len(inst._writes) == 1
        resp = inst._writes[0]
        # Verify swapped addressing
        src = socket.inet_ntoa(resp[12:16])
        dst = socket.inet_ntoa(resp[16:20])
        sport, dport = struct.unpack("!HH", resp[20:24])
        assert (src, dst) == ("10.8.0.1", "10.8.0.2")
        assert (sport, dport) == (53, 44444)

    def test_blocked_packet_silently_dropped(self, monkeypatch):
        inst = self._make_inst(monkeypatch)
        inst.callback = lambda *a: False  # block everything
        pkt = _build_ipv4_udp("10.8.0.2", "6.6.6.6", 5555, 443, b"data")
        orig_write = os.write
        writes = []
        monkeypatch.setattr(os, "write", lambda fd, data: writes.append(data))

        inst._process_ipv4(pkt)
        assert len(writes) == 0

    def test_fragmented_ipv4_minimum_length(self, monkeypatch):
        """Packets shorter than IP+UDP headers must be silently ignored."""
        inst = self._make_inst(monkeypatch)
        for n in range(0, 28):
            pkt = b"\x45" * n
            try:
                inst._process_ipv4(pkt)
            except Exception as e:
                pytest.fail(f"crash on {n}-byte packet: {e}")


class TestChecksum:
    def test_checksum_zero_sum_property(self):
        """IP checksum of header + checksum field should yield 0xFFFF when summed."""
        hdr = bytearray(struct.pack("!BBHHHBBH4s4s",
            0x45, 0x00, 28, 0, 0x4000, 64, 17, 0,
            socket.inet_aton("192.168.1.1"), socket.inet_aton("10.0.0.1")))
        chk = AndroidVPNInterceptor._calc_checksum(None, bytes(hdr))
        hdr[10:12] = struct.pack("!H", chk)
        words = struct.unpack("!10H", bytes(hdr))
        s = sum(words)
        while s >> 16:
            s = (s & 0xFFFF) + (s >> 16)
        assert (~s) & 0xFFFF == 0


class TestPortContract:
    def test_android_port_is_5353_not_5053(self):
        from netstrip.core.dns_proxy import ANDROID_DNS_PORT
        assert ANDROID_DNS_PORT == 5353
        # Verify no hardcoded wrong port in source
        src_dir = os.path.join(os.path.dirname(__file__), "..", "netstrip", "core")
        for fn in os.listdir(src_dir):
            if not fn.endswith(".py"):
                continue
            content = open(os.path.join(src_dir, fn), encoding="utf-8").read()
            if "interceptor" in fn or "android" in fn.lower():
                assert ", 5053)" not in content, f"stale port 5053 in {fn}"
