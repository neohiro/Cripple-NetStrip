<div align="center">
  <img src="assets/cripple_logo.png" alt="Cripple Logo" width="200"/>

  # NetStrip  —  Cripple

  **Intelligent Network Debloater & Multi-Layered Firewall**

  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
  [![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Android-lightgray.svg)](https://github.com/)
  [![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
  [![Build Status](https://github.com/neohiro/Cripple-NetStrip/actions/workflows/release.yml/badge.svg)](https://github.com/neohiro/Cripple-NetStrip/actions)

  *Strip away the noise. Take back control of your network.*

</div>

---

## 📑 Table of Contents

- [Overview](#overview)
- [Core Features](#-core-features)
- [Network Capabilities](#-network-capabilities)
- [Security & Tamper Defenses](#-security--tamper-defenses)
- [GUI & UX](#-gui--ux)
- [Mobile (Android)](#-mobile-android)
- [Architecture](#%EF%B8%8F-architecture)
- [Installation](#-installation)
- [Release Notes](#-release-notes)
- [Credits](#-credits)

---

## Overview

**NetStrip (Cripple)** is a cross-platform FOSS application that acts as a local DNS sinkhole, intelligent firewall, and live connection monitor. It provides absolute visibility into every network request your system makes and receives, allowing you to instantly sever invasive telemetry, ads, and background tracking with surgical precision.

Designed for absolute privacy and network hygiene, NetStrip prevents bypasses that standard DNS blockers miss — blocking hardcoded telemetry IPs, mitigating DNS-over-HTTPS (DoH) browser leaks, and clamping down on stealthy IPv6 Router Advertisements (SLAAC).

---

## ✨ Core Features

### 🚧 Zero-Leak Packet Interception
Most blockers rely on DNS filtering, which fails when applications hardcode IP addresses. NetStrip uses OS-level hooking (`WinDivert` on Windows, `NFQueue` on Linux, `PF` on macOS) to intercept traffic at the IP packet layer, destroying telemetry that bypasses traditional DNS.

### 📊 Multi-Layered DNS Sinkhole
- Evaluates queries asynchronously against **1.5M+ blocked domains** in `O(1)` time
- Online blocklists auto-refresh every 24 hours with staggered network throttling
- Paste any raw `.txt` URL — the engine auto-classifies lists into Trackers, Telemetry, Malware, or System categories
- Upstream resolution via DoT, native DoH, or UDP fallback (auto-detects local DNS proxies)

### 🛡️ Smart Shield & Deep Kernel Integrity
- Real-time malicious behavioral anomaly detection with active neutralization
- **Deep Kernel XDP Mode** — fileless eBPF programs injected into the physical NIC on Linux
- **Layer 2 ARP Lockdown** — pins gateway MAC address to prevent ARP Spoofing / MITM
- **Kernel Bypass Scanner** — neutralizes rogue virtual VPN adapters and Pcap packet-injection tools

### 🧠 DPI & Privacy Filters
- **SNI Extraction** — intercepts HTTP/HTTPS headers via deep packet inspection
- **Deep Connection ARP Pinning** — per-connection MAC validation; terminates on MAC swap
- **IoT Botnet Detection** — identifies rapid-fire scanning (>50 outbound spikes/sec) via sliding rate windows
- **Privacy Stream Mode** — masks all IP addresses in the dashboard for safe live streaming

### 🔑 LAN Shield E2E Mesh
- Cryptographically paired LAN clients via Fernet (AES-128-CBC) pre-shared keys
- Broadcasts encrypted UDP `ANOMALY`, `KILLSWITCH`, and `RESTORE` commands
- One client's anomaly locks down your entire local network grid
- **Easy PSK management** — Copy / Paste / Regenerate buttons with Fernet validation and hot-reload
- PSK persists in `~/.netstrip/netstrip.db` — survives app updates

---

## 🌐 Network Capabilities

| Feature | Description |
|---|---|
| **DoH Sinkhole** | Force-routes 30+ DNS-over-HTTPS providers into the sinkhole |
| **IPv6 SLAAC Lockdown** | Disables IPv6 Router Advertisements across all platforms |
| **Global IPv6 Killswitch** | 1-click brutal disable of IPv6 system-wide |
| **Ghost Mode Killswitch** | Drops ALL traffic across all NICs and protocols — true network ghost |
| **Home Assistant IoT** | Pushes threat events via JSON POST webhooks to Home Assistant, Node-RED, Zigbee/Thread |
| **WMI AV Integration** | Auto-whitelists third-party antivirus (BitDefender, Kaspersky, etc.) via SecurityCenter2 |
| **App-Specific Policies** | Per-executable domain rules |
| **Time Bombs** | 15-minute temporary allow-rules for quick troubleshooting |
| **VPN Pre-Cipher** | Filters traffic before VPN encryption (WireGuard, OpenVPN compatible) |
| **Multi-NIC Gateway** | Full support for dual-adapter NUCs acting as network-wide firewalls |

---

## 🔒 Security & Tamper Defenses

| Defense Layer | Implementation |
|---|---|
| **HMAC-SHA256 Watchdog** | Periodic live integrity scanning of all engine files with keyed hashes |
| **Crash Report Guarantee** | Essential domain whitelist + 5× retry with exponential backoff; reports always get out |
| **DLL Sideloading Mitigation** | `SetDefaultDllDirectories` restricts DLL search paths at startup |
| **IPC Command Validation** | Regex-validated ALLOW/BLOCK commands on the single-instance IPC socket |
| **Fail-Open Recovery** | Watchdog restores DNS, firewall rules, IPv4/IPv6 protocols, and killswitch state on crash |
| **Runtime Tamper Check** | SHA-256 validation of core engine files at runtime |
| **Anti-Corruption DB** | SQLite WAL mode with thread-safe isolation |
| **PowerShell Hardening** | Base64-encoded paths neutralize command injection via crafted filenames |
| **Shell Sandboxing** | All system commands use `shell=False` with isolated list arguments |
| **Anti-Replay Nonces** | LAN Shield broadcasts include nonces to prevent replay attacks |
| **API Bind & Auth** | IoT Local API binds to localhost only with optional token authentication |

---

## 🎨 GUI & UX

### Desktop (CustomTkinter)
- Fully detached from the core engine — all heavy work runs on multi-threaded C-based backends
- Lag-free UI even at 10,000+ queries per second
- **Live App Connections Sidebar** — real-time process traffic with flashing red/green traffic lights
- **Adaptive polling** — 250ms when GUI visible (smooth live feel), 2000ms when headless (CPU saver)
- Conditional version glow animation — only pulses when an update is available

### UX Optimizations

| Optimization | Detail |
|---|---|
| Ghost-Line Sash | Lightweight ghost indicator during drag instead of real-time panel resizes |
| Debounced Resize | Batched window resize events with deferred layout flush |
| Lazy Tab Preloading | Staggered 300ms pre-instantiation for zero-delay tab switching |
| View Caching | Tabs via `grid_remove()` — O(1) swap, never destroyed |
| 3× Scroll Speed | Framework-level mouse wheel patching |
| Splash Loading | Animated splash masks ~2s cold-start initialization |
| Flicker-Free Dashboard | Pre-allocated widget pool with in-place `configure()` updates |

### Android (Kivy)
- Live App Connections as priority tab with flashing traffic lights and blinking connection rows
- Tab layout matches desktop order with connections as index 0
- Cripple branding in upper bar
- Built via GitHub Actions → `buildozer.spec` → standalone `.apk`

---

## 📱 Mobile (Android)

NetStrip supports Android through a Python-for-Android headless bridge with **dual VPN mode**:

### Native VPN Mode (Default)
NetStrip occupies Android's VPN slot directly — **all traffic** (DNS, TCP, UDP) routes through NetStrip's TUN interface for complete packet filtering. No other VPN app needed. Blocked connections are silently dropped at the packet level.

### Companion Mode
DNS-only filtering at `127.0.0.1:5353`. Designed to work **alongside another VPN app** (RethinkDNS, AdGuard, WireGuard, etc.) that handles the actual encrypted tunnel. Point your VPN app's DNS server to `127.0.0.1:5353` for seamless filtering.

### Build Pipeline
GitHub Actions compiles the Python backend, Kivy GUI, Java VPN service, and JNI components into a standalone `.apk` on every tagged release.

---

## 🛠️ Architecture

NetStrip is divided into two independent layers:

1. **Core Engine** — Multi-threaded daemon handling packet evaluation, SQLite logging, DNS proxying, and kernel route monitoring
2. **GUI App** — Hardware-accelerated visualizer powered by CustomTkinter, fully independent from the engine. Can be minimized to tray or closed entirely for headless operation

### Headless & Remote Management
Run completely silently via `--service` for Raspberry Pi, NUCs, or ARM embedded systems. Fully manageable remotely via SSH using live IPC commands. See the **[CLI Guide](CLI_GUIDE.md)** for boot variables and live management commands.

### Backup & Import
Full profile backup and import via JSON. Exports capture all user settings, app rules, custom blocklist URLs, and classifications into a single portable `.json` file. Importing merges cleanly with de-duplication by name.

---

## 📖 Installation

### Option 1: Standalone Executable (Recommended)
Download the pre-compiled binary from the [GitHub Releases page](https://github.com/neohiro/Cripple-NetStrip/releases). Run as Administrator/sudo. No Python required.

### Option 2: Run from Source

```bash
git clone https://github.com/neohiro/Cripple-NetStrip.git
cd Cripple-NetStrip
pip install -r requirements.txt
```

### Running

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

### Requirements
- **OS:** Windows 10/11, macOS, Linux, Android
- **Python:** 3.10+
- **Permissions:** Administrator/Root required for core interception (Android uses VPN Service)

---

## 🚀 Release Notes

### v3.1.0 — Security Hardening & Live Traffic Polish
- **Crash Report Delivery Guarantee** — essential domain whitelist (`api.github.com`, `frenzypenguin.media`, `github.com`) + 5× retry with exponential backoff
- **HMAC-SHA256 Watchdog** — periodic live integrity scanning of all engine files
- **Adaptive Live Traffic Polling** — 250ms GUI / 2000ms headless for real-time connection feel without CPU waste
- **LAN Shield PSK Management** — copy/paste/regenerate with Fernet validation and hot-reload
- **Conditional Version Glow** — RGB animation only when an update is actually available
- **Watchdog Crash Recovery** — full firewall reset, IPv4/IPv6 re-enable, killswitch DB state clear
- **DLL Sideloading Mitigation** — `SetDefaultDllDirectories` at startup
- **IPC Command Sanitization** — regex-validated ALLOW/BLOCK domains
- **Anti-Replay Nonces** — LAN Shield broadcast replay protection
- **Build Pipeline Fix** — PyInstaller `--additional-hooks-dir` compat, fallback zip bundles

### v3.0.0 — Zero-Leak Engine
- Rebuilt zero-leak kernel interception engine
- Multi-platform IPC daemon architecture
- Futuristic-minimalist UI theme
- CPU stability improvements
- Enhanced anomaly whitelisting logic

### v2.0.0 — System Classification Engine
- System Classification Engine
- Auto-Updater rate limits
- GUI rebrand and memory leak optimizations

---

## ⏰ Build Metrics

This entire ecosystem — GUI, Windows packet hooking, eBPF routing, SQLite WAL, system tray integrations, IPC layers, and security audits — was built in **~2.5 days** of pure active coding time.

---

## 🙏 Credits

**Core Technologies:**  
[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) • [dnslib](https://github.com/paulc/dnslib) • [psutil](https://github.com/giampaolo/psutil) • [WinDivert](https://github.com/basil00/Divert) • [cryptography](https://github.com/pyca/cryptography)

**Blocklists & Identity Providers:**  
[AdGuard](https://adguard.com/en/blog/adguard-dns-filter.html) • [oisd](https://oisd.nl/) • [Steven Black Hosts](https://github.com/StevenBlack/hosts) • [HaGeZi](https://github.com/hagezi/dns-blocklists) • [WindowsSpyBlocker](https://github.com/crazy-max/WindowsSpyBlocker) • [URLHaus](https://urlhaus.abuse.ch/) • [v2fly](https://github.com/v2fly/domain-list-community) • [Peter Lowe](https://pgl.yoyo.org/adservers/) • [Dan Pollock](https://someonewhocares.org/hosts/) • [AdAway](https://adaway.org/) • [Energized Protection](https://energized.pro/)

---

## 📄 License

This project is licensed under the MIT License. See `LICENSE` for details.
