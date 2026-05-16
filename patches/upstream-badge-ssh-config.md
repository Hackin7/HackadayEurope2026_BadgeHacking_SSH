# Upstream patch: SSH config defaults in `hardware/badge.py`

Add inside `Badge.__init__` after WiFi defaults (if missing):

```python
        if "ssh_host" not in self.config.db.keys():
            self.config.set("ssh_host", b'')
        if "ssh_port" not in self.config.db.keys():
            self.config.set("ssh_port", b'22')
        if "ssh_user" not in self.config.db.keys():
            self.config.set("ssh_user", b'')
        if "ssh_auth" not in self.config.db.keys():
            self.config.set("ssh_auth", b'password')
        if "ssh_key_path" not in self.config.db.keys():
            self.config.set("ssh_key_path", b'/data/ssh_id_ed25519')
        if "ssh_key_passphrase" not in self.config.db.keys():
            self.config.set("ssh_key_passphrase", b'')
        if "ssh_password" not in self.config.db.keys():
            self.config.set("ssh_password", b'')
```

Without these keys, `Config().get("ssh_host")` still works if set from the SSH app, but first-run defaults are cleaner.
