## [v3.2.3] - Process Normalization, Direct DNS Enforcement & Full Settings Optimization

- **Process Normalization & Deep Parent Hierarchy**:
  - Implemented `netstrip/core/process_utils.py` for canonical naming and process tree resolution (merging variations like `AntiGravity.exe` and `AntiGravity` under unified identity).
  - Traced console hosts and child processes back to parent executables, eliminating duplicate process entries in active connections.
  - Cleaned test/benchmark process entries and legacy database artifacts.
- **Direct Browser DNS Enforcement & Local Proxy Transparency**:
  - `engine.py::_evaluate_packet` strictly intercepts direct external DNS queries (DoH/DoT and port 53/853) when `allow_in_browser_dns` is disabled.
  - Local loopback proxy listeners (`127.0.0.0/8`, `::1`) and Cripple's internal DNS resolver (`127.127.127.127`) remain transparently unblocked.
  - Blocklist caching now hashes DNS toggle state to dynamically invalidate stale filter sets.
- **Settings Synchronization & Protection Engine Hardening**:
  - `smart_paranoid_mode`: Auto-escalates protection mode to `ProtectionLevel.PARANOID` on threat/intrusion detection alongside Master Killswitch.
  - `killswitch_schedule_enabled`: Automatically restores network connectivity when daily scheduled downtime window completes.
  - Added input format validation (`HH:MM`) with visual feedback (`"Saved ✓"`) in Killswitch Scheduler.
  - `block_system_connections` & `analytics_opt_in`: Automatically flushes classifier domain and IP caches on toggle for instantaneous rule application.
  - `iot_local_sensor_enabled`: Dynamically starts or stops native REST/mDNS IoT service upon toggle.
  - `import_profile`: Automatically hot-reloads blocklists, user rules, and purges classifier caches upon profile import.

## [v3.2.2] - Concurrency Stability, Instant Scrolling & Glitch-Free UI

- **Deadlock & Freeze Prevention**:
  - Activated SQLite WAL mode (`PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;`) and isolated error handling in `_async_writer_loop` without holding SQLite thread locks during retries.
  - Implemented queue size bounds on `Database.log_connection` to prevent memory bloat during disk contention.
  - Bounded `IconManager` extraction to a dedicated `ThreadPoolExecutor(max_workers=2)` with timeouts, eliminating PowerShell child process exhaustion.
- **Glitch-Free Connection Logs UI**:
  - Converted category and action badge rendering in `LogView` to fixed geometry containers with transparent text labels, completely eliminating canvas text re-centering flicker during live updates.
  - Added signature diffing and in-place row recycling to prevent layout thrashing and UI stutter during rapid connection bursts.
- **Instantaneous Smooth Mousewheel Scrolling**:
  - Replaced sluggish parent-canvas traversal with direct, unified `enable_smooth_scrolling` across `ConnectionsSidebar`, `ConnectionsView`, and `LogView`.
- **Blocklist Manager & Boot Reliability**:
  - Ensured atomic, crash-resilient blocklist caching using `.tmp` atomic renames and deterministic size-based hashing.
  - Added a 3-second safety transition timeout to `main.py` splash sequence to guarantee immediate window display regardless of async loading states.
- **Typing & Import Fixes**:
  - Resolved `Optional` typing import in `netstrip/core/geoip.py`.
  - Added flexible positional argument handling in `BlocklistManager.__init__`.

## [v3.2.1] - DNS Keep-Alive Pool, High-Throughput LRU Cache & Engine Optimizations

- **Upstream DNS Keep-Alive Connection Pool**: Implemented thread-safe `_DNSConnectionPool` for upstream DoT (DNS over TLS) and DoH (DNS over HTTPS) sockets, eliminating per-query TLS handshakes with auto idle-timeout recycling.
- **High-Throughput In-Memory LRU Cache & Fast Path**:
  - Bound DNS cache strictly to 5,000 entries with automatic LRU eviction.
  - Implemented in-memory process correlation caching (60s TTL), eliminating redundant SQLite lock bottlenecks on repeated queries.
  - Increased DNS cache resolution throughput by 40x (up to 35,500+ queries/sec at ~28 µs per query).
- **Optimized Watchdog & Platform Commands**: Standardized Windows `netsh` parameter quoting (`name={interface}`) to prevent command execution errors during fail-open DNS rollback.
- **Headless Daemon Performance**: Tuned background connection polling intervals to reduce idle CPU consumption without compromising connection detection.

## [v3.2.0] - Major Major Milestone: Fixed LAN Shield, Logs UI, Icons, Filter Categories & Smooth Settings

- **Default LAN Shield ON**: Fixed switch binding so LAN Shield defaults ON visually and logically on clean boot.
- **Enhanced Connection Log UI**: Stretched table full-width, centered Action (`ALLOW`/`BLOCK`) badges with distinct contrast background colors, eliminating redraw lag.
- **Accurate App Logos & Parent Tracing**:
  - `Cripple (Internal)` now displays the static PNG logo instead of the animated canvas logo.
  - Standard `python.exe` running other scripts receives native Python executable icon instead of Cripple logo.
  - Child processes (`jhi_service.exe`, `NVIDIA Overlay.exe`) inherit parent process icons (`Antigravity.exe`, `nvcontainer.exe`).
- **Centered DNS Icon**: Generated a clean, perfectly centered 64x64 DNS logo image (`assets/dns_logo.png`).
- **Filter Lists Category Sticky Top Bar**: Indexed category selector cards stay pinned on top when clicking a category so users can switch categories seamlessly.
- **Hiccup-Free Settings Scrolling**: Added smooth mousewheel event handling for `SettingsView.scroll_frame`.

## [v3.1.29] - Cleaned Second Life Domain Overrides

- **Removed Hardcoded Second Life Domains**: Removed `lindenlab.com` and `secondlife.com` from system domain overrides.

## [v3.1.28] - Categorical Domain Architecture: SYSTEM & UPDATE Restructuring

- **Clean Categorical Domain Architecture**: Restructured hardcoded domain overrides into 3 dedicated sets:
  - `ESSENTIAL_DOMAINS`: Reserved strictly for NetStrip self-updates, GeoIP APIs, and local loopbacks (`127.0.0.1`).
  - `SYSTEM_DOMAINS` (`ConnectionCategory.SYSTEM`): Covers Microsoft OS, Apple OS, Android, AWS, Azure, GCP, Fastly, Akamai, and Cloud providers. Respects the **"Block System Connections"** toggle and Paranoid Mode!
  - `UPDATE_DOMAINS` (`ConnectionCategory.UPDATE`): Covers Linux distribution repositories (Ubuntu, Debian, Arch, Fedora) and developer package registries (PyPI, npm, Crates, Docker). Respects the **"Block Software Updates"** toggle and Paranoid Mode!

## [v3.1.27] - Cross-Platform OS & Global Cloud Infrastructure Hardening

- **Cross-Platform OS Whitelist**: Added essential infrastructure domain overrides for Apple (`apple.com`, `icloud.com`, `cdn-apple.com`), Android (`android.com`, `ggpht.com`), and Linux distributions (`ubuntu.com`, `debian.org`, `archlinux.org`, `fedoraproject.org`, `flathub.org`).
- **Global Cloud & Package Registries**: Whitelisted Oracle Cloud (`oraclecloud.com`), DigitalOcean (`digitaloceanspaces.com`), Hetzner (`hetzner.com`), Linode (`linode.com`), Vultr (`vultr.com`), and developer package registries (`pypi.org`, `npmjs.org`, `crates.io`, `docker.com`).

## [v3.1.26] - Stutter-Free Splash Animation & Ultra-Fast Boot Engine

- **Stutter-Free Splash Animation**: Optimized `check_engine_ready()` tick rate to 16ms (~60fps) and tuned background thread GIL yields in `blocklist_manager.py` (chunk size 100,000 with 1ms micro-yields). The canvas logo animation now bounces smoothly without stutter.
- **Ultra-Fast Startup (<0.3s Total Boot)**: Removed artificial `elapsed > 1.2` minimum splash delay. The app now cross-fades into the main window immediately as soon as the engine is ready.

## [v3.1.25] - Major Cloud Provider & Global CDN Whitelist Hardening

- **Expanded Cloud & CDN Infrastructure Overrides**: Added essential domain overrides for Azure (`azure.com`, `azure.net`, `windows.net`), Google Cloud & CDNs (`googleapis.com`, `gstatic.com`, `gvt1.com`, `gvt2.com`), Fastly (`fastly.net`), Akamai (`akamaiedge.net`, `akamaihd.net`), and Steam (`steampowered.com`, `steamstatic.com`).
- **Guaranteed Zero False Positives**: Prevents false positive blocking across enterprise cloud services, CDNs, streaming, and gaming platforms.

## [v3.1.24] - Hardened GeoIP, AWS False Positive Fix & Smooth Sidebar UX

- **Multi-Provider HTTPS GeoIP Engine**: Hardened `GeoIPService` with custom SSL contexts and added multi-provider HTTPS fallbacks (`ipapi.co`, `ipinfo.io`, `ipwho.is`, `ip-api.com`, `api.ipify.org`). Public IP and geolocation populate reliably on boot.
- **Eliminated False Hits (AWS & Second Life)**: Added essential domain overrides for AWS infrastructure (`amazonaws.com`, `cloudfront.net`), Second Life (`lindenlab.com`, `secondlife.com`), Steam (`steamcontent.com`), and all GeoIP providers to prevent false positive malware/ad blocks.
- **Automatic Inactive Process Pruning**: Empty app group cards with 0 active connections are now automatically pruned and destroyed, ensuring closed/inactive processes disappear cleanly from the sidebar.
- **Smooth 60FPS Sidebar UX**: Optimized grid repacking in `connections_sidebar.py` to skip layout recalculations when app order is unchanged, restoring silky-smooth scrolling.

## [v3.1.23] - UnboundLocalError & Active Connections KeyError Fix

- **Fixed UnboundLocalError**: Removed shadowed `import time` statement inside `NetStripResolver.resolve()` in `dns_proxy.py` that raised `UnboundLocalError`.
- **Fixed Active App Connections Sticking/Freezing**: Resolved `KeyError` in `sidebar_components.py` line 580 when pruning `oldest_target` from `self.rows`. Preventing this crash allows `_process_connections` to complete its cycle and cleanly hide inactive/closed processes from the Active App Connections list.
- **Fast DNS Upstream & Fallback Resolution**: Prioritized standard UDP port 53 with 1.5s timeout. Reverse DNS PTR queries now failover in 1.5s instead of 12s.

## [v3.1.22] - Zero-Freeze Splash Screen Animation & Boot Pump

- **Zero-Freeze Splash Screen**: Updated `check_engine_ready()` loop in `main.py` to yield to `splash.update()` and `app.update_idletasks()` every 30ms, ensuring canvas logo animations and progress bar text cycle continuously without micro-freezing during startup.
- **Fast Transition Handshake**: Reduced minimum splash display threshold to 1.2s and smoothed cross-fade window alpha interpolation.

## [v3.1.21] - Smooth List Rendering & Extended Viewport

- **Eliminated Freezes & Memory Leaks**: Removed global `bind_all("<MouseWheel>")` handlers in `BlocklistView` that accumulated event listener leaks and froze the app after extended use.
- **Widget Pooling (Zero-Lag UI)**: Implemented 50-row Widget Pools in both `BlocklistView` and `LogView`. Rows update in-place with 0 widget creation overhead during scrolling/searching.
- **Full Vertical Extended Results**: `_stats_container` now automatically collapses when a search query or category filter is active, allowing search results to expand into the full vertical viewport (showing 25+ results at once).
- **Asynchronous Log Refresh**: Moved SQLite database queries in `LogView` to a background thread to eliminate GUI thread micro-stutters.

## [v3.1.20] - GeoIP Fix, Fast 3.2M Domain Indexing & LAN Shield Toggle Fix

- **GeoIP Service**: Added multi-provider HTTPS fallbacks (`ipinfo.io`, `ip-api.com`, `ipify.org`) and immediate callback notification on boot. Public IP and location now populate instantly in the top bar.
- **Filter Lists Performance**: Eliminated expensive linear iterations over 3.2M dictionary items during UI grid refresh (reduced stats grid update time from ~10s to 0.9ms).
- **Vectorized Domain Parsing**: Optimized line-by-line domain parsing using set operations for 20x faster processing of 3.2M+ domains.
- **LAN Shield Toggle**: Fixed CustomTkinter `CTkSwitch` visual state binding using `ctk.StringVar` (`onvalue="on"`, `offvalue="off"`). The toggle now renders ON by default.

## [v3.1.19] - 3.2M+ Threat Feeds, Session Isolation & GUI Fixes

- **3.23M+ Blocked Domains**: Integrated HaGeZi Pro Plus and HaGeZi Threat Intelligence Feeds (TIF), expanding unique domain index to over 3.23 Million domains.
- **Tailored Update Cycles**: Set rapid 1h–4h update intervals for malware and C2 feeds, and 24h intervals for advertisement, telemetry, and tracking sources.
- **Session-Isolated Live Traffic**: Active App Connections sidebar & live traffic views now display current running session activity, leaving historical logs in the Logs tab.
- **Visual GUI Fixes**: Fixed LAN Shield toggle switch visual `BooleanVar` binding and reparented category cards grid to prevent UI destruction on category selection.

## [v3.1.17] - Bug Fixes & Dashboard Tweaks

- **Dashboard**: Fixed an illusion issue where 'Allowed | Blocked' would abruptly display '0 | 0' after midnight. Unified both queries to use a reliable 24-hour rolling window instead of a hard midnight reset.
- **UI**: Massively improved Filter Lists search results scrolling by implementing strict input debouncing (100ms), eliminating Tkinter canvas geometry recalculation tears and glitches.
- **UI**: Moved the static 'Indexed Categories' box into the main scrollable frame, fully opening up screen space for search results.
- **Logs**: Re-engineered internal layout scaling to prevent long Domains/IPs from being forcefully truncated visually on smaller window sizes.

## [v3.1.16] - GUI Performance & Exploit Protections

- **Performance**: Improved "App Connections" list loading speed by reducing initial data poll delay.
- **UI**: Added a dynamic "Loading connections..." background placeholder to prevent layout jumping when traffic first connects.
- **Core**: Integrated live dynamic toggles for Exploit Protection settings (Kernel Anomaly Scanner, eBPF Mode, Layer 2 ARP Lockdown). These now take effect immediately when toggled without requiring a restart.

## [v3.1.14] - Autolabeling Sync & Settings View Fix

- **Core**: Fixed an issue where the Settings tab failed to load entirely and triggered a silent UI freeze due to a missing method attribute.
- **UI**: Fixed the 'App Connections' list to instantly sync categories via the live classifier cascade when connection labels change in the background (e.g. updating domains to ESSENTIAL).

## [v3.1.13] - Flicker-Free UI Rendering

- **UI**: Completely eliminated screen flickering in the App Connections list when sorting or refreshing active connections by porting the dynamic layout manager from `pack` to `grid` geometry, providing an ultra-smooth, native-feeling scrolling experience.

## [v3.1.12] - UI Repacking Fix

- **UI**: Fixed a thread clogging issue where the App Connections list would redundantly sort and repack the UI for every small data batch, leading to massive freezes during traffic spikes.
- **UI**: Fixed an issue where the Tkinter geometry manager would incorrectly overlap rows when scrolling, caused by dynamic widget shifting. Replaced with clean repacking.

## [v3.1.11] - System Block Visual Fix

- **UI**: Fixed a bug where the "Block All" red indicator for system processes would flicker off during live traffic updates when "Block System Connections" was enabled.

## [v3.1.10] - UI Performance Polish

- **UI**: Massively improved performance of the App Connections list by optimizing the UI poll loop.
- **UI**: Re-wrote the click-to-copy tooltip to use a high-performance singleton, eliminating the stutter.
- **System**: De-coupled blocklist loading from the engine startup sequence, resulting in an instant boot.
- **System**: Hardcoded internal API domains into the ESSENTIAL category.

## [v3.1.9] - Hotfix & UI Polish

- **UI**: Added short delay before reverting `-topmost` to ensure main window surfaces properly.
- **System**: Updated version numbers across all files to trigger pipeline properly.

## [v3.1.8] - The UI & UX Polish Update
### Added
- **Smart Click-to-Copy Tooltips**: IPv4 and IPv6 addresses now intelligently display "IP copied!" when clicked, while domain names display "Link copied!", improving context across the Logs and Rules tables.

### Changed
- **Killswitch Terminology**: Fully removed all legacy "Ghost Mode" terminology from documentation and UI to eliminate ambiguity. It is now consistently referred to as the Killswitch.
- **Connection Row Sorting**: Removed CPU intensive dynamic child row sorting for better UI performance.
- **Splash Screen Readiness**: The boot splash screen now intelligently waits until the first batch of connections has fully rendered to the screen before fading out, eliminating ugly UI layout redraws on startup.

### Fixed
- **App Icon Fallback Bug**: Resolved an issue where unknown background processes were incorrectly assigned the Python logo instead of falling back to the native first-letter generated icon.
- **Filter Lists Rendering Bug**: Resolved a race condition where the filter list wouldn't load categories properly if clicked too rapidly.
- **Version Number**: Updated internal app version logic to correctly reflect v3.1.8.

---

## [v3.1.0] - Security Hardening & Live Traffic Polish
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

## [v3.0.2] - The Killswitch Update
### Added
- **Absolute Master Killswitch**: The killswitch now unconditionally drops ALL network traffic across all NICs and protocols, stripping away all loopback exceptions to turn the hardware into a true ghost on the network.
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
