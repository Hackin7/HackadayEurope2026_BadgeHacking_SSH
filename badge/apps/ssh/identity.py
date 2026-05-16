"""SSH credentials: password or on-device private key (OpenSSH PEM)."""

DEFAULT_KEY_PATH = "/data/ssh_id_ed25519"
AUTH_PASSWORD = "password"
AUTH_PUBKEY = "pubkey"


def normalize_auth(mode: str) -> str:
  if mode and str(mode).lower() in ("key", "pubkey", "publickey", "pk"):
    return AUTH_PUBKEY
  return AUTH_PASSWORD


def read_private_key(path: str):
  """Load private key PEM from badge filesystem. Returns str or None."""
  if not path:
    path = DEFAULT_KEY_PATH
  try:
    with open(path, "r") as f:
      data = f.read()
  except OSError:
    return None
  if not data:
    return None
  data = data.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"
  up = data.upper()
  if "BEGIN OPENSSH PUBLIC KEY" in up or "BEGIN SSH PUBLIC KEY" in up:
    return None
  if "PUBLIC KEY" in up and "PRIVATE KEY" not in up:
    return None
  if "BEGIN OPENSSH PRIVATE KEY" in up:
    return data
  if "BEGIN EC PRIVATE KEY" in up:
    return data
  if "BEGIN RSA PRIVATE KEY" in up:
    return data
  if "PRIVATE KEY" in up:
    return data
  return None


def key_file_hint(path: str) -> str:
  """Short status for UI / REPL (no secret material)."""
  if not path:
    path = DEFAULT_KEY_PATH
  try:
    with open(path, "r") as f:
      head = f.read(120)
  except OSError as e:
    return f"missing ({e})"
  head = head.replace("\r", "")
  if "PUBLIC KEY" in head.upper() and "PRIVATE" not in head.upper():
    return "WRONG: public key file — need id_ed25519 private key"
  if "OPENSSH PRIVATE KEY" in head:
    return "OpenSSH private key OK"
  if "RSA PRIVATE KEY" in head:
    return "RSA private key OK"
  if "EC PRIVATE KEY" in head:
    return "EC private key OK"
  if "PRIVATE KEY" in head.upper():
    return "private key OK"
  return "unrecognized key format"


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
    hint = key_file_hint(path)
    if "WRONG: public key" in hint:
      return {}, "public key on badge — install private key (install-key.ps1)"
    if password:
      return _password_kwargs(password, key_passphrase), "using password (no private key)"
    return {}, f"private key not found: {path} ({hint})"

  if has_native_ssh:
    if not password:
      return {}, "SSH password not set (F3 Edit)"
    return _password_kwargs(password, key_passphrase), None

  return _password_kwargs("", ""), None


def build_connect_kwargs(auth_mode, password, key_path, key_passphrase):
  return resolve_connect_kwargs(
    auth_mode, password, key_path, key_passphrase, False
  )
