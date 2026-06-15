#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.local/bin"
TARGET="${TARGET_DIR}/grave"
mkdir -p "$TARGET_DIR"
ln -sf "${ROOT}/grave" "$TARGET"
chmod +x "${ROOT}/grave"
echo "OK     installed local launcher: ${TARGET}"
echo "       Make sure ${TARGET_DIR} is on your PATH."
