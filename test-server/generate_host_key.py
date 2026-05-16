"""Generate RSA host key for local_ssh_server.py (run once)."""

from pathlib import Path

import paramiko

KEY_PATH = Path(__file__).resolve().parent / "test_host_key"


def main():
    key = paramiko.RSAKey.generate(2048)
    key.write_private_key_file(str(KEY_PATH))
    print("Wrote", KEY_PATH)


if __name__ == "__main__":
    main()
