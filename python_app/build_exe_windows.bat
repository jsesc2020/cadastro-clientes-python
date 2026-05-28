@echo off
REM Build Windows executable with PyInstaller
pip install pyinstaller
pyinstaller --onefile --add-data "data;data" --add-data "server/static;server/static" server/app.py
echo Build complete. Output in dist\app.exe (check PyInstaller console for exact filename)
pause