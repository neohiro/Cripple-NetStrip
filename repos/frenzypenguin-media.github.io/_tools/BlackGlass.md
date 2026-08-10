---
title: BlackGlass
tagline: "Multi-client chat viewer for Second Life — unified IM, local chat, group chat with history search"
platform: Windows / Linux / macOS
language: Python (PySide6/Qt)
category: Communication
repo_url: https://github.com/neohiro/BlackGlass
featured: false
weight: 14
icon: |
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z"/>
    <path d="M8 10h8M8 14h5" stroke="var(--purple)" stroke-width="2"/>
  </svg>
---
**BlackGlass** consolidates all your Second Life conversations into a single, searchable desktop client.

## Features

- **Unified Inbox** — IMs, local chat, group chat, notices in one timeline
- **History Search** — Full-text search across all conversations with date filters
- **Multi-Account** — Simultaneous login for multiple avatars
- **Offline Messages** — Queued delivery when recipients come online
- **Chat Logs** — Automatic JSON/CSV export with privacy controls
- **Notifications** — Native desktop notifications with avatar preview
- **Themes** — Dark/light/auto with custom accent colors

## Installation

### Windows
Download `BlackGlass-Setup.exe` from [Releases](https://github.com/neohiro/BlackGlass/releases)

### Linux
```bash
# Flatpak
flatpak install flathub io.github.neohiro.BlackGlass

# AppImage
wget https://github.com/neohiro/BlackGlass/releases/latest/download/BlackGlass.AppImage
chmod +x BlackGlass.AppImage
./BlackGlass.AppImage
```

### macOS
```bash
brew install --cask blackglass
```

## Requirements

- Second Life account (or OpenSim-compatible grid)
- Python 3.10+ with PySide6 (bundled in releases)
- libomv (OpenMetaverse) — bundled

## Protocol Support

- **Second Life** — Full support including mesh, materials, animesh
- **OpenSim** — Partial (core chat/IM works; region features vary)
- **Third-party grids** — Configurable login URI

## Privacy

- **Local-only storage** — No cloud sync; chat logs never leave your machine
- **Encrypted logs** — Optional AES-256 encryption for exported logs
- **No telemetry** — Zero usage tracking

## Related

- [SecondLifePrivate](https://github.com/neohiro/SecondLifePrivate) — Private LSL snippets