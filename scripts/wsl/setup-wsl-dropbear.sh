#!/usr/bin/env bash
# Optional: Dropbear on port 22 (lighter than OpenSSH). Stop OpenSSH first to avoid confusion.
# Run as root: sudo bash setup-wsl-dropbear.sh

set -euo pipefail

DROPBEAR_PORT="${DROPBEAR_PORT:-22}"
BADGE_USER="${BADGE_USER:-badge}"
BADGE_PASS="${BADGE_PASS:-badge}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq dropbear

if ! id -u "${BADGE_USER}" &>/dev/null; then
  useradd -m -s /bin/bash "${BADGE_USER}"
fi
echo "${BADGE_USER}:${BADGE_PASS}" | chpasswd

service ssh stop 2>/dev/null || true

sed -i "s/^DROPBEAR_PORT=.*/DROPBEAR_PORT=${DROPBEAR_PORT}/" /etc/default/dropbear
sed -i "s|^DROPBEAR_EXTRA_ARGS=.*|DROPBEAR_EXTRA_ARGS=\"-s -j -k -p ${DROPBEAR_PORT}\"|" /etc/default/dropbear

service dropbear restart
sleep 1

if ss -tlnp | grep -q ":${DROPBEAR_PORT} "; then
  echo "Dropbear listening on port ${DROPBEAR_PORT}"
else
  echo "ERROR: dropbear not listening" >&2
  exit 1
fi

echo "Test: ssh -p ${DROPBEAR_PORT} ${BADGE_USER}@127.0.0.1"
