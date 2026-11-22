; AI-BS Standalone Bloons TD 6 Trainer NSIS Script
; --------------------------------------------------

Name "AI-BS Game Trainer: Bloons TD 6"
OutFile "AI-BS_Trainer_Setup_v2.21.0.exe"
InstallDir "$PROGRAMFILES\AI-BS\Trainer"
RequestExecutionLevel admin

Page directory
Page instfiles

Section "AI-BS Trainer (Required)"
  SectionIn RO
  
  ; Set output path to the installation directory
  SetOutPath $INSTDIR
  
  ; Include the standalone PyInstaller compiled binary
  File "dist\AI-BS_Trainer.exe"
  
  ; Create Desktop Shortcut
  CreateShortcut "$DESKTOP\AI-BS BTD6 Trainer.lnk" "$INSTDIR\AI-BS_Trainer.exe" "" "$INSTDIR\AI-BS_Trainer.exe" 0
  
  ; Create Start Menu Shortcuts
  CreateDirectory "$SMPROGRAMS\AI-BS Trainer"
  CreateShortcut "$SMPROGRAMS\AI-BS Trainer\AI-BS BTD6 Trainer.lnk" "$INSTDIR\AI-BS_Trainer.exe" "" "$INSTDIR\AI-BS_Trainer.exe" 0
  CreateShortcut "$SMPROGRAMS\AI-BS Trainer\Uninstall.lnk" "$INSTDIR\uninstall.exe"
  
  ; Create Uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
  ; Remove Files
  Delete "$INSTDIR\AI-BS_Trainer.exe"
  Delete "$INSTDIR\uninstall.exe"
  
  ; Remove Shortcuts
  Delete "$DESKTOP\AI-BS BTD6 Trainer.lnk"
  Delete "$SMPROGRAMS\AI-BS Trainer\AI-BS BTD6 Trainer.lnk"
  Delete "$SMPROGRAMS\AI-BS Trainer\Uninstall.lnk"
  RMDir "$SMPROGRAMS\AI-BS Trainer"
  
  ; Remove Directory
  RMDir "$INSTDIR"
SectionEnd
