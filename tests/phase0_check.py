"""Run on badge via: mpremote connect COM11 run phase0_check.py
Set WIFI_SSID / WIFI_PASSWORD below before running, or skip WiFi block.
"""

import gc
import sys
import time

WIFI_SSID = ""
WIFI_PASSWORD = ""
TCP_HOST = "test.rebex.net"
TCP_PORT = 22

print("=== phase0_check ===")
print("impl:", sys.implementation)

try:
    import micropython

    micropython.mem_info()
except ImportError:
    pass

for name in ("network", "socket", "ssl", "_thread", "asyncio", "ssh"):
    try:
        __import__(name)
        print(name, "OK")
    except ImportError as e:
        print(name, "MISSING", e)

gc.collect()

if WIFI_SSID:
    import network

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    for i in range(30):
        if wlan.isconnected():
            print("WiFi OK", wlan.ifconfig())
            break
        time.sleep(1)
    else:
        print("WiFi timeout")
else:
    print("WiFi: skipped (set WIFI_SSID in script)")

try:
    import socket

    addr = socket.getaddrinfo(TCP_HOST, TCP_PORT)[0][-1]
    s = socket.socket()
    s.settimeout(10)
    s.connect(addr)
    banner = s.recv(64)
    print("TCP banner:", banner)
    s.close()
except Exception as e:
    print("TCP failed:", e)

gc.collect()
try:
    import micropython

    micropython.mem_info()
except ImportError:
    pass
print("=== done ===")
