---
title: Tetris
tagline: "Classic Tetris — guideline-compliant, T-spin detection, replay system, vs AI"
platform: Windows / Linux / macOS / Web
language: Rust (macroquad) / TypeScript
category: Games
repo_url: https://github.com/neohiro/Tetris
featured: false
weight: 19
icon: |
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <rect x="3" y="3" width="18" height="18" rx="2"/>
    <path d="M7 7h10v4H7z" fill="currentColor" stroke="none"/>
    <path d="M9 11h6M9 15h6" stroke="#0b0e12" stroke-width="2"/>
  </svg>
---
**Tetris** is a faithful, guideline-compliant implementation with modern features: T-spins, 7-bag randomizer, replay analysis, and AI opponent.

## Features

- **Guideline Compliant** — SRS rotation, 7-bag randomizer, hold, ghost piece, 3+ next
- **T-Spin Detection** — Mini, regular, double, triple with bonus scoring
- **Replay System** — Full input recording; frame-perfect playback; export .tetris-replay
- **AI Opponent** — Configurable difficulty (beginner to TGM master); learns from your play
- **Multiplayer** — Local VS, LAN, online (WebRTC); spectator mode
- **Web Version** — Play instantly at [tetris.neohiro.dev](https://tetris.neohiro.dev)
- **Statistics** — APM, PPS, VS%, survival time, T-spin rate, B2B chains

## Play Now

**Web:** [tetris.neohiro.dev](https://tetris.neohiro.dev) (WASM)

**Desktop:**
- Windows: `Tetris-Setup.exe` from [Releases](https://github.com/neohiro/Tetris/releases)
- Linux: Flatpak / AppImage / `cargo install tetris-neo`
- macOS: `brew install --cask tetris-neo`

## Scoring (Guideline)

| Action | Points |
|--------|--------|
| Single | 100 × level |
| Double | 300 × level |
| Triple | 500 × level |
| Tetris | 800 × level |
| T-Spin Mini | 100 × level |
| T-Spin | 400 × level |
| T-Spin Double | 1200 × level |
| T-Spin Triple | 1600 × level |
| Back-to-Back | ×1.5 |
| Perfect Clear | 2000 × level (single), 3600 (Tetris) |

## Modes

| Mode | Description |
|------|-------------|
| Marathon | 150 lines; variable goal |
| Sprint | 40 lines; fastest time |
| Ultra | 3 minutes; max score |
| Master | TGM-style; invisible, 20G |
| VS AI | 1v1 against configurable bot |
| VS Human | LAN / WebRTC / local |

## Controls

| Action | Keyboard | Gamepad |
|--------|----------|---------|
| Move | ←/→ | D-Pad / Left Stick |
| Soft Drop | ↓ | Down / A |
| Hard Drop | Space / ↑ | Up / Y |
| Rotate CW | Z / X | LB / RB |
| Rotate CCW | Shift / C | LT / RT |
| 180° | A | Back / Select |
| Hold | C / Ctrl | Left Stick Press |

## Replay Format

`.tetris-replay` is JSON with:
```json
{
  "version": 1,
  "seed": 1234567890,
  "mode": "marathon",
  "inputs": [
    {"frame": 0, "input": "right"},
    {"frame": 3, "input": "rotate_cw"}
  ],
  "stats": {"apm": 62.4, "pps": 1.8, "tspin_rate": 0.23}
}
```

## Requirements

- **Desktop:** OpenGL 3.3+; 512 MB RAM
- **Web:** WebGL 2; 1 GB RAM
- **Binary size:** ~3 MB (compressed)

## Related

- [TristarMania](https://github.com/neohiro/TristarMania) — Space shooter
- [GhostMaze](https://github.com/neohiro/GhostMaze) — 2D RPG