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

# Detect OS to handle sudo/admin flags
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
        --hidden-import "PIL._tkinter_finder" \
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
        --hidden-import "PIL._tkinter_finder" \
        main.py
        
    echo "[5.5] Generating Linux .desktop shortcut..."
    cat > dist/NetStrip.desktop << EOL
[Desktop Entry]
Version=1.0
Type=Application
Name=NetStrip
Comment=Intelligent Network Traffic Debloater
Exec=bash -c '"\$(dirname "\%k")/NetStrip/NetStrip"'
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
