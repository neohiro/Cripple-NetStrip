## [v3.1.0] - Security Hardening & Live Traffic Polish
### Added
- **Crash Report Delivery Guarantee**: Essential domain whitelist (`api.github.com`, `frenzypenguin.media`, `github.com`) bypasses all blocking. Crash reporter retries 5× with exponential backoff (2s→4s→8s→16s) to survive network restoration glitches.
- **HMAC-SHA256 Watchdog**: Periodic live integrity scanning of all engine files with keyed hashes. Detects tampering at runtime.
- **Adaptive Live Traffic Polling**: 250ms refresh when GUI is visible for real-time connection feel, 2000ms when headless to preserve CPU.
- **LAN Shield PSK Management**: Redesigned settings panel with Copy (visual feedback), Paste (Fernet validation), and Regenerate buttons. Hot-reloads LAN Shield without restart. PSK persists across app updates.
- **Conditional Version Glow**: RGB animation on version label only activates when an update is actually available.
- **DLL Sideloading Mitigation**: `SetDefaultDllDirectories` restricts DLL search paths at startup.
- **IPC Command Sanitization**: Regex-validated ALLOW/BLOCK domain commands on the IPC socket.
- **Anti-Replay Nonces**: LAN Shield broadcast messages include nonces to prevent replay attacks.
- **IoT Local API Auth**: API binds to localhost only with optional token authentication.

### Changed
- **Watchdog Crash Recovery**: Now performs full cleanup on crash — resets firewall rules, re-enables IPv4/IPv6 protocols, clears killswitch DB state.
- **Build Pipeline**: Replaced deprecated PyInstaller `--hookspath` with `--additional-hooks-dir`. Added fallback source zip bundles for CI resilience.
- **Analytics Delivery**: Removed placeholder `netstrip.io` domains. All telemetry now routes through GitHub Issues API.
- **Animation Timings**: Tightened pulse/flash animations (340ms total cycle vs 680ms) for snappier live traffic feel.

### Fixed
- Desktop connections sidebar polling loop dying when window not mapped
- Right pane connections list not showing in desktop GUI
- Firewall reset not completing gracefully on app close
- Watchdog leaving orphaned IPv6/IPv4 protocol bindings disabled after hard crash

---

## [v3.0.2] - The Ghost Mode Update
### Added
- **Absolute Master Killswitch (Ghost Mode)**: The killswitch now unconditionally drops ALL network traffic across all NICs and protocols, stripping away all loopback exceptions to turn the hardware into a true ghost on the network.
- **Fast-Updating Threat Intel**: Implemented custom update cycles per blocklist, allowing botnet and malware C2 lists (like Feodo Tracker and URLhaus) to update every 1-4 hours while ads remain on a 24-hour cycle.
- **Millions of Domains globally**: Added massive multi-million domain lists (HaGeZi Ultimate) and dozens of regional and cultural blocklists (EasyList Germany, AdGuard Russian, YousList, etc.).

### Changed
- **Update Category Protection**: Bumped OS Update and System connection categories to sit just below Essential, ensuring critical patches are never misclassified by overly aggressive tracking blocklists.
- **Paranoid Mode Overrides**: Hardened Paranoid Mode while preserving the ability for manual UI whitelists (App Connections Sidebar & List Manager) to punch through the blanket block perfectly.

# Changelog

## [2.1.0] - Elite Integrity Update
### Added
- **Deep Kernel Active Neutralization**: Built a custom eBPF/XDP engine for Linux to physically drop raw `AF_PACKET` socket bypasses at the NIC layer.
- **Dynamic Layer 2 ARP Pinning**: Mathematically neutralizes ARP spoofing/MITM on Windows, Linux, and macOS by statically pinning the Router's MAC address natively in the OS.
- **Active Anomaly Neutralizer**: Background scanner now actively issues `SIGKILL` to unauthorized Pcap packet injectors and automatically disables rogue VPN (TAP/TUN) virtual adapters.
- **Headless Live IPC CLI**: Server admins can now run commands like `python main.py --block evil.com` from a remote SSH terminal to update the NetStrip daemon in real-time.
- **Global IPv4 Execution**: Experimental ability to forcefully disable the IPv4 stack globally to isolate the system.
- **Engineer Audit**: Added advanced OOS (Out-of-Scope) vectors to documentation for Enterprise Security Architects.

### Changed
- Slimmed GUI documentation to focus entirely on the multi-threaded, C-based backend performance.
- Integrity Modules (Kernel Scanner, ARP Pinning) are now enabled by default and elegantly neutralize threats without unnecessarily forcing the entire system into a Paranoid killswitch state.

🚀 NetStrip v2.0.1 Hotfix & Auto-Updater Release!

✨ **New Features**
- **Automated Update Checker**: NetStrip now automatically polls GitHub every 24 hours to check for new releases securely in the background.
- **Dynamic Glowing Updates**: The GUI version tracker pulses a bright yellow glow when an update is available, acting as an organic unobtrusive notification. Clicking it instantly navigates you to the new Updates tab!
- **System Block Visuals**: The parent process group 'Block All' button now universally reflects red when 'Block System Connections' is active and all child connections are marked SYSTEM.

🐛 **Bug Fixes**
- **Native OS Binary Icons**: Bypassed a fallback logic glitch causing core Windows background processes (like \	askhostw.exe\ and \svchost.exe\) to display an incorrect generic GitHub icon. They now properly display the official Microsoft Windows 4-squares icon.
- **Privacy Stream Mode**: Enabled Privacy Sweep for GUI labels masking Location and Public IP details.
- **Autostart**: Implemented native OS scheduling components for macOS, Linux, and Windows autostart features.
- **In-Browser DNS Toggle**: Hot-reloading enabled without restarting the DNS proxy.
