# Copy badge app sources from this repo into Communicator Badge firmware tree.
. "$PSScriptRoot\..\_repo.ps1"

$FirmwareBadge = Join-Path $FirmwareDir "badge"

Copy-Item -Force "$BadgeSrc\apps\ssh\*" "$FirmwareBadge\apps\ssh\"
Copy-Item -Force "$BadgeSrc\apps\ssh_client.py" "$FirmwareBadge\apps\ssh_client.py"
Copy-Item -Force "$BadgeSrc\hardware\wifi.py" "$FirmwareBadge\hardware\wifi.py"
Write-Host "Synced to $FirmwareBadge"
