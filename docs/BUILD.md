# Custom firmware with native `ssh` module

Stock Communicator Badge firmware has **no** `ssh` module. The SSH app falls back to TCP banner probe only until you flash a build that includes `micropython-ssh`.

## Prerequisites

- WSL2 or Linux
- ESP-IDF (e.g. v5.5) — see [LVGL_MICROPYTHON_COMPILE_NOTES](https://github.com/Hackaday/2025-Communicator_Badge/blob/main/firmware/micropython/LVGL_MICROPYTHON_COMPILE_NOTES)
- Clone [2025-Communicator_Badge](https://github.com/Hackaday/2025-Communicator_Badge) `firmware/` next to this repo (for `ucryptography/`)

## Vendor libssh2

```bash
git clone --depth 1 https://github.com/playmiel/libssh2_esp32.git vendor/libssh2_esp32
```

(`vendor/` is gitignored.)

## Build

```powershell
.\scripts\build\build-firmware.ps1
```

Or in WSL from repo root:

```bash
./scripts/build/build-firmware.sh
```

Output: `build/lvgl_micropy_ESP32_GENERIC_S3-SPIRAM_OCT-16-ssh.bin`

## Flash

```powershell
esptool --chip esp32s3 --port COM11 --baud 460800 write-flash --erase-all 0x0 build\lvgl_micropy_ESP32_GENERIC_S3-SPIRAM_OCT-16-ssh.bin
```

Then deploy Python files: [DEPLOY.md](DEPLOY.md).

## Native Python API

Implemented in `micropython-ssh/modssh.c`, used from `badge/apps/ssh/backend.py`:

- `ssh.connect(host, port, user, password, private_key=..., key_passphrase=...) -> int`
- `ssh.get_fingerprint() -> bytes`
- `ssh.open_shell(cols, rows) -> int`
- `ssh.read(n) -> bytes`
- `ssh.write(data) -> int`
- `ssh.close()`
- `ssh.exec(...)` (optional)

Return codes: see `badge/apps/ssh/errors.py` (`-5` password, `-6` pubkey, etc.).
