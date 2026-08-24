"""
Full-GUI regression tests: every primary view must construct cleanly,
expose key widgets, and survive show/hide cycles — catching
widget-before-creation ordering bugs.

All views share a single Tk root to avoid cross-instance ttk.Style pollution.
"""

import os

import pytest

os.environ.setdefault("CTK_INTERACTIVE", "0")

import customtkinter as ctk


@pytest.fixture(scope="module")
def engine():
    """Shared engine stub satisfying all views."""
    from netstrip.core.modes import ConnectionCategory

    class FakeMode:
        name = "NORMAL"

        def get_action_for_category(self, cat, db=None):
            return type("A", (), {"value": "allow"})()

    class FakeClassifier:
        mode = FakeMode()
        def classify_domain(self, d, p=None): return ConnectionCategory.UNKNOWN

    class FakeBL:
        app_whitelist = set(); app_blacklist = set(); app_neutral = set()
        whitelist = set(); blacklist = {}; stats = {}
        sources_metadata = {}
        category_domains = {c: set() for c in ConnectionCategory}
        domain_map = {"doubleclick.net": ConnectionCategory.AD}
        is_loading = False; category_overrides = {}
        def sync_user_rules(self, r): pass
        def get_updater_sources(self): return []
        def get_category_override(self, c): return None
        def set_category_override(self, c, s): self.category_overrides[c] = s
        def search(self, q="", limit=50, category_filter=None, offset=0): return []
        def add_loaded_callback(self, cb): pass
        def get_identity(self, d): return None
        def toggle_updater_source(self, *a): pass

    class FakeDB:
        def get_setting(self, k, d=None): return d or "false"
        def set_setting(self, k, v): pass
        def get_recent_connections(self, limit=100, **kw): return []
        def get_24h_statistics(self): return {"total_blocked": 0, "total_queries": 0, "total_allowed": 0}
        def get_unique_allowed_24h(self): return 0

    class FakeUpdater:
        is_updating = False
        def check_and_update(self, **kw): pass

    class E:
        classifier = FakeClassifier(); blocklist = FakeBL(); db = FakeDB()
        updater = FakeUpdater(); killswitch_active = False; is_headless = False
        on_status_update = staticmethod(lambda x: None)
        on_status = staticmethod(lambda x: None)
        _cached_active_apps = set()

    return E()


@pytest.fixture(scope="module")
def root():
    app = ctk.CTk()
    app.withdraw()
    yield app


# ── Individual view constructions ──────────────────────────────────────────

def test_settings_view(root, engine):
    from netstrip.gui.views.settings import SettingsView
    sv = SettingsView(root, engine)
    root.update()
    assert hasattr(sv, "btn_check_update")
    assert hasattr(sv, "_lang_var")
    # Show / hide cycle
    sv.pack(); root.update(); sv.pack_forget(); sv.pack(); root.update()
    assert sv.winfo_exists()


def test_blocklist_view(root, engine):
    from netstrip.gui.views.blocklists import BlocklistView
    bv = BlocklistView(root, engine)
    root.update()
    assert hasattr(bv, "_search_entry") and hasattr(bv, "_override_buttons")
    bv.pack(); root.update(); bv.pack_forget(); bv.pack(); root.update()
    assert bv.winfo_exists()


def test_logs_view(root, engine):
    from netstrip.gui.views.logs import LogView
    lv = LogView(root, engine)
    root.update()
    assert hasattr(lv, "tree") and hasattr(lv, "_filter_entry")
    lv.pack(); root.update(); lv.pack_forget(); lv.pack(); root.update()
    assert lv.winfo_exists()


def test_dashboard_view(root, engine):
    from netstrip.gui.dashboard import DashboardView
    dv = DashboardView(root, engine)
    root.update()
    assert not isinstance(dv, ctk.CTkScrollableFrame)
    assert hasattr(dv, "stat_traffic") and hasattr(dv, "system_toggle")
    dv.pack(); root.update(); dv.pack_forget(); dv.pack(); root.update()
    assert dv.winfo_exists()


def test_rules_view(root, engine):
    from netstrip.gui.views.rules import AppRulesView
    rv = AppRulesView(root, engine)
    rv.pack(); root.update()
    assert rv.winfo_exists()


# ── Modal lifecycles ────────────────────────────────────────────────────────

def test_killswitch_modal_lifecycle(root, engine):
    from netstrip.gui.killswitch_modal import ManualKillswitchModal, CriticalRecoveryModal
    fired = {}
    m1 = ManualKillswitchModal(root, engine, lambda ok: fired.setdefault("cancel", ok))
    root.update(); m1.on_cancel()
    assert fired.get("cancel") is False
    m2 = ManualKillswitchModal(root, engine, lambda ok: fired.setdefault("confirm", ok))
    root.update(); m2.on_confirm()
    assert fired.get("confirm") is True
    eng2 = type("E2", (), {"set_killswitch": lambda s, v: setattr(s, "ks", v),
                           "ks": True, "master": root})()
    m3 = CriticalRecoveryModal(root, eng2, "test")
    root.update(); m3.on_restore()
    assert eng2.ks is False


def test_smart_modal_lifecycle(root):
    from netstrip.gui.smart_modal import SmartParanoidModal
    calls = []
    eng = type("E3", (), {
        "db": type("D", (), {"set_setting": staticmethod(
            lambda k, v: calls.append((k, v)))})(),
        "set_mode": lambda self, level: calls.append(("mode", level)),
        "classifier": type("C", (), {"mode": type("M", (), {"name": "NORMAL"})()})(),
    })()
    m = SmartParanoidModal(root, eng,
                           {"domain": "evil.example", "process_name": "Bad.exe"})
    root.update()
    m._disable_smart_shield()
    assert ("smart_paranoid_mode", "false") in calls


# ── i18n integration ────────────────────────────────────────────────────────

def test_language_switch_functional(root, engine):
    from netstrip.i18n import set_language, available_languages
    langs = available_languages()
    assert len(langs) >= 20, f"expected >=20 languages, got {len(langs)}"
    for lang in ["es", "de", "ar", "he"]:
        set_language(lang)
    set_language("en")
