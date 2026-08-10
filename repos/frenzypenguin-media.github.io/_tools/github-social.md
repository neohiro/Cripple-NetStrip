---
title: GitHub Social
tagline: "Decentralized social layer · GitHub Social overlays · Browser extension · PWA"
platform: Windows / macOS / Linux / Browser
language: JavaScript + Rust
repo_url: https://github.com/frenzypenguin-media/github-social
demo_url: https://frenzypenguin-media.github.io/github-social
docs_url: https://github.com/frenzypenguin-media/github-social/blob/main/README.md
category: Social / Developer Tools
featured: true
weight: 1
icon: |
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-1a3 3 0 0 0-3-3h-1"/>
    <path d="M16 3.13a3 3 0 0 1 3 3v1"/>
  </svg>
---

**GitHub Social** adds a decentralized, immersive social layer to github.com. The browser extension,
PWA, and Tauri desktop app read `GitHubSocial.md` from any GitHub profile and inject
visitor counters, heart reactions, MOTD banners, music autoplay, and comment threads — all styled
to look native to GitHub.

Activate any profile in 30 seconds — the app and extension bootstrap the file automatically.
No server. No tracking. No account required.

**Three ways to use:** [Tauri desktop app](https://github.com/frenzypenguin-media/github-social/releases)
· [PWA (no install)](https://frenzypenguin-media.github.io/github-social)
· [Browser extension](https://github.com/frenzypenguin-media/github-social/tree/main/extension)

---

## Quick install (PWA)

No install needed — visit **[frenzypenguin-media.github.io/github-social](https://frenzypenguin-media.github.io/github-social)** and add to your home screen.

---

## Features

| Feature | Description |
|---------|-------------|
| **Immersive overlays** | Buttons and counters that match github.com's CSS exactly |
| **GitHubSocial.md** | Your profile's social config — theme, music, MOTD, buttons |
| **Journey log** | Every visit and reaction recorded in your own file |
| **Spoof detection** | Integrity checker flags tampered profiles |
| **Music autoplay** | Set a `music_url` in your MD; visitors hear it on arrival |
| **Anonymous metrics** | Weekly SVG dashboards show platform trends |
| **Invite flow** | Detect non-users and send a one-click invite issue |

---

## Architecture

```
GitHubSocial.md (in your profile repo)
        ^
        | read by: extension / PWA / Tauri app
        |
  ┌─────┴──────────────────────────────┐
  │  github.com/{login}/GitHubSocial.md  │
  │  (public, no auth needed to read)     │
  └─────────────────────────────────────┘
        ^
        | two write paths:
        |  1. Your own file (journey log + counters) via gh CLI or REST
        |  2. Other users' files (PR-style reactions, invites)
        |     → opens a GitHub issue on their profile repo
        |     (issue is the reaction; ToS-safe; nothing written silently)
```
