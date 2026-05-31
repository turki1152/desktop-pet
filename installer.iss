; ============================================================
; Desktop Pet — Inno Setup installer script
; Requires: Inno Setup 6  (https://jrsoftware.org/isinfo.php)
;
; Build steps:
;   1. Run build_exe.bat first to create dist\DesktopPet.exe
;   2. Open this file in Inno Setup Compiler and click Build
;   3. Upload output\DesktopPetSetup.exe to your website
; ============================================================

#define AppName      "Desktop Pet"
#define AppVersion   "1.0.0"
#define AppPublisher "tyx"
#define AppExeName   "DesktopPet.exe"
#define AppURL       "https://your-website.com"

[Setup]
AppId={{A7B3C2D1-4E5F-6789-ABCD-EF0123456789}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=DesktopPetSetup
SetupIconFile=assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "startup";     Description: "Launch {#AppName} when Windows &starts (recommended)"; GroupDescription: "Startup:"; Flags: checked

[Files]
; The single-file exe produced by build_exe.bat
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}";Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";  Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Add to Windows startup if the user ticked the startup task
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "DesktopPet"; \
  ValueData: """{app}\{#AppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startup

[Run]
; Launch the pet immediately after install (without UAC prompt)
Filename: "{app}\{#AppExeName}"; \
  Description: "Launch {#AppName} now"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Kill the running pet before uninstall
Filename: "taskkill"; Parameters: "/F /IM {#AppExeName}"; Flags: runhidden

[UninstallDelete]
; Remove settings and reminders saved beside the exe
Type: files; Name: "{app}\settings.json"
Type: files; Name: "{app}\reminders.json"
Type: filesandordirs; Name: "{app}\characters"
Type: filesandordirs; Name: "{app}\assets"
Type: dirifempty; Name: "{app}"

[Code]
// Remove from startup registry on uninstall (in case the user never ran the app)
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RegDeleteValue(HKCU,
      'Software\Microsoft\Windows\CurrentVersion\Run',
      'DesktopPet');
end;
