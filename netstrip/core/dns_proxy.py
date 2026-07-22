"""
DNS Proxy Server for NetStrip
Intercepts local DNS queries, classifies them, and acts as a sinkhole for blocked domains.
"""

from dnslib import DNSRecord, RR, A, QTYPE
from dnslib.server import DNSServer, BaseResolver, DNSLogger
import threading
import logging
import time
from netstrip.core.classifier import TrafficClassifier
from netstrip.core.modes import ConnectionAction
from netstrip.data.database import Database
import urllib.request
from typing import Callable

logger = logging.getLogger(__name__)

# Disable DoH to prevent recursive getaddrinfo loop since NetStrip itself intercepts DNS.
# Upstream queries will fallback to standard UDP which uses raw IP sockets.
DOH_PROVIDERS = {
    "1.1.1.1": ("cloudflare-dns.com", "/dns-query"),
    "1.1.1.2": ("security.cloudflare-dns.com", "/dns-query"),
    "1.1.1.3": ("family.cloudflare-dns.com", "/dns-query"),
    "8.8.8.8": ("dns.google", "/dns-query"),
    "9.9.9.9": ("dns.quad9.net", "/dns-query"),
    "9.9.9.10": ("dns10.quad9.net", "/dns-query"),
    "94.140.14.14": ("dns.adguard-dns.com", "/dns-query"),
    "94.140.14.15": ("family.adguard-dns.com", "/dns-query"),
    "94.140.15.15": ("dns.adguard-dns.com", "/dns-query"),
    # OpenDNS
    "208.67.222.222": ("doh.opendns.com", "/dns-query"),
    "208.67.220.220": ("doh.opendns.com", "/dns-query"),
    # Mullvad
    "194.242.2.4": ("doh.mullvad.net", "/dns-query"),
    # ControlD
    "76.76.2.0": ("freedns.controld.com", "/p0"),
    # DNS.SB
    "185.222.222.222": ("doh.dns.sb", "/dns-query"),
    # LibreDNS
    "116.202.176.26": ("doh.libredns.gr", "/dns-query"),
}

DNS_UPSTREAM_OPTIONS = {
    "1.1.1.1": "1.1.1.1 (Cloudflare)",
    "8.8.8.8": "8.8.8.8 (Google)",
    "9.9.9.9": "9.9.9.9 (Quad9)",
    "94.140.14.14": "94.140.14.14 (AdGuard)",
    "208.67.222.222": "208.67.222.222 (OpenDNS)",
    "194.242.2.4": "194.242.2.4 (Mullvad)",
    "76.76.2.0": "76.76.2.0 (ControlD)",
    "185.222.222.222": "185.222.222.222 (DNS.SB)",
    "116.202.176.26": "116.202.176.26 (LibreDNS)",
}

# Dynamically load the online providers list if available
try:
    import json
    import os
    # lists_dir is typically at C:\Users\Wout\.gemini\antigravity\scratch\NetStrip\netstrip\data\lists
    # So we compute it dynamically
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _doh_file = os.path.join(_current_dir, '..', 'data', 'lists', 'doh_providers_online.json')
    if os.path.exists(_doh_file):
        with open(_doh_file, 'r', encoding='utf-8') as _f:
            _online_providers = json.load(_f)
            
        for _p in _online_providers:
            _ip = _p['ip']
            _name = _p['hostname']
            if _p['type'] == 'DoH':
                DOH_PROVIDERS[_ip] = (_name, _p['path'])
            # We don't have DOT_PROVIDERS dict, we just use DoT implicitly if they aren't in DOH_PROVIDERS
            # but for the upstream options dropdown, we add them all!
            if _ip not in DNS_UPSTREAM_OPTIONS:
                # Add domain base name for a cleaner UI (e.g. dns.google -> google)
                _short_name = _name.split('.')[-2].title() if '.' in _name else _name.title()
                DNS_UPSTREAM_OPTIONS[_ip] = f"{_ip} ({_short_name})"
                
except Exception as e:
    logger.debug(f"Could not load online DoH providers: {e}")

class NetStripResolver(BaseResolver):
    def __init__(self, classifier: TrafficClassifier, db: Database, default_upstream_port: int = 53, engine=None):
        self.classifier = classifier
        self.db = db
        self.engine = engine
        self.on_status: Callable = None
        self.upstream_port = default_upstream_port
        self._dns_cache = {} # (qname, qtype) -> (timestamp, proxy_response_bytes)
        self._cache_ttl = 300 # 5 minutes TTL
        
    def _infer_process(self, domain: str, src_port: int = None) -> str:
        # 1. Direct Socket Mapping: If the app bypasses OS DNS and sends its own UDP packets
        if src_port and self.engine and hasattr(self.engine, 'connection_monitor'):
            pid = self.engine.connection_monitor.port_to_pid.get(src_port)
            if pid:
                try:
                    import psutil
                    name = psutil.Process(pid).name()
                    if name.lower() not in ('svchost.exe', 'dnscache'):
                        return name
                except:
                    pass
                    
        # 2. Database History Inference
        try:
            with self.db.lock:
                with self.db._get_connection() as conn:
                    # A. Has this exact domain been requested by ANY process recently?
                    query1 = """
                        SELECT process_name FROM connection_log 
                        WHERE domain = ? AND process_name != 'Unknown (DNS)'
                        ORDER BY id DESC LIMIT 1
                    """
                    row = conn.execute(query1, (domain,)).fetchone()
                    if row and row['process_name']:
                        return row['process_name']
                        
                    # B. Fallback to Parent Domain correlation (e.g. ads.example.com -> example.com)
                    parts = domain.split('.')
                    if len(parts) > 2:
                        parent_domain = f"%.{parts[-2]}.{parts[-1]}"
                        query2 = """
                            SELECT process_name FROM connection_log 
                            WHERE domain LIKE ? AND process_name != 'Unknown (DNS)'
                            ORDER BY id DESC LIMIT 1
                        """
                        row = conn.execute(query2, (parent_domain,)).fetchone()
                        if row and row['process_name']:
                            return row['process_name']
                            
        except Exception as e:
            logger.debug(f"Process inference failed: {e}")
            
        return "Unknown (DNS)"

    def _send_dot(self, request_packet, ip, timeout=3):
        import socket
        import ssl
        import struct
        try:
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            
            sock = socket.create_connection((ip, 853), timeout=timeout)
            tls_sock = ctx.wrap_socket(sock)
            try:
                length = struct.pack("!H", len(request_packet))
                tls_sock.sendall(length + request_packet)
                
                resp_len_bytes = tls_sock.recv(2)
                if not resp_len_bytes:
                    return None
                resp_len = struct.unpack("!H", resp_len_bytes)[0]
                
                resp_data = b""
                while len(resp_data) < resp_len:
                    chunk = tls_sock.recv(resp_len - len(resp_data))
                    if not chunk: break
                    resp_data += chunk
                    
                return resp_data if len(resp_data) == resp_len else None
            finally:
                try:
                    tls_sock.close()
                except: pass
                try:
                    sock.close()
                except: pass
        except Exception as e:
            logger.debug(f"DoT error for {ip}: {e}")
            return None

    def _send_doh(self, request_packet, ip, host, url_path, timeout=2):
        import urllib.request
        import http.client
        import socket
        import ssl
        try:
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            class CustomHTTPSConnection(http.client.HTTPSConnection):
                def connect(self):
                    sock = socket.create_connection((ip, self.port), self.timeout, self.source_address)
                    self.sock = ctx.wrap_socket(sock, server_hostname=self.host)

            class CustomHTTPSHandler(urllib.request.HTTPSHandler):
                def https_open(self, req):
                    return self.do_open(CustomHTTPSConnection, req)

            opener = urllib.request.build_opener(CustomHTTPSHandler())
            req = urllib.request.Request(
                f"https://{host}{url_path}", 
                data=request_packet, 
                headers={'Content-Type': 'application/dns-message', 'Accept': 'application/dns-message'}
            )
            with opener.open(req, timeout=timeout) as response:
                return response.read()
        except Exception as e:
            logger.debug(f"DoH error for {ip}: {e}")
            return None

    def resolve(self, request, handler):
        qname = str(request.q.qname)
        # Strip trailing dot for processing
        domain = qname.rstrip('.') if qname.endswith('.') else qname
        qtype = QTYPE[request.q.qtype]

        # 1. Classify
        category = self.classifier.classify_domain(domain)
        
        # 2. Get action from mode
        action = self.classifier.mode.get_action_for_category(category, self.db)

        # 3. Log to DB
        src_port = getattr(handler, 'client_address', (None, None))[1]
        process_name = self._infer_process(domain, src_port)
        self.db.log_connection({
            'process_name': process_name,
            'domain': domain,
            'protocol': 'DNS',
            'category': category.value,
            'action': action.value,
            'mode': self.classifier.mode.name
        })
        self.db.update_daily_stats(action.value, category.value)

        # 4. Handle Sinkhole
        if action == ConnectionAction.BLOCK or action == ConnectionAction.SINKHOLE:
            if self.on_status:
                self.on_status(f"DNS Autoblocked {category.value.capitalize()}: {domain}")
            reply = request.reply()
            reply.add_answer(RR(qname, rdata=A("0.0.0.0")))
            return reply

        # 5. Handle Allow (Forward to Upstream)
        
        # Check cache
        import time
        cache_key = (qname, qtype)
        if cache_key in self._dns_cache:
            timestamp, cached_bytes = self._dns_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                # Re-parse from raw bytes and inject the correct transaction ID
                try:
                    cached_record = DNSRecord.parse(cached_bytes)
                    cached_record.header.id = request.header.id
                    return cached_record
                except:
                    pass
            else:
                del self._dns_cache[cache_key]
        
        # Fetch dynamic upstream from settings
        upstream_ip = self.db.get_setting("dns_upstream", "8.8.8.8")
        has_local_proxy = bool(self.db.get_setting("local_dns_tool"))
        
        if upstream_ip == "127.127.127.127":
            # Never proxy to our own bind IP
            upstream_ip = "8.8.8.8" 
        elif upstream_ip in ("127.0.0.1", "localhost", "::1") and not has_local_proxy:
            # Prevent infinite recursive loop if we didn't detect a 3rd party tool (e.g. YogaDNS, DNSCrypt)
            upstream_ip = "8.8.8.8" 
            
        try:
            proxy_response = None
            is_public_ip = not upstream_ip.startswith("127.") and upstream_ip != "::1"
            
            # 1. Try DNS-over-TLS (DoT) within 2 seconds. Better performance (less overhead) but sometimes blocked by firewalls on port 853.
            if is_public_ip:
                proxy_response = self._send_dot(request.pack(), upstream_ip, timeout=2)
                
            # 2. Try DNS-over-HTTPS (DoH) within 3 seconds if DoT failed. Higher overhead, but evades firewalls on port 443.
            if not proxy_response and is_public_ip and upstream_ip in DOH_PROVIDERS:
                host, url_path = DOH_PROVIDERS[upstream_ip]
                proxy_response = self._send_doh(request.pack(), upstream_ip, host, url_path, timeout=3)
                
            # 3. Fallback to standard UDP port 53 within 4 seconds if all secure methods failed or local proxy
            if not proxy_response:
                proxy_response = request.send(upstream_ip, self.upstream_port, timeout=4)
                
            record = DNSRecord.parse(proxy_response)
            
            # Save to cache
            if len(self._dns_cache) > 10000:
                self._dns_cache.clear()
            self._dns_cache[cache_key] = (time.time(), proxy_response)
            
            # Extract A (1) and AAAA (28) records to populate persistent database cache
            for rr in record.rr:
                if rr.rtype in (1, 28): 
                    ip = str(rr.rdata)
                    self.db.cache_domain_mapping(ip, domain)
                    
            return record
        except Exception as e:
            logger.error(f"DNS Upstream error for {domain} via {upstream_ip}: {e}")
            if upstream_ip != "1.1.1.1":
                try:
                    logger.info(f"Falling back to 1.1.1.1 for {domain}")
                    proxy_response = request.send("1.1.1.1", 53, timeout=3)
                    record = DNSRecord.parse(proxy_response)
                    # Don't cache the fallback A records, just return them
                    return record
                except Exception as e_fallback:
                    logger.error(f"DNS Fallback error: {e_fallback}")
            return request.reply()


class DNSProxyService:
    def __init__(self, classifier: TrafficClassifier, db: Database, bind_ip="127.0.0.1", port=53, engine=None):
        self.resolver = NetStripResolver(classifier, db, engine=engine)
        self.bind_ip = bind_ip
        self.port = port
        self.dns_logger = DNSLogger(log="") 
        import socketserver
        self.udp_server = DNSServer(self.resolver, port=port, address=bind_ip, logger=self.dns_logger, server=socketserver.ThreadingUDPServer)
        self.tcp_server = DNSServer(self.resolver, port=port, address=bind_ip, tcp=True, logger=self.dns_logger, server=socketserver.ThreadingTCPServer)
        
        # IPv6 Support
        class ThreadingUDPServer6(socketserver.ThreadingUDPServer): address_family = __import__('socket').AF_INET6
        class ThreadingTCPServer6(socketserver.ThreadingTCPServer): address_family = __import__('socket').AF_INET6
        
        self.udp_server_v6 = None
        self.tcp_server_v6 = None
        try:
            self.udp_server_v6 = DNSServer(self.resolver, port=port, address="fd00::127", logger=self.dns_logger, server=ThreadingUDPServer6)
            self.tcp_server_v6 = DNSServer(self.resolver, port=port, address="fd00::127", tcp=True, logger=self.dns_logger, server=ThreadingTCPServer6)
        except Exception as e:
            logger.warning(f"Could not bind IPv6 DNS Proxy: {e}")
            
        self.is_running = False

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.udp_server.start_thread()
        self.tcp_server.start_thread()
        if self.udp_server_v6:
            self.udp_server_v6.start_thread()
            self.tcp_server_v6.start_thread()
        logger.info(f"DNS Proxy started on {self.bind_ip}:{self.port} and [fd00::127]:{self.port}")

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self.udp_server.stop()
        self.tcp_server.stop()
        if self.udp_server_v6:
            self.udp_server_v6.stop()
            self.tcp_server_v6.stop()
        logger.info("DNS Proxy stopped")
