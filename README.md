# Hackaday Communicator Badge — SSH client

MicroPython SSH terminal app and native `ssh` module (libssh2) for the [Hackaday Europe Communicator Badge](https://github.com/Hackin7/HackadayEurope2026_BadgeHacking_SSH).

## Repository tree

```
.
├── README.md
├── badge/                      # Deploy to badge (synced into upstream firmware/badge/)
│   ├── apps/
│   │   ├── ssh/                # SSH app package
│   │   │   ├── app.py          # UI + keyboard
│   │   │   ├── backend.py      # native ssh / TCP fallback
│   │   │   ├── worker.py       # Session thread
│   │   │   ├── terminal.py     # Scrollback display
│   │   │   └── ...
│   │   └── ssh_client.py       # App menu entry (APP_NAME = "SSH")
│   └── hardware/
│       └── wifi.py             # WiFi STA helper
├── micropython-ssh/            # C module: import ssh
├── patches/                    # GCC thumb patch, upstream notes
├── vendor/                     # libssh2_esp32 (clone before build, gitignored)
├── build/                      # Firmware .bin output (gitignored)
├── docs/
│   ├── BUILD.md                # Custom firmware
│   ├── DEPLOY.md               # mpremote / flash
│   └── UPSTREAM.md             # Files outside this repo
├── scripts/
│   ├── deploy/                 # push, flash, keys, config
│   ├── build/                  # WSL firmware build
│   ├── test/                   # PC-side test runners
│   └── wsl/                    # Optional WSL OpenSSH helpers
├── tests/                      # On-badge REPL test scripts
└── test-server/                # Local Paramiko server (port 2222)
```

## Quick start

**Prerequisites:** Badge on USB, [upstream `firmware/venv`](../../2025-Communicator_Badge/firmware) with `mpremote`, custom firmware with `import ssh` (see [docs/BUILD.md](docs/BUILD.md)).

```powershell
# Deploy full badge filesystem (after sync to upstream tree)
.\scripts\deploy\push-to-badge.ps1 -Port COM11

# Install private key for pubkey auth
.\scripts\deploy\install-key.ps1 -Port COM11

# On badge: Apps → SSH → F4 (pubkey) → F1 Connect
```

**Local test** (PC Paramiko server, same WiFi as badge):

```powershell
.\scripts\deploy\configure-local-test.ps1 -Port COM11 -WifiPassword "your-pass"
.\scripts\test\run-ssh-rw-test.ps1 -Port COM11
```

## Documentation

| Doc | Topic |
|-----|--------|
| [docs/DEPLOY.md](docs/DEPLOY.md) | Upload app, keys, flash workflow |
| [docs/BUILD.md](docs/BUILD.md) | Firmware with native `ssh` |
| [docs/UPSTREAM.md](docs/UPSTREAM.md) | Communicator Badge files you still need |
| [test-server/README.md](test-server/README.md) | Local password SSH server |

## Root shortcuts

These forward to `scripts/`:

| Script | Forwards to |
|--------|-------------|
| `push-to-badge.ps1` | `scripts/deploy/push-to-badge.ps1` |
| `build-firmware.ps1` | `scripts/build/build-firmware.ps1` |
| `run-ssh-rw-test.ps1` | `scripts/test/run-ssh-rw-test.ps1` |

## Authentication

- **Password:** F3 edit user/password, F4 shows `Pass`, F1 connect.
- **Pubkey:** Copy private key to `/data/ssh_id_ed25519` (or set `ssh_key_path`), F4 until `pubkey`, F1 connect.

Requires custom firmware for real SSH (not just TCP probe). Keys: OpenSSH PEM or RSA PEM.

## License

Match upstream Communicator Badge and component licenses (libssh2, LVGL, MicroPython).
