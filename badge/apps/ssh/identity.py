"""SSH credentials: password or on-device private key (OpenSSH PEM)."""

DEFAULT_KEY_PATH = "/data/ssh_id_ed25519"
AUTH_PASSWORD = "password"
AUTH_PUBKEY = "pubkey"


def normalize_auth(mode: str) -> str:
  if mode and str(mode).lower() in ("key", "pubkey", "publickey", "pk"):
    return AUTH_PUBKEY
  return AUTH_PASSWORD


def read_private_key(path: str):
  if not path:
    path = DEFAULT_KEY_PATH
  try:
    with open(path, "r") as f:
      data = f.read()
  except OSError:
    return None
  if not data or "PRIVATE KEY" not in data:
    return None
  return data


def build_connect_kwargs(
  auth_mode: str,
  password: str,
  key_path: str,
  key_passphrase: str,
):
  """Return (kwargs for backend.Session.connect, error_message)."""
  auth_mode = normalize_auth(auth_mode)
  if auth_mode == AUTH_PUBKEY:
    pem = read_private_key(key_path or DEFAULT_KEY_PATH)
    if not pem:
      path = key_path or DEFAULT_KEY_PATH
      return {}, f"SSH key not found: {path}"
    kw = {
      "password": "",
      "private_key": pem,
      "key_passphrase": key_passphrase or "",
    }
    return kw, None
  return {"password": password or "", "private_key": None, "key_passphrase": ""}, None
