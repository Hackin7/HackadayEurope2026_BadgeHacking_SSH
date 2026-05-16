"""Trust-on-first-use host keys at /data/ssh_known_hosts."""

PATH = "/data/ssh_known_hosts"


def _line_key(host: str, port: int) -> str:
  return f"{host}:{port}"


def lookup(host: str, port: int) -> str | None:
  key = _line_key(host, port)
  try:
    with open(PATH, "r") as f:
      for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
          continue
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[0] == key:
          return parts[1]
  except OSError:
    pass
  return None


def trust(host: str, port: int, fingerprint: str) -> None:
  key = _line_key(host, port)
  fp = fingerprint.strip()
  lines = []
  try:
    with open(PATH, "r") as f:
      lines = f.readlines()
  except OSError:
    pass
  out = []
  found = False
  for line in lines:
    if line.startswith(key + " "):
      out.append(f"{key} {fp}\n")
      found = True
    else:
      out.append(line)
  if not found:
    out.append(f"{key} {fp}\n")
  with open(PATH, "w") as f:
    f.writelines(out)


def verify(host: str, port: int, fingerprint: str) -> bool:
  stored = lookup(host, port)
  if stored is None:
    return False
  return stored == fingerprint.strip()
