"""Diagnose pubkey auth on badge. Run: mpremote connect COM11 run repl_pubkey_test.py"""

import gc


def cfg(key, default=""):
    from hardware.datafile import Config

    v = Config().get(key, default.encode() if isinstance(default, str) else default)
    if v is None:
        return default
    return v.decode() if isinstance(v, bytes) else str(v)


print("=== repl_pubkey_test ===")

try:
    import ssh
except ImportError:
    print("FAIL: no native ssh module")
    raise SystemExit

from apps.ssh import backend, identity

host = cfg("ssh_host")
port = int(cfg("ssh_port", "22") or "22")
user = cfg("ssh_user")
auth = cfg("ssh_auth", "password")
key_path = cfg("ssh_key_path", identity.DEFAULT_KEY_PATH)
key_pp = cfg("ssh_key_passphrase")

_, host, port = backend.parse_host_port(host, port)
print("host", repr(host), "port", port)
print("user", repr(user), "(must match server account, e.g. zunmun)")
print("auth", repr(auth), "->", identity.normalize_auth(auth))
print("key_path", repr(key_path))
print("key_file", identity.key_file_hint(key_path))

ssid = cfg("wifi_ssid")
from hardware.wifi import wifi

if not wifi.is_connected():
    if not wifi.connect(ssid, cfg("wifi_password"), timeout_ms=30000):
        print("FAIL WiFi", wifi.status())
        raise SystemExit

kw, note = identity.resolve_connect_kwargs(
    identity.AUTH_PUBKEY, "", key_path, key_pp, True
)
print("resolve note", note)
if not kw or not kw.get("private_key"):
    print("FAIL: no private_key loaded —", note or identity.key_file_hint(key_path))
    raise SystemExit

pem = kw["private_key"]
print("private_key bytes", len(pem), "lines", pem.count("\n") + 1)
print("first line", pem.split("\n", 1)[0])

if not user:
    print("FAIL: ssh_user empty — set to server username (F3 Edit)")
    raise SystemExit

print("ssh.connect pubkey...")
err = ssh.connect(
    host,
    port,
    user,
    "",
    private_key=pem,
    key_passphrase=kw.get("key_passphrase", ""),
)
print("connect err", err)
print("codes: -5 password -6 pubkey rejected -7 key format/passphrase")
if err == 0:
    print("PASS — trust host in app if prompted")
    ssh.close()
else:
    print("FAIL")
    print("Checklist:")
    print("  1. Server has THIS public key in ~/.ssh/authorized_keys")
    print("  2. Badge has PRIVATE key (not .pub) at", key_path)
    print("  3. ssh_user matches Linux user on server")
    print("  4. F4 until menu shows Auth: pubkey")
    print("  5. Key passphrase in config if key is encrypted")

gc.collect()
print("=== done ===")
