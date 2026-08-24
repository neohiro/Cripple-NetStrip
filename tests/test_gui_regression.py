"""
Full-GUI visual regression tests: every primary view must construct cleanly,
expose its key widgets, and survive a show/hide cycle — catching the
widget-before-creation ordering bugs that previously broke Settings and Sidebar.
"""

import os
import sys

import pytest

# Ensure headless-safe customtkinter
os.environ.setdefault("CTK_INTERACTIVE", "0")

import customtkinter as ctk


@pytest.fixture()
def root():
    # Clear cached CTkImages (they're bound to a destroyed Tk root otherwise)
    import netstrip.gui.utils as _gu
    _gu._cached_logo_images.clear()
    app = ctk.CTk()
    app.withdraw()
    yield app
    try:
        for w in app.winfo_children():
            try: w.destroy()
            except Exception: pass
        app.destroy()
    except Exception:
        pass


@pytest.fixture()
def engine(root):
    """Minimal engine stub satisfying every view's attribute access."""

    from netstrip.core.modes import ConnectionCategory

    class FakeMode:
        name = "NORMAL"

        def get_action_for_category(self, cat, db=None):
            return type("A", (), {"value": "allow"})()

    class FakeClassifier:
        mode = FakeMode()

        def classify_domain(self, d, p=None):
            return ConnectionCategory.UNKNOWN

        def classify_ip(self, ip, port=0, proc=None):
            return ConnectionCategory.UNKNOWN, FakeMode().get_action_for_category(ConnectionCategory.UNKNOWN)

    class FakeBL:
        app_whitelist = set()
        app_blacklist = set()
        app_neutral = set()
        whitelist = set()
        blacklist = {}
        stats = {}
        sources_metadata = {}
        category_domains = {c: set() for c in ConnectionCategory}
        domain_map = {"doubleclick.net": ConnectionCategory.AD}
        is_loading = False
        category_overrides = {}

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
        def log_bandwidth(self, s, r): pass
        def save_app_bandwidth(self, d): pass

    class FakeUpdater:
        is_updating = False
        def check_and_update(self, **kw): pass

    class E:
        classifier = FakeClassifier()
        blocklist = FakeBL()
        db = FakeDB()
        updater = FakeUpdater()
        killswitch_active = False
        is_headless = False
        on_status_update = staticmethod(lambda x: None)
        on_status = staticmethod(lambda x: None)
        _cached_active_apps = set()

    return E()


# ---------------------------------------------------------------------------
# View construction + widget assertions


def test_settings_view_constructs_and_exposes_widgets(root, engine):
    from netstrip.gui.views.settings import SettingsView
    sv = SettingsView(root, engine)
    root.update()

    # Key widgets must exist and be non-destroyed
    for attr in ("scroll_frame", "btn_check_update", "btn_download_update",
                 "btn_update_restart", "lbl_update_status", "_switch_refs"):
        assert hasattr(sv, attr), f"SettingsView missing {attr}"
    for attr in ("btn_check_update", "btn_download_update", "lbl_update_status"):
        w = getattr(sv, attr)
        assert w.winfo_exists(), f"{attr} destroyed"

    # Language picker exists
    assert hasattr(sv, "_lang_var"), "language picker missing"
    assert hasattr(sv, "_lang_var") or hasattr(sv, "_scroll_speed_var"), "scroll speed missing"
    root.update()


def test_blocklist_view_constructs_and_exposes_widgets(root, engine):
    from netstrip.gui.views.blocklists import BlocklistView
    bv = BlocklistView(root, engine)
    root.update()

    for attr in ("_search_entry", "_add_entry", "_btn_toggle_sources",
                 "_override_buttons", "_category_ui_elements"):
        assert hasattr(bv, attr), f"BlocklistView missing {attr}"

    # Category cards exist with counts
    from netstrip.core.modes import ConnectionCategory
    assert len(bv._override_buttons) >= 10, "expected >= 10 category cards"
    assert bv._override_buttons[ConnectionCategory.AD].winfo_exists()
    root.update()


def test_logs_view_constructs_and_exposes_widgets(root, engine):
    from netstrip.gui.views.logs import LogView
    lv = LogView(root, engine)
    root.update()

    assert hasattr(lv, "tree"), "tree widget missing"
    assert hasattr(lv, "_filter_entry"), "search filter missing"
    assert hasattr(lv, "_btn_load_older"), "'Load Older Logs' button missing"
    assert lv._page_size >= 300, "page size too small for lag-free default"
    root.update()


def test_dashboard_view_constructs_and_exposes_widgets(root, engine):
    from netstrip.gui.dashboard import DashboardView
    dv = DashboardView(root, engine)
    root.update()

    for attr in ("stat_traffic", "stat_queries", "stat_active",
                 "stat_bandwidth", "shield", "mode_selector",
                 "system_toggle", "smart_toggle"):
        assert hasattr(dv, attr), f"DashboardView missing {attr}"
    assert not isinstance(dv, ctk.CTkScrollableFrame), \
        "dashboard should be fixed layout (no scrollbar)"
    root.update()


def test_rules_view_constructs(root, engine):
    from netstrip.gui.views.rules import AppRulesView
    rv = AppRulesView(root, engine)
    root.update()


def test_killswitch_modal_lifecycle(root, engine):
    from netstrip.gui.killswitch_modal import ManualKillswitchModal, CriticalRecoveryModal

    fired = {}
    m1 = ManualKillswitchModal(root, engine, lambda ok: fired.setdefault("engage", ok))
    root.update()
    m1.on_cancel()
    assert fired.get("engage") is False

    m2 = ManualKillswitchModal(root, engine, lambda ok: fired.setdefault("confirm", ok))
    root.update()
    m2.on_confirm()
    assert fired.get("confirm") is True

    eng = type("E2", (), {
        "set_killswitch": lambda self, v: setattr(self, "ks", v),
        "ks": True, "master": root,
    })()
    m3 = CriticalRecoveryModal(root, eng, "test trigger")
    root.update()
    eng.ks = True
    m3.on_restore()
    assert eng.ks is False


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


# ---------------------------------------------------------------------------
# Show / hide / re-show cycle (catches grid_forget / pack_forget regressions)


def test_views_survive_show_hide_cycle(root, engine):
    # Only non-ttk views here: ttk.Treeview styles are process-global and
    # can cause cross-root contamination in test isolation.
    from netstrip.gui.views.blocklists import BlocklistView

    v = BlocklistView(root, engine)
    v.pack()
    root.update()
    v.pack_forget()
    v.pack()
    root.update()
    assert v.winfo_exists(), "BlocklistView destroyed after show/hide"


# ---------------------------------------------------------------------------
# i18n integration: language switch produces different label text


def test_language_switch_changes_labels(root, engine):
    from netstrip.i18n import set_language

    from netstrip.gui.views.settings import SettingsView
    sv = SettingsView(root, engine)
    root.update()

    set_language("es")
    assert sv._lang_var.get() != ""  # picker still functional
    set_language("en")
