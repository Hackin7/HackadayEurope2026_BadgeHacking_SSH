# Flash SSH firmware, deploy Python app, install WSL RSA key, run REPL test.
# Usage: .\flash-and-deploy.ps1 [-Port COM11] [-SkipBackup] [-SkipFlash]

param(
    [string]$Port = "COM11",
    [switch]$SkipBackup,
    [switch]$SkipFlash
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Bin = Join-Path $Root "build\lvgl_micropy_ESP32_GENERIC_S3-SPIRAM_OCT-16-ssh.bin"
$BackupDir = Resolve-Path (Join-Path $Root "..\backup")
$Firmware = Resolve-Path (Join-Path $Root "..\..\2025-Communicator_Badge\firmware")
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"

if (-not (Test-Path $Bin)) {
    Write-Error "Firmware not found: $Bin`nRun: .\build-firmware.ps1"
    exit 1
}

Set-Location $Firmware
& .\venv\Scripts\activate

if (-not $SkipBackup) {
    Write-Host "Backing up current flash (16 MB)..."
    $BackupBin = Join-Path $BackupDir "badge-flash-$Stamp.bin"
    & esptool --chip esp32s3 --port $Port --baud 1500000 read-flash 0 0x1000000 $BackupBin
    Write-Host "Backup: $BackupBin"
}

if (-not $SkipFlash) {
    Write-Host "Flashing SSH firmware (erases chip)..."
    Write-Host "If this fails: hold GPIO0, press reset, release GPIO0."
    & esptool --chip esp32s3 --port $Port --baud 460800 write-flash --erase-all 0x0 $Bin
}

Write-Host "Syncing SSH app sources to firmware tree..."
& (Join-Path $Root "sync-to-firmware.ps1")

Write-Host "Deploying app to badge..."
& (Join-Path $Root "push-to-badge.ps1") $Port

Write-Host "Installing WSL id_rsa + config..."
& (Join-Path $Root "install-wsl-rsa-to-badge.ps1") -Port $Port

Write-Host "Verifying native ssh on badge..."
Start-Sleep -Seconds 3
mpremote connect $Port exec "import ssh; print('ssh OK', [x for x in dir(ssh) if not x.startswith('_')])"

Write-Host ""
Write-Host "Running connect test (repl_connect_test.py)..."
mpremote connect $Port run (Join-Path $Root "repl_connect_test.py")

Write-Host ""
Write-Host "Done. Open SSH app: F4 pubkey, F1 Conn."
