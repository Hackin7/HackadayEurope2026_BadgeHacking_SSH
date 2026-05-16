#!/usr/bin/env bash
# Configure OpenSSH in WSL for badge/local testing (port 2222, user badge).
# Run as root: sudo bash setup-wsl-openssh.sh

set -euo pipefail

SSH_PORT="${SSH_PORT:-2222}"
BADGE_USER="${BADGE_USER:-badge}"
BADGE_PASS="${BADGE_PASS:-badge}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
if ! dpkg -s openssh-server &>/dev/null; then
  apt-get update -qq
  apt-get install -y -qq openssh-server
fi

if ! id -u "${BADGE_USER}" &>/dev/null; then
  useradd -m -s /bin/bash "${BADGE_USER}"
  echo "${BADGE_USER}:${BADGE_PASS}" | chpasswd
  echo "Created user ${BADGE_USER}"
else
  echo "${BADGE_USER}:${BADGE_PASS}" | chpasswd
  echo "Updated password for ${BADGE_USER}"
fi

SSHD_CFG=/etc/ssh/sshd_config
for key in Port ListenAddress PasswordAuthentication PubkeyAuthentication; do
  sed -i "/^[#[:space:]]*${key}[[:space:]]/d" "${SSHD_CFG}"
done
{
  echo ""
  echo "# WSL badge test (setup-wsl-openssh.sh)"
  echo "Port ${SSH_PORT}"
  echo "ListenAddress 0.0.0.0"
  echo "ListenAddress ::"
  echo "PasswordAuthentication yes"
  echo "PubkeyAuthentication yes"
} >> "${SSHD_CFG}"

ssh-keygen -A

WSL_CONF=/etc/wsl.conf
if [[ ! -f "${WSL_CONF}" ]] || ! grep -q '^\[boot\]' "${WSL_CONF}"; then
  cat >> "${WSL_CONF}" <<'EOF'

[boot]
command=service ssh start
EOF
  echo "Appended [boot] to ${WSL_CONF} (restart WSL to apply auto-start)"
fi

service ssh restart || /usr/sbin/sshd
sleep 1

if ss -tlnp | grep -q ":${SSH_PORT} "; then
  echo "OpenSSH listening on port ${SSH_PORT}"
else
  echo "ERROR: sshd not listening on ${SSH_PORT}" >&2
  exit 1
fi

echo "Test from WSL: ssh -p ${SSH_PORT} ${BADGE_USER}@127.0.0.1"
echo "From LAN: use Windows WiFi IP and port ${SSH_PORT} after running setup-wsl-ssh.ps1"
