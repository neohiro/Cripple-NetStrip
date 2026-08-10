#!/bin/bash
echo "========================================================"
echo "NetStrip - Bootstrapping Run Environment"
echo "========================================================"
echo ""

echo "[1] Checking for Python..."
if ! command -v python3 &> /dev/null
then
    echo "Python 3 is not installed or not in PATH!"
    echo "Please install Python 3.10+ (e.g. sudo apt install python3)"
    exit 1
fi

echo "[2] Installing Requirements..."
python3 -m pip install -r requirements.txt --quiet || echo "Warning: Pip install failed, trying to continue anyway."

echo "[3] Launching NetStrip..."
python3 main.py
