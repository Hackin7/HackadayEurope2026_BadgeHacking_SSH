"""SSH backends: native `ssh` module or TCP banner probe only."""

try:
  import ssh as _ssh_native

  _HAS_NATIVE = True
except ImportError:
  _ssh_native = None
  _HAS_NATIVE = False


def has_native_ssh() -> bool:
  return _HAS_NATIVE


def parse_host_port(host: str, port: int):
  """Split user@host:port from config mistakes."""
  user = ""
  if "@" in host:
    user, _, host = host.partition("@")
  if ":" in host:
    h, _, p = host.rpartition(":")
    if p.isdigit():
      host = h
      port = int(p)
  return user, host.strip(), port


def tcp_banner(host: str, port: int, timeout: int = 15) -> bytes:
  import socket

  _, host, port = parse_host_port(host, port)
  addrs = socket.getaddrinfo(host, port)
  last_err = None
  for info in addrs:
    addr = info[-1]
    s = socket.socket()
    try:
      s.settimeout(timeout)
      s.connect(addr)
      data = s.recv(256)
      s.close()
      return data
    except OSError as e:
      last_err = e
      try:
        s.close()
      except OSError:
        pass
  if last_err:
    raise last_err
  raise OSError("no address")


def _native_connect(host, port, user, password="", private_key=None, key_passphrase=""):
  if private_key:
    if hasattr(_ssh_native, "connect"):
      try:
        return _ssh_native.connect(
          host,
          port,
          user,
          password,
          private_key=private_key,
          key_passphrase=key_passphrase,
        )
      except TypeError:
        pass
    return -6
  return _ssh_native.connect(host, port, user, password)


def exec_command(
  host: str,
  port: int,
  user: str,
  password: str,
  command: str,
  private_key=None,
  key_passphrase: str = "",
):
  if not _HAS_NATIVE:
    raise OSError("native ssh module not installed")
  url = f"{host}/{command}"
  if private_key and hasattr(_ssh_native, "exec"):
    try:
      return _ssh_native.exec(
        url,
        user,
        password,
        port=port,
        private_key=private_key,
        key_passphrase=key_passphrase,
      )
    except TypeError:
      return (-6, b"exec", b"pubkey needs new firmware")
  return _ssh_native.exec(url, user, password, port=port)  # type: ignore


def _native_write(data: bytes) -> int:
  """Send bytes on the SSH channel (handles legacy modssh.write arity)."""
  if not _HAS_NATIVE or not data:
    return 0
  try:
    return _ssh_native.write(data)
  except TypeError:
    pass
  for extra in (None, _ssh_native):
    try:
      return _ssh_native.write(extra, data)
    except TypeError:
      continue
  return 0


class Session:
  """Interactive shell when native ssh + PTY APIs exist."""

  def __init__(self):
    self._open = False

  @staticmethod
  def available() -> bool:
    return _HAS_NATIVE and hasattr(_ssh_native, "open_shell")

  def connect(
    self,
    host: str,
    port: int,
    user: str,
    password: str = "",
    private_key=None,
    key_passphrase: str = "",
  ) -> int:
    if not _HAS_NATIVE:
      return -1
    if private_key and not has_native_ssh():
      return -6
    err = _native_connect(host, port, user, password, private_key, key_passphrase)
    self._open = err == 0
    return err

  def fingerprint(self) -> str:
    if not _HAS_NATIVE or not hasattr(_ssh_native, "get_fingerprint"):
      return ""
    fp = _ssh_native.get_fingerprint()
    if isinstance(fp, bytes):
      return fp.hex()
    return str(fp)

  def open_shell(self, cols: int, rows: int) -> int:
    if not self._open:
      return -1
    return _ssh_native.open_shell(cols, rows)

  def read(self, max_len: int = 256) -> bytes:
    if not _HAS_NATIVE:
      return b""
    return _ssh_native.read(max_len)

  def write(self, data: bytes) -> None:
    _native_write(data)

  def close(self) -> None:
    if _HAS_NATIVE:
      try:
        _ssh_native.close()
      except OSError:
        pass
    self._open = False
