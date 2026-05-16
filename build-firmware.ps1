# Build MicroPython firmware with native ssh module (WSL required).
# Usage: .\build-firmware.ps1 [-SkipBuild]  # use existing build/*.bin

param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$OutBin = Join-Path $Root "build\lvgl_micropy_ESP32_GENERIC_S3-SPIRAM_OCT-16-ssh.bin"

if (-not $SkipBuild) {
    Write-Host "Building firmware in WSL (30-60 min first time, faster if cached)..."
    $wslRoot = "/mnt/c/Users/zunmun/Documents/Stuff/Workspace/2026/hackadayeurope/badgehacking/ssh"
    wsl -e bash -lc "cd '$wslRoot' && ./build-firmware.sh" 2>&1 | Tee-Object -FilePath (Join-Path $Root "build-log.txt")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "WSL build failed. See build-log.txt"
        exit 1
    }
}

if (-not (Test-Path $OutBin)) {
    Write-Error "Missing $OutBin — run without -SkipBuild"
    exit 1
}

$hash = (Get-FileHash $OutBin -Algorithm SHA256).Hash
Write-Host ""
Write-Host "Firmware ready:"
Write-Host "  $OutBin"
Write-Host "  SHA256: $hash"
Write-Host "  Size:   $((Get-Item $OutBin).Length) bytes"
Write-Host ""
Write-Host "Next: .\flash-and-deploy.ps1 -Port COM11"
