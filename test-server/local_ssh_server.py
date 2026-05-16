#!/usr/bin/env python3
"""Minimal Paramiko SSH server for badge password-auth testing.

Defaults: user badge / password badge, port 2222, bind 0.0.0.0
"""

import socket
import sys
import threading
from pathlib import Path

import paramiko
from paramiko.common import (
    AUTH_FAILED,
    AUTH_SUCCESSFUL,
    OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED,
    OPEN_SUCCEEDED,
)

HOST = "0.0.0.0"
PORT = 2222
USERNAME = "badge"
PASSWORD = "badge"
KEY_PATH = Path(__file__).resolve().parent / "test_host_key"


class BadgeSSHServer(paramiko.ServerInterface):
    def check_auth_password(self, username, password):
        ok = username == USERNAME and password == PASSWORD
        print(f"auth password user={username!r} ok={ok}")
        return AUTH_SUCCESSFUL if ok else AUTH_FAILED

    def check_auth_publickey(self, username, key):
        print(f"auth pubkey user={username!r} rejected")
        return AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        if kind in ("session", "exec"):
            return OPEN_SUCCEEDED
        return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

    def check_channel_shell_request(self, channel):
        return True

    def get_allowed_auths(self, username):
        return "password"


def _handle_client(client: socket.socket, addr):
    print(f"connection from {addr}")
    try:
        client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        transport = paramiko.Transport(client)

        if not KEY_PATH.is_file():
            print(f"Missing {KEY_PATH} — run: python generate_host_key.py", file=sys.stderr)
            return

        host_key = paramiko.RSAKey(filename=str(KEY_PATH))
        transport.add_server_key(host_key)
        transport.start_server(server=BadgeSSHServer())

        channel = transport.accept(20)
        if channel is None:
            print("no channel")
            return

        # Client (badge) sends pty-req + shell; ServerInterface approves them.
        channel.send("badge-ssh-test shell ready\r\n")

        while transport.is_active():
            if channel.recv_ready():
                data = channel.recv(1024)
                if not data:
                    break
                if data.strip():
                    print(f"recv: {data!r}")
                # Instant per-character echo (same bytes as received).
                channel.send(data)
            if channel.closed:
                break
    except Exception as exc:
        print(f"client error: {exc}")
    finally:
        try:
            client.close()
        except OSError:
            pass
        print(f"closed {addr}")


def main():
    if not KEY_PATH.is_file():
        print("Run: python generate_host_key.py")
        sys.exit(1)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(32)
    print(f"SSH test server on {HOST}:{PORT}  user={USERNAME!r}  password={PASSWORD!r}")
    print(f"Host key: {KEY_PATH}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            client, addr = sock.accept()
            threading.Thread(target=_handle_client, args=(client, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
