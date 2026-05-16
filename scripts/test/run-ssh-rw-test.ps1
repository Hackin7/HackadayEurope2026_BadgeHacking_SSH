# Local Paramiko server + native ssh read/write test on badge.
# Usage: .\scripts\test\run-ssh-rw-test.ps1 [-Port COM11]

param([string]$PcIp = "", [string]$Port = "COM11")

Get-Job | Stop-Job -ErrorAction SilentlyContinue
Get-Job | Remove-Job -Force -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 2222 -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

. "$PSScriptRoot\..\_repo.ps1"
& (Join-Path $PSScriptRoot "run-local-ssh-test.ps1") -PcIp $PcIp -Port $Port `
    -ReplScript (Join-Path $TestsDir "repl_ssh_rw_test.py")
