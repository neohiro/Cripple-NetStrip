<div align="center">
  <img src="assets/cripple_logo.png" alt="Cripple Logo" width="200"/>

  # NetStrip  —  Cripple

  **See everything. Control everything. Trust nothing.**

  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
  [![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Android-lightgray.svg)](https://github.com/)
  [![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
  [![Build Status](https://github.com/neohiro/Cripple-NetStrip/actions/workflows/release.yml/badge.svg)](https://github.com/neohiro/Cripple-NetStrip/actions)

  > **Compatibility :** Cripple is designed to work seamlessly alongside your existing network and security tools—including dnscrypt-proxy, torifier, YogaDNS, NextDNS, AVG and other antivirus & VPN programs. It intelligently detects local proxies and security suites to operate cooperatively without creating network conflicts or infinite DNS loops.
</div>

---

## Why Cripple?

Every second your devices are online, dozens of applications are silently phoning home. Your browser leaks DNS queries through encrypted side channels. Your operating system broadcasts telemetry you never consented to. Smart devices on your network talk to servers in countries you've never heard of. And traditional firewalls? They can't even see most of it.

**Cripple strips all of that away.**

It's not just a DNS blocker. It intercepts traffic at the raw packet level — before it ever leaves your machine — so nothing escapes. Not hardcoded IPs, not encrypted DNS tunnels, not stealthy IPv6 broadcasts. If something tries to talk to the internet without your permission, Cripple kills it.

### What you get

- **Complete visibility** — A live dashboard showing every connection every app on your system is making, right now, in real time.
- **Surgical control** — Block individual domains, entire apps, or nuke your entire network connection with one click.
- **Protection that actually works** — Unlike browser extensions or hosts-file blockers, Cripple operates at the OS kernel level. Apps can't bypass it, and neither can your browser's DNS-over-HTTPS.
- **Zero-configuration privacy** — Ships with **3.2+ Million unique blocked domains** out of the box across 42 active threat feeds. Ads, trackers, telemetry, and malware — gone before you even open a browser.
- **Your network, offline** — Run it on a Raspberry Pi, a NUC, or a home server and protect every device on your LAN without installing anything on them.

---

## 📑 Contents

- [How It Works](#how-it-works)
- [What Gets Blocked](#what-gets-blocked)
- [Active Blocklists & Threat Feeds](#-active-blocklists--threat-feeds)
- [Protecting Your LAN](#-protecting-your-lan)
- [Android](#-android)
- [Headless & Remote Management](#-headless--remote-management)
- [Safety & Anti-Lockout](#-safety--anti-lockout)
- [Under the Hood](#-under-the-hood)
- [Getting Started](#-getting-started)
- [Release Notes](#-release-notes)

---

## How It Works

Most "ad blockers" and "firewalls" work at a single layer — they rewrite DNS queries or filter HTTP headers. Cripple is different. It works at **three layers simultaneously**:

### Layer 1 — DNS Sinkhole
Every DNS query your system makes passes through Cripple first. Known bad domains (ads, trackers, telemetry, malware) get sinkholed — they resolve to `0.0.0.0` so the connection never happens. This is fast, silent, and invisible to the apps making the requests.

> **Why this matters to you:** Your browser loads pages faster because ad networks never even get contacted. Your system uses less bandwidth. And tracking companies get zero data about you.

### Layer 2 — Packet Interception
Some apps don't use DNS. They hardcode IP addresses directly. Cripple hooks into the OS kernel (`WinDivert` on Windows, `NFQueue` on Linux, `PF` on macOS) and inspects every outbound packet before it leaves. If the destination is on a blocklist — or if the connection wasn't explicitly allowed — it gets destroyed.

> **Why this matters to you:** This closes the biggest gap in traditional blockers. When your graphics driver phones home to an analytics server via raw IP, Cripple catches it. Browser extensions never will.

### Layer 3 — Deep Packet Inspection
For encrypted traffic, Cripple reads TLS handshake headers (SNI) to identify the destination domain even when the payload is encrypted. It also detects DNS-over-HTTPS tunnels and force-routes them back through the sinkhole.

> **Why this matters to you:** Chrome, Firefox, and Edge all try to bypass your DNS settings using DoH. Cripple intercepts 30+ DoH providers and redirects them. Your privacy settings actually stick.

---

## What Gets Blocked

Out of the box, with no configuration, Cripple blocks:

| Category | What it covers | Why you care |
|---|---|---|
| **Ads** | Banner ads, video pre-rolls, pop-ups, native ads | Faster page loads, cleaner browsing, less bandwidth |
| **Trackers** | Cross-site tracking pixels, fingerprinting scripts | Companies can't build a profile of your browsing habits |
| **Telemetry** | OS phoning home, app crash reports, usage statistics | Your computer stops reporting your behavior to Microsoft/Apple/Google |
| **Malware** | Known C2 servers, phishing domains, botnets, exploit kits | Protection against drive-by downloads and compromised sites |
| **IoT Chatter** | Smart devices calling home to cloud servers | Your smart TV stops sending your viewing habits to advertisers |

You can customize everything: add your own blocklists (paste any URL), create per-app rules, set temporary "time bomb" allows that auto-expire, or switch between three protection modes:

| Mode | Behavior | Best for |
|---|---|---|
| **🔓 Loose** | Blocks confirmed bad domains only | Maximum compatibility, minimal friction |
| **🔰 Normal** | Blocks ads + trackers + telemetry | Daily use (recommended) |
| **🔒 Paranoid** | Blocks everything not explicitly whitelisted | Maximum security, hardened environments |

---

## 🛡 Active Blocklists & Threat Feeds

Cripple aggregates **3,236,262+ unique domains** from 42 active, high-reputation blocklists and threat intelligence feeds. Feeds are automatically updated on tailored schedules:

### ☠ Rapid Threat Intelligence & Malware Feeds (1h–4h Cycle)
| Blocklist Source | Category | Update Interval | Description |
|---|---|---|---|
| **URLhaus Malware** | Malware / C2 | **1 hour** | Real-time malware distribution and C2 server domains |
| **Feodo Tracker Botnet C2** | Malware / C2 | **1 hour** | Active botnet command and control servers |
| **HaGeZi TIF** | Threat Intelligence | **2 hours** | Threat Intelligence Feeds blocking phishing, malware, and exploits |
| **DShield Suspicious Domains** | Security | **4 hours** | High-risk suspicious domains reported by SANS Internet Storm Center |
| **PhishTank / Phishing Army** | Malware / Phishing | **4 hours** | Verified active phishing campaigns and credential harvesting sites |

### 🚫 Advertisement & Tracking Blocklists (24h Cycle)
| Blocklist Source | Category | Unique Domains | Description |
|---|---|---|---|
| **HaGeZi Ultimate** | Ads / Trackers | `677,000+` | Comprehensive high-coverage ad and tracker blocklist |
| **HaGeZi Pro Plus** | Ads / Trackers | `586,000+` | Expanded protection covering intrusive popups and trackers |
| **OISD Big** | Ads / Trackers | `333,000+` | Curated zero-false-positive ad and telemetry blocklist |
| **AdGuard Base Filter** | Ads | `158,000+` | Primary AdGuard desktop & mobile ad-blocking rules |
| **Steven Black Unified** | Ads / Malware | `93,000+` | Amalgamated hosts file combining top community blocklists |
| **Dan Pollock Hosts** | Ads | `12,900+` | Classic hosts file covering ad networks and malware hosts |
| **AdGuard Mobile Ads** | Mobile Ads | `10,700+` | Mobile ad networks, in-app trackers, and SDK analytics |
| **AdAway Default** | Ads | `6,500+` | AdAway mobile ad server blocking list |
| **Peter Lowe AdServers** | Ads | `3,500+` | Curated list of ad servers and tracking hosts |
| **AdGuard Regional Filters** | Regional Ads | `30,000+` | Specific rules for Russian, Japanese, Turkish, Chinese, and French sites |
| **EasyList Regional Filters** | Regional Ads | `15,000+` | Specific rules for German, Italian, Dutch, Arabic, and Korean (YousList) sites |

### 📡 OS Telemetry & Identity Protection (24h Cycle)
| Blocklist Source | Category | Description |
|---|---|---|
| **HaGeZi Windows Telemetry** | System Telemetry | Blocks Microsoft Windows 10/11 telemetry and diagnostics |
| **HaGeZi Apple Telemetry** | System Telemetry | Blocks macOS and iOS analytics and diagnostics endpoints |
| **HaGeZi Mobile Telemetry** | System Telemetry | Native telemetry blocking for Xiaomi, Huawei, Vivo, Oppo, Realme, & Amazon |
| **WindowsSpyBlocker (Spy/Update/Extra)** | System Telemetry | Deep Windows telemetry, diagnostics, and forced update server blocking |
| **HaGeZi DoH/DoT Providers** | Security | Prevents browser Encrypted DNS (DoH/DoT) bypass attempts |
| **v2fly Identity Lists** | Identity Mapping | Category mapping for Microsoft, Google, Apple, Amazon, Facebook, Cloudflare, & Fastly |

---

## 🔑 Protecting Your LAN

Cripple doesn't just protect one machine — it can protect your entire local network.

### LAN Shield Mesh
When you run Cripple on multiple devices, they communicate via **encrypted UDP broadcasts** using a shared pre-shared key (PSK). If one device detects a threat, it instantly broadcasts an encrypted `LOCKDOWN` command — and every other Cripple instance on the network locks down simultaneously.

**Setting it up is two commands:**
```bash
# On your first device — get the auto-generated key
python main.py --get-psk

# On every other device — paste it in
python main.py --set-psk "your-key-here"
```

The PSK uses **Fernet (AES-128-CBC)** encryption with anti-replay nonces, and the listener is **always active** — it survives killswitch mode, ghost mode, and interface failures with automatic socket recovery.

### Ghost Mode vs. Killswitch

Two levels of network isolation, depending on how serious the threat is:

| | Ghost Mode | Killswitch |
|---|---|---|
| **Severity** | ⚠ Stealth isolation | ☠ Total network death |
| **Whitelists** | Ghost Mode preferences honored | Nothing honored — no exceptions |
| **SSH** | Survives if whitelisted in Ghost prefs | Disconnects (unless SSH Safeguard is on) |
| **Remote recovery** | `--unghost` works remotely | Requires physical access |
| **LAN Shield** | Listeners stay active | Everything dies |
| **Use case** | "Go dark but stay manageable" | "Nuke it — I'll deal with it in person" |

Both require typing `YES` to confirm in the CLI. Pressing Enter always cancels.

---

## 📱 Android

Cripple runs natively on Android with **two VPN modes** — choose at launch:

### Native VPN (Default)
Cripple **becomes your device's VPN**. All traffic — DNS, TCP, UDP — flows through Cripple's TUN interface. Blocked connections are silently dropped at the packet level. No root required.

> **When to use this:** You want one app that handles everything. No other VPN app needed.

### Companion Mode
DNS-only filtering at `127.0.0.1:5353`. Designed for users who already run a VPN (WireGuard, AdGuard, etc.) and want Cripple to handle just the blocking.

> **When to use this:** You're already running a VPN for geo-unblocking or work, and you want Cripple for privacy filtering alongside it.

---

## 🖥 Headless & Remote Management

Cripple is designed to run silently on servers, Raspberry Pis, NUCs, and embedded systems. Start it with `--service` and manage everything via SSH.

### 25+ CLI Commands

**No daemon needed** — these work directly on the database:
```bash
python main.py --get-psk              # Display LAN Shield PSK
python main.py --set-psk "key"        # Import PSK from another device
python main.py --export backup.json   # Full profile export
python main.py --import backup.json   # Import on another machine
python main.py --set ssh_safeguard true   # Never lock yourself out
```

**Live commands** — sent to the running daemon via IPC:
```bash
python main.py --block evil-tracker.com   # Block a domain instantly
python main.py --allow example.com        # Whitelist a domain
python main.py --mode PARANOID            # Escalate protection
python main.py --status                   # Check daemon status
python main.py --stats                    # View 24h statistics
python main.py --ghost                    # Go dark (with confirmation)
python main.py --killswitch              # Nuclear option (with confirmation)
python main.py --update-blocklists       # Force blocklist refresh
```

Full reference: **[CLI Guide](CLI_GUIDE.md)**

---

## 🛡 Safety & Anti-Lockout

Cripple is designed to never lock you out of your own machine, even when running the most aggressive security modes.

### SSH Safeguard
A single setting that guarantees you can always SSH in — no matter what:

```bash
python main.py --set ssh_safeguard true
```

When enabled, inbound connections on **port 22 and 2222 are always allowed** — even during killswitch, ghost mode, paranoid mode, or strict inbound blocking. This check runs **before** every other security evaluation in the engine.

> Auto-enabled when you start Cripple in headless mode (`--service`). You'll never accidentally lock yourself out of a remote Pi.

### Confirmation Prompts
Every CLI command that could sever your connection requires explicit confirmation:

| Command | Confirmation required? |
|---|---|
| `--killswitch` | ✅ Must type `YES` (Enter cancels) |
| `--ghost` | ✅ Must type `YES` (Enter cancels) |
| `--mode PARANOID` | ✅ Must type `YES` (Enter cancels) |
| `--blockinbound` | ✅ Must type `YES` (Enter cancels) |
| `--unkillswitch` | ❌ Instant (recovery should be fast) |
| `--unghost` | ❌ Instant |
| `--mode NORMAL` | ❌ Instant |

All prompts can be bypassed with `--force` for scripted automation.

### Crash Recovery
If Cripple crashes, the watchdog automatically restores:
- DNS settings to their original state
- Firewall rules (removes all NetStrip rules)
- IPv4/IPv6 protocol bindings (re-enables if they were disabled)
- Killswitch state (clears the lockdown flag)

You'll never end up with a bricked network because Cripple died mid-operation.

---

## ⚙ Under the Hood

For the technically curious — here's what powers the engine.

### Architecture
Two independent layers that never block each other:

1. **Core Engine** — Multi-threaded C-level daemon: packet evaluation, SQLite logging, DNS proxying, kernel route monitoring, anomaly detection
2. **GUI** — Hardware-accelerated CustomTkinter visualizer, fully optional. Can be closed for pure headless operation

### Security Hardening

| Layer | What it does |
|---|---|
| **🛡️ Post-Quantum Cryptography** | Pure-Python AES-256-CBC + HMAC-SHA512 + HKDF-SHA512 (immune to Grover's quantum attack & WDAC blocks) |
| **🔍 HMAC-SHA512 Watchdog** | Ephemeral 512-bit keyed hashes continuously verify integrity of all engine files & modules against live tampering |
| **DLL Sideloading Mitigation** | `LOAD_LIBRARY_SEARCH_DEFAULT_DIRS` + dynamic `_MEIPASS` search path restriction at startup |
| **IPC Command Validation** | Regex-validated domain commands on the IPC socket |
| **Shell Sandboxing** | All system commands use `shell=False` with isolated arguments |
| **Anti-Replay Nonces** | LAN Shield broadcasts include cryptographic nonces — replaying old packets does nothing |
| **Crash Report Guarantee** | Essential domains are whitelisted, crash reports retry 5× with exponential backoff |
| **Anti-Corruption DB** | SQLite WAL mode with thread-safe isolation |
| **ARP Lockdown** | Gateway MAC address pinned — prevents ARP spoofing / MITM attacks |
| **eBPF XDP Mode** | On Linux, fileless eBPF programs injected into the NIC for wire-speed filtering |

### Performance

| Optimization | Effect |
|---|---|
| Adaptive polling | 250ms refresh when GUI visible, 2000ms when headless |
| View caching | Tab swaps in O(1) via `grid_remove()`, never destroyed |
| Lazy preloading | Tabs pre-instantiated at 300ms intervals for zero-delay switching |
| Debounced resize | Batched window resize events prevent layout thrashing |
| Flicker-free dashboard | Pre-allocated widget pool with in-place `configure()` updates |
| 3× scroll speed | Framework-level mouse wheel patching |

---

## 📖 Getting Started

### Option 1: Download (Recommended)
Grab the pre-compiled binary from [Releases](https://github.com/neohiro/Cripple-NetStrip/releases). Run as Administrator/sudo. No Python required.

### Option 2: Run from Source
```bash
git clone https://github.com/neohiro/Cripple-NetStrip.git
cd Cripple-NetStrip
pip install -r requirements.txt
```

**Windows:** `python main.py`  
**macOS / Linux:** `sudo python3 main.py`  
**Headless:** `sudo python3 main.py --service`  
**Android:** Built via GitHub Actions → standalone `.apk`

### Requirements
- **OS:** Windows 10/11, macOS, Linux, Android
- **Python:** 3.10+ (not needed for pre-compiled binaries)
- **Permissions:** Administrator/Root (Android uses VPN Service)

---

## 🚀 Release Notes

### v3.3.2 — Semantic Versioning, Card Badge Polish, Domain Precedence & Nested Filter Scrolling
- **Semantic Versioning Hierarchy Engine**: Integrated `parse_version_tuple` and `is_newer_version` across update loops to accurately evaluate future release versions (`3.3.1` < `3.3.2` < `3.10.0`).
- **Connection Log Card Badges & Zero-Thrash**: Curved pill badges (`corner_radius=11`) with card containers, high contrast, and smooth pooling.
- **Domain Precedence & Deduplication**: Expanded `ESSENTIAL_DOMAINS`, `SYSTEM_DOMAINS`, and `UPDATE_DOMAINS` and enforced strict category priority over ad/tracker lists.
- **Filter Lists Tab Nested Scrolling**: Smooth scrolling for entire tab combined with dedicated scrollbar for 100-result filter entries.
- **LAN Shield Default Active Enforcement**: Defaulted LAN Shield to ON across database initialization and GUI sidebar.

### v3.3.1 — Snappy Window Restore, Centralized 4x Smooth Scroll & UI Hardening
- **Snappy Window Restore**: Filtered root-level `<Map>` events and throttled `AnimatedLogo` when minimized to eliminate window unminimization latency.
- **Centralized 4x Smooth Mousewheel Scrolling**: Globally monkey-patched `CTkScrollableFrame` with 4x scrolling speed and eliminated conflicting local handlers and `unbind_all` wipes.
- **LAN Shield Startup Sync**: Initialized LAN Shield active mode in engine boot and bound sidebar/view toggles to `lan_shield.is_active`.
- **Connection Logs Row Rendering Fix**: Fixed `sqlite3.Row` dictionary indexing to restore full connection log row visibility.
- **Settings Subtitle Dynamic Text Layout**: Added left anchoring and responsive container width wrapping to eliminate text clipping.

### v3.3.0 — Post-Quantum Cryptography Architecture & 512-bit Watchdog Verification
- **Post-Quantum Cryptography Engine (`QuantumFernet`)**: Pure-Python AES-256-CBC (14 rounds, 256-bit key) + HMAC-SHA512 for quantum-grade confidentiality and authenticity ($128+$ bits Grover resistance).
- **RFC 5869 HKDF-SHA512 Key Derivation**: Seamlessly elevates existing 44-char keys to 512-bit independent key material, preserving backward pairing while providing full quantum security. Supports native 88-char keys.
- **Post-Quantum Watchdog File Verification**: Upgraded live file integrity monitoring to 512-bit ephemeral keys and HMAC-SHA512, ensuring instantaneous detection and termination if any engine module is modified or deleted.
- **LAN Shield Post-Quantum Protocol**: `NetStrip:PQANOMALY:` header with AES-256 broadcast protection.
- **UI "🛡️ QUANTUM-PROOF" Badge**: Visual indicator and 512-bit key generator in Settings.

### v3.2.6 — Pure-Python Fernet Engine & Windows Application Control Resiliency
- **Pure-Python Fallback**: 100% pure-Python symmetric cryptography bypassing WDAC / AppLocker CFFI restrictions.
- **Safe DLL Search Path**: Safe dynamic DLL loading for PyInstaller frozen binaries.

### v3.2.0 — Major Milestone: Fixed LAN Shield, Logs UI, Icons, Filter Categories & Smooth Settings
- **LAN Shield ON Default**: LAN Shield switch defaults ON on clean boot.
- **Centered Action Badges**: Full-width logs table with centered `ALLOW` / `BLOCK` badges.
- **Smart App Logos & Parent Tracing**: Static Cripple logo for internal tasks, native Python icon for standard scripts, and parent icon inheritance for child processes (`jhi_service.exe`, `NVIDIA Overlay.exe`).
- **Centered DNS Icon**: Perfect geometric center alignment for fallback DNS queries.
- **Sticky Filter Categories**: Category selector cards remain pinned at top for easy category switching.
- **Hiccup-Free Settings**: Smooth mousewheel canvas scrolling.

### v3.1.0 — Security Hardening & Full CLI
- SSH Safeguard — always allows port 22/2222, survives all lockdown modes
- Dual Android VPN — native VPN slot or companion mode alongside another VPN
- 25+ CLI commands — PSK management, settings, export/import, killswitch, ghost, stats
- Confirmation prompts for all lockout-risk commands (killswitch, ghost, paranoid, blockinbound)
- Always-on LAN Shield listener with auto-recovery on socket death
- Crash report delivery guarantee with essential domain whitelist
- HMAC-SHA256 watchdog for engine file integrity
- Adaptive 250ms/2000ms GUI/headless polling
- Anti-replay nonces on LAN Shield broadcasts

### v3.0.0 — Zero-Leak Engine
- Rebuilt kernel interception engine with zero-leak packet evaluation
- Multi-platform IPC daemon architecture
- Futuristic-minimalist UI theme
- CPU stability improvements

---

## 🙏 Credits

**Core Technologies:**  
[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) • [dnslib](https://github.com/paulc/dnslib) • [psutil](https://github.com/giampaolo/psutil) • [WinDivert](https://github.com/basil00/Divert) • [cryptography](https://github.com/pyca/cryptography)

**Blocklists & Threat Feeds:**  
[HaGeZi DNS Blocklists](https://github.com/hagezi/dns-blocklists) • [AdGuard Filters](https://adguard.com/) • [OISD](https://oisd.nl/) • [Steven Black Hosts](https://github.com/StevenBlack/hosts) • [URLhaus](https://urlhaus.abuse.ch/) • [Feodo Tracker](https://feodotracker.abuse.ch/) • [PhishTank](https://phishing.army/) • [DShield](https://www.dshield.org/) • [WindowsSpyBlocker](https://github.com/crazy-max/WindowsSpyBlocker) • [v2fly](https://github.com/v2fly/domain-list-community) • [Peter Lowe](https://pgl.yoyo.org/adservers/) • [Dan Pollock](https://someonewhocares.org/hosts/) • [AdAway](https://adaway.org/) • [EasyList](https://easylist.to/)

---

## 📄 License

MIT License. See `LICENSE` for details.
