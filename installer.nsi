; ============================================================
;  NetSentinel — AI-Powered Network Threat Detection
;  Built with NSIS 3.x + MUI2
; ============================================================

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; ─── App Metadata ─────────────────────────────────────────
!define APP_NAME        "NetSentinel"
!define APP_VERSION     "1.0.0"
!define APP_PUBLISHER   "NetSentinel Labs"
!define APP_URL         "https://github.com/Naman-1508/PacketCapture"
!define APP_EXE         "NetSentinel.exe"
!define UNINSTALLER     "Uninstall.exe"
!define REG_UNINST_KEY  "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

Name             "${APP_NAME} ${APP_VERSION}"
OutFile          "NetSentinel-Setup-${APP_VERSION}.exe"
InstallDir       "$PROGRAMFILES64\${APP_NAME}"
InstallDirRegKey HKLM "${REG_UNINST_KEY}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor    /SOLID lzma
SetCompressorDictSize 32

; ─── Branding ─────────────────────────────────────────────
BrandingText     "${APP_NAME} ${APP_VERSION} — Real-Time Threat Detection"

; ─── MUI Settings ─────────────────────────────────────────
!define MUI_ABORTWARNING
!define MUI_ICON                    "assets\icon.ico"
!define MUI_UNICON                  "assets\icon.ico"
!define MUI_FINISHPAGE_RUN          "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT     "Launch NetSentinel"
!define MUI_FINISHPAGE_LINK         "Visit Project on GitHub"
!define MUI_FINISHPAGE_LINK_LOCATION "${APP_URL}"

; ─── Installer Pages ──────────────────────────────────────
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE       "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; ─── Uninstaller Pages ────────────────────────────────────
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; ─── Version Info ─────────────────────────────────────────
VIProductVersion                    "1.0.0.0"
VIAddVersionKey "ProductName"       "${APP_NAME}"
VIAddVersionKey "ProductVersion"    "${APP_VERSION}"
VIAddVersionKey "CompanyName"       "${APP_PUBLISHER}"
VIAddVersionKey "FileDescription"   "NetSentinel Installer"
VIAddVersionKey "FileVersion"       "${APP_VERSION}"
VIAddVersionKey "LegalCopyright"    "© 2025 ${APP_PUBLISHER}"

; ─── Install Section ──────────────────────────────────────
Section "NetSentinel" SecMain
  SectionIn RO   ; Required — cannot be deselected

  ; Kill old process if running
  nsExec::ExecToStack 'taskkill /F /IM "${APP_EXE}" /T'

  SetOutPath "$INSTDIR"

  ; Main executable (Python/PyWebView backend bundled)
  File "/oname=${APP_EXE}" "backend\dist\NetSentinel.exe"

  ; ML Risk Engine (Bundled FastAPI/Scikit/XGBoost backend)
  SetOutPath "$INSTDIR\ml_engine"
  File /r "ml_risk_engine\dist\ml_engine\*.*"

  ; Pre-trained models
  SetOutPath "$INSTDIR\ml_risk_engine\models\saved"
  File /r "ml_risk_engine\models\saved\*.*"

  ; App icon
  SetOutPath "$INSTDIR"
  File "/oname=icon.ico" "assets\icon.ico"

  ; Frontend static files
  SetOutPath "$INSTDIR\frontend\out"
  File /r "frontend\out\*.*"

  ; ── Start Menu Shortcut ───────────────────────────────
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
                  "$INSTDIR\${APP_EXE}" "" \
                  "$INSTDIR\icon.ico" 0 SW_SHOWNORMAL "" \
                  "Real-time Network Threat Detection & ML Analysis"
  CreateShortcut  "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" \
                  "$INSTDIR\${UNINSTALLER}"

  ; ── Desktop Shortcut ──────────────────────────────────
  CreateShortcut  "$DESKTOP\${APP_NAME}.lnk" \
                  "$INSTDIR\${APP_EXE}" "" \
                  "$INSTDIR\icon.ico" 0 SW_SHOWNORMAL "" \
                  "Real-time Network Threat Detection & ML Analysis"

  ; ── Registry — Add/Remove Programs entry ──────────────
  WriteRegStr   HKLM "${REG_UNINST_KEY}" "DisplayName"      "${APP_NAME}"
  WriteRegStr   HKLM "${REG_UNINST_KEY}" "DisplayVersion"   "${APP_VERSION}"
  WriteRegStr   HKLM "${REG_UNINST_KEY}" "Publisher"        "${APP_PUBLISHER}"
  WriteRegStr   HKLM "${REG_UNINST_KEY}" "URLInfoAbout"     "${APP_URL}"
  WriteRegStr   HKLM "${REG_UNINST_KEY}" "InstallLocation"  "$INSTDIR"
  WriteRegStr   HKLM "${REG_UNINST_KEY}" "UninstallString"  '"$INSTDIR\${UNINSTALLER}"'
  WriteRegStr   HKLM "${REG_UNINST_KEY}" "DisplayIcon"      "$INSTDIR\icon.ico"
  WriteRegDWORD HKLM "${REG_UNINST_KEY}" "NoModify"         1
  WriteRegDWORD HKLM "${REG_UNINST_KEY}" "NoRepair"         1

  ; Compute and write install size
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "${REG_UNINST_KEY}" "EstimatedSize" "$0"

  ; Write uninstaller
  WriteUninstaller "$INSTDIR\${UNINSTALLER}"

SectionEnd

; ─── Uninstall Section ────────────────────────────────────
Section "Uninstall"
  ; Kill process if running
  nsExec::ExecToStack 'taskkill /F /IM "${APP_EXE}" /T'

  ; Remove shortcuts
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
  RMDir  "$SMPROGRAMS\${APP_NAME}"

  ; Remove files
  Delete "$INSTDIR\${APP_EXE}"
  Delete "$INSTDIR\${UNINSTALLER}"
  RMDir /r "$INSTDIR\frontend"
  RMDir  "$INSTDIR"

  ; Remove registry entry
  DeleteRegKey HKLM "${REG_UNINST_KEY}"

SectionEnd
