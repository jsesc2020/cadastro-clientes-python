; NSIS installer script for Cadastro Clientes Local
; Produz um instalador que copia app.exe, banco local e frontend estático.

Name "Cadastro Clientes Local"
OutFile "dist\installer\CadastroClientesInstaller.exe"
InstallDir "$PROGRAMFILES\CadastroClientes"
RequestExecutionLevel user
ShowInstDetails show
ShowUninstDetails show

Section "Install"
  SetOutPath "$INSTDIR"
  File "..\dist\app.exe"

  CreateDirectory "$INSTDIR\data"
  SetOutPath "$INSTDIR\data"
  File /r "..\data\*"

  CreateDirectory "$INSTDIR\server\static"
  SetOutPath "$INSTDIR\server\static"
  File /r "..\server\static\*"

  CreateDirectory "$SMPROGRAMS\CadastroClientes"
  CreateShortCut "$SMPROGRAMS\CadastroClientes\CadastroClientes.lnk" "$INSTDIR\app.exe" "" "$INSTDIR\app.exe"
  CreateShortCut "$DESKTOP\CadastroClientes.lnk" "$INSTDIR\app.exe" "" "$INSTDIR\app.exe"
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\CadastroClientes\CadastroClientes.lnk"
  RMDir "$SMPROGRAMS\CadastroClientes"
  Delete "$DESKTOP\CadastroClientes.lnk"
  Delete "$INSTDIR\app.exe"
  RMDir /r "$INSTDIR\data"
  RMDir /r "$INSTDIR\server\static"
  RMDir "$INSTDIR\server"
  RMDir "$INSTDIR"
SectionEnd
