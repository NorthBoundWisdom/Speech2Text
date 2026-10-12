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
AppName=SonaFolio
AppVersion={#ReleaseVersion}
VersionInfoVersion={#NumericVersion}
DefaultDirName={autopf}\SonaFolioQt
DefaultGroupName=SonaFolio
OutputDir={#OutputDir}
OutputBaseFilename=SonaFolioQt-v{#ReleaseVersion}-Windows-x64-Setup
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
Compression=lzma2
SolidCompression=yes
LicenseFile={#SourceDir}\licenses\LICENSE
UninstallDisplayIcon={app}\bin\SonaFolioQt.exe
[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\SonaFolio"; Filename: "{app}\bin\SonaFolioQt.exe"
[Run]
Filename: "{app}\vc_redist.x64.exe"; Parameters: "/install /passive /norestart"; StatusMsg: "Installing Microsoft Visual C++ Runtime..."; Flags: waituntilterminated
Filename: "{app}\bin\SonaFolioQt.exe"; Description: "Launch SonaFolio"; Flags: nowait postinstall skipifsilent
