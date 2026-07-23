<div align="center">
  <img src="assets/cripple_logo.png" alt="Cripple Logo" width="200"/>

  # NetStrip  -  Cripple
  **Intelligent Network Debloater & Multi-Layered Firewall**

  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
  [![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgray.svg)](https://github.com/)
  [![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
  [![Build Status](https://github.com/neohiro/Cripple-NetStrip/actions/workflows/release.yml/badge.svg)](https://github.com/neohiro/Cripple-NetStrip/actions)

  
  *Strip away the noise. Take back control of your network.*
  
  **NetStrip (also known as Cripple)** is a cross-platform desktop FOSS application that acts as a local DNS sinkhole, intelligent firewall, and live connection monitor. It provides absolute visibility into every outbound network request your system makes, allowing you to instantly sever invasive telemetry, ads, and background tracking with surgical precision.

  *Fully compatible with VPNs, Torifier, TOR Router, YogaDNS, NextDNS, dnscrypt-proxy and more.*
</div>

---

## 🛡️ What is NetStrip?

NetStrip is a next-generation network traffic analyzer. Operating securely at the OS-level, it drops ads, telemetry, trackers, and malware packets before they ever leave your network interface.

Designed for absolute privacy and network hygiene, NetStrip prevents bypasses that standard DNS blockers miss—blocking hardcoded telemetry IPs, mitigating DNS-over-HTTPS (DoH) browser leaks, and clamping down on stealthy IPv6 Router Advertisements (SLAAC).

## ✨ Key Features

### 🚧 Absolute Zero-Leak Packet Interception
- **Kernel-Level Drops**: Utilizes `WinDivert` (Windows), `route blackholing` (macOS), and dynamic `iptables` (Linux) to intercept traffic natively.
- **DoH Sinkhole**: Forcibly routes 30+ major DNS-over-HTTPS providers (Cloudflare, Google, AliDNS) into the sinkhole, preventing browsers from bypassing your filters.
- **IPv6 SLAAC Lockdown**: Disables IPv6 Router Advertisements across all operating systems to prevent rogue routers from slipping external DNS configurations into your OS.
- **Global IPv6 Killswitch**: A 1-click brutal disable of IPv6 globally across the OS, forcing all traffic onto easily monitorable IPv4 routes.
- **LAN Shield**: Instantly block or allow all private subnet communications (10.x, 172.16.x, 192.168.x).

### 📊 Multi-Layered DNS Sinkhole
- Evaluates queries asynchronously against over **1.5 million** blocked domains in `O(1)` time.
- **Auto-Updating Engine**: Online blocklists are automatically refreshed every 24 hours in the background (with staggered network throttling to prevent bandwidth spikes).
- **Intelligent Custom Lists**: Paste any raw `.txt` URL into the Filter Manager to instantly add a new permanent blocklist. The engine uses a dual-layer heuristic scanner (URL & file header analysis) to automatically detect if the list contains Trackers, Telemetry, Malware, or System domains, and natively maps it to the correct protection toggle! If it is unidentifiable, it defaults safely to the "User Blocked" category.
- Resolves upstream queries via DNS-over-TLS (DoT), native DNS-over-HTTPS (DoH) for downstream privacy or UDP as a last resort if using internal DNS proxy (autodetects third-party local DNS proxy software!).
- **App-Specific Policies**: Enforce rules per executable (e.g., allow `tracker.com` only when `discord.exe` requests it).
- **Time Bombs**: Quick 15-minute temporary allow-rules to quickly unbreak websites without permanently whitelisting them.

### 🧠 Smart Shield & Streamer Privacy
- **Smart Shield**: Auto-escalates from Normal to Paranoid Mode—blocking everything except critical apps—if severe threats (C&C connections, known malware) are detected.
- **Privacy Stream Mode**: 1-click UI masking that seamlessly obscures all Local and Public IP addresses in the dashboard to prevent leaks while live streaming.
- **0-ms Kernel Route Monitor**: Micro-polls your OS routing table via dummy UDP sockets every 100ms. If your VPN drops, the Master Killswitch engages instantly before packets can leak to your ISP.

### 🖥️ Headless Architecture & IPC
- **True Daemon Mode**: Run completely silently in the background via the `--service` CLI flag, perfect for Raspberry Pi or ARM embedded systems.
- **Single-Instance Lock**: A built-in TCP socket securely binds to `127.0.0.1:54321` to ensure only one firewall engine runs at a time. 
- **Dynamic GUI Restoration**: Launching the app while the headless daemon is already running seamlessly merges the two. The new instance silently signals the daemon to load the UI, then exits smoothly.

## 🔒 Security & Tamper Defenses

NetStrip integrates deep defense-in-depth mechanisms to protect its runtime environment and guarantee internet availability:

- **Runtime Tamper Verification**: Cryptographic SHA-256 validation of the core engine files guarantees that malware cannot quietly replace the sinkhole binaries while NetStrip runs.
- **Fail-Open Recovery**: If an unrecoverable crash occurs, a detached watchdog process forcibly removes all active firewall hooks. It dynamically reads your original pre-NetStrip DNS configurations from the local database and flawlessly restores them (precisely reverting back to your specific static IPs or DHCP configuration) to guarantee the host machine never loses internet.
- **Strict Pathing & Privilege Defenses**: Absolute path enforcement and execution policy hardening prevent malicious actors from hijacking the NetStrip daemon via relative path spoofing or DLL sideloading.
- **Anti-Corruption Database Locks**: The SQLite WAL (Write-Ahead Logging) mode is paired with strict thread-safe isolation to ensure firewall rules and connection logs cannot be deliberately corrupted by aggressive IO attacks.
- **Local IPC Socket Authorization**: The single-instance communication socket actively validates structured JSON payloads to prevent Local Privilege Escalation (LPE) or unauthorized GUI hijacking from other user accounts.
- **PowerShell Injection Hardening**: The background icon extraction engine mathematically sanitizes and Base64-encodes all file paths before OS interaction, completely neutralizing arbitrary command execution via crafted executable names.
- **Subprocess Shell Sandboxing**: All system-level operations (`netsh`, `schtasks`, UAC elevations) are strictly executed with `shell=False` using isolated list arguments, preventing any possibility of OS-level shell injection exploits.

## 🛠️ Architecture

NetStrip is meticulously divided into two independent layers to maximize stability and minimize overhead:

1. **The Core Engine**: A multi-threaded daemon handling packet evaluation, SQLite logging, DNS proxying, and Kernel Route monitoring.
2. **The GUI App**: A hardware-accelerated visualizer powered by `CustomTkinter`. Built entirely independent from the Core Engine, allowing it to be safely minimized to the system tray or completely closed for pure headless operation.

### 🎨 GUI & UX Optimizations

The interface has been meticulously optimized to feel responsive and fluid, even under heavy network traffic:

- **Ghost-Line Sash Dragging**: The divider between the main content and connections sidebar uses a lightweight ghost indicator during drag instead of triggering real-time panel resizes, eliminating all stutter and rendering artifacts.
- **Debounced Window Resize**: Window resize events are batched and the connections sidebar refresh loop is paused during active resizing. Layout recalculations flush once on release, preventing graphical delays and widget thrashing.
- **Lazy Tab Preloading**: Non-active tabs are pre-instantiated in staggered 300ms intervals after boot, so switching between Dashboard, Logs, Filter Lists, and Settings is instant with zero construction delay.
- **View Caching**: Once a tab is built, it is never destroyed — only hidden via `grid_remove()`. Switching tabs is a zero-cost O(1) swap with no widget reconstruction.
- **3× Faster Scroll Speed**: Mouse wheel events are patched at the framework level to scroll 3 lines per tick instead of CustomTkinter's sluggish default.
- **Animated Logo Canvas**: The animated logo renders on a lightweight Canvas widget to avoid PIL overhead during idle.
- **Splash Screen with Progressive Loading**: A splash screen with animated progress bars masks the ~2s cold-start initialization, preventing any white/black window flash on launch.
- **Flicker-Free Dashboard**: The activity feed uses a pre-allocated widget pool — rows are updated in-place via `configure()` calls rather than being destroyed and recreated every refresh cycle.

### 💾 Backup & Import

Full profile backup and import via JSON is built in. The export captures **all** user settings, app rules, custom online blocklist URLs, and their block/allow classifications into a single portable `.json` file. Importing merges cleanly — custom blocklist sources are de-duplicated by name, and settings are applied immediately. This enables easy migration between machines or deploying identical configurations to headless embedded instances by copying a single file.

## 📖 Installation

### Option 1: Standalone Executable (Recommended for Windows, macOS & Linux)
Download the pre-compiled `.exe` file from the [GitHub Releases page](https://github.com/neohiro/Cripple-NetStrip/releases). Run as Administrator. No Python installation required.

### Option 2: Run from Source (All Platforms)

```bash
git clone https://github.com/neohiro/Cripple-NetStrip.git
cd Cripple-NetStrip
pip install -r requirements.txt
```

### Running NetStrip
*Note: NetStrip requires administrative/root privileges to bind to system-level network interfaces and inject kernel rules.*

**Windows:**
```powershell
python main.py
```

**macOS/Linux:**
```bash
sudo python3 main.py
```

**Headless Mode:**
```bash
sudo python3 main.py --service
```
## 🙏 Credits

Powered by the incredible open-source community:

**Core Technologies:**
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) by Tom Schimansky
- [dnslib](https://github.com/paulc/dnslib) by PaulC
- [psutil](https://github.com/giampaolo/psutil) by Giampaolo Rodola
- [WinDivert](https://github.com/basil00/Divert) by basil00

**Blocklists & Identity Providers:**
- [AdGuard](https://adguard.com/en/blog/adguard-dns-filter.html)
- [oisd](https://oisd.nl/) by sjhgvr
- [Steven Black Hosts](https://github.com/StevenBlack/hosts)
- [HaGeZi](https://github.com/hagezi/dns-blocklists)
- [WindowsSpyBlocker](https://github.com/crazy-max/WindowsSpyBlocker)
- [URLHaus](https://urlhaus.abuse.ch/)
- [v2fly / domain-list-community](https://github.com/v2fly/domain-list-community) (Used for Corporate Identity Profiling)
- [Peter Lowe's Ad/Tracking List](https://pgl.yoyo.org/adservers/)
- [Dan Pollock's hosts](https://someonewhocares.org/hosts/)
- [AdAway](https://adaway.org/)
- [Energized Protection](https://energized.pro/)

## 🚀 Release Notes (v2.0.0)
- **New Version v2.0.0**: Cripple has officially reached version 2.0.0!
- **System Classification Engine**: New intelligent DNS-level OS tracking telemetry interception.
- **Auto-Updater Rate Limits**: Implemented proper caching for dynamic DNSCrypt resolvers.
- **GUI Refinements**: Fully rebranded all references to Cripple, optimized memory leaks, and improved factory reset resilience.

## 📄 License
This project is licensed under the MIT License. See `LICENSE` for details.
