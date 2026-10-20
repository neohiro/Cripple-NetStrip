"""
Linux Platform Implementation for NetStrip
"""
import os
import subprocess
import logging
from typing import List, Optional
from netstrip.platform.base import PlatformBase

logger = logging.getLogger(__name__)

class LinuxPlatform(PlatformBase):
    def __init__(self):
        super().__init__()
        self._iptables_rules = {}

    def is_admin(self) -> bool:
        return os.geteuid() == 0

    def request_admin(self, script_path: str) -> bool:
        if self.is_admin():
            return True
        try:
            # Simple terminal sudo elevation (for GUI pkexec is preferred)
            subprocess.run(["sudo", "python3", script_path], check=True)
            return True
        except Exception as e:
            logger.error(f"Failed to elevate privileges: {e}")
            return False

    def _run_cmd(self, cmd: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, capture_output=True, text=True)

    def set_system_dns(self, interface: str, dns_server: str) -> bool:
        # Simplified: using iptables redirect instead of touching resolv.conf
        try:
            for proto in ["udp", "tcp"]:
                self._run_cmd(["iptables", "-t", "nat", "-A", "OUTPUT", "-p", proto, "--dport", "53", "-j", "REDIRECT", "--to-ports", "53"])
                
            # Disable IPv6 Router Advertisements (SLAAC)
            self._run_cmd(["sysctl", "-w", f"net.ipv6.conf.{interface}.accept_ra=0"])
            self._run_cmd(["sysctl", "-w", "net.ipv6.conf.all.accept_ra=0"])
            return True
        except Exception:
            return False

    def restore_system_dns(self, interface: str, original_dns_server: Optional[str] = None) -> bool:
        try:
            for proto in ["udp", "tcp"]:
                self._run_cmd(["iptables", "-t", "nat", "-D", "OUTPUT", "-p", proto, "--dport", "53", "-j", "REDIRECT", "--to-ports", "53"])
                
            # Restore IPv6 Router Advertisements
            self._run_cmd(["sysctl", "-w", f"net.ipv6.conf.{interface}.accept_ra=1"])
            self._run_cmd(["sysctl", "-w", "net.ipv6.conf.all.accept_ra=1"])
            return True
        except Exception:
            return False

    def get_original_dns(self, interface: str) -> Optional[str]:
        return "8.8.8.8"

    def get_active_interfaces(self) -> List[str]:
        return ["eth0", "wlan0"]

    def get_default_gateway(self) -> Optional[str]:
        res = self._run_cmd(["ip", "route", "show", "default"])
        if res.stdout:
            parts = res.stdout.split()
            if len(parts) >= 3:
                return parts[2]
        return None

    def get_current_ssid(self) -> str:
        # Simplistic default for Linux (can be expanded with iwgetid)
        return ""

    def add_firewall_rule(self, rule_name: str, direction: str, action: str, 
                          remote_ip: Optional[str] = None, remote_port: Optional[int] = None, 
                          protocol: Optional[str] = None, program: Optional[str] = None) -> bool:
        chain = "INPUT" if direction == "in" else "OUTPUT"
        target = "DROP" if action == "block" else "ACCEPT"
        
        ips = []
        if remote_ip:
            ips = [ip.strip() for ip in remote_ip.split(",") if ip.strip()]
        else:
            ips = [None]
            
        success = True
        added_ips = []
        
        for ip in ips:
            cmd = ["iptables", "-A", chain]
            if ip:
                cmd.extend(["-d" if direction == "out" else "-s", ip])
            if protocol:
                cmd.extend(["-p", protocol])
            if remote_port:
                cmd.extend(["--dport", str(remote_port)])
            cmd.extend(["-j", target])
            
            res = self._run_cmd(cmd)
            if res.returncode == 0:
                if ip:
                    added_ips.append(ip)
            else:
                success = False
                
        if rule_name and added_ips:
            if rule_name not in self._iptables_rules:
                self._iptables_rules[rule_name] = []
            self._iptables_rules[rule_name].extend(added_ips)
            
        return success

    def remove_firewall_rule(self, rule_name: str) -> bool:
        if rule_name in self._iptables_rules:
            for ip in self._iptables_rules[rule_name]:
                self._run_cmd(["iptables", "-D", "OUTPUT", "-d", ip, "-j", "DROP"])
                self._run_cmd(["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"])
            del self._iptables_rules[rule_name]
        return True

    def rule_exists(self, rule_name: str) -> bool:
        return rule_name in self._iptables_rules

    def remove_all_NetStrip_rules(self) -> bool:
        rules_to_remove = [k for k in list(self._iptables_rules.keys()) if k.startswith("NetStrip_")]
        for rule in rules_to_remove:
            self.remove_firewall_rule(rule)
        return True

    def remove_all_app_block_rules(self) -> bool:
        rules_to_remove = [k for k in list(self._iptables_rules.keys()) if k.startswith("NetStrip_AppBlock_")]
        for rule in rules_to_remove:
            self.remove_firewall_rule(rule)
        return True

    def disable_ipv4(self) -> bool:
        # Single self-contained rule per direction: drop non-loopback traffic
        # EXCEPT the Tailscale management path. (A separate ACCEPT rule would be
        # shadowed, because the DROP is also inserted at position 1.)
        res1 = self._run_cmd(["iptables", "-I", "INPUT", "1", "!", "-i", "lo", "!", "-s", self._MGMT_V4, "-p", "all", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"])
        res2 = self._run_cmd(["iptables", "-I", "OUTPUT", "1", "!", "-o", "lo", "!", "-d", self._MGMT_V4, "-p", "all", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"])
        return res1.returncode == 0 and res2.returncode == 0

    def enable_ipv4(self) -> bool:
        # Delete by comment (matches how disable_ipv4 inserted it). The old code
        # deleted a rule spec without the comment, so it never matched and the
        # host stayed blackholed forever — a real fail-open regression.
        patterns = (
            ["iptables", "-D", "INPUT", "!", "-i", "lo", "!", "-s", self._MGMT_V4, "-p", "all", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"],
            ["iptables", "-D", "OUTPUT", "!", "-o", "lo", "!", "-d", self._MGMT_V4, "-p", "all", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"],
            # Older revision without the management exemption.
            ["iptables", "-D", "INPUT", "!", "-i", "lo", "-p", "all", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"],
            ["iptables", "-D", "OUTPUT", "!", "-o", "lo", "-p", "all", "-m", "comment", "--comment", "NetStrip_IPv4_Block", "-j", "DROP"],
        )
        for delete in patterns:
            check = list(delete)
            check[1] = "-C"
            while self._run_cmd(check).returncode == 0:
                self._run_cmd(delete)
        # Remove management-path exemptions left by the intermediate revision.
        for chain, flag in (("INPUT", "-s"), ("OUTPUT", "-d")):
            while self._run_cmd(["iptables", "-D", chain, flag, self._MGMT_V4, "-j", "ACCEPT"]).returncode == 0:
                pass
        return True

    def is_ipv4_enabled(self) -> bool:
        return True

    def kill_tcp_connections(self, target_ip: Optional[str] = None, target_process_path: Optional[str] = None):
        """Forcefully terminate active TCP connections on Linux using ss."""
        try:
            if not target_ip and not target_process_path:
                # Kill all
                self._run_cmd(["ss", "-K", "state", "established"])
            else:
                targets = self._get_target_connections(target_ip, target_process_path)
                for t in targets:
                    self._run_cmd(["ss", "-K", "src", t['l_ip'], "sport", f"={t['l_port']}", 
                                   "dst", t['r_ip'], "dport", f"={t['r_port']}"])
        except Exception as e:
            logger.error(f"Failed to kill TCP connections on Linux: {e}")

    # Management paths that must NEVER be blackholed by the killswitch.
    # Losing these makes a remote/headless host permanently unreachable.
    #   100.64.0.0/10  -> Tailscale CGNAT (tailnet + Tailscale SSH)
    #   fd7a:115c:a1e0::/48 -> Tailscale IPv6 ULA
    _MGMT_V4 = "100.64.0.0/10"
    _MGMT_V6 = "fd7a:115c:a1e0::/48"
    _KS_COMMENT = "NetStrip_Killswitch"

    def enable_killswitch(self) -> bool:
        """Ghost-mode lockdown.

        Unlike the old implementation, the rules are comment-tagged so they can
        be removed deterministically, and they always exempt loopback plus the
        Tailscale management ranges. Without those exemptions a headless node
        loses Tailscale SSH the instant the killswitch trips and can never be
        recovered remotely.

        IMPORTANT: the exemption is expressed *inside* each DROP rule via `! -s`
        / `! -d`. An earlier revision inserted a separate ACCEPT rule at position
        1 and then inserted the DROP at position 1 as well — iptables prepends,
        so the DROP ended up ABOVE the ACCEPT and shadowed it, leaving the tailnet
        blocked. A single self-contained rule has no ordering hazard.
        """
        # Idempotency: never stack duplicate killswitch rules.
        self.disable_killswitch()

        res = []
        # IPv4: drop everything except loopback and the tailnet management path.
        res.append(self._run_cmd([
            "iptables", "-I", "INPUT", "1", "!", "-i", "lo", "!", "-s", self._MGMT_V4,
            "-m", "comment", "--comment", self._KS_COMMENT, "-j", "DROP",
        ]).returncode == 0)
        res.append(self._run_cmd([
            "iptables", "-I", "OUTPUT", "1", "!", "-o", "lo", "!", "-d", self._MGMT_V4,
            "-m", "comment", "--comment", self._KS_COMMENT, "-j", "DROP",
        ]).returncode == 0)
        # IPv6: same, for the Tailscale ULA range.
        res.append(self._run_cmd([
            "ip6tables", "-I", "INPUT", "1", "!", "-i", "lo", "!", "-s", self._MGMT_V6,
            "-m", "comment", "--comment", self._KS_COMMENT, "-j", "DROP",
        ]).returncode == 0)
        res.append(self._run_cmd([
            "ip6tables", "-I", "OUTPUT", "1", "!", "-o", "lo", "!", "-d", self._MGMT_V6,
            "-m", "comment", "--comment", self._KS_COMMENT, "-j", "DROP",
        ]).returncode == 0)
        self.kill_tcp_connections()
        return all(res)

    def disable_killswitch(self) -> bool:
        """Remove every killswitch rule (comment-tagged + legacy untagged).

        The loop is deliberately unbounded-safe: it removes duplicate rules left
        behind by older versions and by crash/restart cycles, guaranteeing a
        fail-open state. It also cleans up the separate tailnet ACCEPT rules used
        by an intermediate revision, and any stray untagged global DROP.
        """
        removed = False
        for table in ("iptables", "ip6tables"):
            mgmt = self._MGMT_V4 if table == "iptables" else self._MGMT_V6
            for chain, flag in (("INPUT", "-i"), ("OUTPUT", "-o")):
                direction = "-s" if chain == "INPUT" else "-d"
                # Comment-tagged DROP rules: both the current self-contained form
                # (`! -s <mgmt>`) and the older plain form, in case of an upgrade.
                for mgmt_clause in (["!", direction, mgmt], []):
                    check = [table, "-C", chain, "!", flag, "lo", *mgmt_clause,
                             "-m", "comment", "--comment", self._KS_COMMENT, "-j", "DROP"]
                    delete = [table, "-D", chain, "!", flag, "lo", *mgmt_clause,
                              "-m", "comment", "--comment", self._KS_COMMENT, "-j", "DROP"]
                    while self._run_cmd(check).returncode == 0:
                        self._run_cmd(delete)
                        removed = True
                # Separate tailnet ACCEPT exemptions (intermediate revision).
                while self._run_cmd([table, "-C", chain, direction, mgmt, "-j", "ACCEPT"]).returncode == 0:
                    self._run_cmd([table, "-D", chain, direction, mgmt, "-j", "ACCEPT"])
                    removed = True
                # Legacy untagged global DROP from pre-comment-tag versions.
                # Match the EXACT spec the old enable_killswitch inserted rather
                # than a positional `-D <chain> 1 -j DROP`: the positional form
                # can delete an unrelated rule that merely happens to be a bare
                # DROP at the top of the chain.
                while self._run_cmd([table, "-C", chain, "-j", "DROP"]).returncode == 0:
                    self._run_cmd([table, "-D", chain, "-j", "DROP"])
                    removed = True
        return True

    def block_lan_traffic(self) -> bool:
        lan_subnets = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        success = True
        for subnet in lan_subnets:
            if self._run_cmd(["iptables", "-A", "OUTPUT", "-d", subnet, "-j", "DROP"]).returncode != 0:
                success = False
        return success

    def unblock_lan_traffic(self) -> bool:
        """Remove every LAN-shield DROP rule (idempotent, order-independent).

        Returns True when no matching rule remains afterwards, regardless of
        whether any were present to begin with.
        """
        subnets = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        for subnet in subnets:
            while self._run_cmd(["iptables", "-D", "OUTPUT", "-d", subnet, "-j", "DROP"]).returncode == 0:
                pass
            while self._run_cmd(["iptables", "-D", "INPUT", "-s", subnet, "-j", "DROP"]).returncode == 0:
                pass
        # Verify the end state rather than trusting delete exit codes.
        for subnet in subnets:
            if self._run_cmd(["iptables", "-C", "OUTPUT", "-d", subnet, "-j", "DROP"]).returncode == 0:
                return False
            if self._run_cmd(["iptables", "-C", "INPUT", "-s", subnet, "-j", "DROP"]).returncode == 0:
                return False
        return True

    def lockdown_arp(self, ip: str, mac: str) -> bool:
        res = self._run_cmd(["arp", "-s", ip, mac])
        return res.returncode == 0
        
    def unlock_arp(self, ip: str) -> bool:
        res = self._run_cmd(["arp", "-d", ip])
        return res.returncode == 0

    def disable_ipv6(self) -> bool:
        success = True
        if self._run_cmd(["sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=1"]).returncode != 0:
            success = False
        if self._run_cmd(["sysctl", "-w", "net.ipv6.conf.default.disable_ipv6=1"]).returncode != 0:
            success = False
        return success

    def enable_ipv6(self) -> bool:
        success = True
        if self._run_cmd(["sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=0"]).returncode != 0:
            success = False
        if self._run_cmd(["sysctl", "-w", "net.ipv6.conf.default.disable_ipv6=0"]).returncode != 0:
            success = False
        return success

    def is_ipv6_enabled(self) -> bool:
        try:
            with open("/proc/sys/net/ipv6/conf/all/disable_ipv6", "r") as f:
                return f.read().strip() == "0"
        except Exception:
            return True

    def install_autostart(self) -> bool:
        if not self.is_admin():
            logger.error("Root privileges required to install systemd service.")
            return False
            
        import sys
        import os
        exe_path = os.path.abspath(sys.argv[0])
        service_path = "/etc/systemd/system/netstrip.service"
        
        service_content = f"""[Unit]
Description=Cripple NetStrip Daemon
After=network.target

[Service]
Type=simple
ExecStart={exe_path}
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
"""
        try:
            with open(service_path, "w") as f:
                f.write(service_content)
            self._run_cmd(["systemctl", "daemon-reload"])
            self._run_cmd(["systemctl", "enable", "netstrip.service"])
            logger.info("systemd service installed and enabled.")
            return True
        except Exception as e:
            logger.error(f"Failed to install systemd service: {e}")
            return False

    def uninstall_autostart(self) -> bool:
        if not self.is_admin():
            logger.error("Root privileges required to uninstall systemd service.")
            return False
            
        service_path = "/etc/systemd/system/netstrip.service"
        try:
            self._run_cmd(["systemctl", "disable", "netstrip.service"])
            if os.path.exists(service_path):
                os.remove(service_path)
            self._run_cmd(["systemctl", "daemon-reload"])
            logger.info("systemd service uninstalled.")
            return True
        except Exception as e:
            logger.error(f"Failed to uninstall systemd service: {e}")
            return False

    def is_autostart_installed(self) -> bool:
        import os
        return os.path.exists("/etc/systemd/system/netstrip.service")

    def disable_protocol_bindings(self) -> bool:
        """Disable redundant, privacy-leaking protocol daemons and sysctl bindings on Linux."""
        sysctl_params = [
            ("net.ipv4.conf.all.accept_redirects", "0"),
            ("net.ipv4.conf.default.accept_redirects", "0"),
            ("net.ipv4.conf.all.send_redirects", "0"),
            ("net.ipv4.conf.default.send_redirects", "0"),
            ("net.ipv4.conf.all.drop_unicast_in_l2_multicast", "1"),
            ("net.ipv6.conf.all.accept_ra", "0"),
            ("net.ipv6.conf.default.accept_ra", "0"),
        ]
        for key, val in sysctl_params:
            self._run_cmd(["sysctl", "-w", f"{key}={val}"])

        # Stop discovery and broadcast daemons (avahi/mDNS, lldp, smb/nmb)
        for svc in ["avahi-daemon", "lldpd", "lldpad", "smbd", "nmbd"]:
            self._run_cmd(["systemctl", "stop", svc])
        return True

    def restore_protocol_bindings(self) -> bool:
        """Restore standard protocol bindings on Linux."""
        sysctl_params = [
            ("net.ipv4.conf.all.accept_redirects", "1"),
            ("net.ipv4.conf.default.accept_redirects", "1"),
            ("net.ipv6.conf.all.accept_ra", "1"),
            ("net.ipv6.conf.default.accept_ra", "1"),
        ]
        for key, val in sysctl_params:
            self._run_cmd(["sysctl", "-w", f"{key}={val}"])
        return True
