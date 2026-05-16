"""User-facing SSH / WiFi error messages."""

# WiFi helper status strings
WIFI_ERRORS = {
  "timeout": "WiFi: connection timed out",
  "no network module": "WiFi: not available on this firmware",
}


def _wifi_internal_message(text: str) -> str:
  low = text.lower()
  if "internal" in low:
    return "WiFi stack busy — retry in a few seconds"
  return ""

# Native ssh.connect() return codes (modssh.c)
SSH_CONNECT_ERRORS = {
  -1: "SSH: libssh2 init failed",
  -2: "SSH: TCP connect failed",
  -3: "SSH: session init failed",
  -4: "SSH: handshake failed",
  -5: "SSH: login failed (user/password)",
  -6: "SSH: public key auth failed",
}


def format_wifi_error(status: dict) -> str:
  err = status.get("error", "")
  if not err:
    return "WiFi: could not connect"
  if err in WIFI_ERRORS:
    return WIFI_ERRORS[err]
  hint = _wifi_internal_message(err)
  if hint:
    return hint
  if err.startswith("wifi status"):
    code = err.split()[-1]
    if code == "201":
      return "WiFi: wrong password"
    if code in ("202", "203", "204"):
      return "WiFi: AP not found or connect failed"
    return f"WiFi: connect failed ({code})"
  return f"WiFi: {err}"


def format_error(payload) -> str:
  if payload is None:
    return "Unknown error"
  text = str(payload).strip()
  if not text:
    return "Unknown error"

  low = text.lower()
  if low in WIFI_ERRORS:
    return WIFI_ERRORS[low]
  if low == "host key denied":
    return "Host key not trusted (F1 to trust)"
  if low == "no _thread":
    return "SSH worker unavailable"
  if low == "set wifi first":
    return "Set WiFi (F2) before connecting"
  if low == "host/user required":
    return "Set host and user (F3 Edit)"
  if low.startswith("ssh key not found"):
    return text
  if "pubkey needs" in low:
    return "Public key needs custom firmware"

  if text.startswith("exec failed"):
    return "Remote command failed"

  if text.startswith("connect "):
    try:
      code = int(text.split(" ", 1)[1])
      if code in SSH_CONNECT_ERRORS:
        return SSH_CONNECT_ERRORS[code]
    except ValueError:
      pass
    return f"SSH connect failed ({text})"

  hint = _wifi_internal_message(text)
  if hint:
    return hint
  if "wifi" in low or low == "timeout":
    return format_wifi_error({"error": text})

  if "[errno 110]" in low or "timed out" in low or "timeout" in low:
    return "Network: connection timed out"
  if "[errno -2]" in low or "enoent" in low:
    return "Network: host not found"
  if "[errno -3]" in low or "econnaborted" in low:
    return "Network: connection aborted"
  if "gaierror" in low or "errno" in low or "econn" in low:
    return f"Network: {text[:60]}"

  if "auth" in low or "password" in low or "login" in low:
    return f"Auth failed: {text[:50]}"

  return text[:80]
