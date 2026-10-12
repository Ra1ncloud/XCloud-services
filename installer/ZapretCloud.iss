; ZapretCloud — скрипт установщика Inno Setup 6
#define AppName "ZapretCloud"
#define AppVersion "2.2.14"
#define AppExe "ZapretCloud.exe"

[Setup]
AppId={{B6C4F7A2-3E91-4D8B-A5C0-7F1E2D9A4C63}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppName}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=ZapretCloud_Setup_{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
ShowLanguageDialog=auto

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"; LicenseFile: "license_ru.txt"; InfoBeforeFile: "info_ru.txt"
Name: "english"; MessagesFile: "compiler:Default.isl"; LicenseFile: "license_en.txt"; InfoBeforeFile: "info_en.txt"

[CustomMessages]
russian.AutoStart=Запускать ZapretCloud вместе с Windows
english.AutoStart=Start ZapretCloud with Windows
russian.Other=Дополнительно:
english.Other=Other:
russian.SetAutostart=Настройка автозапуска...
english.SetAutostart=Configuring autostart...
russian.DelData=Удалить также ваши настройки, пресеты, свои сайты и профили (%AppData%\ZapretCloud)?
english.DelData=Also delete your settings, presets, custom sites and profiles (%AppData%\ZapretCloud)?

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "{cm:AutoStart}"; GroupDescription: "{cm:Other}"; Flags: unchecked

[Files]
Source: "..\dist\ZapretCloud\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "license_ru.txt"; DestDir: "{app}"; DestName: "LICENSES.txt"; Languages: russian
Source: "license_en.txt"; DestDir: "{app}"; DestName: "LICENSES.txt"; Languages: english

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Parameters: "--set-autostart"; StatusMsg: "{cm:SetAutostart}"; Flags: runhidden waituntilterminated; Tasks: autostart
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent runascurrentuser
; автообновление из программы (тихая установка) — сразу запускаем новую версию
Filename: "{app}\{#AppExe}"; Flags: nowait runascurrentuser; Check: WizardSilent

[UninstallRun]
Filename: "{app}\{#AppExe}"; Parameters: "--vpn-cleanup"; Flags: runhidden waituntilterminated; RunOnceId: "VpnCleanup"
Filename: "{sys}\taskkill.exe"; Parameters: "/F /T /IM {#AppExe}"; Flags: runhidden; RunOnceId: "KillApp"
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM winws.exe"; Flags: runhidden; RunOnceId: "KillWinws"
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM winws2.exe"; Flags: runhidden; RunOnceId: "KillWinws2"
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM sing-box.exe"; Flags: runhidden; RunOnceId: "KillSingBox"
Filename: "{sys}\sc.exe"; Parameters: "stop Monkey"; Flags: runhidden; RunOnceId: "StopMonkey"
Filename: "{sys}\sc.exe"; Parameters: "delete Monkey"; Flags: runhidden; RunOnceId: "DelMonkey"
Filename: "{sys}\sc.exe"; Parameters: "stop WinDivert"; Flags: runhidden; RunOnceId: "StopWD"
Filename: "{sys}\sc.exe"; Parameters: "delete WinDivert"; Flags: runhidden; RunOnceId: "DelWD"
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ZapretCloud /F"; Flags: runhidden; RunOnceId: "DelTask"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\engine\lists\zc_custom"
Type: filesandordirs; Name: "{app}\engine\vpn"
Type: dirifempty; Name: "{app}"

[Code]
procedure Run(const F, P: String);
var Code: Integer;
begin
  Exec(F, P, '', SW_HIDE, ewWaitUntilTerminated, Code);
end;

// перед установкой/обновлением останавливаем программу и драйвер, иначе файлы заняты
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Run(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM ZapretCloud.exe');
  Run(ExpandConstant('{sys}\taskkill.exe'), '/F /IM winws.exe');
  Run(ExpandConstant('{sys}\taskkill.exe'), '/F /IM winws2.exe');
  Run(ExpandConstant('{sys}\sc.exe'), 'stop Monkey');
  Run(ExpandConstant('{sys}\sc.exe'), 'delete Monkey');
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent then
    if MsgBox(CustomMessage('DelData'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DelTree(ExpandConstant('{userappdata}\ZapretCloud'), True, True, True);
end;
