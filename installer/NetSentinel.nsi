!include "MUI2.nsh"

Name "NetSentinel"
OutFile "..\backend\dist\NetSentinel-Setup.exe"
InstallDir "$PROGRAMFILES64\NetSentinel"
RequestExecutionLevel admin
Unicode true

!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File "..\backend\dist\NetSentinel.exe"

  CreateDirectory "$SMPROGRAMS\NetSentinel"
  CreateShortcut "$SMPROGRAMS\NetSentinel\NetSentinel.lnk" "$INSTDIR\NetSentinel.exe"
  CreateShortcut "$DESKTOP\NetSentinel.lnk" "$INSTDIR\NetSentinel.exe"

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NetSentinel" "DisplayName" "NetSentinel"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NetSentinel" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NetSentinel" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NetSentinel" "DisplayVersion" "1.0.0"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NetSentinel" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NetSentinel" "NoRepair" 1
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\NetSentinel.lnk"
  Delete "$SMPROGRAMS\NetSentinel\NetSentinel.lnk"
  RMDir "$SMPROGRAMS\NetSentinel"

  Delete "$INSTDIR\NetSentinel.exe"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NetSentinel"
SectionEnd
