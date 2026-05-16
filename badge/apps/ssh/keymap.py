"""Map badge keyboard events to bytes for SSH."""

from hardware.keyboard import Keyboard


def key_to_bytes(key, keyboard: Keyboard):
  if key is None:
    return None
  if key == keyboard.ENTER:
    return b"\n"
  if key == keyboard.BS:
    return b"\x7f"
  if key == keyboard.DEL:
    return b"\x7f"
  if key == keyboard.TAB:
    return b"\t"
  if key == keyboard.UP:
    return b"\x1b[A"
  if key == keyboard.DOWN:
    return b"\x1b[B"
  if key == keyboard.RIGHT:
    return b"\x1b[C"
  if key == keyboard.LEFT:
    return b"\x1b[D"
  if len(key) == 1 and keyboard.control_pressed:
    c = ord(key)
    if 97 <= c <= 122:
      return bytes([c - 96])
    if 65 <= c <= 90:
      return bytes([c - 64])
    if key == " ":
      return b"\x00"
  if len(key) == 1 and not key.startswith("`"):
    return key.encode()
  return None
