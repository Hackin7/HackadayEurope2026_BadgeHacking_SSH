# Start local Paramiko SSH server (background) and run badge password test.
# Usage: .\run-local-ssh-test.ps1 [-PcIp 10.86.82.1] [-Port COM11] [-SkipServer]

param(
    [string]$PcIp = "",
    [string]$Port = "COM11",
    [switch]$SkipServer,
    [string]$ReplScript = ""
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerDir = Join-Path $Root "test-server"
$Firmware = Resolve-Path (Join-Path $Root "..\..\2025-Communicator_Badge\firmware")
if (-not $ReplScript) {
    $ReplScript = Join-Path $Root "repl_password_local_test.py"
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
    if (-not $PcIp) {
        Write-Error "Could not detect WiFi IPv4. Pass -PcIp <address> from ipconfig."
        exit 1
    }
    Write-Host "Detected PC IP: $PcIp"
} else {
    Write-Host "Using PC IP: $PcIp"
}

# Patch PC_HOST in repl script temp copy
$replTmp = Join-Path $env:TEMP ("repl_badge_test_" + [IO.Path]::GetFileName($ReplScript))
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
    Write-Host "Running badge test on $Port ..."
    mpremote connect $Port run $replTmp
} finally {
    if ($serverJob) {
        Write-Host "Stopping SSH test server..."
        Stop-Job $serverJob -ErrorAction SilentlyContinue
        Remove-Job $serverJob -Force -ErrorAction SilentlyContinue
    }
}
