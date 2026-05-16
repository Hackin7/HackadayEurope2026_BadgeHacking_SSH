# Upload an OpenSSH *private* key to the badge for pubkey auth.
# Usage: .\scripts\deploy\install-key.ps1 [-Port COM11] [-KeyPath ~/.ssh/id_ed25519]

param(
    [string]$Port = "COM11",
    [string]$KeyPath = "$env:USERPROFILE\.ssh\id_ed25519",
    [string]$RemotePath = "/data/ssh_id_ed25519"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\..\_repo.ps1"

if (-not (Test-Path $KeyPath)) {
    Write-Error "Key not found: $KeyPath"
    exit 1
}

$head = Get-Content $KeyPath -TotalCount 3 -Raw
if ($head -match "PUBLIC KEY" -and $head -notmatch "PRIVATE KEY") {
    Write-Error "Use the private key file (no .pub): $KeyPath"
    exit 1
}

$pub = "$KeyPath.pub"
if (Test-Path $pub) {
    Write-Host "Public key for server authorized_keys:"
    Get-Content $pub
    Write-Host ""
}

Enter-FirmwareVenv
cmd /c "mpremote connect $Port mkdir :/data 2>nul"
mpremote connect $Port cp $KeyPath ":$RemotePath"
Write-Host "Installed -> $RemotePath"
Write-Host "Badge: F4 pubkey, F1 Connect"
Write-Host "Test: mpremote connect $Port run $TestsDir\repl_pubkey_test.py"
