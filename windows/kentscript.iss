; KentScript Installer for Windows
; Supports Windows 7, 8, 8.1, 10, 11
; Requires Inno Setup 5+ or 6+ to compile: https://jrsoftware.org/isdl.php

#define MyAppName "KentScript"
#define MyAppVersion "3.1.0"
#define MyAppPublisher "pyLord"
#define MyAppURL "https://github.com/musikaalvin/kentscript"
#define MyAppExeName "kentscript.exe"

[Setup]
AppId={{"A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
AppPublisherURL={{#MyAppURL}}
DefaultDirName={{autopf}}\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
OutputDir=dist
OutputBaseFilename=KentScript-Setup-{{#MyAppVersion}}
Compression=lzma
SolidCompression=yes
ChangesEnvironment=yes
PrivilegesRequired=admin
SetupIconFile=kentscript.ico
UninstallDisplayIcon={{app}}\{{#MyAppExeName}}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
Name: "addtopath"; Description: "Add to PATH"; GroupDescription: "System:"

[Files]
Source: "dist\kentscript\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\{{#MyAppName}}"; Filename: "{{app}}\{{#MyAppExeName}}"
Name: "{{group}}\{{cm:UninstallProgram,{{#MyAppName}}}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\{{#MyAppName}}"; Filename: "{{app}}\{{#MyAppExeName}}"; Tasks: desktopicon

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{{olddata}};{{app}}"; Tasks: addtopath; Check: NeedsAddPath('{{app}}')

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

[Run]
Filename: "{{app}}\{{#MyAppExeName}}"; Description: "Launch {{#MyAppName}}"; Flags: nowait postinstall skipifsilent
