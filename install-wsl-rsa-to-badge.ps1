# Copy WSL ~/.ssh/id_rsa to badge and set pubkey auth config.
# Usage: .\install-wsl-rsa-to-badge.ps1 [-Port COM11]

param(
    [string]$Port = "COM11",
    [string]$SshHost = "34.28.97.3",
    [string]$WifiSsid = "zfliphack",
    [string]$WifiPassword = ""
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Tmp = Join-Path $env:TEMP "wsl_id_rsa_for_badge"
$Firmware = Resolve-Path (Join-Path $Root "..\..\2025-Communicator_Badge\firmware")

Write-Host "Exporting WSL id_rsa (LF)..."
wsl -e bash -c "tr -d '\r' < ~/.ssh/id_rsa > /mnt/c/Users/zunmun/AppData/Local/Temp/wsl_id_rsa_for_badge"

Write-Host "Testing WSL key against server..."
wsl -e bash -c "ssh -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa zunmun@34.28.97.3 'echo wsl-ok'"
if ($LASTEXITCODE -ne 0) {
    Write-Warning "WSL ssh test failed - fix server authorized_keys before badge test."
}

Set-Location $Firmware
& .\venv\Scripts\activate

Write-Host "Uploading to badge $Port ..."
cmd /c "mpremote connect $Port mkdir :/data 2>nul"
mpremote connect $Port cp $Tmp :/data/ssh_id_rsa

$cfgPy = Join-Path $env:TEMP "badge_ssh_config.py"
$cfgBody = @"
from hardware.datafile import Config
from apps.ssh import identity
c = Config()
pairs = [
    ("ssh_host", "$SshHost"),
    ("ssh_port", "22"),
    ("ssh_user", "zunmun"),
    ("ssh_auth", "pubkey"),
    ("ssh_key_path", "/data/ssh_id_rsa"),
    ("wifi_ssid", "$WifiSsid"),
]
if "$WifiPassword":
    pairs.append(("wifi_password", "$WifiPassword"))
for k, v in pairs:
    c.set(k.encode(), v.encode())
c.flush()
print("key", identity.key_file_hint("/data/ssh_id_rsa"))
"@
[System.IO.File]::WriteAllText($cfgPy, $cfgBody.TrimStart() + "`n")
mpremote connect $Port run $cfgPy

Write-Host ""
Write-Host "Run on-badge test:"
Write-Host "  mpremote connect $Port run repl_connect_test.py"
Write-Host ""
Write-Host 'If connect returns -6, reflash firmware with rsa-sha2 sign pref in modssh.c.'
