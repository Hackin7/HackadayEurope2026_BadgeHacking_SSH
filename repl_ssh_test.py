"""SSH/WiFi REPL test — run on badge:
  mpremote connect COM11 run repl_ssh_test.py

Uses /data/config (wifi_ssid, ssh_host, ssh_port, ssh_user).
Override host with SSH_TEST_HOST env not available on MPY — edit SSH_HOST below.
"""

import gc
import sys
import time

# Fallback if config empty
SSH_HOST = ""
SSH_PORT = 22


def cfg_bytes(key, default=b""):
    try:
        from hardware.datafile import Config

        v = Config().get(key, default)
        return v if v is not None else default
    except Exception as e:
        print("config err", e)
        return default


def cfg_str(key, default=""):
    raw = cfg_bytes(key, default.encode() if default else b"")
    return raw.decode() if isinstance(raw, bytes) else str(raw)


print("=== repl_ssh_test ===")
print(sys.implementation)

ssid = cfg_str("wifi_ssid")
password = cfg_str("wifi_password")
host = cfg_str("ssh_host") or SSH_HOST
port = int(cfg_str("ssh_port", "22") or "22")
user = cfg_str("ssh_user")
if "@" in host and not user:
    user, _, host = host.partition("@")
    print("parsed user@host -> user:", repr(user[:8] + "..."), "host:", host)

print("config ssid:", repr(ssid[:20] + ("..." if len(ssid) > 20 else "")))
print("config host:", repr(host), "port:", port, "user:", repr(user))

try:
    import ssh

    print("native ssh: OK")
except ImportError:
    print("native ssh: MISSING")

# WiFi
if not ssid:
    print("SKIP WiFi: wifi_ssid empty — set in SSH app (F2) or Config")
else:
    from hardware.wifi import wifi

    print("connecting WiFi...")
    ok = wifi.connect(ssid, password, timeout_ms=25000)
    st = wifi.status()
    print("WiFi:", ok, st)
    if not ok:
        print("abort: no WiFi")
        raise SystemExit

# TCP SSH banner
if not host:
    host = "test.rebex.net"
    print("using default host:", host)

try:
    import socket

    print("resolve", host, port)
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.settimeout(15)
    s.connect(addr)
    banner = s.recv(128)
    print("TCP OK banner:", banner)
    s.send(b"SSH-2.0-badge-test\r\n")
    s.close()
except Exception as e:
    print("TCP FAIL:", type(e).__name__, e)

# App backend
try:
    from apps.ssh import backend

    print("backend has_native:", backend.has_native_ssh())
    print("backend Session.available:", backend.Session.available())
    key_path = cfg_str("ssh_key_path", "/data/ssh_id_ed25519")
    auth = cfg_str("ssh_auth", "password")
    from apps.ssh import identity

    kw, err = identity.build_connect_kwargs(auth, "", key_path, "")
    if err:
        print("auth:", err)
    elif backend.has_native_ssh() and user and host:
        print("trying ssh.exec auth=", auth)
        r = backend.exec_command(
            host, port, user, kw.get("password", ""), "uname -a",
            private_key=kw.get("private_key"),
            key_passphrase=kw.get("key_passphrase", ""),
        )
        print("exec result code:", r[0] if r else "?")
        if r and len(r) > 2:
            print("exec out:", r[2][:200])
except Exception as e:
    print("backend err:", e)

gc.collect()
try:
    import micropython

    micropython.mem_info()
except ImportError:
    pass
print("=== done ===")
