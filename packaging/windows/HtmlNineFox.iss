#ifndef MyVersion
  #define MyVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "."
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif
#ifndef IconFile
  #define IconFile "htmlninefox.ico"
#endif

[Setup]
AppId={{CC732B92-C625-48B2-B20D-CF8588C6B0B4}
AppName=Html九尾狐
AppVersion={#MyVersion}
AppPublisher=KratosLee · Html九尾狐项目组
DefaultDirName={localappdata}\Programs\HtmlNineFox
DefaultGroupName=Html九尾狐
OutputDir={#OutputDir}
OutputBaseFilename=HtmlNineFox-Setup-{#MyVersion}
SetupIconFile={#IconFile}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
WizardStyle=modern
UninstallDisplayIcon={app}\HtmlNineFox.exe

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Html九尾狐"; Filename: "{app}\HtmlNineFox.exe"
Name: "{autodesktop}\Html九尾狐"; Filename: "{app}\HtmlNineFox.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加选项："

[Run]
Filename: "{app}\HtmlNineFox.exe"; Description: "启动 Html九尾狐"; Flags: nowait postinstall skipifsilent
