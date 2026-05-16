# Deploy SSH app, start local server, run repl_app_io_test.py on the badge.
# Usage: .\run-app-io-test.ps1 [-PcIp 10.86.82.124] [-Port COM11] [-SkipPush] [-SkipServer]

param(
    [string]$PcIp = "",
    [string]$Port = "COM11",
    [switch]$SkipPush,
    [switch]$SkipServer
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerDir = Join-Path $Root "test-server"
$Firmware = Resolve-Path (Join-Path $Root "..\..\2025-Communicator_Badge\firmware")
$ReplScript = Join-Path $Root "repl_app_io_test.py"

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
    if (-not $PcIp) {
        Write-Error "Could not detect WiFi IPv4. Pass -PcIp from ipconfig."
        exit 1
    }
    Write-Host "Detected PC IP: $PcIp"
} else {
    Write-Host "Using PC IP: $PcIp"
}

if (-not $SkipPush) {
    Write-Host "Pushing SSH app to $Port ..."
    & (Join-Path $Root "push-to-badge.ps1") $Port
}

$replTmp = Join-Path $env:TEMP "repl_app_io_test.py"
$content = Get-Content $ReplScript -Raw
$content = $content -replace 'PC_HOST = "[^"]*"', "PC_HOST = `"$PcIp`""
Set-Content -Path $replTmp -Value $content -NoNewline

$serverJob = $null
if (-not $SkipServer) {
    $venvPy = Join-Path $ServerDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPy)) {
        Write-Host "Creating test-server venv..."
        Set-Location $ServerDir
        python -m venv .venv
        & .\.venv\Scripts\pip install -q -r requirements.txt
        if (-not (Test-Path "test_host_key")) { & $venvPy generate_host_key.py }
        Set-Location $Root
    }
    if (-not (Test-Path (Join-Path $ServerDir "test_host_key"))) {
        & $venvPy (Join-Path $ServerDir "generate_host_key.py")
    }
    Write-Host "Starting Paramiko server on port 2222..."
    $serverJob = Start-Job -ScriptBlock {
        param($dir, $py)
        Set-Location $dir
        & $py local_ssh_server.py 2>&1
    } -ArgumentList $ServerDir, $venvPy
    Start-Sleep -Seconds 2
}

try {
    Set-Location $Firmware
    & .\venv\Scripts\activate
    Write-Host "Running app I/O test on $Port ..."
    mpremote connect $Port run $replTmp
} finally {
    if ($serverJob) {
        Write-Host "Stopping SSH test server..."
        Stop-Job $serverJob -ErrorAction SilentlyContinue
        Remove-Job $serverJob -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "Manual UI test (optional):"
Write-Host "  Host=$PcIp  Port=2222  User=badge  Pass=badge (F4=Pass)"
Write-Host "  Open SSH app -> F1 Conn -> F1 trust host if asked -> type PING + Enter"
Write-Host "  Expect: shell ready banner, then echoed PING when you type"
