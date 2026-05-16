# Close port 2222 listeners, start Paramiko server, run native ssh read/write test on badge.
# Usage: .\run-ssh-rw-test.ps1 [-PcIp 10.86.82.124] [-Port COM11]

param(
    [string]$PcIp = "",
    [string]$Port = "COM11"
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Get-Job | Stop-Job -ErrorAction SilentlyContinue
Get-Job | Remove-Job -Force -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 2222 -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

& (Join-Path $Root "run-local-ssh-test.ps1") -PcIp $PcIp -Port $Port -ReplScript (Join-Path $Root "repl_ssh_rw_test.py")
