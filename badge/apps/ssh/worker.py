"""SSH session worker thread."""

import gc
import time

try:
  import _thread
except ImportError:
  _thread = None

from apps.ssh import backend, identity, known_hosts
from apps.ssh.errors import format_wifi_error
from apps.ssh.terminal import COLS, ROWS
from hardware.wifi import wifi


class SessionHandle:
  def __init__(self):
    self.running = False
    self.stop_flag = False
    self.trusted = False


def _progress(event_queue, message: str):
  event_queue.append(("progress", message))


def _wait_trust(handle, host, port, fp, event_queue, timeout_ms=120000):
  if not fp or known_hosts.verify(host, port, fp):
    handle.trusted = True
    return True
  _progress(event_queue, "Waiting: trust host (F1)")
  start = time.ticks_ms()
  while handle.running and not handle.stop_flag:
    if handle.trusted:
      known_hosts.trust(host, port, fp)
      return True
    if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
      return False
    time.sleep_ms(100)
  return False


def _pty_session_loop(session, handle, tx_queue, rx_queue):
  """Interactive shell I/O.

  libssh2 read() blocks in blocking mode and would stall TX if done in one loop.
  Use a dedicated read thread so the main loop can always drain tx_queue.
  """

  def read_loop():
    try:
      while handle.running and not handle.stop_flag:
        data = session.read(256)
        if data:
          rx_queue.append(data)
        time.sleep_ms(1)
    except OSError:
      pass

  if _thread:
    _thread.start_new_thread(read_loop, ())
  else:
    read_loop()

  while handle.running and not handle.stop_flag:
    while tx_queue:
      session.write(tx_queue.popleft())
    time.sleep_ms(20)


def _worker(
  host,
  port,
  user,
  connect_kwargs,
  wifi_ssid,
  wifi_password,
  tx_queue,
  rx_queue,
  event_queue,
  handle,
  use_pty,
  skip_wifi=False,
):
  password = connect_kwargs.get("password", "")
  private_key = connect_kwargs.get("private_key")
  key_passphrase = connect_kwargs.get("key_passphrase", "")
  try:
    if not skip_wifi:
      _progress(event_queue, "WiFi: connecting...")
      if not wifi.connect(wifi_ssid, wifi_password):
        st = wifi.status()
        event_queue.append(("error", format_wifi_error(st)))
        return
    if not wifi.is_connected():
      event_queue.append(("error", format_wifi_error(wifi.status())))
      return
    st = wifi.status()
    ip = st.get("ip", "")
    _progress(event_queue, f"WiFi OK {ip}")

    if use_pty and backend.Session.available():
      _progress(event_queue, f"SSH: {host}:{port}")
      if private_key:
        _progress(event_queue, "SSH: pubkey auth...")
      session = backend.Session()
      _progress(event_queue, "SSH: handshake...")
      err = session.connect(
        host,
        port,
        user,
        password=password,
        private_key=private_key,
        key_passphrase=key_passphrase,
      )
      if err != 0:
        event_queue.append(("error", f"connect {err}"))
        session.close()
        return
      _progress(event_queue, "SSH: authenticated")
      fp = session.fingerprint()
      if fp:
        event_queue.append(("fingerprint", fp))
        _progress(event_queue, "SSH: check host key")
      if not _wait_trust(handle, host, port, fp, event_queue):
        event_queue.append(("error", "host key denied"))
        session.close()
        return
      _progress(event_queue, "SSH: opening shell...")
      session.open_shell(COLS, ROWS)
      event_queue.append(("session", "pty"))
      _progress(event_queue, "Connected")
      _pty_session_loop(session, handle, tx_queue, rx_queue)
      session.close()
      event_queue.append(("done", None))
      return

    _progress(event_queue, f"TCP: {host}:{port}")
    if backend.has_native_ssh():
      if private_key and not password:
        _progress(event_queue, "SSH: pubkey exec...")
      _progress(event_queue, "SSH: running command...")
      res = backend.exec_command(
        host,
        port,
        user,
        password,
        "uname -a",
        private_key=private_key,
        key_passphrase=key_passphrase,
      )
      code = res[0] if res else -1
      if code != 0:
        event_queue.append(("error", f"exec failed ({code})"))
        return
      event_queue.append(("exec", res))
      _progress(event_queue, "Command done")
    else:
      _progress(event_queue, "TCP: waiting for banner...")
      try:
        banner = backend.tcp_banner(host, port)
        rx_queue.append(banner)
        event_queue.append(("banner", None))
        _progress(event_queue, "Banner received")
      except OSError as e:
        event_queue.append(("error", str(e)))
  except OSError as e:
    event_queue.append(("error", str(e)))
  except Exception as e:
    event_queue.append(("error", str(e)))
  finally:
    handle.running = False
    gc.collect()


def start_session(
  host,
  port,
  user,
  connect_kwargs,
  wifi_ssid,
  wifi_password,
  tx_queue,
  rx_queue,
  event_queue,
  use_pty=True,
  skip_wifi=False,
):
  if _thread is None:
    event_queue.append(("error", "no _thread"))
    return None
  handle = SessionHandle()
  handle.running = True
  handle.stop_flag = False
  handle.trusted = False

  def run():
    _worker(
      host,
      port,
      user,
      connect_kwargs,
      wifi_ssid,
      wifi_password,
      tx_queue,
      rx_queue,
      event_queue,
      handle,
      use_pty,
      skip_wifi,
    )

  _thread.start_new_thread(run, ())
  return handle


def stop_session(handle):
  if handle is None:
    return
  handle.stop_flag = True
  handle.running = False
