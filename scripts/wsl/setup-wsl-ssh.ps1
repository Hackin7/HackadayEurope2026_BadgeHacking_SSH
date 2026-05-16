# Forward Windows :2222 -> WSL OpenSSH, open firewall, run WSL ssh setup.
# Run elevated:  Start-Process powershell -Verb RunAs -ArgumentList '-File', '...\setup-wsl-ssh.ps1'
# Usage: .\setup-wsl-ssh.ps1 [-Distro kali-linux] [-Port 2222] [-SkipWslConfig]

param(
    [string]$Distro = "kali-linux",
    [int]$Port = 2222,
    [switch]$SkipWslConfig
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$WslScript = Join-Path $PSScriptRoot "setup-wsl-openssh.sh"

function Get-WslIPv4 {
    $ip = (wsl -d $Distro -e bash -lc "hostname -I | awk '{print `$1}'").Trim()
    if (-not $ip -or $ip -notmatch '^\d+\.\d+\.\d+\.\d+$') {
        throw "Could not read WSL IPv4 (is $Distro running?)"
    }
    return $ip
}

function Test-Admin {
    $id = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    return $id.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    Write-Host "Re-launching as Administrator..."
    Start-Process powershell -Verb RunAs -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", $MyInvocation.MyCommand.Path,
        "-Distro", $Distro,
        "-Port", $Port
    )
    exit 0
}

if (-not $SkipWslConfig) {
    $wslPath = (wsl -d $Distro -e wslpath -a $WslScript).Trim()
    Write-Host "Configuring OpenSSH inside $Distro..."
    wsl -d $Distro -u root -e bash -lc "SSH_PORT=$Port bash '$wslPath'"
}

$wslIp = Get-WslIPv4
Write-Host "WSL IP: $wslIp"

netsh interface portproxy delete v4tov4 listenport=$Port listenaddress=0.0.0.0 2>$null | Out-Null
netsh interface portproxy add v4tov4 listenport=$Port listenaddress=0.0.0.0 connectport=$Port connectaddress=$wslIp
Write-Host "Port proxy: 0.0.0.0:$Port -> ${wslIp}:$Port"

$ruleName = "WSL SSH $Port"
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existing) { Remove-NetFirewallRule -DisplayName $ruleName }
New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port | Out-Null
Write-Host "Firewall rule: $ruleName"

$pcIp = (Get-NetIPConfiguration -ErrorAction SilentlyContinue |
    Where-Object { $_.NetAdapter.Status -eq "Up" -and $_.IPv4DefaultGateway } |
    ForEach-Object { $_.IPv4Address.IPAddress } |
    Where-Object { $_ -notlike "169.254*" } |
    Select-Object -First 1)

Write-Host ""
Write-Host "OpenSSH on WSL is reachable at:"
Write-Host "  localhost:${Port}  (from this PC)"
if ($pcIp) { Write-Host "  ${pcIp}:${Port}  (from badge / LAN — use in configure-local-test.ps1)" }
Write-Host "  user: badge  password: badge"
Write-Host ""
Write-Host "After WSL restarts, re-run this script (WSL IP may change) or use:"
Write-Host "  .\setup-wsl-ssh.ps1 -SkipWslConfig"
