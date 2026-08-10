---
title: ubuntu
tagline: "Ubuntu post-install hardening — firewall, encrypted DNS, Tor, AppArmor, snap/flatpak control, GNOME privacy"
platform: Ubuntu 20.04 / 22.04 / 24.04
language: Shell / Python
category: Security Guides
repo_url: https://github.com/neohiro/ubuntu
featured: false
weight: 11
icon: |
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <circle cx="12" cy="12" r="10"/>
    <path d="M12 6v6l4 2" stroke="var(--orange)" stroke-width="2"/>
    <circle cx="12" cy="12" r="4" stroke="var(--orange)" stroke-width="1.5" opacity="0.5"/>
  </svg>
---
**ubuntu** provides Ubuntu-specific hardening with a guided TUI installer and optional GNOME desktop privacy settings.

## Features

- **Guided Installer** — Interactive TUI walks through profile selection
- **Profiles** — `minimal` (server), `desktop` (workstation), `paranoid` (max security)
- **GNOME Privacy** — Telemetry, location, usage stats, crash reports disabled
- **Snap/Flatpak Control** — Disable auto-refresh, remove telemetry snaps
- **AppArmor** — Enforce profiles for Firefox, Thunderbird, containers
- **Encrypted DNS** — systemd-resolved + DNSCrypt-proxy integration
- **Automatic Updates** — Unattended-upgrades with security-only option

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/neohiro/ubuntu/main/install.sh | sudo bash
```

## Profiles

| Profile | Target | Includes |
|---------|--------|----------|
| `minimal` | Servers, containers | Firewall, SSH, auditd, sysctl, auto-updates |
| `desktop` | Workstations | Minimal + GNOME privacy, encrypted DNS, AppArmor |
| `paranoid` | High-security | Desktop + Tor, MAC randomization, kernel lockdown |

## Post-Install

Run `ubuntu-hardening --verify` to audit current state.
Run `ubuntu-hardening --rollback` to revert last changes.

## Related

- [linux](https://github.com/neohiro/linux) — Cross-distro version
- [windows](https://github.com/neohiro/windows) — Windows equivalent