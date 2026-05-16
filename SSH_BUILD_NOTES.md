# Custom firmware with native `ssh` module

Stock Hackaday Europe MicroPython has **no** `ssh` module. The SSH app still runs in **TCP banner mode** (`socket` + port 22) until you flash a custom build.

## Prerequisites

- Linux or WSL2 (ESP-IDF toolchain)
- Follow upstream: `firmware/micropython/LVGL_MICROPYTHON_COMPILE_NOTES`

## Outline

1. Clone `lvgl_micropython` under `2025-Communicator_Badge/firmware/`
2. Add `badgehacking/ssh/micropython-ssh/` as `USER_C_MODULE` (libssh2 / LibSSH-ESP32)
3. Build with ucryptography **and** micropython-ssh:

```bash
python3 make.py esp32 BOARD=ESP32_GENERIC_S3 BOARD_VARIANT=SPIRAM_OCT \
  --flash-size=16 DISPLAY=nv3007 --enable-uart-repl=y --enable-cdc-repl=n \
  USER_C_MODULE="$(pwd)/../ucryptography/micropython.cmake:$(pwd)/../badgehacking/ssh/micropython-ssh/micropython.cmake"
```

4. Flash `build/lvgl_micropy_ESP32_GENERIC_S3-SPIRAM_OCT-16.bin` via esptool (see backup restore commands in `badgehacking/backup/`).

## Python API expected on badge

See `firmware/badge/apps/ssh/backend.py`:

- `ssh.connect(host, port, user, password) -> int`
- `ssh.get_fingerprint() -> bytes`
- `ssh.open_shell(cols, rows) -> int`
- `ssh.read(n) -> bytes`
- `ssh.write(data)`
- `ssh.close()`
- `ssh.exec(url, user, password, port=22)` (loboris-style MVP)

Implementation sources: [LibSSH-ESP32](https://github.com/ewpa/LibSSH-ESP32), [loboris ssh wiki](https://github.com/loboris/MicroPython_ESP32_psRAM_LoBo/wiki/ssh).
