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


def _password_kwargs(password: str, key_passphrase: str = ""):
  return {
    "password": password or "",
    "private_key": None,
    "key_passphrase": key_passphrase or "",
  }


def resolve_connect_kwargs(
  auth_mode: str,
  password: str,
  key_path: str,
  key_passphrase: str,
  has_native_ssh: bool,
):
  """Pick auth for connect; fall back when pubkey unavailable on this firmware."""
  auth_mode = normalize_auth(auth_mode)
  path = key_path or DEFAULT_KEY_PATH

  if has_native_ssh and auth_mode == AUTH_PUBKEY:
    pem = read_private_key(path)
    if pem:
      return {
        "password": "",
        "private_key": pem,
        "key_passphrase": key_passphrase or "",
      }, None
    if password:
      return _password_kwargs(password, key_passphrase), "using password (no key file)"
    return {}, f"SSH key not found: {path}"

  if has_native_ssh:
    if not password:
      return {}, "SSH password not set (F3 Edit)"
    return _password_kwargs(password, key_passphrase), None

  # Stock firmware: TCP banner probe only (no SSH auth on device).
  return _password_kwargs("", ""), None


# Backward-compatible name
def build_connect_kwargs(auth_mode, password, key_path, key_passphrase):
  return resolve_connect_kwargs(
    auth_mode, password, key_path, key_passphrase, False
  )
