---
title: SystemMonitor
tagline: "Live system health on your desktop — CPU, RAM, disk, network, GPU, sensors with alerts"
platform: Windows / Linux
language: Python (PySide6/Qt) / C++
category: System Utilities
repo_url: https://github.com/neohiro/SystemMonitor
featured: true
weight: 7
icon: |
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <rect x="3" y="3" width="18" height="18" rx="2"/>
    <path d="M9 17v-5M13 17v-9M17 17v-3" stroke="var(--cyan)" stroke-width="2" stroke-linecap="round"/>
  </svg>
---
**SystemMonitor** is a lightweight, always-on-top desktop widget showing real-time system metrics with customizable alerts.

## Features

- **Always-on-Top Widget** — Semi-transparent, click-through optional, multi-monitor
- **Metric Panels** — CPU (per-core), RAM, Disk I/O, Network, GPU, Temperatures, Fans
- **History Graphs** — 1h/6h/24h sparklines for each metric
- **Alert Rules** — "CPU > 90% for 5m → notify", "Disk < 5GB → warn"
- **Notification Channels** — Desktop, sound, webhook, email, Matrix
- **Remote Monitoring** — View metrics from phone via web UI (optional)
- **Process Top** — Click panel to see top consumers for that resource

## Installation

### Windows
Download `SystemMonitor-Setup.exe` from [Releases](https://github.com/neohiro/SystemMonitor/releases)

### Linux
```bash
# Flatpak
flatpak install flathub io.github.neohiro.SystemMonitor

# AppImage
wget https://github.com/neohiro/SystemMonitor/releases/latest/download/SystemMonitor.AppImage
chmod +x SystemMonitor.AppImage
./SystemMonitor.AppImage

# Arch/AUR
yay -S systemmonitor-git
```

## Configuration

Right-click widget → Settings, or edit `~/.config/SystemMonitor/config.yaml`:

```yaml
widget:
  position: "top-right"
  opacity: 0.85
  click_through: false
  width: 280
  theme: "auto"  # dark, light, auto

panels:
  - cpu: { enabled: true, per_core: true, graph_hours: 6 }
  - memory: { enabled: true, show_swap: true, graph_hours: 6 }
  - disk: { enabled: true, mounts: ["/", "/home"], graph_hours: 24 }
  - network: { enabled: true, interfaces: ["auto"], graph_hours: 6 }
  - gpu: { enabled: true, vendor: "auto", graph_hours: 6 }
  - sensors: { enabled: true, show_fans: true }

alerts:
  - name: "High CPU"
    metric: "cpu.total"
    condition: "> 90%"
    duration: "5m"
    channels: ["desktop", "sound"]
  - name: "Low Disk"
    metric: "disk.root.free"
    condition: "< 5GB"
    channels: ["desktop", "webhook"]
    webhook_url: "https://..."

remote:
  enabled: false
  port: 8765
  tls: true
  auth_token: "changeme"
```

## Supported Sensors

| Source | Platform | Metrics |
|--------|----------|---------|
| `psutil` | All | CPU, RAM, Disk, Network, Battery |
| `nvidia-smi` | Linux/Windows | GPU temp, memory, utilization, power |
| `rocm-smi` | Linux (AMD) | GPU temp, memory, utilization |
| `lm-sensors` | Linux | CPU/board temps, fan speeds, voltages |
| `WMI` | Windows | CPU temps, fan speeds, SMART |
| `powermetrics` | macOS | CPU/GPU temps, power, thermal pressure |

## Remote Web UI

Enable `remote.enabled: true` to access:
- `https://your-pc:8765` — Full dashboard
- `https://your-pc:8765/api/metrics` — JSON API for custom clients
- `https://your-pc:8765/api/alerts` — Alert history

## Performance

- **Idle CPU** < 0.5% (single core)
- **Memory** ~45 MB base + 5 MB per panel
- **GPU** Zero when panel hidden; ~2% when visible
- **Network** ~1 KB/s for remote UI

## Privacy

- **No telemetry** — Zero data collection
- **Local-only** — Remote UI requires explicit enable + auth
- **No cloud** — All data stays on your machine

## Related

- [windows](https://github.com/neohiro/windows) — Includes system health checks
- [linux](https://github.com/neohiro/linux) — Sensor setup via lm-sensors