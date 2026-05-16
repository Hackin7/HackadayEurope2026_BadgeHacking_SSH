# Flash SSH firmware, deploy filesystem, install WSL RSA key, run connect test.
# Usage: .\scripts\deploy\flash-and-deploy.ps1 [-Port COM11] [-SkipBackup] [-SkipFlash]

param(
    [string]$Port = "COM11",
    [switch]$SkipBackup,
    [switch]$SkipFlash
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\..\_repo.ps1"

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"

if (-not (Test-Path $BuildOut)) {
    Write-Error "Firmware not found: $BuildOut`nRun: .\scripts\build\build-firmware.ps1"
    exit 1
}

Enter-FirmwareVenv

if (-not $SkipBackup -and (Test-Path $BackupDir)) {
    Write-Host "Backing up flash (16 MB)..."
    $BackupBin = Join-Path $BackupDir "badge-flash-$Stamp.bin"
    & esptool --chip esp32s3 --port $Port --baud 1500000 read-flash 0 0x1000000 $BackupBin
    Write-Host "Backup: $BackupBin"
}

if (-not $SkipFlash) {
    Write-Host "Flashing (erase-all)..."
    & esptool --chip esp32s3 --port $Port --baud 460800 write-flash --erase-all 0x0 $BuildOut
}

& (Join-Path $PSScriptRoot "push-to-badge.ps1") -Port $Port
& (Join-Path $PSScriptRoot "install-wsl-rsa-to-badge.ps1") -Port $Port

Start-Sleep -Seconds 3
mpremote connect $Port exec "import ssh; print('ssh', [x for x in dir(ssh) if not x.startswith('_')])"
mpremote connect $Port run (Join-Path $TestsDir "repl_connect_test.py")

Write-Host "Done. SSH app: F4 pubkey, F1 Conn."
