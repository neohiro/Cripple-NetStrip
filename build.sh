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
    # macOS
    pyinstaller \
        --noconfirm \
        --onedir \
        --windowed \
        --name "NetStrip" \
        --icon "assets/logo.png" \
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
        --icon "assets/logo.png" \
        --add-data "$CTK_PATH:customtkinter/" \
        --add-data "netstrip/data/lists:netstrip/data/lists" \
        --add-data "netstrip/data/updater_sources.json:netstrip/data" \
        --add-data "assets:assets/" \
        --hidden-import "PIL._tkinter_finder" \
        main.py
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
