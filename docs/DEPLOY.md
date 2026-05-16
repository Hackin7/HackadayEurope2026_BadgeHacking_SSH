# Deploying to the badge

Requires [Communicator Badge firmware](https://github.com/Hackaday/2025-Communicator_Badge) with `mpremote` in `firmware/venv`.

## App only (custom firmware already flashed)

```powershell
.\scripts\deploy\push-to-badge.ps1 -Port COM11 -Reset
```

Uploads the **full** upstream `firmware/badge/` tree (synced from this repo’s `badge/` first). After a full flash erase you need this, not just `apps/ssh/`.

## SSH app sources only (manual)

If the badge already has stock filesystem:

```powershell
.\scripts\deploy\sync-to-firmware.ps1
# Then from firmware/: mpremote connect COM11 cp -r badge/apps/ssh :apps/ssh
```

Do **not** copy only `hardware/wifi.py` unless you copy the whole `hardware/` package — a partial folder shadows frozen modules.

## Keys and config

| Script | Purpose |
|--------|---------|
| `scripts/deploy/install-key.ps1` | Copy `id_ed25519` (or other PEM) to `/data/` |
| `scripts/deploy/install-wsl-rsa-to-badge.ps1` | WSL `id_rsa` + remote host config |
| `scripts/deploy/configure-local-test.ps1` | WiFi + PC IP for local Paramiko test |

## Local SSH test (no remote server)

```powershell
.\scripts\deploy\configure-local-test.ps1 -Port COM11 -WifiPassword "your-wifi-pass"
.\scripts\test\run-ssh-rw-test.ps1 -Port COM11
```

See [test-server/README.md](../test-server/README.md) for the Paramiko server.

## Flash custom firmware + deploy

```powershell
.\scripts\build\build-firmware.ps1          # WSL, first time ~30-60 min
.\scripts\deploy\flash-and-deploy.ps1 -Port COM11
```

Backup is written to `../backup/` if that folder exists.

## Badge UI

Apps menu → **SSH** → **F3** edit host/user → **F4** toggle password/pubkey → **F1** connect.
