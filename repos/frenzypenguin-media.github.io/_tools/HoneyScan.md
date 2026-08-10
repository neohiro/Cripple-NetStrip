---
title: HoneyScan
tagline: "Passive honeypot for home networks — detects scans, brute-force, IoT malware with zero config"
platform: Linux (Raspberry Pi, VM, bare metal)
language: Python / Shell
category: Network Security
repo_url: https://github.com/neohiro/HoneyScan
featured: false
weight: 15
icon: |
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="var(--orange)" stroke-width="2"/>
    <circle cx="12" cy="12" r="4" stroke="var(--orange)" stroke-width="2"/>
    <path d="M12 8v4M12 16h.01" stroke="var(--orange)" stroke-width="2"/>
  </svg>
---
**HoneyScan** runs silently on your network, pretending to be vulnerable devices to detect and log attack attempts.

## Features

- **Service Emulation** — SSH, Telnet, HTTP, HTTPS, RDP, SMB, MQTT, CoAP, Modbus
- **Credential Capture** — Logs usernames/passwords from brute-force attempts (hashed)
- **IoT Malware Detection** — Identifies Mirai, Gafgyt, Hajime, Mozi variants
- **Network Mapping** — Discovers scanning hosts, builds attack timeline
- **Zero Config** — Auto-detects subnet, picks unused IPs, starts emulating
- **Alerting** — Email, webhook, syslog, Matrix, Discord notifications
- **Dashboard** — Web UI with attack map, top attackers, service stats

## Quick Start

```bash
# Docker (recommended)
docker run -d --net=host --cap-add=NET_ADMIN \
  -v honeypot-data:/data \
  ghcr.io/neohiro/honeypot:latest

# Bare metal / VM
curl -fsSL https://raw.githubusercontent.com/neohiro/HoneyScan/main/install.sh | sudo bash
```

## Emulated Services

| Service | Port | Variants |
|---------|------|----------|
| SSH | 22 | OpenSSH, Dropbear, BusyBox |
| Telnet | 23 | BusyBox, Cisco, Huawei |
| HTTP | 80 | nginx, Apache, lighttpd, GoAhead |
| HTTPS | 443 | Self-signed certs, common CNs |
| RDP | 3389 | Windows 7/10/Server |
| SMB | 445 | Samba, Windows 10 |
| MQTT | 1883 | Mosquitto, EMQX |
| CoAP | 5683 | libcoap, Californium |

## Deployment

| Platform | Method |
|----------|--------|
| Raspberry Pi | `docker run` or bare metal install |
| VM (Proxmox, ESXi, Hyper-V) | Docker or ISO |
| Old laptop | `install.sh` |
| Cloud VPS | Docker Compose |

## Alerting

```yaml
# config/alerts.yaml
webhooks:
  - url: "https://discord.com/api/webhooks/..."
    events: ["login_attempt", "malware_detected", "new_scanner"]
email:
  smtp: "smtp.gmail.com:587"
  to: "security@yourdomain.com"
matrix:
  homeserver: "https://matrix.org"
  room: "!roomid:matrix.org"
```

## Data Retention

- Attack logs: 90 days (configurable)
- Captured credentials: 30 days (auto-hashed)
- PCAP captures: 7 days (optional)

## Privacy

- **No phone home** — All data stays on your device
- **No external deps** — Runs fully offline after install
- **GDPR-ready** — No personal data collected

## Related

- [Cripple-NetStrip](https://github.com/neohiro/Cripple-NetStrip) — Active network hardening
- [LANScan](https://github.com/neohiro/LANScan) — Active network scanner