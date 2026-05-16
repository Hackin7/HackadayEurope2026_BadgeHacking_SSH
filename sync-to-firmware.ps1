# Copy badge app sources from this repo into Communicator Badge firmware tree.
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$FirmwareBadge = Resolve-Path (Join-Path $Root "..\..\2025-Communicator_Badge\firmware\badge")

Copy-Item -Force "$Root\badge\apps\ssh\*" "$FirmwareBadge\apps\ssh\"
Copy-Item -Force "$Root\badge\apps\ssh_client.py" "$FirmwareBadge\apps\ssh_client.py"
Copy-Item -Force "$Root\badge\hardware\wifi.py" "$FirmwareBadge\hardware\wifi.py"
Write-Host "Synced to $FirmwareBadge"
