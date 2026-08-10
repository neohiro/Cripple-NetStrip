---
title: dnscrypt-proxy-gui
tagline: "Cross-platform GUI for dnscrypt-proxy — encrypted DNS management made simple"
platform: Windows / Linux / macOS
language: Python (PySide6/Qt)
category: Privacy Tools
repo_url: https://github.com/neohiro/dnscrypt-proxy-gui
featured: false
weight: 13
icon: |
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <circle cx="12" cy="12" r="10"/>
    <path d="M12 6v6l4 2" stroke="var(--blue)" stroke-width="2"/>
    <path d="M8 18h8" stroke="var(--blue)" stroke-width="2"/>
    <path d="M12 14v4" stroke="var(--blue)" stroke-width="2"/>
  </svg>
---
**dnscrypt-proxy-gui** provides a clean, native desktop interface for managing dnscrypt-proxy — no config file editing required.

## Features

- **Visual Server List** — Browse, filter, and select from 100+ public DoH/DoT servers
- **Real-time Latency** — Live ping measurements with color-coded health
- **Profile Management** — Save/switch between Home, Work, Travel, Custom profiles
- **System Integration** — One-click system DNS update (requires admin/root)
- **Log Viewer** — Live query log with filtering by domain, type, status
- **Auto-update** — Server list refreshes weekly; binary auto-updates

## Screenshots

**Not published yet.** The three screenshots this page used to show
(`dnscrypt-proxy-gui-main.png`, `-servers.png`, `-log.png`) were referenced but
never committed, so every visitor got three broken images. Rather than ship that,
or invent a stand-in that would look finished, the section says so.

If you are the maintainer: drop the three PNGs into
`_tools/assets/dnscrypt-proxy-gui/` and restore the table with paths relative to
the rendered page (`../../assets/dnscrypt-proxy-gui/main.png` and siblings, or
absolute `/assets/...` if you move them to the site-wide `assets/` tree).
Verify with the link checker in
`template-shared/tests/` before calling it done.

## Installation

### Windows
Download `dnscrypt-proxy-gui-setup.exe` from [Releases](https://github.com/neohiro/dnscrypt-proxy-gui/releases)

### Linux
```bash
# Flatpak (recommended)
flatpak install flathub io.github.neohiro.dnscrypt-proxy-gui

# AppImage
wget https://github.com/neohiro/dnscrypt-proxy-gui/releases/latest/download/dnscrypt-proxy-gui.AppImage
chmod +x dnscrypt-proxy-gui.AppImage
./dnscrypt-proxy-gui.AppImage
```

### macOS
```bash
brew install --cask dnscrypt-proxy-gui
```

## Requirements

- dnscrypt-proxy 2.1+ installed and in PATH
- Python 3.10+ with PySide6 (bundled in releases)

## Configuration

Settings stored in `~/.config/dnscrypt-proxy-gui/settings.json`:

```json
{
  "dnscrypt_proxy_path": "/usr/local/bin/dnscrypt-proxy",
  "auto_start": true,
  "default_profile": "home",
  "doh_port": 53000,
  "log_level": "info"
}
```

## Related

- [dnscrypt-proxy](https://github.com/DNSCrypt/dnscrypt-proxy) — Core daemon
- [Cripple-NetStrip](https://github.com/neohiro/Cripple-NetStrip) — Network hardening with DNS sinkhole
- [linux](https://github.com/neohiro/linux) — Includes DNSCrypt setup