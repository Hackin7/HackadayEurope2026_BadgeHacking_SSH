# Deploy SSH app from this repo to connected badge.
# Usage: .\push-to-badge.ps1 COM11

param(
  [string]$Port = "COM11"
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Badge = Join-Path $Root "badge"
$Firmware = Resolve-Path (Join-Path $Root "..\..\2025-Communicator_Badge\firmware")

Set-Location $Firmware
& .\venv\Scripts\activate

$SshDir = Join-Path $Badge "apps\ssh"
mpremote connect $Port mkdir :apps/ssh 2>$null
Get-ChildItem "$SshDir\*.py" | ForEach-Object {
  mpremote connect $Port cp $_.FullName ":apps/ssh/$($_.Name)"
}
mpremote connect $Port cp "$Badge\apps\ssh_client.py" :apps/ssh_client.py
mpremote connect $Port cp "$Badge\hardware\wifi.py" :hardware/wifi.py
mpremote connect $Port reset
Write-Host "Done. SSH app: F4 toggles password/pubkey auth."
