@echo off
echo ========================================================
echo NetStrip - Bootstrapping Run Environment
echo ========================================================
echo.

echo [1] Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python 3 is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

echo [2] Installing Requirements...
python -m pip install -r requirements.txt >nul

echo [3] Launching NetStrip...
python main.py
