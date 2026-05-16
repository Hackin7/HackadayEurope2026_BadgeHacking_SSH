"""SSH backends: native `ssh` module or TCP banner probe only."""

try:
  import ssh as _ssh_native

  _HAS_NATIVE = True
except ImportError:
  _ssh_native = None
  _HAS_NATIVE = False


def has_native_ssh() -> bool:
  return _HAS_NATIVE


def tcp_banner(host: str, port: int, timeout: int = 10) -> bytes:
  import socket

  addr = socket.getaddrinfo(host, port)[0][-1]
  s = socket.socket()
  s.settimeout(timeout)
  s.connect(addr)
  data = s.recv(128)
  s.close()
  return data


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
    if _HAS_NATIVE and data:
      _ssh_native.write(data)

  def close(self) -> None:
    if _HAS_NATIVE:
      try:
        _ssh_native.close()
      except OSError:
        pass
    self._open = False
