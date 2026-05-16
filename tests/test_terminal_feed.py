"""Unit-style check for terminal.feed (run on host: python test_terminal_feed.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "badge" / "apps" / "ssh"))
from terminal import TerminalView  # noqa: E402


def test_char_echo_no_extra_lines():
    t = TerminalView()
    t.feed(b"banner\n")
    n0 = len(t._lines)
    for ch in b"abc":
        t.note_tx(bytes([ch]))
    assert t._partial == "abc", t._partial
    assert len(t._lines) == n0, (t._lines, n0)
    vis = t.visible_lines()
    assert vis[-1] == "abc", vis


def test_remote_echo_deduped():
    t = TerminalView()
    t.note_tx(b"xy")
    t.feed(b"xy")
    assert t._partial == "xy"
    assert len(t._tx_echo) == 0
    t.feed(b"!\n")
    assert list(t._lines) == ["xy!"]


def test_echo_take_micropython_style():
    t = TerminalView()
    t._tx_echo = bytearray(b"ab")
    assert t._echo_take(ord("a"))
    assert bytes(t._tx_echo) == b"b"


def test_enter_commits_line():
    t = TerminalView()
    t.note_tx(b"hello\n")
    assert list(t._lines) == ["hello"]
    assert t._partial == ""


if __name__ == "__main__":
    test_char_echo_no_extra_lines()
    test_remote_echo_deduped()
    test_echo_take_micropython_style()
    test_enter_commits_line()
    print("terminal.feed OK")
