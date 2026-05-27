$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

if (-not (Get-Command candle -ErrorAction SilentlyContinue)) {
    throw 'WiX Toolset não encontrado. Instale o WiX e certifique-se de que candle.exe está no PATH.'
}
if (-not (Get-Command light -ErrorAction SilentlyContinue)) {
    throw 'WiX Toolset não encontrado. Instale o WiX e certifique-se de que light.exe está no PATH.'
}

$distDir = Join-Path $scriptDir '..\dist'
if (-not (Test-Path $distDir)) {
    New-Item -ItemType Directory -Path $distDir | Out-Null
}

$wxsFile = Join-Path $scriptDir 'wix_sample.wxs'
$wixobjFile = Join-Path $scriptDir 'wix_sample.wixobj'
$outMsi = Join-Path $distDir 'CadastroClientes.msi'

Write-Host "Compilando $wxsFile ..."
candle -out $wixobjFile $wxsFile

Write-Host "Linkando MSI para $outMsi ..."
light -out $outMsi $wixobjFile

Write-Host "MSI gerado em: $outMsi"