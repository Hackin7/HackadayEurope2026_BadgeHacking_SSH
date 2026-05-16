# On-badge test scripts

Run from PC with upstream `firmware/venv` activated:

```powershell
mpremote connect COM11 run tests\repl_ssh_rw_test.py
```

| Script | Purpose |
|--------|---------|
| `repl_ssh_rw_test.py` | Native ssh read/write vs local Paramiko (use `scripts/test/run-ssh-rw-test.ps1`) |
| `repl_password_local_test.py` | Password auth to local server |
| `repl_connect_test.py` | Connect using `/data/config` |
| `repl_pubkey_test.py` | Pubkey diagnostics |
| `repl_app_io_test.py` | Worker + queues (app layer) |
| `repl_lib_test.py` | Module / WiFi / socket smoke test |
| `phase0_check.py` | Early hardware/network sanity check |

Most LAN tests patch `PC_HOST` automatically when run via `scripts/test/run-local-ssh-test.ps1`.
