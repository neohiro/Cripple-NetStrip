<div align="center">
  <img src="assets/cripper_logo.png" alt="Cripper Logo" width="200"/>

  # NetStrip (Cripple)
  **Intelligent Network Debloater & Multi-Layered Firewall**

  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
  [![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgray.svg)](https://github.com/)
  [![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
  
  *Strip away the noise. Take back control of your network.*
  
  **NetStrip (also known as Cripple)** is a powerful, cross-platform desktop application that acts as a local DNS sinkhole, intelligent firewall, and live connection monitor. It provides absolute visibility into every outbound network request your system makes, allowing you to instantly sever invasive telemetry, ads, and background tracking with surgical precision.
</div>

---

## 🛡️ What is NetStrip?

NetStrip is a next-generation network traffic analyzer. Operating securely at the system level, it drops ads, telemetry, trackers, and malware packets before they even leave your network interface.

Designed for absolute privacy and network hygiene, NetStrip prevents bypasses that standard DNS blockers miss—blocking hardcoded telemetry IPs, mitigating DNS-over-HTTPS (DoH) browser leaks, and clamping down on stealthy IPv6 Router Advertisements (SLAAC).

## ✨ Core Capabilities

### 🚧 Absolute Zero-Leak Packet Interception
- **Kernel Integrations**: Uses `WinDivert` (Windows), `route blackholing` (macOS), and dynamic `iptables` (Linux) to drop unwanted packets instantly at the OS level.
- **DoH Sinkhole**: Intercepts and sinkholes 30+ major DNS-over-HTTPS providers (like Cloudflare, Google, AliDNS) to prevent web browsers from stealthily bypassing NetStrip's filtering.
- **IPv6 SLAAC Lockdown**: Forcibly disables IPv6 Router Advertisements across all operating systems to prevent rogue routers from slipping external DNS configurations into your OS.
- **Global IPv6 Killswitch**: 1-click option to brutally disable IPv6 globally across the OS, forcing all traffic onto easily monitorable IPv4 routes.
- **LAN Shield**: Instantly block or allow all private subnet communications (10.x, 172.16.x, 192.168.x).

### 🧠 Smart Shield & Streamer Privacy
- **Smart Shield**: NetStrip continuously monitors your connections. If severe threats (C&C connections, known malware) are detected, it automatically escalates from Normal to Paranoid Mode—blocking everything except critical apps.
- **Privacy Stream Mode**: 1-click UI masking feature that seamlessly obscures all Local and Public IP addresses in the dashboard, live logs, and connection sidebars, preventing IP leaks while live streaming.
- **Kernel Route Monitor (0-ms Killswitch)**: Micro-polls your OS routing table via dummy UDP sockets every 100ms. If your VPN drops and traffic shifts to your ISP, the Master Killswitch engages instantly.

### ⏱️ Dynamic Crash Recovery Watchdog
- Spawns a detached, invisible `watchdog.py` subprocess. 
- **Runtime Tamper Verification**: Before initiating any restart, the watchdog cryptographically verifies the SHA-256 hashes of all core engine files against a trusted baseline to prevent malware from hijacking the sinkhole engine.
- If the main NetStrip engine crashes, the watchdog gracefully attempts to recover the engine up to 3 times.
- If all attempts fail, it triggers an OS-specific emergency routine (restoring Windows DHCP, clearing macOS DNS, flushing Linux iptables) to fail-open and bring your internet back online.
### 📊 Multi-Layered DNS Sinkhole
- Asynchronous local DNS proxy intercepting queries against over **1.5 million** blocked domains in `O(1)` time.
- Resolves upstream queries via UDP, DNS-over-TLS (DoT), or native DNS-over-HTTPS (DoH) to secure your downstream privacy.
- App-specific DNS policies: Define custom rules (e.g., Allow `tracker.com` only when `discord.exe` requests it).
- Includes quick "15-Minute Time Bomb" temporary allow rules for quickly unbreaking websites.

### 🖥️ Headless & Embedded Operation
- Detects Raspberry Pi, ARM embedded systems, or the `--service` CLI flag to run completely silently in the background.
- Saves hundreds of megabytes of RAM by unloading the GUI and running exclusively as a daemon.

### 🎨 Hardware-Accelerated GUI
- Powered by `CustomTkinter` for a stunning, glassmorphism-inspired dark mode experience.
- Features lazy-loaded tabs, live GeoIP mapping interfaces, comprehensive analytics dashboards, and simple 1-click toggles for complex kernel networking commands.

## 🛠️ Architecture

NetStrip is meticulously divided into two independent layers to maximize stability and minimize overhead:

1. **The Core Engine**: A multi-threaded daemon handling packet evaluation, SQLite logging (WAL mode), DNS proxying, and Kernel Route monitoring.
2. **The GUI App**: The visualizer. Built independently from the Core Engine, allowing it to be safely minimized to tray or completely closed for pure headless operation.

## 📖 Installation

### Option 1: Standalone Executable (Recommended for Windows)
The easiest way to install NetStrip on Windows is to download the pre-compiled `.exe` file from the [GitHub Releases page](https://github.com/neohiro/Cripple-NetStrip/releases). 
Just download, run as Administrator, and you're good to go! No Python installation required.

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
- **CustomTkinter** (Tom Schimansky), **dnslib** (PaulC), **psutil** (Giampaolo Rodola), **WinDivert**
- **Blocklists**: AdGuard, oisd (sjhgvr), Steven Black Hosts, HaGeZi, WindowsSpyBlocker, URLHaus, and many more.

## 📄 License
This project is licensed under the MIT License. See `LICENSE` for details.
