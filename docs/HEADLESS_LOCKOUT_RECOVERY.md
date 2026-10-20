# Headless Self-Lockout — Root Cause, Fix & Node Recovery

**Status:** root-caused and fixed at source; node currently needs out-of-band access.

---

## 1. What happened (verified from source + live logs)

The `node` VPS (`tor.frenzypenguin.media` / `92.119.124.2` / `100.126.213.83`)
became unreachable while `cripple.service` was running in headless Ghost mode.

Live evidence captured immediately before the lockout:

```
[INFO]  Mode changed to: GHOST. Loaded 38 'PARANOID' user rules.
[ERROR] NetStrip.LinuxNFQueue: NetfilterQueue library not found.
[WARN]  LAN Shield deployment failed verification!
[CRIT]  THREAT ESCALATION: {'process_name': 'Kernel Bypass Scanner', ...}
[WARN]  Raw AF_PACKET sockets detected (1 open). Dropping via eBPF.
```

Post-lockout evidence:

```
$ tailscale status
100.126.213.83  node  linux  active; offers exit node; relay "fra", tx 10800 rx 0
                  ^^^^^^^^^ LastWrite fresh, InEngine true, RxBytes exactly 0

$ ssh root@100.126.213.83   ->  Connection timed out
$ ping 92.119.124.2         ->  traceroute reaches provider edge, no port responds
```

`rx 0` with growing `tx` and a fresh `LastWrite` means the node's tailscaled is
alive and **sending**, but **nothing can reach it**.

## 2. Root cause (proven, not inferred)

A false-positive kernel anomaly escalated into a full-network blackhole:

1. `engine._handle_anomaly()` → `engine.trigger_threat_escalation()` (engine.py:211)
2. → `set_mode(GHOST)` + `set_killswitch(True)` (engine.py:193-194)
3. → `LinuxPlatform.enable_killswitch()` (platform/linux.py:166, original):
   ```
   iptables  -I INPUT  1 -j DROP      # unconditional
   iptables  -I OUTPUT 1 -j DROP      # unconditional
   ```
4. **The rules carried no comment**, so `disable_killswitch()` could not reliably
   match them.
5. **The fail-open watchdog was never spawned in headless mode**:
   ```python
   if not getattr(sys, 'frozen', False) and not self.is_headless:   # <-- bug
   ```
6. systemd `Restart=always` relaunched the engine, which re-applied the rules.

Result: a permanent, self-inflicted lockout of every interface — including
Tailscale SSH, the only remote access path.

A second, related fail-open bug was found in the same file:
`disable_ipv4()` inserted a **comment-tagged** rule while `enable_ipv4()` tried to
delete a spec **without** the comment, so it never matched and the host stayed
blackholed after the engine exited.

## 3. Fixes applied (source: `repos/Cripple-NetStrip`)

| # | File | Fix |
|---|------|-----|
| 1 | `netstrip/platform/linux.py` | Killswitch rules are **comment-tagged** (`NetStrip_Killswitch`) and **idempotent**; every rule now excludes loopback **and exempts the Tailscale ranges** (`100.64.0.0/10`, `fd7a:115c:a1e0::/48`) so SSH survives a lockdown. |
| 2 | `netstrip/platform/linux.py` | `disable_killswitch()` now removes tagged rules, **legacy untagged rules**, and management ACCEPTs, in a loop until none remain. |
| 3 | `netstrip/platform/linux.py` | `enable_ipv4()` deletes by the **same comment** `disable_ipv4()` inserts; `disable_ipv4()` also exempts the tailnet. |
| 4 | `netstrip/core/engine.py` | The fail-open **watchdog now spawns in headless mode too**. |
| 5 | `netstrip/core/engine.py` | Headless killswitches **auto-revert after 300 s** (`_schedule_killswitch_autorevert`), so an unattended trip can never be permanent. |
| 6 | `netstrip/watchdog.py` | Crash recovery now also strips killswitch DROP rules and management exemptions. |
| 7 | `netstrip/data/async_database.py` | `SyncDatabaseWrapper` delegates unknown attributes to the sync `Database` (fixes the `get_user_rules` AttributeError that made headless mode crash-loop). |
| 8 | `main.py` | GUI deps (`customtkinter`/`PIL`) are skipped for headless runs; the headless exception is no longer swallowed by `sys.exit(0)` in `finally`. |
| 9 | `deploy/netstrip-failopen-recovery.sh` | Idempotent recovery script: strips every NetStrip blackhole rule and re-asserts tailnet ACCEPT. |
| 10 | `deploy/cripple.service` | `ExecStartPre`/`ExecStopPost` run the recovery script, so **every restart begins from a clean, reachable state**. |

Regression guard: `tests/test_failopen_lockout_regression.py` (11 tests) locks in
each invariant so this class of bug cannot come back.

```
$ python -m pytest tests/test_failopen_lockout_regression.py -q
11 passed
```

## 4. Recovering the node (requires out-of-band access)

The node cannot be reached over any network path right now, so recovery needs the
**provider console / rescue shell** (the VPS panel at the `tor.frenzypenguin.media`
provider). Once you have a shell on the node, either of these fixes it:

**Fastest — clear the rules (network returns in seconds):**
```bash
# from the provider console / rescue shell
sudo bash /opt/cripple/netstrip/deploy/netstrip-failopen-recovery.sh
# or, if the script is not deployed yet:
sudo iptables  -D INPUT  -j DROP
sudo iptables  -D OUTPUT -j DROP
sudo ip6tables -D INPUT  -j DROP
sudo ip6tables -D OUTPUT -j DROP
sudo iptables  -I INPUT  1 -s 100.64.0.0/10 -j ACCEPT
sudo iptables  -I OUTPUT 1 -d 100.64.0.0/10 -j ACCEPT
```

**Then stop the loop and deploy the fix:**
```bash
sudo systemctl stop cripple.service
sudo systemctl disable cripple.service        # keep it down until the fixed build is in place
```

**Reboot also works:** the iptables rules are runtime-only, so a hard reboot
clears them. But without the fixes below, the service re-bricks the node on the
next start.

## 5. Re-deploying the fixed build onto the node

From a machine that can reach the node (once it is back):

```bash
# 1. Ship the fixed sources
scp netstrip/platform/linux.py  root@node:/opt/cripple/netstrip/netstrip/platform/linux.py
scp netstrip/core/engine.py     root@node:/opt/cripple/netstrip/netstrip/core/engine.py
scp netstrip/watchdog.py        root@node:/opt/cripple/netstrip/netstrip/watchdog.py
scp netstrip/data/async_database.py root@node:/opt/cripple/netstrip/netstrip/data/async_database.py
scp main.py                     root@node:/opt/cripple/netstrip/main_fixed.py
scp -r deploy                   root@node:/opt/cripple/netstrip/deploy

# 2. Install the hardened unit (ExecStartPre fail-open recovery)
ssh root@node 'install -m 0644 /opt/cripple/netstrip/deploy/cripple.service /etc/systemd/system/cripple.service
                chmod +x /opt/cripple/netstrip/deploy/netstrip-failopen-recovery.sh
                systemctl daemon-reload
                systemctl enable --now cripple.service
                systemctl status cripple.service --no-pager'

# 3. Verify the fail-open guarantees hold
ssh root@node 'iptables -S | grep -i netstrip'
ssh root@node 'tailscale status | grep node'     # RxBytes should grow again
```

## 6. Node access facts

| Item | Value |
|---|---|
| Hostname | `node` |
| Tailscale IP | `100.126.213.83` |
| Public IP | `92.119.124.2` (`tor.frenzypenguin.media`) |
| SSH (when healthy) | `ssh -l root -o BatchMode=yes root@100.126.213.83` |
| SOCKS5 (intentionally open) | `42891` — `from: 0.0.0.0/0` per requirement |
| Service | `/etc/systemd/system/cripple.service` → `main_fixed.py --service` |
| DB | `/root/.NetStrip/NetStrip.db` |
| Recovery script | `/opt/cripple/netstrip/deploy/netstrip-failopen-recovery.sh` |
