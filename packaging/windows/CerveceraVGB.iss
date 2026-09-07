; Cervecera VGB - Instalador Inno Setup (Windows)
; Compilar: iscc CerveceraVGB.iss  (desde packaging/windows)

#define MyAppName "Cervecera VGB"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SaintWick"
#define MyAppExeName "Cervecera_VGB.exe"

[Setup]
AppId={{8A2F5B1E-4C9D-4E6F-9A1B-6C3D2E8F4A5B}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Cervecera VGB
DefaultGroupName=Cervecera VGB
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=..\..\dist_installers
OutputBaseFilename=CerveceraVGB-Setup-{#MyAppVersion}
SetupIconFile=..\..\packaging\icons\windows\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
InfoBeforeFile=..\..\packaging\legends\LEYENDA_WINDOWS.txt

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
Name: "startmenuicon"; Description: "Crear acceso en el menú Inicio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\..\dist\Cervecera_VGB\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenuicon
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar {#MyAppName} ahora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
