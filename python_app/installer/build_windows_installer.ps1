$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location (Join-Path $root '..')

# Adiciona NSIS ao PATH
$env:Path += ";C:\Program Files (x86)\NSIS"

# Verifica makensis
if (-not (Get-Command makensis -ErrorAction SilentlyContinue)) {
    $nsisPath = "C:\Program Files (x86)\NSIS\makensis.exe"
    if (Test-Path $nsisPath) {
        Set-Alias -Name makensis -Value $nsisPath
    } else {
        Write-Warning "NSIS nao encontrado. Pulando build do instalador."
        exit 0
    }
}

# Garante que main.py existe
if (-not (Test-Path main.py)) {
    throw 'main.py nao encontrado em python_app/main.py'
}

# Instala dependencias
Write-Host 'Instalando dependencias...'
pip install -r requirements.txt
pip install pyinstaller

Write-Host 'Gerando executavel com PyInstaller...'
# IMPORTANTE: --add-data "server/static;server/static" preserva o caminho
# para que app.py encontre os arquivos em _MEIPASS/server/static
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
Write-Host 'Executavel gerado: dist\app.exe'

# Diretorio de saida (compativel com PowerShell 5.1)
$installerOutputDir = Join-Path (Join-Path (Get-Location) "dist") "installer"
New-Item -ItemType Directory -Path $installerOutputDir -Force | Out-Null

Write-Host 'Gerando instalador NSIS...'
if (-not (Test-Path installer\windows_installer.nsi)) {
    throw 'Script NSIS nao encontrado: installer\windows_installer.nsi'
}
& makensis installer\windows_installer.nsi

if ($LASTEXITCODE -ne 0) {
    if (Test-Path "$installerOutputDir\CadastroClientesInstaller.exe") {
        Write-Host "Instalador criado com avisos."
    } else {
        throw "NSIS falhou e o instalador nao foi criado."
    }
}

Write-Host 'Build completo!'
