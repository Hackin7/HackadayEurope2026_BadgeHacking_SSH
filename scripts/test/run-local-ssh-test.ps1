# Start Paramiko test server and run a badge REPL test script.
# Usage: .\scripts\test\run-local-ssh-test.ps1 [-ReplScript tests\repl_password_local_test.py]

param(
    [string]$PcIp = "",
    [string]$Port = "COM11",
    [switch]$SkipServer,
    [string]$ReplScript = ""
)

. "$PSScriptRoot\..\_repo.ps1"

if (-not $ReplScript) {
    $ReplScript = Join-Path $TestsDir "repl_password_local_test.py"
}

function Get-WifiIPv4 {
    $cfg = Get-NetIPConfiguration -ErrorAction SilentlyContinue |
        Where-Object { $_.NetAdapter.Status -eq "Up" -and $_.IPv4DefaultGateway -ne $null }
    foreach ($c in $cfg) {
        $addr = $c.IPv4Address | Select-Object -First 1 -ExpandProperty IPAddress
        if ($addr -and $addr -notlike "169.254*") { return $addr }
    }
    return $null
}

if (-not $PcIp) {
    $PcIp = Get-WifiIPv4
    if (-not $PcIp) { Write-Error "Pass -PcIp"; exit 1 }
    Write-Host "Detected PC IP: $PcIp"
}

$replTmp = Join-Path $env:TEMP ("repl_badge_test_" + [IO.Path]::GetFileName($ReplScript))
$content = Get-Content $ReplScript -Raw
$content = $content -replace 'PC_HOST = "[^"]*"', "PC_HOST = `"$PcIp`""
Set-Content -Path $replTmp -Value $content -NoNewline

$serverJob = $null
if (-not $SkipServer) {
    $venvPy = Join-Path $TestServerDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPy)) {
        Set-Location $TestServerDir
        python -m venv .venv
        & .\.venv\Scripts\pip install -q -r requirements.txt
        if (-not (Test-Path "test_host_key")) { & $venvPy generate_host_key.py }
        Set-Location $RepoRoot
    }
    if (-not (Test-Path (Join-Path $TestServerDir "test_host_key"))) {
        & $venvPy (Join-Path $TestServerDir "generate_host_key.py")
    }
    Write-Host "Starting Paramiko server on port 2222..."
    $serverJob = Start-Job -ScriptBlock {
        param($dir, $py)
        Set-Location $dir
        & $py local_ssh_server.py 2>&1
    } -ArgumentList $TestServerDir, $venvPy
    Start-Sleep -Seconds 2
}

try {
    Enter-FirmwareVenv
    Write-Host "Running $ReplScript on $Port ..."
    mpremote connect $Port run $replTmp
} finally {
    if ($serverJob) {
        Stop-Job $serverJob -ErrorAction SilentlyContinue
        Remove-Job $serverJob -Force -ErrorAction SilentlyContinue
    }
}
