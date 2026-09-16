; =====================================================================
; AI-BS SOVEREIGN INTELLIGENCE STUDIO - OFFICIAL INNO SETUP SCRIPT
; Version: 5.296.0
; Architecture: Windows 11 / Windows 10 (x64)
; =====================================================================

#define MyAppName "AI-BS Sovereign Studio"
#define MyAppVersion "5.296.0"
#define MyAppPublisher "Brett Stehouwer / Stehouwer Publishing"
#define MyAppURL "https://ai-bs-dashboard.web.app"
#define MyAppExeName "Launch_Desktop_Studio.vbs"

[Setup]
AppId={{E589417A-8991-497B-9BDC-7281D6277C50}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\AI-BS Sovereign Studio
UsePreviousAppDir=no
DisableProgramGroupPage=no
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=AI_BS_Studio_Setup_v5.296.0
SetupIconFile=app_icon.ico
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Primary Desktop Launchers & Runners
Source: "Launch_Desktop_Studio.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "Launch_Desktop_Studio.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "Launch_Broadcast_Studio.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "Shutdown_Desktop_Studio.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "Update_Desktop_Studio.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "serve_desktop.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "aibs_updater.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\Launch_AI_BS.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\Shutdown_AI_BS.bat"; DestDir: "{app}"; Flags: ignoreversion

; Production Frontend Single Page Application (Sovereign Studio, Wave Studio, DAW Studio, Repair Guide)
Source: "..\frontend\dist\*"; DestDir: "{app}\frontend_dist"; Flags: ignoreversion recursesubdirs createallsubdirs

; Production Broadcast Studio Application
Source: "..\BroadcastStudioApp\dist\*"; DestDir: "{app}\broadcast_dist"; Flags: ignoreversion recursesubdirs createallsubdirs

; Go Commercial Engine & Gateway
Source: "..\go-core\aibs_engine.exe"; DestDir: "{app}\go-core"; Flags: ignoreversion

; Broadcast Virtual Camera Drivers
Source: "..\BroadcastStudioApp\drivers\*"; DestDir: "{app}\drivers"; Flags: ignoreversion recursesubdirs createallsubdirs

; Python Backend Daemons & Routers
Source: "..\backend\*.py"; DestDir: "{app}\backend"; Flags: ignoreversion; Excludes: "*__pycache__*,*.log,*.tmp,*.git*,test_*"
Source: "..\backend\requirements.txt"; DestDir: "{app}\backend"; Flags: ignoreversion
Source: "..\backend\server.js"; DestDir: "{app}\backend"; Flags: ignoreversion
Source: "..\backend\compute_telemetry.json"; DestDir: "{app}\backend"; Flags: ignoreversion
Source: "..\backend\pearl_payout_ledger.json"; DestDir: "{app}\backend"; Flags: ignoreversion
Source: "..\backend\commercial_gateway\*"; DestDir: "{app}\backend\commercial_gateway"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*__pycache__*"
Source: "..\backend\routers\*"; DestDir: "{app}\backend\routers"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*__pycache__*"

; Documentation & Architectural Ledgers
Source: "..\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
; Root URI Scheme Handler (aibs://)
Root: HKA; Subkey: "Software\Classes\aibs"; ValueType: string; ValueName: ""; ValueData: "URL:AI-BS Sovereign Protocol"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\aibs"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\aibs\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\app_icon.ico,0"
Root: HKA; Subkey: "Software\Classes\aibs\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Launch_Desktop_Studio.bat"" ""%1"""

; File Association .aibs (AI-BS Master Studio Project)
Root: HKA; Subkey: "Software\Classes\.aibs"; ValueType: string; ValueName: ""; ValueData: "AIBS.Project"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\AIBS.Project"; ValueType: string; ValueName: ""; ValueData: "AI-BS Master Studio Project"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\AIBS.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\app_icon.ico,0"
Root: HKA; Subkey: "Software\Classes\AIBS.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Launch_Desktop_Studio.bat"" ""%1"""

; File Association .daw (AI-BS Neural DAW Track)
Root: HKA; Subkey: "Software\Classes\.daw"; ValueType: string; ValueName: ""; ValueData: "AIBS.DAWTrack"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\AIBS.DAWTrack"; ValueType: string; ValueName: ""; ValueData: "AI-BS Neural DAW Track"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\AIBS.DAWTrack\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\app_icon.ico,0"
Root: HKA; Subkey: "Software\Classes\AIBS.DAWTrack\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Launch_Desktop_Studio.bat"" ""%1"""

; File Association .stehouwer (Stehouwer Wave Audio Session)
Root: HKA; Subkey: "Software\Classes\.stehouwer"; ValueType: string; ValueName: ""; ValueData: "Stehouwer.WaveSession"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Stehouwer.WaveSession"; ValueType: string; ValueName: ""; ValueData: "Stehouwer Wave Audio Session"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Stehouwer.WaveSession\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\app_icon.ico,0"
Root: HKA; Subkey: "Software\Classes\Stehouwer.WaveSession\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Launch_Desktop_Studio.bat"" ""%1"""

[Icons]
; Start Menu Program Group
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Comment: "Launch AI-BS Sovereign Intelligence Studio"
Name: "{group}\AI-BS Check for Updates"; Filename: "{app}\Update_Desktop_Studio.bat"; IconFilename: "{app}\app_icon.ico"; Comment: "In-place patch and update AI-BS Sovereign Studio without re-running installer"
Name: "{group}\AI-BS Broadcast Studio"; Filename: "{app}\Launch_Broadcast_Studio.bat"; IconFilename: "{app}\app_icon.ico"; Comment: "Launch AI-BS Broadcast & DAW Workstation"
Name: "{group}\AI-BS Matrix Boot Sequence"; Filename: "{app}\Launch_AI_BS.bat"; IconFilename: "{app}\app_icon.ico"; Comment: "Execute Full Matrix Boot Sequence"
Name: "{group}\AI-BS Clean Shutdown"; Filename: "{app}\Shutdown_Desktop_Studio.bat"; IconFilename: "{app}\app_icon.ico"; Comment: "Gracefully Stop All AI-BS Background Processes"
Name: "{group}\AI-BS Master Ecosystem Manual"; Filename: "{app}\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md"; Comment: "Open AI-BS Ecosystem Technical Manual"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop Shortcuts
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon; Comment: "Launch AI-BS Sovereign Intelligence Studio"
Name: "{autodesktop}\AI-BS Check Updates"; Filename: "{app}\Update_Desktop_Studio.bat"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon; Comment: "In-place patch and update AI-BS Sovereign Studio without re-running installer"
Name: "{autodesktop}\AI-BS Broadcast Studio"; Filename: "{app}\Launch_Broadcast_Studio.bat"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon; Comment: "Launch AI-BS Broadcast & DAW Workstation"
Name: "{autodesktop}\AI-BS Matrix Boot"; Filename: "{app}\Launch_AI_BS.bat"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon; Comment: "Execute Full Matrix Boot Sequence"
Name: "{autodesktop}\AI-BS Shutdown"; Filename: "{app}\Shutdown_Desktop_Studio.bat"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon; Comment: "Stop All AI-BS Background Processes"

[Run]
Filename: "{app}\Launch_Desktop_Studio.bat"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
