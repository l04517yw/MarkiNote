; MarkiNote Windows 安装包脚本（Inno Setup 6）
;
; 前置条件：
;   1. 先打包：  pyinstaller MarkiNote.spec --noconfirm
;      产物应在 dist\MarkiNote\ 下
;   2. 安装 Inno Setup 6：https://jrsoftware.org/isdl.php
;
; 编译：
;   iscc installer\MarkiNote.iss
;   产物：installer\Output\MarkiNote-<版本>-setup.exe
;
; 注意：用户数据存放在 %APPDATA%\MarkiNote\lib，不随卸载删除，
;       避免升级或卸载时丢失笔记。卸载时只做提示，不主动清理。

#define AppName        "MarkiNote"
#define AppVersion     "1.0.1"
#define AppPublisher   "wink-wink-wink555"
#define AppURL         "https://github.com/l04517yw/MarkiNote"
#define AppExeName     "MarkiNote.exe"
#define SourceDir      "..\dist\MarkiNote"

[Setup]
AppId={{B7C3F1A2-6D4E-4F3B-9A21-8E5C7D0B4A93}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=Output
OutputBaseFilename={#AppName}-{#AppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
MinVersion=10.0
; 打包产物里包含大量静态资源，关掉"每个文件都刷新进度"以加快安装
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}

[Languages]
; ChineseSimplified.isl 是 Inno Setup 的非官方翻译，官方安装包不自带，
; 因此随项目一起放在 installer/ 下，保证克隆仓库后可直接编译。
; 来源：https://github.com/jrsoftware/issrc (Files/Languages/Unofficial)
Name: "chinese"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: checkedonce
Name: "launchapp";   Description: "安装完成后启动 {#AppName}"; GroupDescription: "附加任务:"; Flags: checkedonce

[Files]
; 整个 PyInstaller onedir 产物
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"
Name: "{group}\卸载 {#AppName}";      Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";     Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "启动 {#AppName}"; Flags: nowait postinstall skipifsilent; Tasks: launchapp

[UninstallDelete]
; 仅清理卸载后残留的空目录，用户笔记在 %APPDATA% 下，不动
Type: dirifempty; Name: "{app}"
