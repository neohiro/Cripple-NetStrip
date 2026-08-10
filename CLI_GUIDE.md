# Cripple CLI Guide

Cripple (NetStrip) can be fully managed from the command line, making it perfect for headless servers, Raspberry Pis, NUCs, and SSH environments.

---

## 1. Boot Variables
These flags are used when starting `main.py` (or the compiled executable).

| Flag | Description |
|---|---|
| `--service` | Headless/daemon mode (no GUI). Auto-activates Headless Admin Bypass for SSH/VNC. |
| `--blockinbound` | Block ALL inbound connections including LAN. *Warning: locks out WAN SSH.* |
| `--allowlan` | Permit LAN connections even in strict modes. |
| `--android` | Force Android/Mobile layout for UI testing. |

**Example:** `sudo python main.py --service --blockinbound`

---

## 2. Direct Commands (No Running Daemon Needed)
These commands work by directly accessing the `~/.netstrip/netstrip.db` database. The daemon does not need to be running.

### LAN Shield PSK
| Command | Action |
|---|---|
| `--get-psk` | Display the current LAN Shield Pre-Shared Key. |
| `--set-psk <KEY>` | Set/import a PSK from another Cripple device (validates 44-char Fernet key). |

**Pairing two Cripple devices:**
```bash
# On Device A: get the auto-generated PSK
sudo python main.py --get-psk
# Output: LAN Shield PSK: AbCdEfGhIjKlMnOpQrStUvWxYz0123456789ABCD=

# On Device B: import Device A's PSK
sudo python main.py --set-psk "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789ABCD="
```

### Settings & Profile
| Command | Action |
|---|---|
| `--get <key>` | Read any engine setting from the database. |
| `--set <key> <value>` | Write any engine setting to the database. |
| `--set-telemetry-token <PAT>` | Save a GitHub Personal Access Token for crash telemetry. |
| `--export <file.json>` | Export full settings, rules, and classifications to JSON. |
| `--import <file.json>` | Import a settings profile from JSON (merges with de-duplication). |

**Example: Cloning config to a second device**
```bash
# Export from Device A
sudo python main.py --export ~/netstrip_profile.json

# Copy to Device B (via scp, USB, etc.)
scp ~/netstrip_profile.json user@device-b:~/

# Import on Device B
sudo python main.py --import ~/netstrip_profile.json
```

---

## 3. Live IPC Commands (Sent to Running Daemon)
If the daemon is already running (e.g. in `tmux` or as a systemd service), these commands are sent via IPC to the live engine. No restart needed.

### Domain Rules
| Command | Action |
|---|---|
| `--block <domain>` | Add domain to user blocklist (effective immediately). |
| `--allow <domain>` | Add domain to user allowlist (overrides sinkhole). |

### Firewall Mode
| Command | Action |
|---|---|
| `--mode <LEVEL>` | Switch mode: `LOOSE`, `STANDARD`, `STRICT`, `PARANOID`. |
| `--killswitch` | Engage Master Killswitch — **requires confirmation** (type `YES`). |
| `--unkillswitch` | Disengage Master Killswitch. |
| `--ghost` | Ghost Mode — **requires confirmation** (type `YES`). |
| `--unghost` | Disengage Ghost Mode. |
| `--force` | Skip confirmation prompts (for scripts/automation). |

> **⚠ Warning:** `--killswitch` is the nuclear option — it drops ALL traffic unconditionally, ignores all whitelists, and disables loopback. Recovery requires **physical access** to the machine. `--ghost` is softer: it honors user whitelists/preferences, SSH may survive if explicitly whitelisted, and remote recovery via `--unghost` is still possible. Both prompts default to cancel (just press Enter to abort).

### Monitoring
| Command | Action |
|---|---|
| `--status` | Print daemon status: mode, killswitch, ghost mode, LAN Shield, active threats. |
| `--stats` | Print 24h connection statistics (blocked, allowed, DNS, ads, trackers, malware). |

### Security & Maintenance
| Command | Action |
|---|---|
| `--allow-anomaly <name>` | Whitelist a kernel threat and unlock the system lockdown. |
| `--update-blocklists` | Force an immediate blocklist refresh from upstream sources. |

### WiFi Trust (LAN Shield)
| Command | Action |
|---|---|
| `--trust-wifi <SSID>` | Mark a WiFi network as trusted for LAN Shield broadcasts. |
| `--untrust-wifi <SSID>` | Remove a WiFi network from the trusted list. |

---

## 4. Example Live Management Session

```bash
# 1. Start daemon in background
sudo python main.py --service &

# 2. Check status
sudo python main.py --status

# 3. Block a tracker
sudo python main.py --block evil-tracker.com

# 4. View today's stats
sudo python main.py --stats

# 5. Escalate to Paranoid mode
sudo python main.py --mode PARANOID

# 6. Something went wrong — kill the network
sudo python main.py --killswitch

# 7. Resolved — restore network
sudo python main.py --unkillswitch

# 8. Force refresh blocklists
sudo python main.py --update-blocklists

# 9. Get PSK for pairing another device
sudo python main.py --get-psk
```
