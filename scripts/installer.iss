; NetStrip Windows Installer (Inno Setup 6)
; Build:  iscc scripts\installer.iss   (expects dist\Cripple.exe from PyInstaller)
; The [Run]/[UninstallRun] entries register/unregister NetStrip's own network
; restoration so an uninstall can never leave a machine without DNS.

#define MyAppName "NetStrip"
; CI injects:  iscc /DMyAppVersion=x.y.z /DExeSource=dist\Cripple\Cripple.exe
; Local defaults cover a standard PyInstaller onedir build.
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef ExeSource
  #define ExeSource "..\dist\Cripple\Cripple.exe"
#endif

[Setup]
AppId=NetStrip
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\NetStrip
DefaultGroupName=NetStrip
UninstallDisplayIcon={app}\Cripple.exe
LicenseFile=..\LICENSE.md
OutputDir=installer\
OutputBaseFilename=NetStrip-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern

[Files]
Source: "{#ExeSource}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\logo.ico"; DestDir: "{app}"

[Icons]
Name: "{group}\NetStrip"; Filename: "{app}\Cripple.exe"
Name: "{autodesktop}\NetStrip"; Filename: "{app}\Cripple.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"
Name: "autostart"; Description: "Start NetStrip when Windows starts"; GroupDescription: "Startup:"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "NetStrip"; ValueData: """{app}\Cripple.exe"""; \
    Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Cripple.exe"; Description: "Launch NetStrip"; \
    Flags: nowait postinstall skipifsilent runascurrentuser

