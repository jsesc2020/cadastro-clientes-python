$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location (Join-Path $root '..')

# Refresh environment to pick up recently installed tools (NSIS, etc.)
if (Test-Path 'C:\ProgramData\chocolatey\bin\refreshenv.cmd') {
    & cmd /c 'C:\ProgramData\chocolatey\bin\refreshenv.cmd'
}

Write-Host 'Installing PyInstaller...'
pip install pyinstaller

Write-Host 'Building executable with PyInstaller...'
pyinstaller --onefile --add-data "data;data" --add-data "server/static;server/static" server/app.py

if (-not (Test-Path dist\app.exe)) {
    throw 'Build failed: dist\app.exe not found'
}

if (-not (Test-Path dist\installer)) {
    New-Item -ItemType Directory -Path dist\installer | Out-Null
}

Write-Host 'Generating NSIS installer...'
if (-not (Test-Path installer\windows_installer.nsi)) {
    throw 'NSIS script not found: installer\windows_installer.nsi'
}
makensis installer\windows_installer.nsi

Write-Host 'Build complete. Installer created at dist\installer\CadastroClientesInstaller.exe'