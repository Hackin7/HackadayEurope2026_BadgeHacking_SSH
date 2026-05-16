"""Exercise the SSH *app* I/O path on the badge (worker + tx/rx queues).

Same code path as SSHClientApp in SESSION state, without LVGL.
PC test server: port 2222, user badge, password badge.

Run (from firmware venv):
  mpremote connect COM11 run repl_app_io_test.py
Or: .\\run-app-io-test.ps1 -Port COM11
"""

import gc
import time
from collections import deque

# Patched by run-app-io-test.ps1
PC_HOST = "192.168.1.100"
PC_PORT = 2222
PC_USER = "badge"
PC_PASSWORD = "badge"

TIMEOUT_MS = 45000


def cfg(key, default=""):
    from hardware.datafile import Config

    v = Config().get(key, default.encode() if isinstance(default, str) else default)
    if v is None:
        return default
    return v.decode() if isinstance(v, bytes) else str(v)


def drain_rx(rx_queue, buf):
    while rx_queue:
        chunk = rx_queue.popleft()
        if chunk:
            buf.append(chunk)
    return b"".join(buf)


print("=== repl_app_io_test ===")
print("target", PC_HOST, PC_PORT, PC_USER)

try:
    from apps.ssh import backend, identity, worker
except ImportError as e:
    print("FAIL: apps.ssh missing — run push-to-badge.ps1 first:", e)
    raise SystemExit

if not backend.Session.available():
    print("FAIL: native ssh + open_shell required")
    raise SystemExit

ssid = cfg("wifi_ssid")
wifi_pass = cfg("wifi_password")
if not ssid:
    print("FAIL: wifi_ssid empty")
    raise SystemExit

from hardware.wifi import wifi

if not wifi.is_connected():
    print("WiFi connecting...")
    if not wifi.connect(ssid, wifi_pass, timeout_ms=30000):
        print("FAIL: WiFi", wifi.status())
        raise SystemExit
print("WiFi OK", wifi.status().get("ip"))

kw, note = identity.resolve_connect_kwargs(
    identity.AUTH_PASSWORD,
    PC_PASSWORD,
    "",
    "",
    backend.has_native_ssh(),
)
if not kw:
    print("FAIL: auth", note)
    raise SystemExit

tx_queue = deque([], 64)
rx_queue = deque([], 32)
event_queue = deque([], 16)

handle = worker.start_session(
    PC_HOST,
    PC_PORT,
    PC_USER,
    kw,
    ssid,
    wifi_pass,
    tx_queue,
    rx_queue,
    event_queue,
    use_pty=True,
    skip_wifi=True,
)
if handle is None:
    print("FAIL: no _thread")
    raise SystemExit

received = []
session_ok = False
sent = False
start = time.ticks_ms()

print("waiting for session...")
while time.ticks_diff(time.ticks_ms(), start) < TIMEOUT_MS:
    drain_rx(rx_queue, received)

    while event_queue:
        kind, payload = event_queue.popleft()
        print("event", kind, payload)
        if kind == "fingerprint" and handle:
            handle.trusted = True
            print("auto-trust host key")
        elif kind == "session":
            session_ok = True
        elif kind == "error":
            print("FAIL:", payload)
            worker.stop_session(handle)
            raise SystemExit

    if session_ok and not sent:
        # Wait for banner so we know the read thread is receiving.
        if not any(b"shell ready" in c for c in received):
            time.sleep_ms(25)
            continue
        ping = b"PING\n"
        print("tx_queue append", ping, "qlen", len(tx_queue))
        tx_queue.append(ping)
        sent = True
        send_at = time.ticks_ms()

    if sent:
        joined = b"".join(received)
        if b"PING" in joined and len(joined) > len(b"shell ready"):
            print("rx after send:", joined[-80:])
            break
        if time.ticks_diff(time.ticks_ms(), send_at) > 8000:
            print("timeout tx_queue len", len(tx_queue), "rx", len(joined))
            break

    time.sleep_ms(25)

worker.stop_session(handle)
time.sleep_ms(200)
drain_rx(rx_queue, received)

joined = b"".join(received)
print("total rx bytes", len(joined))
print("rx tail:", joined[-200:] if joined else b"")

recv_banner = b"shell ready" in joined
recv_echo = sent and b"PING" in joined and len(joined) > len(b"shell ready")
ok = session_ok and sent and recv_banner and recv_echo
print("PASS" if ok else "FAIL")
print("  session:", session_ok, " sent:", sent, " banner:", recv_banner, " echo:", recv_echo)
if not ok and sent and len(tx_queue):
    print("  hint: tx_queue not drained — push worker.py (read thread fix)")
gc.collect()
print("=== done ===")
