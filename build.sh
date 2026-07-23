#!/bin/bash
echo "========================================================"
echo "NetStrip - PyInstaller Build Script (Linux/macOS)"
echo "========================================================"
echo ""

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 not found! Please install python3-pip."
    exit 1
fi

echo "[1] Checking for PyInstaller..."
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo "PyInstaller not found! Installing..."
    pip3 install pyinstaller
fi

# Ensure required packages are installed
echo "[2] Installing requirements..."
pip3 install -r requirements.txt

echo "[3] Locating CustomTkinter package path..."
CTK_PATH=$(python3 -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))")
echo "   CustomTkinter found at: $CTK_PATH"

echo "[4] Cleaning previous build directories..."
rm -rf build dist 2>/dev/null

echo "[5] Building NetStrip executable..."
echo "   This will take a few minutes. Please wait..."

# Common hidden imports for all netstrip modules
HIDDEN_IMPORTS=(
    --hidden-import "PIL._tkinter_finder"
    --hidden-import "netstrip"
    --hidden-import "netstrip.core"
    --hidden-import "netstrip.core.engine"
    --hidden-import "netstrip.core.firewall"
    --hidden-import "netstrip.core.classifier"
    --hidden-import "netstrip.core.connection_monitor"
    --hidden-import "netstrip.core.dns_proxy"
    --hidden-import "netstrip.core.anomaly_scanner"
    --hidden-import "netstrip.core.analytics"
    --hidden-import "netstrip.core.geoip"
    --hidden-import "netstrip.core.lan_shield"
    --hidden-import "netstrip.core.linux_ebpf_monitor"
    --hidden-import "netstrip.core.modes"
    --hidden-import "netstrip.core.network_monitor"
    --hidden-import "netstrip.core.notifier"
    --hidden-import "netstrip.core.sound"
    --hidden-import "netstrip.core.updater"
    --hidden-import "netstrip.core.interceptor"
    --hidden-import "netstrip.core.interceptor.base"
    --hidden-import "netstrip.core.interceptor.windows"
    --hidden-import "netstrip.core.interceptor.linux"
    --hidden-import "netstrip.core.interceptor.macos"
    --hidden-import "netstrip.data"
    --hidden-import "netstrip.data.database"
    --hidden-import "netstrip.data.blocklist_manager"
    --hidden-import "netstrip.gui"
    --hidden-import "netstrip.gui.app"
    --hidden-import "netstrip.gui.animated_logo"
    --hidden-import "netstrip.gui.connections_sidebar"
    --hidden-import "netstrip.gui.dashboard"
    --hidden-import "netstrip.gui.hovertip"
    --hidden-import "netstrip.gui.icon_manager"
    --hidden-import "netstrip.gui.killswitch_modal"
    --hidden-import "netstrip.gui.notification_popup"
    --hidden-import "netstrip.gui.popups"
    --hidden-import "netstrip.gui.smart_modal"
    --hidden-import "netstrip.gui.splash"
    --hidden-import "netstrip.gui.theme"
    --hidden-import "netstrip.gui.utils"
    --hidden-import "netstrip.gui.widgets"
    --hidden-import "netstrip.gui.components"
    --hidden-import "netstrip.gui.components.sidebar_components"
    --hidden-import "netstrip.gui.views"
    --hidden-import "netstrip.gui.views.anomaly_alert"
    --hidden-import "netstrip.gui.views.blocklists"
    --hidden-import "netstrip.gui.views.logs"
    --hidden-import "netstrip.gui.views.rules"
    --hidden-import "netstrip.gui.views.settings"
    --hidden-import "netstrip.platform"
    --hidden-import "netstrip.platform.base"
    --hidden-import "netstrip.platform.windows"
    --hidden-import "netstrip.platform.linux"
    --hidden-import "netstrip.platform.linux_ebpf"
    --hidden-import "netstrip.platform.macos"
    --hidden-import "netstrip.watchdog"
)

# Detect OS to handle platform-specific flags
OS="$(uname -s)"
if [ "$OS" = "Darwin" ]; then
    echo "[5.5] Generating macOS .icns icon..."
    mkdir -p assets/logo.iconset
    sips -z 16 16     assets/cripple_logo.png --out assets/logo.iconset/icon_16x16.png >/dev/null
    sips -z 32 32     assets/cripple_logo.png --out assets/logo.iconset/icon_16x16@2x.png >/dev/null
    sips -z 32 32     assets/cripple_logo.png --out assets/logo.iconset/icon_32x32.png >/dev/null
    sips -z 64 64     assets/cripple_logo.png --out assets/logo.iconset/icon_32x32@2x.png >/dev/null
    sips -z 128 128   assets/cripple_logo.png --out assets/logo.iconset/icon_128x128.png >/dev/null
    sips -z 256 256   assets/cripple_logo.png --out assets/logo.iconset/icon_128x128@2x.png >/dev/null
    sips -z 256 256   assets/cripple_logo.png --out assets/logo.iconset/icon_256x256.png >/dev/null
    sips -z 512 512   assets/cripple_logo.png --out assets/logo.iconset/icon_256x256@2x.png >/dev/null
    sips -z 512 512   assets/cripple_logo.png --out assets/logo.iconset/icon_512x512.png >/dev/null
    sips -z 1024 1024 assets/cripple_logo.png --out assets/logo.iconset/icon_512x512@2x.png >/dev/null
    iconutil -c icns assets/logo.iconset
    rm -rf assets/logo.iconset

    # macOS
    pyinstaller \
        --noconfirm \
        --onedir \
        --windowed \
        --name "NetStrip" \
        --icon "assets/logo.icns" \
        --add-data "$CTK_PATH:customtkinter/" \
        --add-data "netstrip/data/lists:netstrip/data/lists" \
        --add-data "netstrip/data/updater_sources.json:netstrip/data" \
        --add-data "assets:assets/" \
        "${HIDDEN_IMPORTS[@]}" \
        main.py
else
    # Linux
    pyinstaller \
        --noconfirm \
        --onedir \
        --windowed \
        --name "NetStrip" \
        --add-data "$CTK_PATH:customtkinter/" \
        --add-data "netstrip/data/lists:netstrip/data/lists" \
        --add-data "netstrip/data/updater_sources.json:netstrip/data" \
        --add-data "assets:assets/" \
        "${HIDDEN_IMPORTS[@]}" \
        main.py
        
    echo "[5.5] Generating Linux .desktop shortcut..."
    cat > dist/NetStrip.desktop << EOL
[Desktop Entry]
Version=1.0
Type=Application
Name=NetStrip
Comment=Intelligent Network Traffic Debloater
Exec=bash -c '"\\$(dirname "\\%k")/NetStrip/NetStrip"'
Icon=assets/logo.png
Terminal=false
Categories=Utility;Network;Security;
EOL
    chmod +x dist/NetStrip.desktop
fi

echo ""
echo "[6] Build Complete!"
if [ "$OS" = "Darwin" ]; then
    echo "You can find the compiled NetStrip.app in the 'dist' folder."
else
    echo "You can find the compiled executable in the 'dist/NetStrip' folder."
fi
echo "You can now compress it for distribution or run it directly."
echo ""
