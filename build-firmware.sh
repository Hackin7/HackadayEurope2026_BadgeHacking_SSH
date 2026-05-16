#!/usr/bin/env bash
# Build Hackaday badge MicroPython + LVGL + ucryptography + ssh (WSL/Linux only).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FIRMWARE_DIR="$(cd "$SCRIPT_DIR/../../2025-Communicator_Badge/firmware" && pwd)"
# Build on Linux FS — /mnt/c often breaks git submodules
BUILD_ROOT="${BUILD_ROOT:-/tmp/badge_ssh_build}"
LVGL_DIR="$BUILD_ROOT/lvgl_micropython"
UCRYPTO_SRC="$FIRMWARE_DIR/ucryptography"
SSH_SRC="$SCRIPT_DIR/micropython-ssh"
VENDOR_SRC="$SCRIPT_DIR/vendor/libssh2_esp32"
PATCH="${PATCH:-$SCRIPT_DIR/patches/inline_thumb_patch}"
OUT_BIN="$SCRIPT_DIR/build/lvgl_micropy_ESP32_GENERIC_S3-SPIRAM_OCT-16-ssh.bin"
mkdir -p "$BUILD_ROOT" "$(dirname "$OUT_BIN")" "$SCRIPT_DIR/patches"

# USER_C_MODULE paths on /mnt/c can break cmake; mirror to Linux FS when needed.
mirror_to_build() {
  local name="$1" src="$2"
  local dest="$BUILD_ROOT/modules/$name"
  if [[ "$src" == /mnt/* ]]; then
    mkdir -p "$(dirname "$dest")"
    if [[ ! -d "$dest" ]] || [[ "$src" -nt "$dest" ]]; then
      echo "==> mirror $name -> $dest" >&2
      rm -rf "$dest"
      cp -a "$src" "$dest"
    fi
    printf '%s' "$dest"
  else
    printf '%s' "$src"
  fi
}

echo "==> firmware dir: $FIRMWARE_DIR"

if [[ ! -d "$LVGL_DIR" ]]; then
  echo "==> clone lvgl_micropython"
  git clone --depth 1 https://github.com/lvgl-micropython/lvgl_micropython "$LVGL_DIR"
fi

if [[ ! -d "$UCRYPTO_SRC" ]]; then
  echo "==> clone ucryptography"
  git clone --depth 1 https://github.com/dmazzella/ucryptography.git "$UCRYPTO_SRC"
  (cd "$UCRYPTO_SRC" && git submodule update --init --depth 1)
fi

if [[ ! -d "$VENDOR_SRC" ]]; then
  echo "==> clone libssh2_esp32"
  git clone --depth 1 https://github.com/playmiel/libssh2_esp32.git "$VENDOR_SRC"
fi

UCRYPTO_DIR="$(mirror_to_build ucryptography "$UCRYPTO_SRC")"
SSH_DIR="$(mirror_to_build micropython-ssh "$SSH_SRC")"
mirror_to_build vendor/libssh2_esp32 "$VENDOR_SRC" >/dev/null
SSH_MOD="$SSH_DIR/micropython.cmake"

cd "$LVGL_DIR"

apply_thumb_patch() {
  if [[ ! -f "$PATCH" ]] || [[ ! -f lib/micropython/py/emitinlinethumb.c ]]; then
    return 0
  fi
  if grep -q nonstring lib/micropython/py/emitinlinethumb.c 2>/dev/null; then
    return 0
  fi
  echo "==> apply inline_thumb patch"
  local patch_copy="$BUILD_ROOT/inline_thumb_patch"
  cp "$PATCH" "$patch_copy"
  cp "$patch_copy" lib/micropython/
  (cd lib/micropython && patch -p1 --forward < inline_thumb_patch) || true
}

ensure_idf_python() {
  local idf_tools="$LVGL_DIR/lib/esp-idf/tools/idf_tools.py"
  [[ -f "$idf_tools" ]] || return 0
  if ! python3 "$idf_tools" check-python-env 2>/dev/null; then
    echo "==> install ESP-IDF Python packages"
    python3 "$idf_tools" install-python-env
  fi
}

# Montserrat fonts for badge
LV_CONF=lib/lv_conf.h
if [[ -f "$LV_CONF" ]]; then
  for sz in 28 42 48; do
    sed -i "s/#define LV_FONT_MONTSERRAT_${sz} .*/#define LV_FONT_MONTSERRAT_${sz} 1/" "$LV_CONF" 2>/dev/null || true
  done
fi

mkdir -p "$(dirname "$OUT_BIN")"

BUILD_ARGS=(
  esp32 BOARD=ESP32_GENERIC_S3 BOARD_VARIANT=SPIRAM_OCT
  --flash-size=16 DISPLAY=nv3007 --enable-uart-repl=y --enable-cdc-repl=n
  "USER_C_MODULE=$UCRYPTO_DIR/micropython.cmake"
  "USER_C_MODULE=$SSH_MOD"
)

apply_thumb_patch
ensure_idf_python

echo "==> build (first run may fail on GCC 15 — re-run script if needed)..."
if ! python3 make.py "${BUILD_ARGS[@]}"; then
  echo "==> build failed; applying thumb patch and retrying..."
  apply_thumb_patch
  python3 make.py "${BUILD_ARGS[@]}"
fi

if [[ ! -f build/lvgl_micropy_ESP32_GENERIC_S3-SPIRAM_OCT-16.bin ]]; then
  echo "==> ERROR: firmware binary not found" >&2
  exit 1
fi
cp build/lvgl_micropy_ESP32_GENERIC_S3-SPIRAM_OCT-16.bin "$OUT_BIN"
echo "==> OK: $OUT_BIN"
ls -la "$OUT_BIN"
