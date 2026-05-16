"""Scrollback terminal buffer for small LCD."""

from collections import deque

COLS = 40
ROWS = 6
MAX_LINES = 200
ECHO_BUF = 128


def _strip_ansi(data: bytes) -> str:
  out = bytearray()
  i = 0
  n = len(data)
  while i < n:
    if data[i] == 0x1B and i + 1 < n and data[i + 1] == ord("["):
      i += 2
      while i < n and not (64 <= data[i] <= 126):
        i += 1
      if i < n:
        i += 1
      continue
    out.append(data[i])
    i += 1
  return out.decode("utf-8", "ignore").replace("\r", "")


class TerminalView:
  def __init__(self, cols: int = COLS, rows: int = ROWS):
    self.cols = cols
    self.rows = rows
    self._lines: deque[str] = deque([], MAX_LINES)
    self._partial = ""
    self._tx_echo = bytearray()

  def _append_wrapped(self, line: str) -> None:
    while len(line) > self.cols:
      self._lines.append(line[: self.cols])
      line = line[self.cols :]
    self._lines.append(line)
    while len(self._lines) > MAX_LINES:
      self._lines.popleft()

  def _commit_partial(self) -> None:
    if self._partial:
      self._append_wrapped(self._partial)
      self._partial = ""

  def _apply_char(self, ch: str) -> None:
    if ch == "\n":
      self._commit_partial()
    elif ch == "\x7f" or ch == "\b":
      if self._partial:
        self._partial = self._partial[:-1]
    elif ch >= " " or ch == "\t":
      self._partial += ch

  def _apply_text(self, text: str) -> None:
    for ch in text:
      self._apply_char(ch)

  def _echo_take(self, byte_val: int) -> bool:
    """Consume one pending local-echo byte (MicroPython bytearray has no .pop)."""
    if self._tx_echo and self._tx_echo[0] == byte_val:
      self._tx_echo = self._tx_echo[1:]
      return True
    return False

  def note_tx(self, data: bytes) -> None:
    """Show typed bytes immediately; skip duplicate bytes when echo returns."""
    if not data:
      return
    text = _strip_ansi(data)
    self._apply_text(text)
    enc = text.encode()
    if len(self._tx_echo) + len(enc) > ECHO_BUF:
      self._tx_echo = self._tx_echo[-(ECHO_BUF // 2) :]
    self._tx_echo.extend(enc)

  def feed(self, data: bytes) -> None:
    if not data:
      return
    remote = _strip_ansi(data)
    extra = []
    for ch in remote:
      if self._echo_take(ord(ch)):
        continue
      extra.append(ch)
    if extra:
      self._apply_text("".join(extra))

  def visible_lines(self) -> list[str]:
    buf = list(self._lines)
    if self._partial:
      tail = self._partial
      while len(tail) > self.cols:
        buf.append(tail[: self.cols])
        tail = tail[self.cols :]
      buf.append(tail)
    if len(buf) <= self.rows:
      pad = self.rows - len(buf)
      return [""] * pad + buf
    return buf[-self.rows :]

  def as_text(self) -> str:
    return "\n".join(self.visible_lines())

  def clear(self) -> None:
    self._lines = deque([], MAX_LINES)
    self._partial = ""
    self._tx_echo = bytearray()
