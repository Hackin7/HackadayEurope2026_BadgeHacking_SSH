"""Native ssh module read/write test against local Paramiko server.

Run: mpremote connect COM11 run repl_ssh_rw_test.py
"""

import gc
import time

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


def native_write(data):
    from apps.ssh import backend

    return backend._native_write(data)


print("=== repl_ssh_rw_test ===")
print("target", PC_HOST, PC_PORT)

import ssh

ssid = cfg("wifi_ssid")
wifi_pass = cfg("wifi_password")
from hardware.wifi import wifi

if not wifi.is_connected():
    if not wifi.connect(ssid, wifi_pass, timeout_ms=30000):
        print("FAIL WiFi", wifi.status())
        raise SystemExit
print("WiFi", wifi.status().get("ip"))

err = ssh.connect(PC_HOST, PC_PORT, PC_USER, PC_PASSWORD)
print("connect", err)
if err != 0:
    raise SystemExit

rc = ssh.open_shell(40, 6)
print("open_shell", rc)
if rc != 0:
    ssh.close()
    raise SystemExit

time.sleep_ms(300)
banner = ssh.read(512)
print("read banner:", banner)

ok = True
echoed = b""
for ch in b"abc":
    n = native_write(bytes([ch]))
    print("write", repr(bytes([ch])), "->", n)
    time.sleep_ms(150)
    chunk = ssh.read(256)
    print("read", repr(chunk))
    if chunk:
        echoed += chunk

if echoed != b"abc":
    print("FAIL char echo expected b'abc' got", echoed)
    ok = False
else:
    print("char echo OK")

n = native_write(b"\n")
print("write newline ->", n)
time.sleep_ms(150)
chunk = ssh.read(256)
print("read after nl:", repr(chunk))

n = native_write(b"xyz\n")
print("write xyz\\n ->", n)
time.sleep_ms(300)
chunk = ssh.read(256)
print("read after xyz:", repr(chunk))
if chunk and b"xyz" not in chunk:
    print("FAIL xyz echo")
    ok = False

ssh.close()
print("PASS" if ok and b"shell ready" in (banner or b"") else "FAIL")
gc.collect()
