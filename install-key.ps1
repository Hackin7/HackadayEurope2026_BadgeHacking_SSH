# Upload an OpenSSH private key to the badge for pubkey auth.
# Usage: .\install-key.ps1 COM11 C:\Users\you\.ssh\id_ed25519

param(
  [string]$Port = "COM11",
  [string]$KeyPath = "$env:USERPROFILE\.ssh\id_ed25519",
  [string]$RemotePath = "/data/ssh_id_ed25519"
)

if (-not (Test-Path $KeyPath)) {
  Write-Error "Key not found: $KeyPath"
  exit 1
}

$Firmware = Resolve-Path (Join-Path $PSScriptRoot "..\..\2025-Communicator_Badge\firmware")
Set-Location $Firmware
& .\venv\Scripts\activate

mpremote connect $Port cp $KeyPath ":$RemotePath"
Write-Host "Installed $KeyPath -> $RemotePath"
Write-Host "In SSH app: F4 until Auth shows pubkey, F3 Edit to set key path if needed."
