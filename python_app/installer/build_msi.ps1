$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# Add Chocolatey-installed tool paths to PATH
$wixPaths = @(
    "C:\Program Files (x86)\WiX Toolset v3.11\bin",
    "C:\Program Files (x86)\WiX Toolset v3.14\bin",
    "C:\Program Files\WiX Toolset v3.11\bin",
    "C:\Program Files\WiX Toolset v3.14\bin"
)
foreach ($path in $wixPaths) {
    if (Test-Path $path) {
        $env:Path = "$path;$($env:Path)"
        break
    }
}

# Refresh environment to pick up recently installed tools (WiX, etc.)
if (Test-Path 'C:\ProgramData\chocolatey\bin\refreshenv.cmd') {
    & cmd /c 'C:\ProgramData\chocolatey\bin\refreshenv.cmd' | Out-Null
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Check for WiX tools
if (-not (Get-Command candle -ErrorAction SilentlyContinue)) {
    Write-Warning "candle not found in PATH. Checking common installation paths..."
    $candlePath = $null
    $wixPaths | ForEach-Object {
        $testPath = Join-Path $_ "candle.exe"
        if (Test-Path $testPath) {
            $candlePath = $testPath
        }
    }
    if ($candlePath) {
        Write-Host "Found candle at $candlePath"
        Set-Alias -Name candle -Value $candlePath
    } else {
        Write-Warning "WiX Toolset not installed or candle.exe not found. Skipping MSI build."
        exit 0
    }
}
if (-not (Get-Command light -ErrorAction SilentlyContinue)) {
    Write-Warning "light not found in PATH. Checking common installation paths..."
    $lightPath = $null
    $wixPaths | ForEach-Object {
        $testPath = Join-Path $_ "light.exe"
        if (Test-Path $testPath) {
            $lightPath = $testPath
        }
    }
    if ($lightPath) {
        Write-Host "Found light at $lightPath"
        Set-Alias -Name light -Value $lightPath
    } else {
        Write-Warning "WiX Toolset not installed or light.exe not found. Skipping MSI build."
        exit 0
    }
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