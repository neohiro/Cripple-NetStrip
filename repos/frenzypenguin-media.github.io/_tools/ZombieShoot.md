---
title: ZombieShoot
tagline: "Top-down zombie shooter — procedural levels, permadeath, moddable (Windows/Linux)"
platform: Windows / Linux
language: Python (PyGame) / C++
category: Games
repo_url: https://github.com/neohiro/ZombieShoot
featured: false
weight: 17
icon: |
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <circle cx="12" cy="8" r="4"/>
    <path d="M12 12v8M8 16l4-4 4 4M8 20h8"/>
    <path d="M10 7h4M10 7l1 3h2M14 7l-1 3h-2" stroke="var(--red)" stroke-width="2"/>
  </svg>
---
**ZombieShoot** is a retro-styled top-down shooter with procedural generation, permadeath, and deep modding support.

## Features

- **Procedural Levels** — Infinite city blocks, sewers, malls, forests
- **Permadeath** — One life; death = new run (legacy items unlock)
- **Weapon Crafting** — Combine parts: barrel + stock + receiver + mod
- **Enemy Types** — 20+ zombie variants with unique behaviors
- **Mod Support** — JSON data files for weapons, enemies, levels, items
- **Replay System** — Full run recording with ghost playback
- **Local Co-op** — 2-player split-screen (keyboard + gamepad)

## Installation

### Windows
Download `ZombieShoot-Setup.exe` from [Releases](https://github.com/neohiro/ZombieShoot/releases)

### Linux
```bash
# Flatpak
flatpak install flathub io.github.neohiro.ZombieShoot

# AppImage
wget https://github.com/neohiro/ZombieShoot/releases/latest/download/ZombieShoot.AppImage
chmod +x ZombieShoot.AppImage
./ZombieShoot.AppImage

# Arch/AUR
yay -S zombieshoot-git
```

## Controls

| Action | Keyboard | Gamepad |
|--------|----------|---------|
| Move | WASD | Left Stick |
| Aim | Mouse | Right Stick |
| Shoot | LMB / Space | RT / A |
| Reload | R | RB / X |
| Switch Weapon | 1-4 / Scroll | D-Pad |
| Interact | E | Y / Triangle |
| Map | M | View / Touchpad |

## Modding

Create `mods/my_mod/` with:

```
mods/my_mod/
├── mod.json           # Metadata, dependencies
├── weapons/
│   └── railgun.json   # New weapon definition
├── enemies/
│   └── boss_tyrant.json
├── levels/
│   └── military_base.json
└── items/
    └── stimpack.json
```

Load via Main Menu → Mods → Enable.

## Legacy System

Complete runs to unlock:
- **Starting weapons** — Pistol, SMG, Shotgun variants
- **Perks** — Faster reload, more health, ammo finder
- **Cosmetics** — Character skins, weapon skins, UI themes
- **Difficulty modifiers** — Hardcore, speedrun, pacifist modes

## Requirements

- Python 3.10+ (bundled in releases)
- PyGame 2.5+ / SDL2
- OpenGL 3.3+ (for shaders)
- 2 GB RAM minimum

## Related

- [TristarMania](https://github.com/neohiro/TristarMania) — Space shooter
- [GhostMaze](https://github.com/neohiro/GhostMaze) — 2D RPG