# FrenzyPenguin Media

> Security hardening deep-dives, exploit mitigation tutorials, and privacy engineering.

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![ Jekyll](https://img.shields.io/badge/Jekyll-4.4-blueviolet.svg)](https://jekyllrb.com/)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-frenzypenguin.media-brightgreen)](https://frenzypenguin.media)

**FrenzyPenguin Media** is the indie media and creative arm of the neohiro network.
We produce video deep-dives on security hardening, exploit mitigation, and privacy
engineering for Windows and Linux.

**Live site:** [frenzypenguin.media](https://frenzypenguin.media)

---

## What we publish

- Video tutorials on Windows STIG-style hardening
- Deep-dives into exploit protection settings (ASR, CFG, DEP, SEHOP)
- DNS privacy engineering (dnscrypt-proxy, encrypted DNS, sinkholes)
- Network defense tooling walkthroughs
- Privacy engineering case studies

**Subscribe:** [YouTube @FrenzyPenguinMedia](https://www.youtube.com/FrenzyPenguinMedia?sub_confirmation=1)

---

## Related repositories

This repo is the **content source** for the FrenzyPenguin Media GitHub Pages site.
The actual tools live in the [neohiro](https://github.com/neohiro) organization:

| Tool | Repo | Description |
|------|------|-------------|
| ExploitProtection | [neohiro/ExploitProtection](https://github.com/neohiro/ExploitProtection) | Windows Exploit Protection GUI |
| dnscrypt-proxy-gui | [neohiro/dnscrypt-proxy-gui](https://github.com/neohiro/dnscrypt-proxy-gui) | Encrypted DNS GUI |
| Cripple-NetStrip | [neohiro/Cripple-NetStrip](https://github.com/neohiro/Cripple-NetStrip) | DNS sinkhole + firewall |
| Windows Hardening | [neohiro/windows](https://github.com/neohiro/windows) | STIG-style Windows hardening |
| Linux Hardening | [neohiro/linux](https://github.com/neohiro/linux) | Post-install Linux hardening |

---

## Host directory

Every subdomain in the `frenzypenguin.media` DNS zone has a page here, plus a
grouped directory that says which of them actually answer.

| Path | What it is |
|------|------------|
| [`/hosts/`](https://frenzypenguin-media.github.io/hosts/) | All 34 records, grouped by category, deadest first |
| [`/artists/`](https://frenzypenguin-media.github.io/artists/) | The artist roster |
| `/<slug>/` | One page per host, for every host in the zone |
| `/artists/<slug>/` | Canonical page for an artist record |
| Hosts menu | The navbar dropdown, one row per host with a live/dead dot |

### `_data/hosts.yml` is the single source of truth

Adding a host to the zone is a data edit. One record, and the directory, the
per-host pages, the navbar menu and the status report all follow.

```yaml
- slug: kennethgame
  title: Kenneth Game
  owner: FrenzyPenguin Media - artist roster
  symbol: <emoji>
  category: artists
  type: url
  url: https://...          # the address a visitor should use
  source: https://...       # the address as the zone records it, even if broken
  status: ok                # ok | guarded | down | broken-dns
  checked: 2026-10-04
  raw: host/path            # the literal string, for the copyable raw link
  blurb: One line.
  intro: A paragraph, personalised per host.
  artist:                   # artist-category records only
    bpm: 124-128
    genres: [Deep house, Hypnotic]
    style: Warm, rolling, patient.
```

`status` is a four-value scale, and the distinction between the two middle values
is the whole point of it:

| Value | Meaning |
|-------|---------|
| `ok` | Answered a plain `GET` with a browser user agent |
| `guarded` | Reachable, but a bot wall (403/429/400/999) answered instead. Unverified, **not** broken |
| `down` | No answer: connection refused, port closed, or 404 |
| `broken-dns` | The name resolves but nothing will serve it. The fix is a certificate or a CNAME, not a restarted service |

A bot wall is never reported as a dead link. `guarded` renders in the live colour
in the UI because a human in a browser gets through, and colouring it red would be
a lie.

### Scripts

```bash
# Probe every address in the zone. Writes scripts/hostcheck.csv.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-hosts.ps1

# Regenerate the 44 generated pages from _data/hosts.yml.
python scripts/build_host_pages.py

# Fail if any generated page is missing or stale, without writing.
python scripts/build_host_pages.py --check

# Delete generated pages whose record has gone away.
python scripts/build_host_pages.py --clean

# Verify a built _site. Run after `jekyll build`.
python scripts/check_host_pages.py
```

`check_host_pages.py` is the one that matters in CI. It exists because three
different defects in this directory all rendered without looking wrong:

- a modifier class with no matching CSS rule, so the eight most broken records
  rendered as healthy (a class named `broken-dns` where the stylesheet knew
  `broken`)
- an `aria-controls` pointing at an id that did not exist
- an off-site link that also carried the swirl opener's data attribute, so it
  opened a card instead of navigating

None of those throw. All three are silent, and all three are now assertions.

### The swirl-open card

Each host is a small disc that swirls open into a frame carrying the raw link,
the probe result, and a bio frame with deliberately empty labelled slots. The
slots are meant to stay empty: an honest blank is more useful than a placeholder
sentence, because a placeholder looks finished. See `assets/css/hosts.css` and
`assets/js/hosts.js`; the state contract is documented at the top of both.

The card works without JavaScript - the source disc is a real `<button>` with a
real `aria-expanded`, and a `#fragment` opens any card by name - and it stops
animating under `prefers-reduced-motion`.

### Two Liquid traps this directory hit

Both are now written into the files that contain them, because both fail
silently:

1. `{% for x in some_hash %}` yields `[key, value]` **pairs**, not keys. Binding
   the pair straight into `where` compares a String to an Array, matches
   nothing, and stringifies the whole pair into your `id=` attributes.
2. `| where_exp: "x", "a and b"` is **not** an AND. Liquid rejects `and` there, so
   the condition is truthy for every element and the filter returns its input
   unchanged. Chain two single-comparison filters instead.

### Known zone defect

`www.frenzypenguin.media` is a CNAME to `frenzypenguin-media.github.io`, and
GitHub Pages does not issue a certificate for a `www` host. The apex
`https://frenzypenguin.media` works and has one. That single missing certificate
is why **eight** records in this directory are `broken-dns` rather than live: the
`contact`, `disclaimer`, `technical`, `gaming`, `openpgp`, `kennethgame`,
`professorbenji` and `ravebeacon` pages all hang off `www`. Adding a `www` CNAME
in the DNS zone, or repointing those records at the apex, fixes all eight at
once.

## Repository structure

```
frenzypenguin-media/
├── _tools/          # Tool descriptions for the Jekyll catalog
├── _includes/       # Shared Jekyll includes (badges, contact cards)
├── _layouts/        # Page layouts
├── _config.yml      # Jekyll configuration
├── assets/          # CSS, JS, images
├── github-social/   # GitHub card graphics
├── heartbeats/      # Heart cadence signals (live counter data)
├── index.md         # Homepage source
├── media.md         # Video portfolio page
└── repositories.md  # Full tools catalog page
```

---

## Contributing

Found a security hardening technique we missed? Have a tool to submit?

1. Open an issue with your suggestion or proposed addition
2. For tool additions, include: name, tagline, repo URL, platform, language
3. For content corrections, be specific and include sources

For security vulnerabilities, see [SECURITY.md](SECURITY.md) for private disclosure.

---

## Sister sites

- [neohiro](https://neohiro.github.io) — Security hardening & privacy tools
- [transhumanists](https://transhumanists.github.io) — Transhumanism & human enhancement
- [openstageisland](https://openstageis.land) — Second Life music venue

---

## License

GPL-3.0 — see [LICENSE](LICENSE) and [SECURITY.md](SECURITY.md).
