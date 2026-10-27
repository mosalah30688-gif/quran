; سراج — مثبّت Windows حديث بنمط per-user، لا يحتاج صلاحية مدير.
#define MyAppName "سراج"
#define MyAppDescription "قرآن كريم"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#ifndef MySourceDir
  #define MySourceDir "..\..\dist\Siraj"
#endif
#ifndef MyOutputDir
  #define MyOutputDir "..\..\release"
#endif

[Setup]
AppId={{EDF6A7C0-7173-4657-A0DF-08E16EEFFC4A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Siraj
AppPublisherURL=https://github.com/mosalah30688-gif/quran
AppSupportURL=https://github.com/mosalah30688-gif/quran/issues
AppUpdatesURL=https://github.com/mosalah30688-gif/quran/releases
AppComments={#MyAppDescription}
DefaultDirName={localappdata}\Programs\Siraj
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#MyOutputDir}
OutputBaseFilename=Siraj-Quran-Setup-{#MyAppVersion}-x64
SetupIconFile=..\..\assets\siraj.ico
UninstallDisplayIcon={app}\Siraj.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
CloseApplications=force
RestartApplications=yes
CloseApplicationsFilter=Siraj.exe
SetupLogging=yes
UsePreviousAppDir=yes
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany=Siraj
VersionInfoDescription={#MyAppName} - {#MyAppDescription}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCopyright=Copyright © 2026 Siraj
#ifdef SignToolName
SignTool={#SignToolName}
SignedUninstaller=yes
#endif

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "إنشاء اختصار على سطح المكتب"; GroupDescription: "اختصارات إضافية:"; Flags: unchecked
Name: "launchstartup"; Description: "تشغيل سراج بعد تسجيل الدخول"; GroupDescription: "خيارات التشغيل:"; Flags: unchecked

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\سراج"; Filename: "{app}\Siraj.exe"; Comment: "قرآن كريم"; WorkingDir: "{app}"
Name: "{autodesktop}\سراج"; Filename: "{app}\Siraj.exe"; Comment: "قرآن كريم"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\سراج"; Filename: "{app}\Siraj.exe"; WorkingDir: "{app}"; Tasks: launchstartup

[Run]
Filename: "{app}\Siraj.exe"; Description: "تشغيل سراج"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\Siraj.exe"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
