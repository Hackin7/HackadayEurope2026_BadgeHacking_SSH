#!/bin/bash
set -e
WIN_KEY="/mnt/c/Users/zunmun/AppData/Local/Temp/badge_rsa_from_badge"
KEY="/tmp/badge_rsa_from_badge"
PUB="/tmp/badge_rsa_from_badge.pub"
tr -d '\r' < "$WIN_KEY" > "$KEY"
chmod 600 "$KEY"
echo "=== key head ==="
head -1 "$KEY"
echo "size $(wc -c < "$KEY")"
echo "=== public key (add to server authorized_keys if missing) ==="
ssh-keygen -y -f "$KEY" | tee "$PUB"
echo "=== ssh test with badge RSA key ==="
ssh -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=no -i "$KEY" zunmun@34.28.97.3 "echo wsl-rsa-ok"
