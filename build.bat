@echo off
echo ========================================================
echo Cripple (NetStrip) - PyInstaller Build Script
echo ========================================================
echo.

echo [1] Checking for PyInstaller...
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found! Installing...
    pip install pyinstaller
)

echo [2] Locating CustomTkinter package path...
for /f "delims=" %%i in ('python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"') do set CTK_PATH=%%i
echo    CustomTkinter found at: %CTK_PATH%

echo [3] Cleaning previous build directories...
rmdir /S /Q build 2>nul
rmdir /S /Q dist 2>nul

echo [4] Building Cripple executable...
echo    This will take a few minutes. Please wait...

echo [4.5] Generating high-resolution Windows icon...
python -c "from PIL import Image; img=Image.open('assets/cripple_logo.png'); img.save('assets/logo.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)], bitmap_format='bmp')"

pyinstaller ^
    --noconfirm ^
    --onefile ^
    --noconsole ^
    --windowed ^
    --uac-admin ^
    --name "Cripple" ^
    --icon "assets/logo.ico" ^
    --add-data "%CTK_PATH%;customtkinter/" ^
    --add-data "netstrip/data/lists;netstrip/data/lists" ^
    --add-data "netstrip/data/updater_sources.json;netstrip/data" ^
    --add-data "assets;assets/" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "pystray._win32" ^
    --hidden-import "netstrip" ^
    --hidden-import "netstrip.core" ^
    --hidden-import "netstrip.core.engine" ^
    --hidden-import "netstrip.core.firewall" ^
    --hidden-import "netstrip.core.classifier" ^
    --hidden-import "netstrip.core.connection_monitor" ^
    --hidden-import "netstrip.core.dns_proxy" ^
    --hidden-import "netstrip.core.anomaly_scanner" ^
    --hidden-import "netstrip.core.analytics" ^
    --hidden-import "netstrip.core.crash_reporter" ^
    --hidden-import "netstrip.core.github_telemetry" ^
    --hidden-import "netstrip.core.geoip" ^
    --hidden-import "netstrip.core.lan_shield" ^
    --hidden-import "netstrip.core.linux_ebpf_monitor" ^
    --hidden-import "netstrip.core.modes" ^
    --hidden-import "netstrip.core.network_monitor" ^
    --hidden-import "netstrip.core.notifier" ^
    --hidden-import "netstrip.core.sound" ^
    --hidden-import "netstrip.core.updater" ^
    --hidden-import "netstrip.core.interceptor" ^
    --hidden-import "netstrip.core.interceptor.base" ^
    --hidden-import "netstrip.core.interceptor.windows" ^
    --hidden-import "netstrip.core.interceptor.linux" ^
    --hidden-import "netstrip.core.interceptor.macos" ^
    --hidden-import "netstrip.data" ^
    --hidden-import "netstrip.data.database" ^
    --hidden-import "netstrip.data.blocklist_manager" ^
    --hidden-import "netstrip.gui" ^
    --hidden-import "netstrip.gui.app" ^
    --hidden-import "netstrip.gui.animated_logo" ^
    --hidden-import "netstrip.gui.connections_sidebar" ^
    --hidden-import "netstrip.gui.dashboard" ^
    --hidden-import "netstrip.gui.hovertip" ^
    --hidden-import "netstrip.gui.icon_manager" ^
    --hidden-import "netstrip.gui.killswitch_modal" ^
    --hidden-import "netstrip.gui.notification_popup" ^
    --hidden-import "netstrip.gui.popups" ^
    --hidden-import "netstrip.gui.smart_modal" ^
    --hidden-import "netstrip.gui.splash" ^
    --hidden-import "netstrip.gui.theme" ^
    --hidden-import "netstrip.gui.utils" ^
    --hidden-import "netstrip.gui.widgets" ^
    --hidden-import "netstrip.gui.components" ^
    --hidden-import "netstrip.gui.components.sidebar_components" ^
    --hidden-import "netstrip.gui.views" ^
    --hidden-import "netstrip.gui.views.anomaly_alert" ^
    --hidden-import "netstrip.gui.views.blocklists" ^
    --hidden-import "netstrip.gui.views.logs" ^
    --hidden-import "netstrip.gui.views.rules" ^
    --hidden-import "netstrip.gui.views.settings" ^
    --hidden-import "netstrip.platform" ^
    --hidden-import "netstrip.platform.base" ^
    --hidden-import "netstrip.platform.windows" ^
    --hidden-import "netstrip.platform.linux" ^
    --hidden-import "netstrip.platform.linux_ebpf" ^
    --hidden-import "netstrip.platform.macos" ^
    --hidden-import "netstrip.watchdog" ^
    main.py

echo.
echo [5] Build Complete!
echo You can find the compiled executable in the 'dist\Cripple' folder.
echo You should compress the 'Cripple' folder into a .zip file for distribution.
echo.
echo.
