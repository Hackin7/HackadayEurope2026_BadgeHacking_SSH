"""Per-character echo test: send a,b,c and print raw RX chunks."""

import time
from collections import deque

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


from apps.ssh import backend, identity, terminal, worker
from hardware.wifi import wifi

print("=== repl_char_echo_test ===")

ssid = cfg("wifi_ssid")
if not wifi.is_connected():
    wifi.connect(ssid, cfg("wifi_password"), timeout_ms=30000)

kw, _ = identity.resolve_connect_kwargs(
    identity.AUTH_PASSWORD, PC_PASSWORD, "", "", True
)
tx = deque([], 64)
rx = deque([], 32)
ev = deque([], 16)
h = worker.start_session(
    PC_HOST, PC_PORT, PC_USER, kw, ssid, "", tx, rx, ev, True, True
)
t = terminal.TerminalView()
start = time.ticks_ms()
trusted = False
ready = False
while time.ticks_diff(time.ticks_ms(), start) < 30000:
    while ev:
        k, p = ev.popleft()
        if k == "fingerprint":
            h.trusted = True
        if k == "session":
            ready = True
        if k == "error":
            print("ERR", p)
            raise SystemExit
    while rx:
        chunk = rx.popleft()
        print("rx chunk", repr(chunk))
        t.feed(chunk)
    if ready and not trusted:
        trusted = True
    if ready and trusted and not tx:
        for c in b"abc":
            tx.append(bytes([c]))
            time.sleep_ms(200)
        time.sleep_ms(500)
        while rx:
            chunk = rx.popleft()
            print("rx chunk", repr(chunk))
            t.feed(chunk)
        print("partial", repr(t._partial))
        print("lines", list(t._lines))
        print("screen:\n", t.as_text())
        ok = t._partial == "abc" and len(t._lines) == 1
        print("PASS" if ok else "FAIL")
        break
    time.sleep_ms(25)

worker.stop_session(h)
