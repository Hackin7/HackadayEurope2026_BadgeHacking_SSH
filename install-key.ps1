# Upload an OpenSSH *private* key to the badge for pubkey auth.
# Usage: .\install-key.ps1 COM11 C:\Users\you\.ssh\id_ed25519

param(
  [string]$Port = "COM11",
  [string]$KeyPath = "$env:USERPROFILE\.ssh\id_ed25519",
  [string]$RemotePath = "/data/ssh_id_ed25519"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $KeyPath)) {
  Write-Error "Key not found: $KeyPath"
  exit 1
}

$head = Get-Content $KeyPath -TotalCount 3 -Raw
if ($head -match "PUBLIC KEY" -and $head -notmatch "PRIVATE KEY") {
  Write-Error @"
$KeyPath looks like a PUBLIC key (.pub).
Install the private key file (no .pub extension), e.g.:
  $env:USERPROFILE\.ssh\id_ed25519
"@
  exit 1
}
if ($head -notmatch "PRIVATE KEY") {
  Write-Warning "File may not be a PEM private key; expected OPENSSH PRIVATE KEY or similar."
}

$pub = "$KeyPath.pub"
if (Test-Path $pub) {
  Write-Host "Matching public key on PC (put this line in server authorized_keys):"
  Get-Content $pub
  Write-Host ""
}

$Firmware = Resolve-Path (Join-Path $PSScriptRoot "..\..\2025-Communicator_Badge\firmware")
Set-Location $Firmware
& .\venv\Scripts\activate

mpremote connect $Port cp $KeyPath ":$RemotePath"
Write-Host "Installed $KeyPath -> $RemotePath"
Write-Host ""
Write-Host "On badge SSH app:"
Write-Host "  F3 Edit -> User = your Linux username (e.g. zunmun)"
Write-Host "  F4 until menubar shows Auth: pubkey"
Write-Host "  F1 Connect"
Write-Host ""
Write-Host "Verify: mpremote connect $Port run repl_pubkey_test.py"
