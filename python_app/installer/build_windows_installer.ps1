$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location (Join-Path $root '..')

# Adiciona NSIS ao PATH
$env:Path += ";C:\Program Files (x86)\NSIS"

# Verifica se makensis esta disponivel
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

# Instala dependencias do projeto + PyInstaller
Write-Host 'Installing dependencies...'
pip install -r requirements.txt
pip install pyinstaller

# Garante que main.py existe na raiz do python_app
if (-not (Test-Path main.py)) {
    throw 'main.py nao encontrado. Certifique-se de que o arquivo existe em python_app/main.py'
}

Write-Host 'Building executable with PyInstaller...'
pyinstaller --onefile `
    --name app `
    --add-data "server/static;server/static" `
    --hidden-import flask `
    --hidden-import flask.json `
    --hidden-import flask.logging `
    --hidden-import werkzeug `
    --hidden-import werkzeug.security `
    --hidden-import werkzeug.routing `
    --hidden-import werkzeug.exceptions `
    --hidden-import werkzeug.middleware.proxy_fix `
    --hidden-import jwt `
    --hidden-import bcrypt `
    --hidden-import dotenv `
    --hidden-import sqlite3 `
    --hidden-import server `
    --hidden-import server.app `
    --hidden-import server.routes `
    --hidden-import server.routes.clients `
    --hidden-import server.routes.contracts `
    --hidden-import server.routes.pontos `
    --hidden-import server.routes.proprietarios `
    --collect-all flask `
    --collect-all werkzeug `
    --collect-all bcrypt `
    --collect-all jwt `
    main.py

if (-not (Test-Path dist\app.exe)) {
    throw 'Build falhou: dist\app.exe nao foi gerado'
}

Write-Host 'Executavel gerado com sucesso: dist\app.exe'

# Cria diretorio de saida para o instalador (compativel com PowerShell 5.1)
$installerOutputDir = Join-Path (Join-Path (Get-Location) "dist") "installer"
New-Item -ItemType Directory -Path $installerOutputDir -Force | Out-Null
Write-Host "Output directory ready: $installerOutputDir"

Write-Host 'Generating NSIS installer...'
if (-not (Test-Path installer\windows_installer.nsi)) {
    throw 'NSIS script not found: installer\windows_installer.nsi'
}

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
