# Set badge config for local Paramiko SSH test (port 2222).
# Usage: .\scripts\deploy\configure-local-test.ps1 [-Port COM11] [-WifiPassword "..."]

param(
    [string]$PcIp = "",
    [string]$Port = "COM11",
    [string]$WifiSsid = "zfliphack",
    [string]$WifiPassword = ""
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\..\_repo.ps1"

if (-not $PcIp) {
    $PcIp = (Get-NetIPConfiguration -ErrorAction SilentlyContinue |
        Where-Object { $_.NetAdapter.Status -eq "Up" -and $_.IPv4DefaultGateway } |
        ForEach-Object { $_.IPv4Address.IPAddress } |
        Where-Object { $_ -notlike "169.254*" } |
        Select-Object -First 1)
    if (-not $PcIp) { Write-Error "Pass -PcIp"; exit 1 }
}

if (-not $WifiPassword -and $env:BADGE_WIFI_PASSWORD) {
    $WifiPassword = $env:BADGE_WIFI_PASSWORD
}

$cfgPy = Join-Path $env:TEMP "badge_local_ssh_config.py"
$wifiLine = ""
if ($WifiPassword) {
    $wifiLine = "    (`"wifi_password`", `"$WifiPassword`"),`n"
}
$cfgBody = @"
from hardware.datafile import Config
c = Config()
for k, v in [
    ("wifi_ssid", "$WifiSsid"),
$wifiLine    ("ssh_host", "$PcIp"),
    ("ssh_port", "2222"),
    ("ssh_user", "badge"),
    ("ssh_password", "badge"),
    ("ssh_auth", "password"),
]:
    c.set(k.encode(), v.encode())
c.flush()
print("config ok", "$PcIp", "wifi", "$WifiSsid")
"@
[System.IO.File]::WriteAllText($cfgPy, $cfgBody.TrimStart() + "`n")

Enter-FirmwareVenv
mpremote connect $Port run $cfgPy
Write-Host "Badge SSH app: F4 Pass, F1 Conn. Or run scripts\test\run-ssh-rw-test.ps1"
