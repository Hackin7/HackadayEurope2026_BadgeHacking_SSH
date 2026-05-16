"""On-badge library test: read /data/config, WiFi, TCP, ssh module, apps.ssh.backend.
Run: mpremote connect COM11 run repl_lib_test.py
"""

import gc
import sys


def cfg(key, default=""):
    from hardware.datafile import Config

    v = Config().get(key, default.encode() if isinstance(default, str) else default)
    if v is None:
        return default
    return v.decode() if isinstance(v, bytes) else str(v)


def mask(s, show=4):
    if not s:
        return "(empty)"
    if len(s) <= show:
        return "*" * len(s)
    return s[:show] + "..." + ("*" * min(4, len(s) - show))


print("=== repl_lib_test ===")
print("mpy:", sys.implementation.name, getattr(sys.implementation, "version", ""))

# --- config ---
keys = [
    "wifi_ssid",
    "wifi_password",
    "ssh_host",
    "ssh_port",
    "ssh_user",
    "ssh_password",
    "ssh_auth",
    "ssh_key_path",
    "ssh_key_passphrase",
]
print("\n--- /data/config ---")
cfgmap = {}
for k in keys:
    cfgmap[k] = cfg(k)
    if "password" in k or "passphrase" in k:
        print(k + ":", mask(cfgmap[k]))
    else:
        print(k + ":", repr(cfgmap[k]))

host = cfgmap["ssh_host"]
port = int(cfgmap["ssh_port"] or "22")
user = cfgmap["ssh_user"]
if "@" in host and not user:
    user, _, host = host.partition("@")
    print("parsed user@host -> user:", mask(user), "host:", host)

try:
    from apps.ssh import backend

    _, host, port = backend.parse_host_port(host, port)
    print("parsed host/port:", repr(host), port)
except Exception as e:
    print("parse_host_port err:", e)

# --- native ssh module ---
print("\n--- import ssh ---")
try:
    import ssh as ssh_native

    print("ssh: OK", dir(ssh_native))
    for fn in ("connect", "get_fingerprint", "open_shell", "read", "write", "close", "exec"):
        print(" ", fn, ":", hasattr(ssh_native, fn))
except ImportError as e:
    ssh_native = None
    print("ssh: MISSING", e)

# --- WiFi ---
print("\n--- hardware.wifi ---")
ssid = cfgmap["wifi_ssid"]
wifi_pass = cfgmap["wifi_password"]
if not ssid:
    print("SKIP: no wifi_ssid")
else:
    from hardware.wifi import wifi

    print("connecting...")
    ok = wifi.connect(ssid, wifi_pass, timeout_ms=30000)
    st = wifi.status()
    print("connect:", ok)
    print("status:", st)

if not host:
    print("\nSKIP SSH: ssh_host empty")
    raise SystemExit

# --- socket raw ---
print("\n--- socket TCP :22 ---")
try:
    import socket

    addrs = socket.getaddrinfo(host, port)
    print("getaddrinfo count:", len(addrs))
    s = socket.socket()
    s.settimeout(20)
    s.connect(addrs[0][-1])
    banner = s.recv(256)
    print("banner:", banner)
    s.close()
except Exception as e:
    print("socket FAIL:", type(e).__name__, e)

# --- backend ---
print("\n--- apps.ssh.backend ---")
try:
    from apps.ssh import backend, identity

    print("has_native_ssh:", backend.has_native_ssh())
    print("Session.available:", backend.Session.available())
    auth = cfgmap["ssh_auth"] or "password"
    ssh_pass = cfgmap["ssh_password"]
    key_path = cfgmap["ssh_key_path"] or identity.DEFAULT_KEY_PATH
    key_pp = cfgmap["ssh_key_passphrase"]
    kw, note = identity.resolve_connect_kwargs(
        auth, ssh_pass, key_path, key_pp, backend.has_native_ssh()
    )
    print("resolve_connect_kwargs note:", note)
    print("kwargs keys:", list(kw.keys()) if kw else None)
    print("has private_key:", bool(kw.get("private_key")) if kw else False)

    print("tcp_banner...")
    b = backend.tcp_banner(host, port, timeout=20)
    print("tcp_banner:", b)

    if backend.has_native_ssh() and user:
        print("\n--- ssh.connect ---")
        err = backend._native_connect(
            host,
            port,
            user,
            kw.get("password", ""),
            kw.get("private_key"),
            kw.get("key_passphrase", ""),
        )
        print("connect err code:", err)
        if err == 0:
            fp = ssh_native.get_fingerprint()
            print("fingerprint:", fp)
            print("open_shell(40,6)...")
            rc = ssh_native.open_shell(40, 6)
            print("open_shell:", rc)
            if rc == 0:
                data = ssh_native.read(512)
                print("read:", data[:120] if data else b"")
            ssh_native.close()
            print("closed")
except Exception as e:
    import sys

    sys.print_exception(e)

gc.collect()
print("\n=== done ===")
