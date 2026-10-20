#!/usr/bin/env bash
# NetStrip fail-open recovery — ALWAYS safe to run, at any time.
#
# Purpose
# -------
# Remove every firewall rule that Cripple-NetStrip can use to blackhole a host,
# so a headless/remote node can never be locked out. Idempotent: running it when
# no NetStrip rules exist is a no-op.
#
# Usage (on the node, from a rescue shell, console, or systemd ExecStartPre):
#     sudo bash deploy/netstrip-failopen-recovery.sh
#
# What it removes
# ---------------
#   1. Ghost-mode killswitch DROPs   (comment: NetStrip_Killswitch)
#   2. Legacy untagged global DROPs  (-I INPUT/OUTPUT 1 -j DROP)
#   3. "IPv4 globally blocked" DROPs (comment: NetStrip_IPv4_Block)
#   4. LAN shield DROPs for RFC1918
#
# It deliberately does NOT insert a management ACCEPT rule. A separate ACCEPT
# at position 1 is shadowed the moment the engine prepends its DROP at position
# 1 as well, which would leave the tailnet blocked while looking "exempted".
# The correct fail-open state is simply "no DROP rules left behind".
#
# It does NOT stop the Cripple service; use `systemctl stop cripple.service`
# if you want to keep it down while debugging.

set -u

LOG_TAG="netstrip-failopen"
log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"; logger -t "$LOG_TAG" "$*" 2>/dev/null || true; }

require_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "Must run as root." >&2
        exit 1
    fi
}

del_all_matching() {
    # $@ = full iptables match spec WITHOUT the -D vs -C difference.
    # Deletes every matching rule until none remain.
    local table="$1"; shift
    while "$table" -C "$@" 2>/dev/null; do
        "$table" -D "$@" || break
    done
}

recover_chain() {
    local table="$1" chain="$2" direction="$3"
    local lo_flag="-o"
    local mgmt_v4="-s"
    if [ "$direction" = "INPUT" ]; then
        lo_flag="-i"
    else
        mgmt_v4="-d"
    fi

    # 1. Killswitch DROP rules — every generation:
    #    a) current self-contained form with a management exemption
    #    b) intermediate plain form
    for mgmt in "100.64.0.0/10" "fd7a:115c:a1e0::/48"; do
        # skip the range that doesn't belong to this table
        case "$mgmt:$table" in
            100.64.0.0/10:ip6tables|fd7a:115c:a1e0::/48:iptables) continue ;;
        esac
        del_all_matching "$table" "$chain" ! "$lo_flag" lo ! "$mgmt_v4" "$mgmt" -m comment --comment NetStrip_Killswitch -j DROP
    done
    del_all_matching "$table" "$chain" ! "$lo_flag" lo -m comment --comment NetStrip_Killswitch -j DROP

    # 2. Legacy untagged global DROP (only the uncommented catch-all form).
    #    Match the exact spec, never `-D "$chain" 1 -j DROP`: the positional form
    #    could delete an unrelated rule that happens to sit at the top.
    del_all_matching "$table" "$chain" -j DROP

    # 3. "IPv4 globally blocked" rules — self-contained and legacy forms.
    del_all_matching "$table" "$chain" ! "$lo_flag" lo ! "$mgmt_v4" "100.64.0.0/10" -p all -m comment --comment NetStrip_IPv4_Block -j DROP
    del_all_matching "$table" "$chain" ! "$lo_flag" lo -p all -m comment --comment NetStrip_IPv4_Block -j DROP

    # 4. Stray tailnet ACCEPT exemptions from an intermediate revision.
    #    (Removed rather than re-added: a separate ACCEPT would be shadowed by a
    #    prepended DROP, so the correct recovery is to leave no DROP behind.)
    for cidr in 100.64.0.0/10 fd7a:115c:a1e0::/48; do
        case "$cidr:$table" in
            100.64.0.0/10:ip6tables|fd7a:115c:a1e0::/48:iptables) continue ;;
        esac
        while "$table" -D "$chain" "$mgmt_v4" "$cidr" -j ACCEPT 2>/dev/null; do :; done
    done
}

recover_lan() {
    for subnet in 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16; do
        del_all_matching iptables OUTPUT -d "$subnet" -j DROP
        del_all_matching iptables INPUT  -s "$subnet" -j DROP
    done
}

verify_no_blackhole() {
    # Hard assertion: after recovery the host must have no DROP rule in INPUT or
    # OUTPUT. recover_lan already deletes the Linux LAN-shield rules, so a
    # successful recovery leaves zero DROPs. Any survivor is a blackhole risk.
    # Returns non-zero if any remain.
    local bad=0
    for table in iptables ip6tables; do
        command -v "$table" >/dev/null 2>&1 || continue
        # Any surviving DROP in INPUT/OUTPUT is a blackhole risk after recovery.
        local offenders
        offenders=$("$table" -S 2>/dev/null \
            | grep -E "^-A (INPUT|OUTPUT)( .*)? -j DROP" || true)
        if [ -n "$offenders" ]; then
            log "ERROR: residual blackhole DROP rules on $table:"
            printf '%s\n' "$offenders" >&2
            bad=1
        fi
    done
    return "$bad"
}

main() {
    require_root
    log "NetStrip fail-open recovery starting."

    for table in iptables ip6tables; do
        command -v "$table" >/dev/null 2>&1 || { log "$table not present, skipping."; continue; }
        recover_chain "$table" INPUT  INPUT
        recover_chain "$table" OUTPUT OUTPUT
    done
    command -v iptables >/dev/null 2>&1 && recover_lan

    # Clear the persisted killswitch flag so a restart does not re-trip it.
    for db in "$HOME/.NetStrip/NetStrip.db" "$HOME/.netstrip/NetStrip.db"; do
        if [ -f "$db" ] && command -v sqlite3 >/dev/null 2>&1; then
            sqlite3 "$db" "DELETE FROM settings WHERE key='killswitch_active';" 2>/dev/null || true
            sqlite3 "$db" "DELETE FROM settings WHERE key='protection_mode';" 2>/dev/null || true
            log "Cleared persisted killswitch/mode flags in $db"
        fi
    done

    # Assert we actually achieved a fail-open state.
    verify_no_blackhole || log "ERROR: residual blackhole rules detected — inspect manually."

    log "Fail-open recovery complete. Network should be reachable."
    log "Current INPUT rules:"
    iptables -L INPUT -n --line-numbers 2>/dev/null | head -n 20 || true
}

main "$@"
