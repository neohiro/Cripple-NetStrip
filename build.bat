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
    --onedir ^
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
    main.py

echo.
echo [5] Build Complete!
echo You can find the compiled executable in the 'dist\Cripple' folder.
echo You should compress the 'Cripple' folder into a .zip file for distribution.
echo.
echo.
