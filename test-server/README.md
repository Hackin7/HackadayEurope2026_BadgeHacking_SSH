# Local SSH test server (Paramiko)

Password-only SSH server for testing the badge MicroPython `ssh` module on the same WiFi LAN.

## Defaults

| Setting  | Value   |
| -------- | ------- |
| Port     | 2222    |
| User     | badge   |
| Password | badge   |

## Setup

```powershell
cd badgehacking\ssh\test-server
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python generate_host_key.py
```

## Find your PC IP

Join the **same WiFi** as the badge (e.g. `zfliphack`), then:

```powershell
ipconfig
```

Use the WiFi adapter IPv4 address (not `127.0.0.1`).

## Windows Firewall

Allow inbound **TCP 2222** on Private networks:

```powershell
New-NetFirewallRule -DisplayName "Badge SSH test 2222" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 2222
```

Or temporarily allow Python through the firewall when prompted.

## Run server

```powershell
python local_ssh_server.py
```

Leave this terminal open. You should see `SSH test server on 0.0.0.0:2222` when ready.

## Sanity check (PC OpenSSH client, optional)

```powershell
ssh -p 2222 badge@<PC_IP>
# password: badge
```

## Badge test

From repo root, with server running:

```powershell
cd badgehacking\ssh
.\run-local-ssh-test.ps1 -PcIp <PC_IP> -Port COM11
```

Or set `PC_HOST` in `repl_password_local_test.py` and:

```powershell
cd 2025-Communicator_Badge\firmware
.\venv\Scripts\activate
mpremote connect COM11 run ..\..\badgehacking\ssh\repl_password_local_test.py
```

Success: `connect 0`, shell output contains `badge-ok`.

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| Badge `connect -2` | Wrong IP, firewall, or server not running |
| Badge `connect -4` | KEX/cipher mismatch — check server log |
| Badge `connect -5` | Wrong user/password |
| No connection logged on PC | Badge and PC not on same LAN |
