# NetStrip hardening audit notes (2026-10-20) — lessons from tailscale-exit hardening

## 1. Refresh / download failures (the recurring problem)
The headless refresh fix (
etstrip-refresh-fix, 
etstrip_refresh_fix.sh) must download lists from many sources with retries and a **keep-previous-on-failure** guarantee. When DNS/HTTP is broken (e.g., Tor SOCKS broken on a node), every curl/wget in the refresh fails → empty locked-names.txt → crash-loop. Fix requirements:
- Download to a temp dir, only move to $BLOCKLIST if the source succeeds AND counts ≥ MIN_LINES.
- On any failure, keep the existing previous file (never overwrite with empty). Log clearly what failed and why.
- Reuse upstream HTTP proxy settings when present so refresh works even through Tor.
- Report per-source: raw entries, good entries, min/max bytes, MD5.
- Never let a failed refresh wipe the blocklist; that is the single largest outage vector for this node.

## 2. No post-load count validation
After BlocklistManager.load_all(), callers often read get_stats() without checking actual domain count. With an empty or missing lists_dir, the DB silently shrinks to only ESSENTIAL/SYSTEM/UPDATE domains (~200 total). Add a minimum-count gate and log loudly when below threshold (e.g., < 100,000 domains).

## 3. Cache invalidation edge cases
- NetStrip_cache.pkl is written off the lists_dir; if lists_dir is on a tmpfs/empttoned partition, the cache becomes stale after restart. Hash includes mtime + size of each .txt (already implemented — keep it).
- If all .txt files fail to parse, 
ew_domain_map stays empty and the engine loads 0 domains. Guard against this by keeping at least the bundled ESSENTIAL_DOMAINS set always loaded (already done via hardcoded sets, but ensure they are non-empty before allowing load completion).

## 4. NetStrip UI status surface
The UI (gui/app.py) should expose DB size, reload status, refresh failures so operators see corruption at a glance. Current build does not surface that. Recommend short-status field in dashboard locklist_domains.

## 5. Service robustness
- cripple.service: Restart=always but no RuntimeDirectory; marker file handling fine-daemon pattern not present; consider ExecStartPre run 
etstrip-check and restart if DB too small (non-fatal, logged).
- The headless daemon (main_fixed.py --service) must not get wedged by lockout state persistence; the 
etstrip-failopen-recovery.sh prevents the most common lockout survival bug. Keep it wired as ExecStartPre.

## 6. Pitfalls (NOT in docs currently — add explicitly)
- Do NOT ship a locklist_manager.py path that uses safe_store_dir='.' — move persistent state to user home only.
- Do NOT silence parse exceptions silently; failure on one list must keep others loaded.
- % in filenames with single quotes (PowerShell portability) — test scripts run on Linux first.
- SQLite busy timeout required under concurrent access.

Docs: README.md, docs/HEADLESS_LOCKOUT_RECOVERY.md, this file.