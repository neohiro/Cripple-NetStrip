"""Regression tests for the headless self-lockout class of bug.

Background (real production incident)
-------------------------------------
On a headless Linux node, `cripple.service` (main.py --service) escalated a
false-positive kernel anomaly into `trigger_threat_escalation()` ->
`set_killswitch(True)` -> `platform.enable_killswitch()`, which ran:

    iptables -I INPUT  1 -j DROP
    iptables -I OUTPUT 1 -j DROP

Because the rules carried no comment, `disable_killswitch()` could not reliably
match them, the headless build never spawned the fail-open watchdog
(`if not self.is_headless`), and systemd `Restart=always` re-applied the rules on
every restart. The node blackholed itself permanently and could not be reached
over Tailscale SSH / any port again.

These tests lock in the invariants that make that impossible:

1. The killswitch rule is comment-tagged, so it is always removable.
2. The killswitch exempts the Tailscale management path, so remote access
   survives a lockdown.
3. The fail-open watchdog is spawned in headless mode too.
4. Headless killswitches auto-revert after a bounded window.
5. `enable_ipv4()` deletes rules by the *same* comment `disable_ipv4()` adds.
"""

import inspect
import os
import re
import shutil
import sys
import tempfile

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from netstrip.platform.linux import LinuxPlatform  # noqa: E402


class TestLinuxKillswitchIsRecoverable:
    """The killswitch must never be able to permanently brick a host."""

    def test_killswitch_rule_is_comment_tagged(self):
        """Comment tag is what lets disable_killswitch remove it deterministically."""
        assert LinuxPlatform._KS_COMMENT == "NetStrip_Killswitch"

    def test_enable_killswitch_exempts_management_path(self):
        """A lockdown must leave the Tailscale tailnet reachable.

        The exemption MUST be part of the DROP rule itself (`! -s <mgmt>`).
        A separate ACCEPT rule inserted at position 1 would be shadowed by the
        DROP (also inserted at position 1), silently leaving the tailnet blocked.
        """
        assert LinuxPlatform._MGMT_V4 == "100.64.0.0/10", "tailnet is Tailscale CGNAT"
        src = inspect.getsource(LinuxPlatform.enable_killswitch)
        assert "_MGMT_V4" in src and "_MGMT_V6" in src, "must exempt both tailnet ranges"
        # The negation must appear alongside the mgmt CIDR in the drop rule.
        for chain, direction in (("INPUT", "-s"), ("OUTPUT", "-d")):
            assert re.search(
                r'"!",\s*"%s",\s*self\._MGMT_V[46]' % re.escape(direction), src
            ) or re.search(
                r"'!',\s*'%s',\s*self\._MGMT_V[46]" % re.escape(direction), src
            ), f"{chain} DROP must negate the {direction} management range"
        # Must NOT rely on a separate ACCEPT rule (shadowing hazard).
        code_lines = [
            ln for ln in src.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        # Strip the docstring region heuristically: ignore lines with prose quotes.
        code_only = "\n".join(
            ln for ln in code_lines if "_run_cmd" in ln or "def " in ln
        )
        assert "ACCEPT" not in code_only, (
            "killswitch must not use a separate ACCEPT rule — a prepended DROP "
            "would shadow it and the tailnet would stay blocked"
        )

    def test_enable_killswitch_prepends_single_rule_per_chain(self):
        """Exactly one DROP insert per chain pair: no ordering hazard."""
        src = inspect.getsource(LinuxPlatform.enable_killswitch)
        # 4 inserts total (v4 IN/OUT, v6 IN/OUT) and no other -I insertions.
        assert src.count('"-I"') == 4, "expected exactly 4 `-I` insertions"

    def test_disable_ipv4_exemption_is_inside_drop_rule(self):
        """disable_ipv4 must negate the mgmt range within the DROP rule."""
        src = inspect.getsource(LinuxPlatform.disable_ipv4)
        assert "NetStrip_IPv4_Block" in src
        assert "_MGMT_V4" in src
        assert src.count('"ACCEPT"') == 0, "no separate ACCEPT (would be shadowed)"

    def test_enable_killswitch_does_not_drop_loopback(self):
        """Only non-loopback traffic may be dropped."""
        src = inspect.getsource(LinuxPlatform.enable_killswitch)
        assert '"!"' in src and '"lo"' in src, "DROP rule must exclude loopback"

    def test_disable_killswitch_handles_comment_and_legacy(self):
        """Recovery must remove both the new tagged rules and legacy untagged ones."""
        src = inspect.getsource(LinuxPlatform.disable_killswitch)
        assert "_KS_COMMENT" in src, "must remove comment-tagged killswitch rules"
        # Legacy untagged global DROP, matched by exact spec.
        assert '"-C", chain, "-j", "DROP"' in src

    def test_disable_killswitch_never_deletes_positionally(self):
        """Must not use `-D <chain> 1 -j DROP`.

        The positional form deletes *whatever* rule sits at index 1 if it is a
        bare DROP, which can silently strip an unrelated firewall rule. Match the
        exact spec instead.
        """
        for name in ("disable_killswitch",):
            src = inspect.getsource(getattr(LinuxPlatform, name))
            assert '"1", "-j", "DROP"' not in src, (
                f"{name} must not delete rules by position"
            )

    def test_disable_killswitch_is_idempotent(self):
        """Calling disable twice must not raise (killswitch re-applies on restart)."""
        src = inspect.getsource(LinuxPlatform.disable_killswitch)
        assert "while" in src, "removal must loop until no matching rule remains"

    def test_enable_killswitch_is_idempotent(self):
        """Enabling twice must not stack duplicate DROP rules."""
        src = inspect.getsource(LinuxPlatform.enable_killswitch)
        assert "disable_killswitch()" in src, "enable must clear prior rules first"

    def test_disable_ipv4_and_enable_ipv4_share_comment(self):
        """enable_ipv4 must delete the exact rule disable_ipv4 inserted.

        The original bug: disable_ipv4 inserted a comment-tagged rule while
        enable_ipv4 deleted a spec without the comment, so it never matched and
        the host stayed blackholed after the engine exited.
        """
        dis = inspect.getsource(LinuxPlatform.disable_ipv4)
        ena = inspect.getsource(LinuxPlatform.enable_ipv4)
        assert "NetStrip_IPv4_Block" in dis
        assert "NetStrip_IPv4_Block" in ena, "enable_ipv4 must delete by the same comment"

    def test_disable_ipv4_exempts_management_path(self):
        src = inspect.getsource(LinuxPlatform.disable_ipv4)
        assert "_MGMT_V4" in src, "global IPv4 block must not cut the tailnet"


class TestHeadlessFailOpen:
    """Headless builds must always retain an automatic recovery path."""

    def _engine_src(self):
        engine_path = os.path.join(REPO_ROOT, "netstrip", "core", "engine.py")
        with open(engine_path, encoding="utf-8") as fh:
            return fh.read()

    def test_watchdog_spawned_in_headless_mode(self):
        """The old `and not self.is_headless` guard removed the only fail-open path."""
        src = self._engine_src()
        assert "and not self.is_headless" not in src, (
            "watchdog must not be disabled for headless builds — that removes the "
            "only automatic network-restore path on a remote node"
        )
        assert "watchdog.py" in src

    def test_headless_killswitch_autoreverts(self):
        """An automatic lockdown with no GUI must expire on its own."""
        src = self._engine_src()
        assert "_schedule_killswitch_autorevert" in src
        assert "_auto_revert_killswitch" in src
        # Wired into the killswitch entry point.
        set_ks = src.split("def set_killswitch", 1)[1].split("def ", 1)[0]
        assert "_schedule_killswitch_autorevert" in set_ks, (
            "set_killswitch(True) must schedule a bounded auto-revert in headless mode"
        )

    def test_autorevert_timer_is_cancelled_on_release(self):
        """Releasing the killswitch must cancel a pending auto-revert.

        Otherwise a legitimate disable is followed by a stale timer that fires
        later and re-runs the restore path (spurious broadcasts / mode churn).
        """
        src = self._engine_src()
        assert "_cancel_killswitch_autorevert" in src
        set_ks = src.split("def set_killswitch", 1)[1].split("def ", 1)[0]
        assert "_cancel_killswitch_autorevert" in set_ks, (
            "set_killswitch(False) must cancel the pending auto-revert timer"
        )


class TestRecoveryScriptCoversAllGenerations:
    """The recovery script must be able to undo every rule the code can emit.

    A recovery script that only understands the current rule shape is useless
    the moment the shape changes; these tests fail on drift.
    """

    def _script(self):
        path = os.path.join(REPO_ROOT, "deploy", "netstrip-failopen-recovery.sh")
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def test_script_removes_killswitch_rules(self):
        assert "NetStrip_Killswitch" in self._script()

    def test_script_removes_ipv4_block_rules(self):
        assert "NetStrip_IPv4_Block" in self._script()

    def test_script_handles_management_exempt_form(self):
        """Must match the `! -s/-d <mgmt>` self-contained rule form."""
        src = self._script()
        assert "100.64.0.0/10" in src, "must cover the tailnet CIDR used in the rule"
        assert '"$mgmt_v4" "$mgmt"' in src or "$mgmt_v4\" \"$mgmt" in src, (
            "must build a match that includes the management exemption clause"
        )

    def test_script_does_not_reintroduce_shadowing_accept(self):
        """Recovering by adding a separate ACCEPT would be shadowed by a DROP."""
        src = self._script()
        # It may only *delete* ACCEPT rules, never insert them.
        assert "-I INPUT  1 -s" not in src
        assert "-I OUTPUT 1 -d" not in src
        for line in src.splitlines():
            if "-j ACCEPT" in line:
                assert " -D " in line, (
                    "recovery script must only delete ACCEPT rules, not insert them"
                )

    def test_script_verifies_fail_open_state(self):
        """Recovery must assert it actually removed the blackhole."""
        assert "verify_no_blackhole" in self._script()

    def test_verifier_pattern_catches_bare_catchall_drop(self):
        """The original lockout was a bare `-I chain 1 -j DROP`.

        `iptables -S` renders that as `-A OUTPUT -j DROP` (no match spec at all),
        so a verifier regex that requires characters before `-j DROP` would miss
        the single most catastrophic rule it exists to detect.
        """
        src = self._script()
        # Extract the verification pattern from the script.
        patterns = re.findall(r'grep -E "([^"]*INPUT\|OUTPUT[^"]*)"', src)
        assert patterns, "verify_no_blackhole must grep INPUT/OUTPUT DROP rules"
        # The documented blackhole forms, and the benign forms.
        blackholes = [
            "-A INPUT -j DROP",
            "-A OUTPUT -j DROP",
            "-A INPUT ! -i lo ! -s 100.64.0.0/10 -m comment --comment NetStrip_Killswitch -j DROP",
            "-A OUTPUT -d 10.0.0.0/8 -j DROP",
        ]
        benign = [
            "-A INPUT -s 192.168.1.0/24 -j ACCEPT",
            "-A OUTPUT -o eth0 -j ACCEPT",
        ]
        for pat in patterns:
            for rule in blackholes:
                assert re.search(pat, rule), (
                    f"verifier pattern {pat!r} MUST flag blackhole rule {rule!r}"
                )
            for rule in benign:
                assert not re.search(pat, rule), (
                    f"verifier pattern {pat!r} must NOT flag benign rule {rule!r}"
                )


class TestWatchdogRestoresKillswitch:
    """The crash watchdog must fully restore a fail-open network state."""

    def test_watchdog_strips_killswitch_rules(self):
        watchdog_path = os.path.join(REPO_ROOT, "netstrip", "watchdog.py")
        with open(watchdog_path, encoding="utf-8") as fh:
            src = fh.read()
        assert "NetStrip_Killswitch" in src, (
            "watchdog must remove ghost-mode killswitch DROP rules on crash recovery"
        )

    def test_watchdog_handles_management_exempt_form(self):
        watchdog_path = os.path.join(REPO_ROOT, "netstrip", "watchdog.py")
        with open(watchdog_path, encoding="utf-8") as fh:
            src = fh.read()
        assert "100.64.0.0/10" in src, (
            "watchdog must also strip the management-exempt killswitch rule form"
        )

    def test_watchdog_never_deletes_positionally(self):
        """Watchdog must match the exact spec, not `-D <chain> 1 -j DROP`."""
        watchdog_path = os.path.join(REPO_ROOT, "netstrip", "watchdog.py")
        with open(watchdog_path, encoding="utf-8") as fh:
            src = fh.read()
        assert '"1", "-j", "DROP"' not in src, (
            "watchdog must not delete rules by position (can strip unrelated rules)"
        )

    def test_watchdog_strips_current_ipv4_block_form(self):
        """Crash recovery must remove the *current* IPv4-block rule shape.

        disable_ipv4 now inserts `! -i lo ! -s 100.64.0.0/10 -p all
        -m comment --comment NetStrip_IPv4_Block -j DROP`. A watchdog that only
        knows the legacy shape would leave the host blackholed after a crash.
        """
        watchdog_path = os.path.join(REPO_ROOT, "netstrip", "watchdog.py")
        with open(watchdog_path, encoding="utf-8") as fh:
            src = fh.read()
        assert "NetStrip_IPv4_Block" in src
        # The management-exemption clause must accompany the IPv4-block cleanup.
        assert '"-s", "100.64.0.0/10"' in src and '"-d", "100.64.0.0/10"' in src, (
            "watchdog must strip the management-exempt IPv4-block rule form"
        )


class TestSyncWrapperDelegation:
    """SyncDatabaseWrapper must serve the full sync surface and clean up.

    The headless crash-loop was caused by AttributeError on sync-only methods
    (get_user_rules / prune_old_logs) once the async migration left them off
    AsyncDatabase. The wrapper delegates them to a lazily-created Database.
    """

    def _make(self):
        tmpdir = tempfile.mkdtemp(prefix="netstrip_wrap_")
        db_path = os.path.join(tmpdir, "NetStrip.db")
        from netstrip.data.async_database import create_async_database

        async_db, wrapper = create_async_database(db_path)
        return tmpdir, async_db, wrapper

    def test_delegates_sync_only_methods(self):
        tmpdir, async_db, wrapper = self._make()
        try:
            rules = wrapper.get_user_rules()
            assert isinstance(rules, list)
            wrapper.add_user_rule({
                "pattern": "example.com", "action": "ALLOW", "scope": "global",
                "app_name": "", "category": "system", "mode_scope": "ALL",
            })
            assert any(r["pattern"] == "example.com" for r in wrapper.get_user_rules())
        finally:
            wrapper.stop()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_explicit_methods_take_priority(self):
        tmpdir, async_db, wrapper = self._make()
        try:
            # get_setting is explicitly defined; it must hit the async path and
            # return the supplied default for a missing key.
            assert wrapper.get_setting("absent-key", "DEFAULT") == "DEFAULT"
        finally:
            wrapper.stop()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_private_attributes_are_not_delegated(self):
        tmpdir, async_db, wrapper = self._make()
        try:
            with pytest.raises(AttributeError):
                wrapper._not_a_real_attribute  # noqa: B018
        finally:
            wrapper.stop()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_stop_releases_delegating_handle(self):
        """stop() must tear down the sync handle so no thread/conn is leaked."""
        tmpdir, async_db, wrapper = self._make()
        try:
            wrapper.get_user_rules()  # force creation of the sync handle
            assert wrapper._sync_db is not None
            wrapper.stop()
            assert wrapper._sync_db is None, (
                "stop() must release the delegating Database handle"
            )
            # Idempotent: a second stop must not raise.
            wrapper.stop()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
