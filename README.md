<div align="center">
  <img src="assets/cripple_logo.png" alt="Cripple Logo" width="200"/>

  # NetStrip  —  Cripple

  **Intelligent Network Debloater & Multi-Layered Firewall**

  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
  [![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Android-lightgray.svg)](https://github.com/)
  [![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
  [![Build Status](https://github.com/neohiro/Cripple-NetStrip/actions/workflows/release.yml/badge.svg)](https://github.com/neohiro/Cripple-NetStrip/actions)

  *Strip away the noise. Take back control of your network.*

  > **🚀 v3.0.0** — Rebuilt zero-leak kernel interception engine, multi-platform IPC daemon architecture, and more!

</div>

## Overview

**NetStrip (Cripple)** is a cross-platform FOSS application that acts as a local DNS sinkhole, intelligent firewall, and live connection monitor. It provides absolute visibility into every network request your system makes and receives, allowing you to instantly sever invasive telemetry, ads, and background tracking with surgical precision.

Designed for absolute privacy and network hygiene, NetStrip prevents bypasses that standard DNS blockers miss — blocking hardcoded telemetry IPs, mitigating DNS-over-HTTPS (DoH) browser leaks, and clamping down on stealthy IPv6 Router Advertisements (SLAAC).

<p align="center">
  <a href="#-key-features">Key Features</a> •
  <a href="#%EF%B8%8F-architecture">Architecture</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-credits">Credits</a>
</p>

## ✨ Key Features

### 🚧 Zero-Leak Packet Interception
Most blockers rely on DNS filtering, which fails when applications hardcode IP addresses. NetStrip uses OS-level hooking (`WinDivert` on Windows, `NFQueue` on Linux, `PF` on macOS) to intercept traffic at the IP packet layer, destroying telemetry that bypasses traditional DNS.

### 🛡️ Smart Shield & Deep Kernel Integrity
Monitors live processes to detect malicious behavioral anomalies in real-time with active neutralization. Deep Kernel XDP Mode injects fileless eBPF programs into the physical NIC on Linux. Layer 2 ARP Lockdown natively pins your gateway MAC address to prevent ARP Spoofing and MITM attacks. The Kernel Bypass Scanner actively neutralizes rogue virtual VPN adapters and stops Pcap packet-injection tools on sight.

### 📊 Multi-Layered DNS Sinkhole
Evaluates queries asynchronously against over **1.5 million** blocked domains in `O(1)` time. Online blocklists auto-refresh every 24 hours with staggered network throttling. Paste any raw `.txt` URL into the Filter Manager — the engine uses dual-layer heuristic scanning to auto-classify lists into Trackers, Telemetry, Malware, or System categories. Resolves upstream queries via DoT, native DoH, or UDP fallback (auto-detects third-party local DNS proxies).

### 🎨 High-Performance GUI
Built on `CustomTkinter`, the GUI is completely detached from the core engine. All heavy network routing, packet interception, and IPC management runs asynchronously on multi-threaded C-based backends, ensuring a lag-free UI even at 10,000+ queries per second.

### 🧠 Smart Shield & Streamer Privacy
DPI Smart Filters intercept HTTP/HTTPS headers via SNI extraction. Deep Connection ARP Pinning enforces per-connection MAC-address validation — if an active connection swaps MAC addresses, NetStrip terminates it immediately. IoT Botnet detection identifies rapid-fire scanning (>50 outbound spikes/sec) using sliding rate windows. Privacy Stream Mode masks all IP addresses in the dashboard for safe live streaming.

### 🔧 Network Capabilities

**DoH Sinkhole** — Force-routes 30+ DNS-over-HTTPS providers into the sinkhole.
**IPv6 SLAAC Lockdown** — Disables IPv6 Router Advertisements across all platforms.
**Global IPv6 Killswitch** — 1-click brutal disable of IPv6 system-wide.
**LAN Shield E2E Mesh** — Cryptographically paired LAN clients broadcast AES-128-GCM encrypted UDP `ANOMALY`, `KILLSWITCH`, and `RESTORE` commands. One client's anomaly locks down your entire local grid.
**Home Assistant IoT Webhooks** — Seamlessly pushes network threat events via JSON POST webhooks to Home Assistant, Node-RED, or Zigbee/Thread monitors. Flash your smart lights red if a device on your network is compromised.
**WMI Antivirus Integration** — Automatically queries `SecurityCenter2` (Windows) or process lists (Linux) to flawlessly whitelist third-party Anti-Malware (BitDefender, Kaspersky) telemetry/definition servers and NDIS drivers.
**App-Specific Policies** — Per-executable domain rules.
**Time Bombs** — 15-minute temporary allow-rules for quick troubleshooting.
**VPN Pre-Cipher Interception** — Filters traffic before VPN encryption (WireGuard, OpenVPN compatible).
**Multi-NIC / Gateway Mode** — Full support for dual-adapter NUCs acting as network-wide firewalls.

### 📱 Mobile Architecture (Android)
NetStrip supports Android dynamically through a Python-for-Android headless bridge:
- **Cloud Build Pipeline**: The repository includes a `buildozer.spec` designed for GitHub Actions. Whenever a release is tagged, the `ubuntu-latest` cloud runner will automatically compile the Python backend, Kivy GUI wrapper, and JNI components into a standalone `.apk` artifact.
- **VPN Loopback**: Because Android strictly restricts binding to privileged ports (like DNS port 53) without Root access, NetStrip automatically detects the Android environment (`hasattr(sys, 'getandroidapilevel')`) and binds its interceptor to the high loopback port `127.0.0.1:5353`. You can then pair this with any local Android VPN application (like RethinkDNS or AdGuard) pointed at `127.0.0.1:5353` to seamlessly filter traffic system-wide!

## 🛠️ Architecture

NetStrip is divided into two independent layers:

1. **Core Engine** — A multi-threaded daemon handling packet evaluation, SQLite logging, DNS proxying, and kernel route monitoring.
2. **GUI App** — A hardware-accelerated visualizer powered by `CustomTkinter`, fully independent from the engine. Can be minimized to tray or closed entirely for headless operation.

### Headless & Remote Management
Run completely silently via `--service` for Raspberry Pi, NUCs, or ARM embedded systems. Fully manageable remotely via SSH using live IPC commands. See the **[CLI Guide](CLI_GUIDE.md)** for boot variables and live management commands.

### GUI & UX Optimizations

**Ghost-Line Sash** — Lightweight ghost indicator during drag instead of real-time panel resizes.
**Debounced Resize** — Batched window resize events with deferred layout flush.
**Lazy Tab Preloading** — Staggered 300ms pre-instantiation for zero-delay tab switching.
**View Caching** — Tabs hidden via `grid_remove()` — O(1) swap, never destroyed.
**3× Scroll Speed** — Framework-level mouse wheel patching.
**Splash Progressive Loading** — Animated splash masks ~2s cold-start initialization.
**Flicker-Free Dashboard** — Pre-allocated widget pool with in-place `configure()` updates.

## 🔒 Security & Tamper Defenses

NetStrip integrates deep defense-in-depth mechanisms to protect its runtime environment:

**Runtime Tamper Verification** — SHA-256 validation of core engine files at runtime.
**Fail-Open Recovery** — Watchdog restores original DNS and removes firewall hooks on crash.
**Strict Pathing** — Absolute path enforcement prevents DLL sideloading and PATH hijacking.
**Anti-Corruption DB** — SQLite WAL mode with thread-safe isolation.
**IPC Authorization** — Structured JSON payload validation on the single-instance socket.
**PowerShell Hardening** — Base64-encoded paths neutralize command injection via crafted filenames.
**Shell Sandboxing** — All system commands use `shell=False` with isolated list arguments.

## 💾 Backup & Import

Full profile backup and import via JSON. Exports capture all user settings, app rules, custom blocklist URLs, and classifications into a single portable `.json` file. Importing merges cleanly with de-duplication by name, enabling easy migration between machines or identical headless deployments.

## 📖 Installation

### Option 1: Standalone Executable (Recommended)
Download the pre-compiled binary from the [GitHub Releases page](https://github.com/neohiro/Cripple-NetStrip/releases). Run as Administrator/sudo. No Python required.

### Option 2: Run from Source

```bash
git clone https://github.com/neohiro/Cripple-NetStrip.git
cd Cripple-NetStrip
pip install -r requirements.txt
```

### Running NetStrip

**Windows:**
```powershell
python main.py
```

**macOS / Linux:**
```bash
sudo python3 main.py
```

**Headless Mode:**
```bash
sudo python3 main.py --service
```

*   **Operating System:** Windows 10/11, macOS, Linux, and Android
*   **Permissions:** Administrator/Root privileges required for core interception (except on Android where VPN Service is used)

## ⏰ Build Metrics

This entire ecosystem — GUI, Windows packet hooking, eBPF routing, SQLite WAL, system tray integrations, IPC layers, and security audits — was built in **~2.5 days** of pure active coding time.

## 🚀 Release Notes

**v3.0.0** — Rebuilt zero-leak kernel interception engine. Multi-platform IPC daemon architecture. Futuristic-minimalist UI theme. CPU stability improvements. Enhanced anomaly whitelisting logic.

**v2.0.0** — System Classification Engine. Auto-Updater rate limits. GUI rebrand and memory leak optimizations.

## 🙏 Credits

**Core Technologies:**  
[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) • [dnslib](https://github.com/paulc/dnslib) • [psutil](https://github.com/giampaolo/psutil) • [WinDivert](https://github.com/basil00/Divert)

**Blocklists & Identity Providers:**  
[AdGuard](https://adguard.com/en/blog/adguard-dns-filter.html) • [oisd](https://oisd.nl/) • [Steven Black Hosts](https://github.com/StevenBlack/hosts) • [HaGeZi](https://github.com/hagezi/dns-blocklists) • [WindowsSpyBlocker](https://github.com/crazy-max/WindowsSpyBlocker) • [URLHaus](https://urlhaus.abuse.ch/) • [v2fly](https://github.com/v2fly/domain-list-community) • [Peter Lowe](https://pgl.yoyo.org/adservers/) • [Dan Pollock](https://someonewhocares.org/hosts/) • [AdAway](https://adaway.org/) • [Energized Protection](https://energized.pro/) • [AdGuard Mobile Filters](https://adguard.com/en/blog/adguard-dns-filter.html) • [HaGeZi Mobile Telemetry](https://github.com/hagezi/dns-blocklists)

## 📄 License

This project is licensed under the MIT License. See `LICENSE` for details.
