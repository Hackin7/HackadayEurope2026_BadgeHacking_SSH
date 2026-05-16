# Set badge config for local Paramiko SSH app test.
# Usage: .\configure-local-test.ps1 [-PcIp 10.86.82.124] [-Port COM11]

param(
    [string]$PcIp = "",
    [string]$Port = "COM11"
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Firmware = Resolve-Path (Join-Path $Root "..\..\2025-Communicator_Badge\firmware")

if (-not $PcIp) {
    $PcIp = (Get-NetIPConfiguration -ErrorAction SilentlyContinue |
        Where-Object { $_.NetAdapter.Status -eq "Up" -and $_.IPv4DefaultGateway } |
        ForEach-Object { $_.IPv4Address.IPAddress } |
        Where-Object { $_ -notlike "169.254*" } |
        Select-Object -First 1)
    if (-not $PcIp) { Write-Error "Pass -PcIp"; exit 1 }
}

$py = @"
from hardware.datafile import Config
c = Config()
for k, v in [
    ('ssh_host', '$PcIp'),
    ('ssh_port', '2222'),
    ('ssh_user', 'badge'),
    ('ssh_password', 'badge'),
    ('ssh_auth', 'password'),
]:
    c.set(k, v.encode())
c.flush()
print('config ok', '$PcIp', '2222', 'badge')
"@

Set-Location $Firmware
& .\venv\Scripts\activate
mpremote connect $Port exec $py
Write-Host "Open SSH app on badge: F4 until menubar shows Pass, then F1 Conn."
