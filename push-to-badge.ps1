# Sync SSH sources and upload full badge filesystem (includes SSH app).
# Usage: .\push-to-badge.ps1 [-Port COM11] [-Reset]

param(
    [string]$Port = "COM11",
    [switch]$Reset
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Firmware = Resolve-Path (Join-Path $Root "..\..\2025-Communicator_Badge\firmware")
$BadgeDir = Join-Path $Firmware "badge"

& (Join-Path $Root "sync-to-firmware.ps1")

Set-Location $Firmware
& .\venv\Scripts\activate

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

Write-Host "Done. Files on badge:"
mpremote connect $Port exec "import os; print(os.listdir('/'))"
