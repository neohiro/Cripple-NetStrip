"""
Guards against translation drift: every catalog must cover the core key set,
and catalogs advertising tooltips must cover the full tooltip namespace.
"""

import json
import os
from pathlib import Path

LOCALES = Path(__file__).resolve().parent.parent / "netstrip" / "locales"

# Derived from scripts/build_locales.py (single source of truth)
CORE_KEYS = {
    "nav.dashboard", "nav.logs", "nav.filter_lists", "nav.settings",
    "dashboard.recent_blocks", "dashboard.block_system", "dashboard.smart_shield",
    "stat.allowed_blocked", "stat.total_queries", "stat.active", "stat.down_up",
    "sub.last24h", "sub.currently", "sub.down_up",
    "btn.check_updates", "btn.download_verify", "btn.export_logs",
    "btn.update_blocklists", "btn.show_online_feeds", "btn.hide_online_feeds",
    "btn.load_older_logs", "common.cancel",
    "status.up_to_date", "status.checking", "status.new_version",
    "status.downloading_verify", "status.all_loaded",
    "settings.updates", "settings.general", "settings.language",
    "settings.scroll_speed",
    "modal.killswitch.title", "modal.killswitch.body",
    "modal.killswitch.cancel", "modal.killswitch.engage",
    "modal.recovery.title", "modal.recovery.stay", "modal.recovery.restore",
    "modal.smart.title", "modal.smart.disable", "modal.smart.stay",
}

TOOLTIP_KEYS = {
    "tooltip.Dashboard", "tooltip.Logs", "tooltip.Filter Lists",
    "tooltip.Settings", "tooltip.Allow", "tooltip.Block", "tooltip.Sinkhole",
    "tooltip.Export Logs", "tooltip.Refresh Blocklists",
    "tooltip.View Custom Rules", "tooltip.Reset Custom Rules",
    "tooltip.\U0001F50A", "tooltip.\U0001F507",
}


def _locales():
    return {p.stem: json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(LOCALES.glob("*.json"))}


def test_every_catalog_covers_core_keys():
    cats = _locales()
    assert len(cats) >= 20, f"expected a broad language set, got {len(cats)}"
    for code, data in cats.items():
        missing = CORE_KEYS - set(data)
        assert not missing, f"{code}.json missing core keys: {sorted(missing)[:5]}"


def test_tooltip_catalogs_are_complete_when_started():
    cats = _locales()
    for code, data in cats.items():
        started = [k for k in data if k.startswith("tooltip.")]
        if started:
            missing = TOOLTIP_KEYS - set(data)
            assert not missing, (
                f"{code}.json advertises tooltips but is missing: "
                f"{sorted(missing)[:5]} — finish the set or remove the partials"
            )


def test_english_is_complete_source():
    en = _locales()["en"]
    missing = CORE_KEYS - set(en)
    assert not missing, f"en.json must define every core key: {sorted(missing)}"


def test_no_placeholder_drift_in_formatted_strings():
    """{version}/{count} placeholders must survive translation."""
    for code, data in _locales().items():
        if "status.new_version" in data:
            assert "{version}" in data["status.new_version"], code
        if "btn.load_older_logs" in data:
            assert "{count}" in data["btn.load_older_logs"], code
