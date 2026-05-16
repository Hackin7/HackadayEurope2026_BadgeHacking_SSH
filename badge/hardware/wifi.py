"""WiFi STA helper for badge apps (SSH, etc.)."""

import time

try:
  import network
except ImportError:
  network = None  # type: ignore

# ESP32 MicroPython WLAN.status() values
_STAT_FAIL = (201, 202, 203, 204, -1, -2, -3)


class WiFi:
  def __init__(self):
    self._wlan = None
    self._last_error = ""
    self._connecting = False
    self._ssid = ""
    self._password = ""
    self._deadline = 0
    self._attempt = 0
    self._max_attempts = 2

  def _sta(self):
    if network is None:
      self._last_error = "no network module"
      return None
    if self._wlan is None:
      self._wlan = network.WLAN(network.STA_IF)
    return self._wlan

  def _reset_sta(self, wlan) -> None:
    try:
      if wlan.isconnected():
        wlan.disconnect()
    except OSError:
      pass
    try:
      wlan.active(False)
    except OSError:
      pass
    time.sleep_ms(150)
    wlan.active(True)
    time.sleep_ms(150)

  def active(self) -> bool:
    wlan = self._sta()
    return wlan is not None and wlan.active()

  def is_connected(self) -> bool:
    wlan = self._sta()
    return wlan is not None and wlan.isconnected()

  def status(self) -> dict:
    wlan = self._sta()
    out = {
      "connected": False,
      "ssid": "",
      "ip": "",
      "subnet": "",
      "gateway": "",
      "dns": "",
      "rssi": 0,
      "error": self._last_error,
    }
    if wlan is None:
      return out
    out["connected"] = wlan.isconnected()
    if out["connected"]:
      cfg = wlan.ifconfig()
      out["ip"] = cfg[0]
      out["subnet"] = cfg[1]
      out["gateway"] = cfg[2]
      out["dns"] = cfg[3]
      try:
        out["ssid"] = wlan.config("ssid")
      except OSError:
        out["ssid"] = ""
      try:
        out["rssi"] = wlan.status("rssi")
      except OSError:
        out["rssi"] = 0
    return out

  def begin_connect(self, ssid, password, timeout_ms: int = 25000) -> None:
    wlan = self._sta()
    if wlan is None:
      self._connecting = False
      return
    if isinstance(ssid, bytes):
      ssid = ssid.decode()
    if isinstance(password, bytes):
      password = password.decode()
    self._ssid = ssid
    self._password = password
    self._last_error = ""
    self._attempt = 0
    self._max_attempts = 2
    self._deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
    self._connecting = True
    wlan.active(True)
    if wlan.isconnected():
      try:
        if wlan.config("ssid") == ssid:
          self._connecting = False
          return
      except OSError:
        pass
    self._issue_connect()

  def _issue_connect(self) -> None:
    wlan = self._sta()
    if wlan is None:
      self._connecting = False
      return
    self._attempt += 1
    if self._attempt > 1:
      self._reset_sta(wlan)
    try:
      wlan.connect(self._ssid, self._password)
    except OSError as e:
      msg = str(e)
      self._last_error = msg
      low = msg.lower()
      if "internal" in low and self._attempt < self._max_attempts:
        self._issue_connect()
        return
      self._connecting = False

  def poll_connect(self) -> tuple:
    """Return ('running'|'ok'|'fail'|'idle', detail)."""
    if not self._connecting:
      if self.is_connected():
        return ("ok", "")
      return ("idle", self._last_error)

    wlan = self._sta()
    if wlan is None:
      self._connecting = False
      return ("fail", self._last_error or "no network module")

    if wlan.isconnected():
      self._connecting = False
      self._last_error = ""
      return ("ok", "")

    status = wlan.status()
    if status in _STAT_FAIL:
      self._last_error = f"wifi status {status}"
      if self._attempt < self._max_attempts:
        self._issue_connect()
        return ("running", "")
      self._connecting = False
      return ("fail", self._last_error)

    if time.ticks_diff(self._deadline, time.ticks_ms()) <= 0:
      self._last_error = "timeout"
      self._connecting = False
      return ("fail", "timeout")

    return ("running", "")

  def connect(self, ssid, password, timeout_ms: int = 25000) -> bool:
    self.begin_connect(ssid, password, timeout_ms)
    while self._connecting:
      phase, _ = self.poll_connect()
      if phase == "ok":
        return True
      if phase == "fail":
        return False
      time.sleep_ms(200)
    return self.is_connected()

  def cancel_connect(self) -> None:
    self._connecting = False

  def disconnect(self) -> None:
    self.cancel_connect()
    wlan = self._sta()
    if wlan is not None and wlan.isconnected():
      try:
        wlan.disconnect()
      except OSError:
        pass


wifi = WiFi()
