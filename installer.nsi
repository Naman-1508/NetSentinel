; PacketCapture NSIS Installer
; After install, launches via a Task Scheduler task (no UAC on every open)

Unicode True
RequestExecutionLevel admin

!define APP_NAME    "PacketCapture"
!define APP_VER     "1.0.0"
!define APP_EXE     "PacketCapture.exe"
!define TASK_NAME   "PacketCaptureAdmin"
!define INST_DIR    "$PROGRAMFILES64\${APP_NAME}"
!define REG_KEY     "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
!define MUI_ICON    "electron\icon.ico"
!define MUI_UNICON  "electron\icon.ico"

!define MUI_FINISHPAGE_RUN_FUNCTION "LaunchApp"
!define MUI_FINISHPAGE_RUN_TEXT     "Launch PacketCapture now"

Name    "${APP_NAME} ${APP_VER}"
OutFile "dist\PacketCapture-Setup-${APP_VER}.exe"
InstallDir "${INST_DIR}"
InstallDirRegKey HKLM "${REG_KEY}" "InstallLocation"

!include "MUI2.nsh"
!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

; LaunchApp: called from Finish page
Function LaunchApp
  ; Run via the scheduled task (already elevated, no UAC)
  ExecShell "open" "schtasks.exe" '/run /tn "${TASK_NAME}"' SW_HIDE
FunctionEnd

; ── Main section ──────────────────────────────────────────────────────────────
Section "PacketCapture (required)" SecMain
  SectionIn RO

  SetOutPath "$INSTDIR"
  File "dist\win-unpacked\PacketCapture.exe"
  File "dist\win-unpacked\chrome_100_percent.pak"
  File "dist\win-unpacked\chrome_200_percent.pak"
  File "dist\win-unpacked\d3dcompiler_47.dll"
  File "dist\win-unpacked\ffmpeg.dll"
  File "dist\win-unpacked\icudtl.dat"
  File "dist\win-unpacked\libEGL.dll"
  File "dist\win-unpacked\libGLESv2.dll"
  File "dist\win-unpacked\resources.pak"
  File "dist\win-unpacked\snapshot_blob.bin"
  File "dist\win-unpacked\v8_context_snapshot.bin"
  File "dist\win-unpacked\vk_swiftshader.dll"
  File "dist\win-unpacked\vk_swiftshader_icd.json"
  File "dist\win-unpacked\vulkan-1.dll"

  SetOutPath "$INSTDIR\locales"
  File "dist\win-unpacked\locales\*.*"

  SetOutPath "$INSTDIR\resources\app"
  File "dist\win-unpacked\resources\app\package.json"

  SetOutPath "$INSTDIR\resources\app\electron"
  File "dist\win-unpacked\resources\app\electron\main.js"
  File "dist\win-unpacked\resources\app\electron\preload.js"

  SetOutPath "$INSTDIR\resources\app\frontend\out"
  File /r "dist\win-unpacked\resources\app\frontend\out\*"

  SetOutPath "$INSTDIR\resources\backend"
  File "dist\win-unpacked\resources\backend\backend.exe"

  ; ── VBS launcher: silently calls schtasks /run (no window flash) ─────────────
  ; NOTE: using double-quote NSIS strings so $INSTDIR and ${TASK_NAME} expand.
  SetOutPath "$INSTDIR"
  FileOpen  $0 "$INSTDIR\launch.vbs" w
  FileWrite $0 "CreateObject($\"WScript.Shell$\").Run $\"schtasks /run /tn ${TASK_NAME}$\", 0, False"
  FileClose $0

  ; ── Register Task Scheduler task via PowerShell (handles spaces in path) ─────
  ; Write PS1 to $INSTDIR, execute as admin (NSIS is elevated), then delete.
  FileOpen  $1 "$INSTDIR\setup_task.ps1" w
  FileWrite $1 "$$a = New-ScheduledTaskAction -Execute '$INSTDIR\${APP_EXE}'$\r$\n"
  FileWrite $1 "$$p = New-ScheduledTaskPrincipal -GroupId 'BUILTIN\Administrators' -RunLevel Highest$\r$\n"
  FileWrite $1 "Register-ScheduledTask -Force -TaskName '${TASK_NAME}' -Action $$a -Principal $$p$\r$\n"
  FileClose $1
  ExecWait "powershell.exe -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File $\"$INSTDIR\setup_task.ps1$\""
  Delete "$INSTDIR\setup_task.ps1"

  ; ── Start Menu shortcuts (point to VBS, use PacketCapture.exe icon) ──────────
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
    "$SYSDIR\wscript.exe" "$\"$INSTDIR\launch.vbs$\"" \
    "$INSTDIR\${APP_EXE}" 0
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" \
    "$INSTDIR\Uninstall.exe"

  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr   HKLM "${REG_KEY}" "DisplayName"     "${APP_NAME}"
  WriteRegStr   HKLM "${REG_KEY}" "DisplayVersion"  "${APP_VER}"
  WriteRegStr   HKLM "${REG_KEY}" "Publisher"       "PacketCapture"
  WriteRegStr   HKLM "${REG_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr   HKLM "${REG_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr   HKLM "${REG_KEY}" "DisplayIcon"     '"$INSTDIR\${APP_EXE}"'
  WriteRegDWORD HKLM "${REG_KEY}" "NoModify"        1
  WriteRegDWORD HKLM "${REG_KEY}" "NoRepair"        1
SectionEnd

; ── Desktop shortcut (optional) ───────────────────────────────────────────────
Section "Desktop Shortcut" SecDesktop
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" \
    "$SYSDIR\wscript.exe" "$\"$INSTDIR\launch.vbs$\"" \
    "$INSTDIR\${APP_EXE}" 0
SectionEnd

LangString DESC_SecMain    ${LANG_ENGLISH} "Core application files (required)"
LangString DESC_SecDesktop ${LANG_ENGLISH} "Add a shortcut on your Desktop"

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain}    $(DESC_SecMain)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} $(DESC_SecDesktop)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ── Uninstall ─────────────────────────────────────────────────────────────────
Section "Uninstall"
  nsExec::ExecToLog 'schtasks /delete /tn "${TASK_NAME}" /f'
  Delete   "$DESKTOP\${APP_NAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APP_NAME}"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKLM "${REG_KEY}"
SectionEnd
