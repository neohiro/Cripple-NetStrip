---
title: linux
tagline: "Cross-distro Linux hardening guide — UFW firewall, DNSCrypt, Tor routing, fail2ban, AppArmor/SELinux, sysctl, SSH hardening"
platform: Linux (Debian/Ubuntu/RHEL/Fedora/SUSE/Arch/Manjaro)
language: Shell / Bash
category: Security Guides
repo_url: https://github.com/neohiro/linux
featured: false
weight: 10
icon: |
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <path d="M12 2l10 7v10l-10 7-10-7v-10l10-7z"/>
    <path d="M2 12h20M12 2v20"/>
    <circle cx="12" cy="12" r="3" stroke="var(--green)" stroke-width="2"/>
  </svg>
---
**linux** is a comprehensive, distro-agnostic Linux hardening guide that auto-detects your distribution and applies appropriate security configurations.

## Features

- **Auto-detection** — Identifies Debian/Ubuntu, RHEL/Fedora, SUSE, Arch/Manjaro automatically
- **Firewall** — UFW with default-deny incoming, allow outgoing; IPv6 support
- **Encrypted DNS** — DNSCrypt-proxy with DoH/DoT support, automatic fallback
- **Tor Routing** — Optional transparent Tor proxy for all traffic
- **Intrusion Prevention** — fail2ban with SSH, HTTP, mail jail configs
- **Mandatory Access Control** — AppArmor (Debian/Ubuntu) or SELinux (RHEL/Fedora) profiles
- **Kernel Hardening** — sysctl.conf with network, memory, and filesystem protections
- **SSH Hardening** — Key-only auth, port randomization, connection rate limiting

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/neohiro/linux/main/linuxinstall.sh | sudo bash -s --
```

Or clone and run locally:

```bash
git clone https://github.com/neohiro/linux.git
cd linux
sudo ./linuxinstall.sh
```

## Modules

| Module | Description |
|--------|-------------|
| `firewall` | UFW ruleset with geo-IP blocking option |
| `dnscrypt` | DNSCrypt-proxy with multiple upstream providers |
| `tor` | Transparent Tor proxy (optional) |
| `fail2ban` | SSH, HTTP, SMTP, IMAP jails |
| `apparmor` / `selinux` | MAC profiles for common services |
| `sysctl` | Network stack, VM, filesystem hardening |
| `ssh` | Key auth, port knocking, MFA support |
| `audit` | auditd rules for security-relevant events |

## Requirements

- Root/sudo access
- systemd-based distribution
- Internet access for package installation

## Customization

Edit `config.local` before running to:
- Skip modules (`SKIP_MODULES="tor fail2ban"`)
- Custom firewall rules (`CUSTOM_UFW_RULES=...`)
- DNSCrypt provider selection
- SSH port and key settings

## Related

- [ubuntu](https://github.com/neohiro/ubuntu) — Ubuntu-specific hardening with GUI options
- [windows](https://github.com/neohiro/windows) — Windows equivalent
- [Cripple-NetStrip](https://github.com/neohiro/Cripple-NetStrip) — Network-level hardening