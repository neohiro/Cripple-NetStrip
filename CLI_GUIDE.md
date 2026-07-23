# Cripple CLI Guide

Cripple (NetStrip) can be fully managed from the command line interface, making it perfect for headless servers, Raspberry Pis, NUCs, and SSH environments. 

## 1. Boot Variables
These flags are used when starting the `main.py` daemon (or compiled executable).

| Flag | Description |
|---|---|
| `--service` | Boots Cripple silently into the background tray without showing the GUI window. Automatically activates the **Headless Admin Bypass** to keep SSH/VNC access alive. |
| `--blockinbound` | **Overrides the Headless Admin Bypass.** Forces the Strict Inbound Shield to block **ALL** inbound connections, including local subnet/LAN. *Warning: You will lose WAN SSH access if you are remote.* |
| `--allowlan` | Explicitly enables the Headless Admin Bypass, allowing inbound connections from your local subnet (e.g. 192.168.x.x) even if you aren't running as `--service`. |

*Example:* `python main.py --service --blockinbound`

---

## 2. Live Management Commands
You do not need to restart the daemon to manage Cripple! If the daemon is already running (e.g. running in `tmux` or as a system service), you can send IPC commands from a new terminal window to control the live engine.

| Command | Action |
|---|---|
| `python main.py --block <domain>` | Instantly adds the domain to the global blocklist and drops its traffic immediately. |
| `python main.py --allow <domain>` | Instantly adds the domain to the whitelist, overriding any sinkhole blocks. |
| `python main.py --mode <level>` | Changes the live firewall mode. Options: `NORMAL`, `STRICT`, `PARANOID`. |

*Example Live Management Session:*
```bash
# 1. Start the daemon in the background
sudo python main.py --service &

# 2. You notice a tracker getting through. Block it live!
sudo python main.py --block evil-tracker.com

# 3. Elevate the security mode instantly
sudo python main.py --mode PARANOID
```
