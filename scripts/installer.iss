; NetStrip Windows Installer (Inno Setup 6)
; Build:  iscc scripts\installer.iss   (expects dist\Cripple.exe from PyInstaller)
; The [Run]/[UninstallRun] entries register/unregister NetStrip's own network
; restoration so an uninstall can never leave a machine without DNS.

#define MyAppName "NetStrip"
#define MyAppVersion GetVersionNumbersString("dist\Cripple.exe")

[Setup]
AppId={{8E7B6C1D-52A4-4F0E-9C3B-NETSTRIP64}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\NetStrip
DefaultGroupName=NetStrip
UninstallDisplayIcon={app}\Cripple.exe
LicenseFile=LICENSE.md
OutputDir=installer\
OutputBaseFilename=NetStrip-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern

[Files]
Source: "dist\Cripple.exe"; DestDir: "{app}"; Flags: ignoreversion signonce
Source: "assets\logo.ico"; DestDir: "{app}"

[Icons]
Name: "{group}\NetStrip"; Filename: "{app}\Cripple.exe"
Name: "{autodesktop}\NetStrip"; Filename: "{app}\Cripple.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"
Name: "autostart"; Description: "Start NetStrip when Windows starts"; GroupDescription: "Startup:"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "NetStrip"; ValueData: """{app}\Cripple.exe"" --minimized"; \
    Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Cripple.exe"; Description: "Launch NetStrip"; \
    Flags: nowait postinstall skipifsilent runascurrentuser

[UninstallRun]
; Safety net: restore DNS / firewall rules even if the app never got to clean up
Filename: "{app}\Cripple.exe"; Parameters: "--restore-network"; RunOnceId: "RestoreNet"; Flags: runhidden waituntilterminated skipifdoesntexist
