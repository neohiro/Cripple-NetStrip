---
title: TristarMania
tagline: "Addictive space shooter — procedural waves, ship customization, online leaderboards"
platform: Windows / Linux / macOS
language: Rust (Bevy) / WebAssembly
category: Games
repo_url: https://github.com/neohiro/TristarMania
featured: false
weight: 18
icon: |
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <polygon points="12 2 15 12 12 22 9 22 6 12"/>
    <path d="M12 6v10M9 14h6" stroke="var(--orange)" stroke-width="2"/>
  </svg>
---
**TristarMania** is a fast-paced space shooter with procedural enemy waves, deep ship building, and global leaderboards.

## Features

- **Procedural Waves** — Infinite combinations of formations, bosses, environmental hazards
- **Ship Builder** — Modular hulls, engines, weapons, shields, utilities; 10,000+ combinations
- **Roguelite Progression** — Per-run upgrades; meta-currency unlocks hulls, weapons, cosmetics
- **Online Leaderboards** — Daily/weekly/all-time with replay verification
- **Web Version** — Play instantly in browser via WebAssembly
- **Replay System** — Watch top runs; learn patterns and strategies
- **Accessibility** — Colorblind modes, screen reader support, one-handed mode

## Play Now

**Web:** [tristarmania.neohiro.dev](https://tristarmania.neohiro.dev) (WASM)

**Desktop:**
- Windows: `TristarMania-Setup.exe` from [Releases](https://github.com/neohiro/TristarMania/releases)
- Linux: Flatpak / AppImage / `cargo install tristarmania`
- macOS: `brew install --cask tristarmania`

## Ship Building

```
Hull (frame) → Engine → Weapon × N → Shield → Utility
```

| Slot | Options |
|------|---------|
| Hull | Interceptor, Fighter, Bomber, Carrier, Capital |
| Engine | Ion, Plasma, Warp, Quantum, Stealth |
| Weapon | Laser, Railgun, Missile, Flak, Beam, Torpedo |
| Shield | Bubble, Reactive, Adaptive, Phase, Ablative |
| Utility | Repair, Jammer, Scanner, Decoy, Mine Layer |

## Leaderboards

| Board | Reset | Verification |
|-------|-------|--------------|
| Daily | 00:00 UTC | Server-side replay check |
| Weekly | Monday 00:00 | Top 100 replay review |
| All-Time | Never | Cryptographic proof |

## Tech Stack

- **Engine:** Bevy 0.14 (ECS, parallel scheduling)
- **Graphics:** wgpu (Vulkan/Metal/DX12/WebGPU)
- **Audio:** Kira (spatial, dynamic music)
- **Networking:** gRPC + QUIC for leaderboards
- **WASM:** wasm-bindgen, web-sys, wasm-pack

## Requirements

- **Desktop:** Vulkan 1.2+ / Metal / DX12; 4 GB RAM
- **Web:** WebGPU or WebGL 2; 8 GB RAM; Chrome/Edge/Firefox/Safari
- **Mobile:** Not officially supported (touch controls WIP)

## Related

- [ZombieShoot](https://github.com/neohiro/ZombieShoot) — Top-down shooter
- [Tetris](https://github.com/neohiro/Tetris) — Classic puzzle