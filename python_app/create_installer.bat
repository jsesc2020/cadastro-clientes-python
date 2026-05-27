@echo off
REM Build single-file exe and NSIS installer
pip install pyinstaller
pyinstaller --onefile --add-data "data;data" --add-data "server/static;server/static" server/app.py
if not exist dist\app.exe (
  echo Build failed: dist\app.exe not found
  exit /b 1
)
if not exist dist\installer mkdir dist\installer
if exist installer\windows_installer.nsi (
  makensis installer\windows_installer.nsi
) else (
  echo NSIS script not found: installer\windows_installer.nsi
  exit /b 1
)
pause