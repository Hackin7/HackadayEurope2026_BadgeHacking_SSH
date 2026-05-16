"""SSH client app for Hackaday Communicator Badge."""

import gc
from collections import deque

import lvgl

from apps.base_app import BaseApp
from apps.ssh import backend, identity, states, worker
from apps.ssh.errors import format_error, format_wifi_error
from apps.ssh.keymap import key_to_bytes
from apps.ssh.terminal import TerminalView
from hardware.wifi import wifi
from ui.page import Page


def _cfg_str(badge, key: str, default: str = "") -> str:
  raw = badge.config.get(key, default.encode() if default else b"")
  if raw is None:
    return default
  if isinstance(raw, bytes):
    return raw.decode()
  return str(raw)


class SSHClientApp(BaseApp):
  def __init__(self, name: str, badge):
    super().__init__(name, badge)
    self.foreground_sleep_ms = 15
    self.background_sleep_ms = 500
    self.state = states.MENU
    self.page = None
    self.term_label = None
    self.terminal = TerminalView()
    self.host = ""
    self.port = 22
    self.user = ""
    self.password = ""
    self._edit_field = 0
    self._edit_active = False
    self._pending_fp = ""
    self._error_msg = ""
    self._connect_steps = []
    self._wifi_pending = False
    self._ssh_worker_started = False
    self.tx_queue: deque = deque([], 64)
    self.rx_queue: deque = deque([], 32)
    self.event_queue: deque = deque([], 16)
    self.session_handle = None
    self._connect_kwargs = {}
    self._connect_note = ""
    self._load_config()

  def _load_config(self):
    self.host = _cfg_str(self.badge, "ssh_host")
    self.port = int(_cfg_str(self.badge, "ssh_port", "22") or "22")
    self.user = _cfg_str(self.badge, "ssh_user")
    if "@" in self.host and not self.user:
      self.user, _, self.host = self.host.partition("@")
    _, self.host, self.port = backend.parse_host_port(self.host, self.port)
    self.wifi_ssid = _cfg_str(self.badge, "wifi_ssid")
    self.wifi_password = _cfg_str(self.badge, "wifi_password")
    self.ssh_auth = identity.normalize_auth(_cfg_str(self.badge, "ssh_auth", "password"))
    self.ssh_key_path = _cfg_str(self.badge, "ssh_key_path", identity.DEFAULT_KEY_PATH)
    self.ssh_key_passphrase = _cfg_str(self.badge, "ssh_key_passphrase")
    self.password = _cfg_str(self.badge, "ssh_password")

  def _save_ssh_config(self):
    self.badge.config.set("ssh_host", self.host.encode())
    self.badge.config.set("ssh_port", str(self.port).encode())
    self.badge.config.set("ssh_user", self.user.encode())
    self.badge.config.set("ssh_password", self.password.encode())
    self.badge.config.set("ssh_auth", self.ssh_auth.encode())
    self.badge.config.set("ssh_key_path", self.ssh_key_path.encode())
    self.badge.config.set("ssh_key_passphrase", self.ssh_key_passphrase.encode())
    self.badge.config.flush()

  def _auth_label(self) -> str:
    return "pubkey" if self.ssh_auth == identity.AUTH_PUBKEY else "password"

  def _f4_auth_switch_label(self) -> str:
    """Menubar F4: label the auth mode you switch to when pressed."""
    return "Key" if self.ssh_auth == identity.AUTH_PASSWORD else "Pass"

  def _prepare_connect(self):
    kw, note = identity.resolve_connect_kwargs(
      self.ssh_auth,
      self.password,
      self.ssh_key_path,
      self.ssh_key_passphrase,
      backend.has_native_ssh(),
    )
    if not kw:
      return None, note or "auth failed"
    self._connect_note = note or ""
    return kw, None

  def _save_wifi_config(self):
    self.badge.config.set("wifi_ssid", self.wifi_ssid.encode())
    self.badge.config.set("wifi_password", self.wifi_password.encode())
    self.badge.config.flush()

  def _stop_worker(self):
    wifi.cancel_connect()
    worker.stop_session(self.session_handle)
    self.session_handle = None
    self._wifi_pending = False
    self._ssh_worker_started = False

  def _menu_text(self) -> str:
    native = "Y" if backend.has_native_ssh() else "N"
    pty = "Y" if backend.Session.available() else "N"
    key_hint = self.ssh_key_path.split("/")[-1] if self.ssh_key_path else "?"
    lines = [
      f"Host: {self.host or '?'}",
      f"Port: {self.port}  User: {self.user or '?'}",
      f"Auth: {self._auth_label()}  Key: {key_hint}",
      f"WiFi: {self.wifi_ssid or 'not set'}",
      f"ssh:{native} pty:{pty}",
    ]
    if self._error_msg:
      lines.append(self._error_msg[:40])
    return "\n".join(lines)

  def _build_menu_screen(self):
    self.page = Page()
    f4 = self._f4_auth_switch_label()
    self.page.create_infobar(("SSH", f"F1 Conn  F4→{f4}"))
    self.page.create_content()
    self.term_label = lvgl.label(self.page.content)
    self.term_label.set_width(lvgl.pct(100))
    self.term_label.set_style_text_font(lvgl.font_montserrat_16, 0)
    self.term_label.set_text(self._menu_text())
    self.page.create_menubar(["Conn", "WiFi", "Edit", f4, "Home"])
    self.page.replace_screen()

  def _build_terminal_screen(self, title: str, footer: str):
    self.page = Page()
    self.page.create_infobar((title, footer))
    self.page.create_content()
    self.term_label = lvgl.label(self.page.content)
    self.term_label.set_width(lvgl.pct(100))
    self.term_label.set_style_text_font(lvgl.font_montserrat_16, 0)
    self.terminal.clear()
    self._refresh_terminal()
    self.page.create_menubar(["", "", "", "", "Disc"])
    self.page.replace_screen()

  def _refresh_terminal(self):
    if self.term_label:
      self.term_label.set_text(self.terminal.as_text())

  def _connect_progress_text(self) -> str:
    lines = [f"{self.user}@{self.host}:{self.port}"]
    if self._connect_steps:
      lines.extend(self._connect_steps[-5:])
    else:
      lines.append("Starting...")
    return "\n".join(lines)

  def _push_connect_step(self, message: str):
    if self._connect_steps and self._connect_steps[-1] == message:
      return
    self._connect_steps.append(message)
    if len(self._connect_steps) > 8:
      self._connect_steps = self._connect_steps[-8:]

  def _update_connecting_label(self):
    if self.term_label and self.state == states.CONNECTING:
      self.term_label.set_text(self._connect_progress_text())

  def _build_connecting_screen(self, footer: str = "F5 cancel"):
    self.page = Page()
    self.page.create_infobar(("Connecting", footer))
    self.page.create_content()
    self.term_label = lvgl.label(self.page.content)
    self.term_label.set_width(lvgl.pct(100))
    self.term_label.set_style_text_font(lvgl.font_montserrat_16, 0)
    self.term_label.set_text(self._connect_progress_text())
    self.page.create_menubar(["", "", "", "", "Cancel"])
    self.page.replace_screen()

  def _build_error_screen(self):
    msg = format_error(self._error_msg)
    self.page = Page()
    self.page.create_infobar(("Connection failed", "F5 back"))
    self.page.create_content()
    self.term_label = lvgl.label(self.page.content)
    self.term_label.set_width(lvgl.pct(100))
    self.term_label.set_style_text_font(lvgl.font_montserrat_16, 0)
    body = f"{msg}\n\n{self.host}:{self.port}"
    self.term_label.set_text(body[:200])
    self.page.create_menubar(["", "", "", "", "Back"])
    self.page.replace_screen()

  def _show_error(self, message: str):
    self._error_msg = message
    self.state = states.ERROR
    self._stop_worker()
    self._build_error_screen()

  def _process_events(self):
    while self.event_queue:
      kind, payload = self.event_queue.popleft()
      if kind == "wifi":
        self._push_connect_step("WiFi linked")
        self._update_connecting_label()
      elif kind == "progress":
        self._push_connect_step(str(payload))
        self._update_connecting_label()
      elif kind == "fingerprint":
        self._pending_fp = str(payload)
        if self.state == states.CONNECTING:
          self.state = states.VERIFY
          self._build_verify_screen()
      elif kind == "session":
        self.state = states.SESSION
        self._build_terminal_screen("SSH", "F5 disconnect")
      elif kind == "banner":
        self.state = states.SESSION
        self._build_terminal_screen("TCP", "banner only")
        while self.rx_queue:
          self.terminal.feed(self.rx_queue.popleft())
        self._refresh_terminal()
      elif kind == "exec":
        self.state = states.EXEC
        self.terminal.clear()
        try:
          out = payload[2] if payload and len(payload) > 2 else b""
          if isinstance(out, bytes):
            self.terminal.feed(out)
          else:
            self.terminal.feed(str(out).encode())
        except Exception:
          self.terminal.feed(b"(exec result)")
        self._build_terminal_screen("SSH exec", "F5 home")
        self._refresh_terminal()
      elif kind == "error":
        self._show_error(str(payload))
      elif kind == "done":
        self._stop_worker()
        if self.state == states.SESSION:
          self.state = states.MENU
          self._build_menu_screen()

  def _start_connect(self):
    if not self.host or not self.user:
      self._show_error("host/user required")
      return
    if not self.wifi_ssid:
      self._show_error("set WiFi first")
      return
    kw, err = self._prepare_connect()
    if err:
      self._show_error(err)
      return
    self._connect_kwargs = kw
    self._error_msg = ""
    self._connect_steps = []
    self._stop_worker()
    # MicroPython deque has no .clear(); new instances after worker stop.
    self.tx_queue = deque([], 64)
    self.rx_queue = deque([], 32)
    self.event_queue = deque([], 16)
    self.state = states.CONNECTING
    self._wifi_pending = True
    self._ssh_worker_started = False
    self._push_connect_step("WiFi: connecting...")
    if self._connect_note:
      self._push_connect_step(self._connect_note)
    self._build_connecting_screen()
    wifi.begin_connect(self.wifi_ssid, self.wifi_password)

  def _start_ssh_worker(self):
    if self._ssh_worker_started:
      return
    self._ssh_worker_started = True
    use_pty = backend.Session.available()
    self.session_handle = worker.start_session(
      self.host,
      self.port,
      self.user,
      self._connect_kwargs,
      self.wifi_ssid,
      self.wifi_password,
      self.tx_queue,
      self.rx_queue,
      self.event_queue,
      use_pty=use_pty,
      skip_wifi=True,
    )
    if self.session_handle is None:
      self._show_error("no _thread")

  def _poll_wifi(self):
    phase, detail = wifi.poll_connect()
    if phase == "running":
      return
    self._wifi_pending = False
    if phase == "ok":
      st = wifi.status()
      self._push_connect_step(f"WiFi OK {st.get('ip', '')}")
      self._update_connecting_label()
      self._start_ssh_worker()
      return
    err = detail or wifi.status().get("error", "")
    self._show_error(format_wifi_error({"error": err}))

  def _build_verify_screen(self):
    self.page = Page()
    self.page.create_infobar(("Trust host?", self._pending_fp[:24]))
    self.page.create_content()
    self.term_label = lvgl.label(self.page.content)
    self.term_label.set_text(
      f"{self.host}:{self.port}\nSHA256:\n{self._pending_fp}\nF1 trust F5 cancel"
    )
    self.page.create_menubar(["Trust", "", "", "", "Cancel"])
    self.page.replace_screen()

  def switch_to_foreground(self):
    super().switch_to_foreground()
    self._load_config()
    self.state = states.MENU
    self._build_menu_screen()

  def switch_to_background(self):
    self._stop_worker()
    self._save_ssh_config()
    self.page = None
    self.term_label = None
    gc.collect()
    super().switch_to_background()

  def run_foreground(self):
    self._process_events()

    if self.badge.keyboard.f5():
      if self.state in (states.SESSION, states.EXEC, states.VERIFY, states.CONNECTING):
        self._stop_worker()
        self.state = states.MENU
        self._build_menu_screen()
        return
      if self.state == states.ERROR:
        self.state = states.MENU
        self._build_menu_screen()
        return
      self.switch_to_background()
      return

    if self.state == states.MENU:
      if self.badge.keyboard.f1():
        self._save_ssh_config()
        self._start_connect()
      elif self.badge.keyboard.f2():
        self.state = states.WIFI
        self._wifi_edit_start()
      elif self.badge.keyboard.f3():
        self.state = states.EDIT
        self._edit_field = 0
        self._field_edit_start()
      elif self.badge.keyboard.f4():
        if self.ssh_auth == identity.AUTH_PUBKEY:
          self.ssh_auth = identity.AUTH_PASSWORD
        else:
          self.ssh_auth = identity.AUTH_PUBKEY
        self._save_ssh_config()
        self._build_menu_screen()

    elif self.state == states.WIFI:
      self._wifi_edit_run()

    elif self.state == states.EDIT:
      self._field_edit_run()

    elif self.state == states.VERIFY:
      if self.badge.keyboard.f1() and self.session_handle:
        self.session_handle.trusted = True
        self.state = states.CONNECTING
        self._push_connect_step("Host trusted, resuming...")
        self._build_connecting_screen("auth...")
      if self.badge.keyboard.f5():
        self._stop_worker()
        self.state = states.MENU
        self._build_menu_screen()

    elif self.state in (states.SESSION, states.EXEC):
      while self.rx_queue:
        self.terminal.feed(self.rx_queue.popleft())
      key = self.badge.keyboard.read_key()
      data = key_to_bytes(key, self.badge.keyboard)
      if data and self.session_handle:
        if self.state == states.SESSION:
          self.terminal.note_tx(data)
        self.tx_queue.append(data)
      self._refresh_terminal()

    elif self.state == states.CONNECTING:
      if self._wifi_pending:
        self._poll_wifi()

    elif self.state == states.ERROR:
      pass

  def _wifi_edit_start(self):
    self.page = Page()
    self.page.create_infobar(("WiFi SSID", "F1 next F5 save home"))
    self.page.create_content()
    self.page.create_text_box(self.wifi_ssid, one_line=True, char_limit=32)
    self._edit_active = True
    self._wifi_step = 0
    self.page.create_menubar(["Next", "", "", "", "Save"])
    self.page.replace_screen()

  def _wifi_edit_run(self):
    if not self._edit_active:
      return
    self.page.text_box_type(self.badge.keyboard)
    if self.badge.keyboard.escape_pressed:
      self.page.close_text_box()
      self._edit_active = False
      self.state = states.MENU
      self._build_menu_screen()
    elif self.badge.keyboard.f1() or self.badge.keyboard.f4():
      text = self.page.close_text_box()
      if self._wifi_step == 0:
        self.wifi_ssid = text
        self.page.create_text_box("", one_line=True, char_limit=64)
        self._wifi_step = 1
        self.page.infobar_left.set_text("WiFi password")
      else:
        self.wifi_password = text
        self._edit_active = False
        self._save_wifi_config()
        self.state = states.MENU
        self._build_menu_screen()
    elif self.badge.keyboard.f5():
      text = self.page.close_text_box()
      if self._wifi_step == 0:
        self.wifi_ssid = text
      else:
        self.wifi_password = text
      self._save_wifi_config()
      self._edit_active = False
      self.state = states.MENU
      self._build_menu_screen()

  def _field_edit_start(self):
    self._field_labels = ["Host", "Port", "User", "Password", "Key path"]
    self._field_edit_start_one()

  def _field_edit_start_one(self):
    defaults = [
      self.host,
      str(self.port),
      self.user,
      self.password,
      self.ssh_key_path,
    ]
    label = self._field_labels[self._edit_field]
    self.page = Page()
    self.page.create_infobar((label, "F1 next F5 done"))
    self.page.create_content()
    masked = label == "Password"
    self.page.create_text_box(
      defaults[self._edit_field],
      one_line=True,
      char_limit=48 if not masked else 32,
    )
    self._edit_active = True
    self.page.create_menubar(["Next", "", "", "", "Done"])
    self.page.replace_screen()

  def _field_edit_run(self):
    if not self._edit_active:
      return
    self.page.text_box_type(self.badge.keyboard)
    if self.badge.keyboard.escape_pressed:
      self.page.close_text_box()
      self._edit_active = False
      self.state = states.MENU
      self._build_menu_screen()
    elif self.badge.keyboard.f1():
      self._apply_field(self.page.close_text_box())
      self._edit_field = (self._edit_field + 1) % 5
      if self._edit_field == 0:
        self._save_ssh_config()
        self._edit_active = False
        self.state = states.MENU
        self._build_menu_screen()
      else:
        self._field_edit_start_one()
    elif self.badge.keyboard.f5():
      self._apply_field(self.page.close_text_box())
      self._save_ssh_config()
      self._edit_active = False
      self.state = states.MENU
      self._build_menu_screen()

  def _apply_field(self, text: str):
    if self._edit_field == 0:
      self.host = text
    elif self._edit_field == 1:
      try:
        self.port = int(text)
      except ValueError:
        self.port = 22
    elif self._edit_field == 2:
      self.user = text
    elif self._edit_field == 3:
      self.password = text
    else:
      self.ssh_key_path = text or identity.DEFAULT_KEY_PATH
