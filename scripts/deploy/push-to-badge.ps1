# Sync SSH sources and upload full badge filesystem (includes SSH app).
# Usage: .\scripts\deploy\push-to-badge.ps1 [-Port COM11] [-Reset]

param(
    [string]$Port = "COM11",
    [switch]$Reset
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\..\_repo.ps1"

$BadgeDir = Join-Path $FirmwareDir "badge"

& (Join-Path $PSScriptRoot "sync-to-firmware.ps1")

Enter-FirmwareVenv

Write-Host "Uploading badge filesystem to $Port (all apps + hardware + net)..."
Push-Location $BadgeDir
try {
    mpremote connect $Port cp -r . :
} finally {
    Pop-Location
}

if ($Reset) {
    mpremote connect $Port reset
}

Write-Host "Done. Root on badge:"
mpremote connect $Port exec "import os; print(os.listdir('/'))"
