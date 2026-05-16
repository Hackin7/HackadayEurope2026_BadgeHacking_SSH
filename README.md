# Hackaday Badge SSH Client

Git home for the Communicator Badge SSH app, native `ssh` module (libssh2), and deploy scripts.

## Repository layout

| Path | Purpose |
|------|---------|
| `badge/apps/ssh/` | MicroPython SSH app (deploy to badge) |
| `badge/hardware/wifi.py` | WiFi helper used by SSH |
| `micropython-ssh/` | C `ssh` module for custom firmware |
| `push-to-badge.ps1` | Deploy app over USB (mpremote) |
| `install-key.ps1` | Copy private key to `/data/ssh_id_ed25519` |
| `sync-to-firmware.ps1` | Copy `badge/` into upstream firmware tree |

Upstream firmware: `2025-Communicator_Badge/firmware/badge/`

## Quick start

```powershell
# Deploy app
.\push-to-badge.ps1 COM11

# Install your SSH private key (OpenSSH PEM)
.\install-key.ps1 COM11 $env:USERPROFILE\.ssh\id_ed25519

# On badge: Apps → SSH → F4 until "Auth: pubkey" → F1 Connect
```

## Authentication

- **Password** (default): set user + password in **F3 Edit**.
- **Public key**: **F4** toggles `password` / `pubkey`. Private key file on badge (default `/data/ssh_id_ed25519`). Optional key passphrase in config key `ssh_key_passphrase` (set via REPL/config for now).

Public key auth requires firmware built with `micropython-ssh` (`import ssh` and `connect(..., private_key=...)`). Stock firmware only supports TCP banner probe.

Supported keys: OpenSSH PEM (`BEGIN OPENSSH PRIVATE KEY` or `BEGIN RSA PRIVATE KEY`).

## Custom firmware

See `SSH_BUILD_NOTES.md`. After flashing, deploy the app with `push-to-badge.ps1`.

## Sync to upstream firmware

```powershell
.\sync-to-firmware.ps1
```

Also merge `ssh_auth` / `ssh_key_path` defaults in `hardware/badge.py` (already in upstream if you pulled recent changes).

## Vendor libssh2

```bash
git submodule add https://github.com/warmcat/libssh2-esp32 vendor/libssh2_esp32
# or clone manually into vendor/libssh2_esp32
```

`vendor/` is gitignored; clone before building firmware.
