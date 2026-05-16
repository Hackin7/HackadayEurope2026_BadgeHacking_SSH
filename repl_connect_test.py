"""Connect using badge config (pubkey or password). mpremote connect COM11 run repl_connect_test.py"""

import gc
import time


def cfg(key, default=""):
    from hardware.datafile import Config

    v = Config().get(key, default.encode() if isinstance(default, str) else default)
    if v is None:
        return default
    return v.decode() if isinstance(v, bytes) else str(v)


print("=== repl_connect_test ===")

import ssh
from apps.ssh import backend, identity

host = cfg("ssh_host")
port = int(cfg("ssh_port", "22") or "22")
user = cfg("ssh_user")
auth = cfg("ssh_auth", "password")
password = cfg("ssh_password")
key_path = cfg("ssh_key_path", identity.DEFAULT_KEY_PATH)
key_pp = cfg("ssh_key_passphrase")

_, host, port = backend.parse_host_port(host, port)
print("target", user + "@" + host + ":" + str(port))
print("auth", auth, "key", identity.key_file_hint(key_path))

ssid = cfg("wifi_ssid")
from hardware.wifi import wifi

if not wifi.is_connected():
    wifi.connect(ssid, cfg("wifi_password"), timeout_ms=30000)
print("wifi", wifi.status().get("ip"))

kw, note = identity.resolve_connect_kwargs(
    auth, password, key_path, key_pp, True
)
print("resolve", note, "has_key", bool(kw and kw.get("private_key")))

if not kw:
    print("FAIL resolve")
    raise SystemExit

err = ssh.connect(
    host,
    port,
    user,
    kw.get("password", ""),
    private_key=kw.get("private_key"),
    key_passphrase=kw.get("key_passphrase", ""),
)
print("connect", err)
if err != 0:
    print("FAIL codes -5 pass -6 pubkey")
    raise SystemExit

print("fingerprint", ssh.get_fingerprint())
rc = ssh.open_shell(40, 6)
print("open_shell", rc)
if rc == 0:
    time.sleep_ms(500)
    print("read", ssh.read(512))
    from apps.ssh import backend as b

    backend._native_write(b"echo badge-repl-ok\n")
    time.sleep_ms(400)
    print("after write", ssh.read(512))
ssh.close()
print("PASS")
gc.collect()
