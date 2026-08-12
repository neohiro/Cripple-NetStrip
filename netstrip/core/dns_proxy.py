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

# NetStrip supports DoH, DoT, and UDP. Upstream queries can be configured to force
# DoH/DoT to prevent ISP snooping, or fallback to standard UDP.
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
    import os, json
    # Load online DoH providers list dynamically from the data directory
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _doh_file = os.path.join(_current_dir, '..', 'data', 'lists', 'doh_providers_online.json')
    if os.path.exists(_doh_file):
        with open(_doh_file, 'r', encoding='utf-8') as _f:
            _online_providers = json.load(_f)
            
        for _p in _online_providers:
            _ip = _p['ip']
            _name = _p['hostname']
            
            # Filter out DNSCrypt servers since we only support DoH, DoT and UDP natively
            if 'dnscry' in _name.lower() or 'dnscrypt' in _name.lower():
                continue
                
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

class _DNSConnectionPool:
    """Thread-safe connection pool for DNS over TLS (DoT) and DNS over HTTPS (DoH) keep-alive sockets."""
    def __init__(self, idle_timeout: float = 30.0, max_connections_per_host: int = 4):
        self.idle_timeout = idle_timeout
        self.max_connections_per_host = max_connections_per_host
        self._dot_pool = {}  # ip -> list of (tls_sock, raw_sock, last_used_time)
        self._doh_pool = {}  # (ip, host) -> list of (http_conn, last_used_time)
        self._lock = threading.Lock()

    def get_dot_socket(self, ip: str, port: int = 853, timeout: float = 2.0):
        now = time.time()
        with self._lock:
            if ip in self._dot_pool:
                while self._dot_pool[ip]:
                    tls_sock, raw_sock, last_used = self._dot_pool[ip].pop()
                    if now - last_used <= self.idle_timeout:
                        try:
                            import select
                            r, _, _ = select.select([tls_sock], [], [], 0)
                            if not r:
                                tls_sock.settimeout(timeout)
                                return tls_sock, raw_sock
                        except Exception:
                            pass
                    self._close_sock(tls_sock, raw_sock)

        # Create a new TLS socket
        try:
            import socket
            import ssl
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            raw_sock = socket.create_connection((ip, port), timeout=timeout)
            tls_sock = ctx.wrap_socket(raw_sock)
            tls_sock.settimeout(timeout)
            return tls_sock, raw_sock
        except Exception:
            return None, None

    def put_dot_socket(self, ip: str, tls_sock, raw_sock):
        if not tls_sock or not raw_sock:
            return
        now = time.time()
        with self._lock:
            if ip not in self._dot_pool:
                self._dot_pool[ip] = []
            if len(self._dot_pool[ip]) < self.max_connections_per_host:
                self._dot_pool[ip].append((tls_sock, raw_sock, now))
                return
        self._close_sock(tls_sock, raw_sock)

    def discard_dot_socket(self, tls_sock, raw_sock):
        self._close_sock(tls_sock, raw_sock)

    def _close_sock(self, tls_sock, raw_sock):
        try:
            if tls_sock:
                tls_sock.close()
        except Exception:
            pass
        try:
            if raw_sock:
                raw_sock.close()
        except Exception:
            pass

    def get_doh_connection(self, ip: str, host: str, timeout: float = 2.0):
        key = (ip, host)
        now = time.time()
        with self._lock:
            if key in self._doh_pool:
                while self._doh_pool[key]:
                    conn, last_used = self._doh_pool[key].pop()
                    if now - last_used <= self.idle_timeout and getattr(conn, 'sock', None):
                        try:
                            import select
                            r, _, _ = select.select([conn.sock], [], [], 0)
                            if not r:
                                conn.timeout = timeout
                                return conn
                        except Exception:
                            pass
                    try:
                        conn.close()
                    except Exception:
                        pass

        # Create new HTTPS connection
        try:
            import http.client
            import ssl
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            conn = http.client.HTTPSConnection(ip, 443, context=ctx, timeout=timeout)
            return conn
        except Exception:
            return None

    def put_doh_connection(self, ip: str, host: str, conn):
        if not conn:
            return
        key = (ip, host)
        now = time.time()
        with self._lock:
            if key not in self._doh_pool:
                self._doh_pool[key] = []
            if len(self._doh_pool[key]) < self.max_connections_per_host:
                self._doh_pool[key].append((conn, now))
                return
        try:
            conn.close()
        except Exception:
            pass

    def discard_doh_connection(self, conn):
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    def close_all(self):
        with self._lock:
            for ip, list_socks in self._dot_pool.items():
                for tls_sock, raw_sock, _ in list_socks:
                    self._close_sock(tls_sock, raw_sock)
            self._dot_pool.clear()

            for key, list_conns in self._doh_pool.items():
                for conn, _ in list_conns:
                    try:
                        conn.close()
                    except Exception:
                        pass
            self._doh_pool.clear()


class NetStripResolver(BaseResolver):
    def __init__(self, classifier: TrafficClassifier, db: Database, default_upstream_port: int = 53, engine=None):
        self.classifier = classifier
        self.db = db
        self.engine = engine
        self.on_status: Callable = None
        self.upstream_port = default_upstream_port
        from collections import OrderedDict
        self._dns_cache = OrderedDict()  # (qname, qtype) -> (timestamp, proxy_response_bytes)
        self._max_cache_size = 5000
        self._cache_ttl = 300  # 5 minutes TTL
        self._proc_cache = OrderedDict()  # domain -> (timestamp, process_name)
        self._proc_cache_ttl = 60  # 60 seconds
        self._conn_pool = _DNSConnectionPool(idle_timeout=30.0, max_connections_per_host=4)
        
    def _infer_process(self, domain: str, src_port: int = None) -> str:
        from netstrip.core.process_utils import resolve_process_identity, normalize_process_name
        # Check fast in-memory process cache
        now = time.time()
        if domain in self._proc_cache:
            ts, p_name = self._proc_cache[domain]
            if now - ts < self._proc_cache_ttl:
                return p_name

        # 1. Direct Socket Mapping: If the app sends its own UDP packets
        if src_port and self.engine and hasattr(self.engine, 'connection_monitor'):
            pid = self.engine.connection_monitor.port_to_pid.get(src_port)
            if pid:
                try:
                    import psutil
                    proc = psutil.Process(pid)
                    p_name, _, _, _ = resolve_process_identity(proc)
                    if p_name and p_name.lower() not in ('svchost', 'svchost.exe', 'dnscache', 'unknown'):
                        if len(self._proc_cache) > 2000:
                            self._proc_cache.popitem(last=False)
                        self._proc_cache[domain] = (now, p_name)
                        return p_name
                except Exception:
                    pass
                    
        # 2. Database History Inference
        try:
            with self.db.lock:
                with self.db._get_connection() as conn:
                    # A. Has this exact domain been requested by ANY process recently?
                    query1 = """
                        SELECT process_name FROM connection_log 
                        WHERE domain = ? AND process_name NOT IN ('Unknown (DNS)', 'Cripple (Internal)', 'Cripple')
                        ORDER BY id DESC LIMIT 1
                    """
                    row = conn.execute(query1, (domain,)).fetchone()
                    if row and row['process_name']:
                        p_name = normalize_process_name(row['process_name'])
                        if len(self._proc_cache) > 2000:
                            self._proc_cache.popitem(last=False)
                        self._proc_cache[domain] = (now, p_name)
                        return p_name
                        
                    # B. Fallback to Parent Domain correlation (e.g. ads.example.com -> example.com)
                    parts = domain.split('.')
                    if len(parts) > 2:
                        parent_domain = f"%.{parts[-2]}.{parts[-1]}"
                        query2 = """
                            SELECT process_name FROM connection_log 
                            WHERE domain LIKE ? AND process_name NOT IN ('Unknown (DNS)', 'Cripple (Internal)', 'Cripple')
                            ORDER BY id DESC LIMIT 1
                        """
                        row = conn.execute(query2, (parent_domain,)).fetchone()
                        if row and row['process_name']:
                            p_name = normalize_process_name(row['process_name'])
                            if len(self._proc_cache) > 2000:
                                self._proc_cache.popitem(last=False)
                            self._proc_cache[domain] = (now, p_name)
                            return p_name
                            
        except Exception as e:
            logger.debug(f"Process inference failed: {e}")
            
        inferred = "Unknown (DNS)"
        if len(self._proc_cache) > 2000:
            self._proc_cache.popitem(last=False)
        self._proc_cache[domain] = (now, inferred)
        return inferred

    def _send_dot(self, request_packet, ip, timeout=2):
        import struct
        for attempt in range(2):
            tls_sock, raw_sock = self._conn_pool.get_dot_socket(ip, port=853, timeout=timeout)
            if not tls_sock:
                return None
            try:
                length = struct.pack("!H", len(request_packet))
                tls_sock.sendall(length + request_packet)
                
                resp_len_bytes = tls_sock.recv(2)
                if not resp_len_bytes or len(resp_len_bytes) < 2:
                    self._conn_pool.discard_dot_socket(tls_sock, raw_sock)
                    continue
                resp_len = struct.unpack("!H", resp_len_bytes)[0]
                
                resp_data = b""
                while len(resp_data) < resp_len:
                    chunk = tls_sock.recv(resp_len - len(resp_data))
                    if not chunk: break
                    resp_data += chunk
                    
                if len(resp_data) == resp_len:
                    self._conn_pool.put_dot_socket(ip, tls_sock, raw_sock)
                    return resp_data
                else:
                    self._conn_pool.discard_dot_socket(tls_sock, raw_sock)
            except Exception as e:
                self._conn_pool.discard_dot_socket(tls_sock, raw_sock)
                if attempt == 1:
                    logger.debug(f"DoT error for {ip}: {e}")
        return None

    def _send_doh(self, request_packet, ip, host, url_path, timeout=2):
        for attempt in range(2):
            conn = self._conn_pool.get_doh_connection(ip, host, timeout=timeout)
            if not conn:
                return None
            try:
                headers = {
                    'Host': host,
                    'Content-Type': 'application/dns-message',
                    'Accept': 'application/dns-message',
                    'Content-Length': str(len(request_packet)),
                    'Connection': 'keep-alive'
                }
                conn.request("POST", url_path, body=request_packet, headers=headers)
                res = conn.getresponse()
                if res.status == 200:
                    data = res.read()
                    self._conn_pool.put_doh_connection(ip, host, conn)
                    return data
                else:
                    self._conn_pool.discard_doh_connection(conn)
            except Exception as e:
                self._conn_pool.discard_doh_connection(conn)
                if attempt == 1:
                    logger.debug(f"DoH error for {ip}: {e}")
        return None

    @staticmethod
    def _is_ghost_privacy_query(domain: str) -> bool:
        """Identify OS network topology / discovery queries that leak identity to ISP/WAN DNS."""
        d_lower = domain.lower().strip('.')
        # 1. WPAD proxy auto-discovery
        if d_lower == "wpad" or d_lower.startswith("wpad.") or ".wpad." in d_lower:
            return True
        # 2. ISATAP tunnel auto-discovery
        if d_lower == "isatap" or d_lower.startswith("isatap.") or ".isatap." in d_lower:
            return True
        # 3. Directory Services / LDAP / Kerberos SRV discovery queries (e.g. _ldap._tcp.dc._msdcs.dynamic.ziggo.nl)
        if any(srv in d_lower for srv in ("_msdcs", "_ldap._tcp", "_kerberos._tcp", "_kpasswd._tcp", "_gc._tcp", "_sip._tls", "_ldap._tcp.dc")):
            return True
        # 4. NetBIOS / local broadcast leak queries
        if d_lower.startswith("netbios.") or ".netbios." in d_lower or d_lower.endswith(".corp") or d_lower.endswith(".internal"):
            return True
        return False

    def resolve(self, request, handler):
        from netstrip.core.modes import ProtectionLevel, ConnectionCategory, ConnectionAction
        from dnslib import RCODE
        
        qname = str(request.q.qname)
        # Strip trailing dot for processing
        domain = qname.rstrip('.') if qname.endswith('.') else qname
        qtype = QTYPE[request.q.qtype]

        # 1. Ghost Mode & System Connection Privacy Sinkhole Check:
        # Prevents Windows/OS leaks like WPAD, _ldap._tcp.dc._msdcs, ISATAP, NetBIOS from escaping to upstream WAN/ISP DNS.
        is_ghost = hasattr(self.classifier, 'mode') and getattr(self.classifier.mode, 'level', None) in (ProtectionLevel.GHOST, ProtectionLevel.PARANOID, ProtectionLevel.STRICT)
        block_sys = self.db.get_setting("block_system_connections", "false") == "true"
        
        if (is_ghost or block_sys) and self._is_ghost_privacy_query(domain):
            category = ConnectionCategory.SYSTEM
            action = ConnectionAction.BLOCK
        else:
            # 1. Classify
            category = self.classifier.classify_domain(domain)
            
            # 2. Get action from mode
            action = self.classifier.mode.get_action_for_category(category, self.db)

        src_port = getattr(handler, 'client_address', (None, None))[1]
        process_name = self._infer_process(domain, src_port)

        # 3. Handle Sinkhole & Throttle Logs
        if action == ConnectionAction.BLOCK or action == ConnectionAction.SINKHOLE:
            now = time.time()
            throttle_key = f"{process_name}:{domain}"
            last_blocked = getattr(self, '_last_blocked_cache', {}).get(throttle_key, 0)
            
            # Initialize cache if missing
            if not hasattr(self, '_last_blocked_cache'):
                self._last_blocked_cache = {}
                
            # Only log and broadcast if we haven't blocked this exact domain for this app in the last 10 seconds
            if now - last_blocked > 10:
                self._last_blocked_cache[throttle_key] = now
                if self.on_status:
                    self.on_status(f"DNS Autoblocked {category.value.capitalize()}: {domain}")
                
                src_port = getattr(handler, 'client_address', (None, None))[1]
                self.db.log_connection({
                    'process_name': process_name,
                    'domain': domain,
                    'protocol': 'DNS',
                    'category': category.value,
                    'action': action.value,
                    'mode': getattr(getattr(self.classifier, 'mode', None), 'name', 'GHOST')
                })
                self.db.update_daily_stats(action.value, category.value)
                
            # For SRV / discovery queries, return NXDOMAIN immediately so OS ceases probing
            reply = request.reply()
            if "_msdcs" in domain or "_ldap" in domain or "_kerberos" in domain:
                reply.header.rcode = RCODE.NXDOMAIN
            else:
                reply.add_answer(RR(qname, rdata=A("0.0.0.0")))
            return reply

        # 4. Handle Allow (Check LRU cache first for instant resolution)
        cache_key = (qname, qtype)
        if cache_key in self._dns_cache:
            timestamp, cached_bytes = self._dns_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                self._dns_cache.move_to_end(cache_key)
                try:
                    cached_record = DNSRecord.parse(cached_bytes)
                    cached_record.header.id = request.header.id
                    return cached_record
                except Exception:
                    pass
            else:
                del self._dns_cache[cache_key]

        # Cache Miss: Log Allowed connection and forward upstream
        src_port = getattr(handler, 'client_address', (None, None))[1]
        self.db.log_connection({
            'process_name': process_name,
            'domain': domain,
            'protocol': 'DNS',
            'category': category.value,
            'action': action.value,
            'mode': self.classifier.mode.name
        })
        self.db.update_daily_stats(action.value, category.value)
        
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
            
            force_doh_setting = self.db.get_setting('force_doh', 'auto')
            force_doh = force_doh_setting != 'false'
            
            if force_doh and not has_local_proxy:
                if upstream_ip in DOH_PROVIDERS:
                    host, url_path = DOH_PROVIDERS[upstream_ip]
                    proxy_response = self._send_doh(request.pack(), upstream_ip, host, url_path, timeout=1.5)
                
                if not proxy_response and is_public_ip:
                    proxy_response = self._send_dot(request.pack(), upstream_ip, timeout=1.5)
                    
                if not proxy_response:
                    if force_doh_setting == 'true':
                        reply = request.reply()
                        reply.header.rcode = RCODE.SERVFAIL
                        return reply
                    else:
                        try:
                            proxy_response = request.send(upstream_ip, self.upstream_port, timeout=1.5)
                        except Exception:
                            proxy_response = None
            else:
                # 1. Primary: Standard UDP port 53 (Fastest, 10-30ms response time, 1.5s timeout)
                try:
                    proxy_response = request.send(upstream_ip, self.upstream_port, timeout=1.5)
                except Exception:
                    proxy_response = None
    
                # 2. Secondary: Try DNS-over-TLS (DoT) or DNS-over-HTTPS (DoH) if standard UDP failed and public IP
                if not proxy_response and is_public_ip:
                    proxy_response = self._send_dot(request.pack(), upstream_ip, timeout=1.5)
                    if not proxy_response and upstream_ip in DOH_PROVIDERS:
                        host, url_path = DOH_PROVIDERS[upstream_ip]
                        proxy_response = self._send_doh(request.pack(), upstream_ip, host, url_path, timeout=1.5)

            if not proxy_response:
                raise TimeoutError(f"No response from upstream DNS {upstream_ip}")

            record = DNSRecord.parse(proxy_response)
            
            # Save to bounded LRU cache
            if len(self._dns_cache) >= self._max_cache_size:
                self._dns_cache.popitem(last=False)
            self._dns_cache[cache_key] = (time.time(), proxy_response)
            self._dns_cache.move_to_end(cache_key)
            
            # Extract A (1) and AAAA (28) records to populate persistent database cache
            # Exclude our own telemetry / IP checks from polluting the shared global DNS cache with AWS IPs
            exclude_domains = ('api.ipify.org', 'ipinfo.io', 'ipapi.co', 'ipwho.is', 'icanhazip.com', 'ifconfig.me', 'raw.githubusercontent.com', 'api.github.com')
            
            for rr in record.rr:
                if rr.rtype in (1, 28): 
                    ip = str(rr.rdata)
                    if domain.lower() not in exclude_domains:
                        self.db.cache_domain_mapping(ip, domain)
                    
            return record
        except Exception as e:
            logger.debug(f"DNS Upstream error for {domain} via {upstream_ip}: {e}")
            force_doh_setting = self.db.get_setting('force_doh', 'auto')
            if force_doh_setting == 'true' and not has_local_proxy:
                reply = request.reply()
                reply.header.rcode = RCODE.SERVFAIL
                return reply
                
            if upstream_ip != "1.1.1.1":
                try:
                    proxy_response = request.send("1.1.1.1", 53, timeout=1.5)
                    record = DNSRecord.parse(proxy_response)
                    return record
                except Exception as e_fallback:
                    logger.debug(f"DNS Fallback error for {domain}: {e_fallback}")
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
        if hasattr(self.resolver, '_conn_pool'):
            self.resolver._conn_pool.close_all()
        logger.info("DNS Proxy stopped")
