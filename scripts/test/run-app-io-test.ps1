# Deploy app, start local server, run worker/queue I/O test on badge.
# Usage: .\scripts\test\run-app-io-test.ps1 [-Port COM11] [-SkipPush]

param(
    [string]$PcIp = "",
    [string]$Port = "COM11",
    [switch]$SkipPush,
    [switch]$SkipServer
)

. "$PSScriptRoot\..\_repo.ps1"

if (-not $SkipPush) {
    & (Join-Path $RepoRoot "scripts\deploy\push-to-badge.ps1") -Port $Port
}

& (Join-Path $PSScriptRoot "run-local-ssh-test.ps1") -PcIp $PcIp -Port $Port `
    -SkipServer:$SkipServer -ReplScript (Join-Path $TestsDir "repl_app_io_test.py")
