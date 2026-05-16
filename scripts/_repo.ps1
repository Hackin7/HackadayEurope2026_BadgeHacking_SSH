# Shared paths — dot-source from scripts/deploy|build|test/*.ps1
$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$script:FirmwareDir = (Resolve-Path (Join-Path $script:RepoRoot "..\..\2025-Communicator_Badge\firmware")).Path
$script:BadgeSrc = Join-Path $script:RepoRoot "badge"
$script:TestsDir = Join-Path $script:RepoRoot "tests"
$script:TestServerDir = Join-Path $script:RepoRoot "test-server"
$script:BuildOut = Join-Path $script:RepoRoot "build\lvgl_micropy_ESP32_GENERIC_S3-SPIRAM_OCT-16-ssh.bin"
$script:BackupDir = (Resolve-Path (Join-Path $script:RepoRoot "..\backup") -ErrorAction SilentlyContinue)
if (-not $script:BackupDir) { $script:BackupDir = Join-Path $script:RepoRoot "..\backup" }

function Enter-FirmwareVenv {
    Set-Location $script:FirmwareDir
    & (Join-Path $script:FirmwareDir "venv\Scripts\Activate.ps1")
}
