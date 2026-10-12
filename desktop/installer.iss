; Inno Setup script for the ehpa Billing Button desktop app (built by .github/workflows/desktop-build.yml on a Windows runner).
; What it does: installs the PyInstaller folder build, puts "ehpa Billing Button" on the desktop and in the Start menu, and
; registers the ehpa-billing:// link scheme so the Run button on the billing artifacts can open the app.
#define MyAppName "ehpa Billing Button"
#define MyAppVersion GetEnv("APP_VERSION")
#if MyAppVersion == ""
  #define MyAppVersion "1.0.0"
#endif
#define MyAppExe "ehpa-billing-button.exe"

[Setup]
AppId={{8C3C7A2E-5B61-4F1E-9B55-ehpabilling01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Effinger Health PA
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=ehpa-billing-button-setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Put the Billing Button on the desktop"; GroupDescription: "Shortcuts:"

[Files]
Source: "dist\ehpa-billing-button\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Registry]
; the ehpa-billing:// link scheme (a Run button on a billing artifact opens the app with ehpa-billing://run?mode=dry|live)
Root: HKA; Subkey: "Software\Classes\ehpa-billing"; ValueType: string; ValueName: ""; ValueData: "URL:ehpa Billing Button"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\ehpa-billing"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\ehpa-billing\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExe},0"
Root: HKA; Subkey: "Software\Classes\ehpa-billing\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExe}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Open the Billing Button now"; Flags: nowait postinstall skipifsilent
