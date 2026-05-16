# Upstream Communicator Badge dependencies

This repo is **not** a full firmware tree. It ships the SSH app, WiFi helper, native `ssh` module, and tooling.

## Required on the badge (from [2025-Communicator_Badge](https://github.com/Hackaday/2025-Communicator_Badge))

| Path | Used for |
|------|----------|
| `badge/apps/base_app.py` | `SSHClientApp` base class |
| `badge/apps/app_manager.py` | Discovers `apps/ssh_client.py` |
| `badge/ui/page.py`, `styles.py`, `graphics.py` | Menus and terminal UI |
| `badge/hardware/datafile.py` | `Config` (`ssh_*`, `wifi_*`) |
| `badge/hardware/badge.py` | Display, keyboard, config defaults |
| `badge/hardware/display.py`, `keyboard.py` | UI hardware |
| `badge/main.py` | Boot (full deploy) |

## Optional upstream patch

Default SSH config keys in `hardware/badge.py` (`ssh_host`, `ssh_auth`, `ssh_key_path`, …). See [patches/upstream-badge-ssh-config.md](../patches/upstream-badge-ssh-config.md).

## Build-time (not in this repo)

| Path | Role |
|------|------|
| `firmware/lvgl_micropython/` | ESP32 + LVGL MicroPython build |
| `firmware/ucryptography/` | Second `USER_C_MODULE` |
| ESP-IDF v5.x | Toolchain |
| `vendor/libssh2_esp32` | Cloned into this repo before build |

## What this repo contains

| Path | Role |
|------|------|
| `badge/apps/ssh/` | SSH application |
| `badge/apps/ssh_client.py` | App entry (`APP_NAME = "SSH"`) |
| `badge/hardware/wifi.py` | STA WiFi helper |
| `micropython-ssh/` | Native `import ssh` module |

Sync into your firmware checkout:

```powershell
.\scripts\deploy\sync-to-firmware.ps1
```
