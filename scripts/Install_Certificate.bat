@echo off
setlocal
echo ========================================================
echo Installing FrenzyPenguin Media Trusted Certificate
echo ========================================================
echo.
echo This registers FrenzyPenguin Media as a trusted publisher
echo on your local Windows system to prevent Smart App Control
echo and SmartScreen warnings.
echo.
echo Importing certificate into Trusted Publisher and Root stores...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Import-Certificate -FilePath '%~dp0FrenzyPenguinMedia.cer' -CertStoreLocation Cert:\CurrentUser\TrustedPublisher -ErrorAction SilentlyContinue; Import-Certificate -FilePath '%~dp0FrenzyPenguinMedia.cer' -CertStoreLocation Cert:\CurrentUser\Root -ErrorAction SilentlyContinue; Import-Certificate -FilePath '%~dp0FrenzyPenguinMedia.cer' -CertStoreLocation Cert:\LocalMachine\TrustedPublisher -ErrorAction SilentlyContinue; Import-Certificate -FilePath '%~dp0FrenzyPenguinMedia.cer' -CertStoreLocation Cert:\LocalMachine\Root -ErrorAction SilentlyContinue"
echo.
echo Certificate successfully installed! You can now run Cripple.exe.
echo.
pause
