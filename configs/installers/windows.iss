#ifndef SourceDir
#error SourceDir is required
#endif
#ifndef OutputDir
#error OutputDir is required
#endif
#ifndef ReleaseVersion
#error ReleaseVersion is required
#endif
#ifndef NumericVersion
#error NumericVersion is required
#endif
[Setup]
AppId={{944B08B6-35BA-4B8F-90B8-16B4F750F269}
AppName=Audio2TextQt
AppVersion={#ReleaseVersion}
VersionInfoVersion={#NumericVersion}
DefaultDirName={autopf}\Audio2TextQt
DefaultGroupName=Audio2TextQt
OutputDir={#OutputDir}
OutputBaseFilename=Audio2TextQt-v{#ReleaseVersion}-Windows-x64-Setup
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
Compression=lzma2
SolidCompression=yes
LicenseFile={#SourceDir}\licenses\LICENSE
UninstallDisplayIcon={app}\bin\Audio2TextQt.exe
[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Audio2TextQt"; Filename: "{app}\bin\Audio2TextQt.exe"
[Run]
Filename: "{app}\vc_redist.x64.exe"; Parameters: "/install /passive /norestart"; StatusMsg: "Installing Microsoft Visual C++ Runtime..."; Flags: waituntilterminated
Filename: "{app}\bin\Audio2TextQt.exe"; Description: "Launch Audio2TextQt"; Flags: nowait postinstall skipifsilent
