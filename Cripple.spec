# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\Wout\\AppData\\Local\\Programs\\Python\\Python314\\Lib\\site-packages\\customtkinter', 'customtkinter/'), ('netstrip/data/lists', 'netstrip/data/lists'), ('netstrip/data/updater_sources.json', 'netstrip/data'), ('assets', 'assets/')]
binaries = []
hiddenimports = ['PIL._tkinter_finder', 'pystray._win32', 'netstrip', 'netstrip.core', 'netstrip.core.engine', 'netstrip.core.firewall', 'netstrip.core.classifier', 'netstrip.core.connection_monitor', 'netstrip.core.dns_proxy', 'netstrip.core.anomaly_scanner', 'netstrip.core.analytics', 'netstrip.core.crash_reporter', 'netstrip.core.github_telemetry', 'netstrip.core.geoip', 'netstrip.core.lan_shield', 'netstrip.core.linux_ebpf_monitor', 'netstrip.core.modes', 'netstrip.core.network_monitor', 'netstrip.core.notifier', 'netstrip.core.sound', 'netstrip.core.updater', 'netstrip.core.interceptor', 'netstrip.core.interceptor.base', 'netstrip.core.interceptor.windows', 'netstrip.core.interceptor.linux', 'netstrip.core.interceptor.macos', 'netstrip.data', 'netstrip.data.database', 'netstrip.data.blocklist_manager', 'netstrip.gui', 'netstrip.gui.app', 'netstrip.gui.animated_logo', 'netstrip.gui.connections_sidebar', 'netstrip.gui.dashboard', 'netstrip.gui.hovertip', 'netstrip.gui.icon_manager', 'netstrip.gui.killswitch_modal', 'netstrip.gui.notification_popup', 'netstrip.gui.popups', 'netstrip.gui.smart_modal', 'netstrip.gui.splash', 'netstrip.gui.theme', 'netstrip.gui.utils', 'netstrip.gui.widgets', 'netstrip.gui.components', 'netstrip.gui.components.sidebar_components', 'netstrip.gui.views', 'netstrip.gui.views.anomaly_alert', 'netstrip.gui.views.blocklists', 'netstrip.gui.views.logs', 'netstrip.gui.views.rules', 'netstrip.gui.views.settings', 'netstrip.platform', 'netstrip.platform.base', 'netstrip.platform.windows', 'netstrip.platform.linux', 'netstrip.platform.linux_ebpf', 'netstrip.platform.macos', 'netstrip.watchdog']
tmp_ret = collect_all('netstrip')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Cripple',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon=['assets\\logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Cripple',
)
