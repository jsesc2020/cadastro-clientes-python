$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location (Join-Path $root '..')

# Add Chocolatey-installed tool paths to PATH
$env:Path += ";C:\Program Files (x86)\NSIS"

# Refresh environment to pick up recently installed tools (NSIS, etc.)
if (Test-Path 'C:\ProgramData\chocolatey\bin\refreshenv.cmd') {
    & cmd /c 'C:\ProgramData\chocolatey\bin\refreshenv.cmd' | Out-Null
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Check if makensis is available
if (-not (Get-Command makensis -ErrorAction SilentlyContinue)) {
    Write-Warning "makensis not found in PATH. Checking common installation paths..."
    $nsisPath = "C:\Program Files (x86)\NSIS\makensis.exe"
    if (Test-Path $nsisPath) {
        Write-Host "Found makensis at $nsisPath"
        Set-Alias -Name makensis -Value $nsisPath
    } else {
        Write-Warning "NSIS not installed or makensis.exe not found. Skipping NSIS build."
        exit 0
    }
}

Write-Host 'Installing PyInstaller...'
pip install pyinstaller

Write-Host 'Building executable with PyInstaller...'
pyinstaller --onefile --add-data "data;data" --add-data "server/static;server/static" server/app.py

if (-not (Test-Path dist\app.exe)) {
    throw 'Build failed: dist\app.exe not found'
}

# Create output directory for installer BEFORE calling makensis
$installerOutputDir = Join-Path (Join-Path (Get-Location) "dist") "installer"
New-Item -ItemType Directory -Path $installerOutputDir -Force | Out-Null
Write-Host "Output directory ready: $installerOutputDir"

Write-Host 'Generating NSIS installer...'
if (-not (Test-Path installer\windows_installer.nsi)) {
    throw 'NSIS script not found: installer\windows_installer.nsi'
}

# Call makensis - it will use OutFile path from the NSI script
Write-Host "Running makensis from: $(Get-Location)"
& makensis installer\windows_installer.nsi

if ($LASTEXITCODE -ne 0) {
    Write-Warning "NSIS build failed with exit code $LASTEXITCODE"
    if (Test-Path "$installerOutputDir\CadastroClientesInstaller.exe") {
        Write-Host "Installer file exists despite warnings. Continuing..."
    } else {
        throw "NSIS build failed and installer file was not created"
    }
}

if (Test-Path "$installerOutputDir\CadastroClientesInstaller.exe") {
    Write-Host 'Build complete. Installer created at' "$installerOutputDir\CadastroClientesInstaller.exe"
} else {
    Write-Warning "Installer file not found at expected location. Checking directory contents..."
    Get-ChildItem $installerOutputDir -Recurse
}