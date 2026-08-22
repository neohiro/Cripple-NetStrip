# Architecture

Two independent layers that never block each other:

```
┌────────────────────────────  GUI (optional)  ────────────────────────────┐
│ CustomTkinter views (Dashboard / Logs / Filter Lists / Settings)          │
│ ConnectionsSidebar — persistent fetch worker, pooled rows, bulk toggles   │
│ All DB/network I/O on background threads; UI thread only applies state    │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │ callbacks + after(0) marshalling
┌───────────────────────────────▼───────────────────────────────────────────┐
│                       NetStripEngine (orchestrator)                        │
│                                                                            │
│  Packet path        DNS path            Observers                          │
│  ├ interceptor      ├ dns_proxy         ├ connection_monitor               │
│ │  (WinDivert/     │  (UDP+TCP, v4+v6,  ├ network_monitor (route/MAC/IP)   │
│ │   NFQueue/PF/    │   bounded threads, │ ├ anomaly_scanner                │
│ │   TUN)           │   DoT/DoH pools    │ ├ geoip (public IP + offline mmdb)│
│  └ _evaluate_packet └ sinkhole/NXDOMAIN  ├ lan_shield (encrypted LAN mesh) │
│     (hot path: TTL-                     ├ updater → blocklist_manager      │
│      cached settings)                   ├ watchdog (time bombs, schedule,  │
│                                         │   retention, WAL checkpoint)     │
│  classifier ← blocklist_manager ← database (WAL, split read/write locks)  │
└────────────────────────────────────────────────────────────────────────────┘
```

## Key invariants

- **Packet evaluation is lock-free**: `Database.get_setting_cached()` serves
  hot settings from a per-key TTL map; the writer RLock is never taken on the
  packet path.
- **Reads never queue behind writes**: WAL mode + a dedicated `_read_lock` for
  all `get_*` methods.
- **Bounded resources**: every long-lived cache has an explicit cap and eviction
  strategy (see `tests/test_longevity.py`, which enforces them).
- **Fail-safe restoration**: DNS/firewall/bindings are restored on clean exit,
  crash (detached watchdog), and uninstall (`--restore-network`).

## Data flow of a blocked connection

1. WinDivert/TUN delivers packet → `_evaluate_packet`
2. SSH-safeguard short-circuit → killswitch check → loopback bypass
3. PID→name resolution (60s cache) → classifier (`domain_map` trie +
   user rules + category overrides + presets)
4. Block ⇒ drop + async log write; Allow ⇒ re-inject

# Threat Model

**What NetStrip protects against**

| Threat | Mitigation |
|---|---|
| Telemetry / ads / trackers | Multi-feed DNS sinkhole (58 verified feeds, ~4.4M domains) + kernel-level packet drops for hardcoded IPs |
| Encrypted-DNS bypass | Interception of external :53/:853, DoH provider sinkholing, WPAD/NetBIOS/LDAP discovery sinkholes |
| Malware C2 | URLhaus/Feodo-class feeds, botnet velocity detector (>50 conn/s), Smart Shield auto-escalation |
| ARP spoofing / rogue gateway | Gateway MAC pinning, MAC-change detection, optional LAN isolation |
| Physical tampering of install | HMAC-SHA512 watchdog over engine files; signed blocklist cache (HMAC-SHA256 seal) |
| Local attacker reading config | PSK moved out of SQLite into DPAPI-wrapped keyfile (Windows) / 0600 file |

**Explicitly out of scope / accepted risks**

- **LAN Shield trust = PSK possession.** Any peer holding the shared key can
  send lockdown commands. This is by design ("PSK is the link"); protect the
  key accordingly. There is deliberately no peer allowlist.
- **Root/admin malware on the same machine** can always bypass user-space
  filtering — NetStrip raises the bar, it is not a hypervisor.
- **Feed availability** depends on third parties; URLs are machine-verified at
  CI time (`scripts/check_feeds_online.py`) and failures degrade to fewer
  sources, never to blocking failures.
- **Crypto backends**: tokens are AES-256-CBC + truncated HMAC-SHA512. The
  vetted OpenSSL backend is preferred; the pure-Python fallback exists for
  WDAC/AppLocker-locked hosts and is byte-interoperable.

**Secrets inventory**

| Secret | Location | Protection |
|---|---|---|
| LAN Shield PSK | `~/.NetStrip/psk.key` | DPAPI wrap (Win) / chmod 600; DB keeps only `KEYFILE` marker |
| Cache signing key | `~/.NetStrip/cache.key` | random 32B, 0600, generated first use |
| Telemetry token (optional) | env / file / DB | user-supplied only; nothing embedded |
