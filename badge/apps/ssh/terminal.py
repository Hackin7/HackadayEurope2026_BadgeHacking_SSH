"""Scrollback terminal buffer for small LCD."""

from collections import deque

COLS = 40
ROWS = 6
MAX_LINES = 200


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

  def feed(self, data: bytes) -> None:
    if not data:
      return
    text = self._partial + _strip_ansi(data)
    self._partial = ""
    if text and text[-1] not in "\n":
      idx = text.rfind("\n")
      if idx >= 0:
        self._partial = text[idx + 1 :]
        text = text[: idx + 1]
      else:
        self._partial = text
        text = ""
    for line in text.split("\n"):
      if line:
        while len(line) > self.cols:
          self._lines.append(line[: self.cols])
          line = line[self.cols :]
        self._lines.append(line)
      else:
        self._lines.append("")
    while len(self._lines) > MAX_LINES:
      self._lines.popleft()

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
