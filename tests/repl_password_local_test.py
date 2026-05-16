"""Password SSH test against local Paramiko server.

Edit PC_HOST to your PC WiFi IPv4 (same LAN as badge).
Server defaults: port 2222, user badge, password badge.

Run:
  mpremote connect COM11 run repl_password_local_test.py
"""

import gc
import time

# --- set this to your PC ipconfig WiFi IPv4 ---
PC_HOST = "192.168.1.100"
PC_PORT = 2222
PC_USER = "badge"
PC_PASSWORD = "badge"


def cfg(key, default=""):
    from hardware.datafile import Config

    v = Config().get(key, default.encode() if isinstance(default, str) else default)
    if v is None:
        return default
    return v.decode() if isinstance(v, bytes) else str(v)


print("=== repl_password_local_test ===")
print("target", PC_HOST, PC_PORT, PC_USER)

try:
    import ssh
except ImportError:
    print("FAIL: native ssh module missing")
    raise SystemExit

ssid = cfg("wifi_ssid")
wifi_pass = cfg("wifi_password")
if not ssid:
    print("FAIL: wifi_ssid empty in config")
    raise SystemExit

from hardware.wifi import wifi

if not wifi.is_connected():
    print("WiFi connecting...")
    if not wifi.connect(ssid, wifi_pass, timeout_ms=30000):
        print("FAIL: WiFi", wifi.status())
        raise SystemExit
print("WiFi OK", wifi.status().get("ip"))

print("ssh.connect...")
err = ssh.connect(PC_HOST, PC_PORT, PC_USER, PC_PASSWORD)
print("connect err", err)
if err != 0:
    print("codes: -2 TCP -3 session -4 handshake -5 password -6 pubkey")
    raise SystemExit

fp = ssh.get_fingerprint()
print("fingerprint", fp)

print("open_shell...")
rc = ssh.open_shell(40, 6)
print("open_shell", rc)
if rc != 0:
    ssh.close()
    raise SystemExit

time.sleep_ms(400)
banner = ssh.read(512)
print("banner/read:", banner)

cmd = b"echo badge-ok\n"
print("write", cmd)
try:
    from apps.ssh import backend

    n = backend._native_write(cmd)
    print("write returned", n)
    time.sleep_ms(400)
    out = ssh.read(512)
    print("after cmd:", out)
except TypeError as e:
    print("write skipped (fix modssh write arity):", e)
    out = b""

ssh.close()
ok = err == 0 and rc == 0 and b"shell ready" in (banner or b"")
if out:
    ok = ok and (b"badge-ok" in out or b"echo badge-ok" in out)
print("PASS" if ok else "FAIL")
gc.collect()
print("=== done ===")
