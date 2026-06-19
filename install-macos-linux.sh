#!/usr/bin/env bash
# ===========================================================================
#  Gravewright - one-click setup and launch for macOS and Linux.
#
#  It installs everything it needs the first time (no admin/sudo required),
#  then starts Gravewright and opens your browser. Run it again any time to
#  start playing again.
#
#  How to run:
#    - Open the Terminal in this folder and run:  bash install-macos-linux.sh
#    - Or make it executable once:  chmod +x install-macos-linux.sh
#      then run it with:  ./install-macos-linux.sh
# ===========================================================================
set -euo pipefail

# Always work from the folder this script lives in (the project root).
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo
echo "==========================================================="
echo "  Gravewright - setup and launch (macOS / Linux)"
echo "==========================================================="
echo

# --- 1) Make sure uv (the installer/runtime manager) is available ----------
if ! command -v uv >/dev/null 2>&1; then
  echo "[1/5] Installing uv (one-time)..."
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://astral.sh/uv/install.sh | sh
  else
    echo
    echo "ERROR  Neither curl nor wget is available to download uv."
    echo "       Install uv from https://docs.astral.sh/uv/ and run this again."
    exit 1
  fi
  # uv installs for the current user; make it usable in this same session.
  [ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env" || true
  export PATH="$HOME/.local/bin:$PATH"
else
  echo "[1/5] uv is already installed."
fi

if ! command -v uv >/dev/null 2>&1; then
  echo
  echo "ERROR  uv could not be installed automatically."
  echo "       Close this window, open a new terminal, and run this again."
  exit 1
fi

# --- 2) Install the matching Python + all dependencies ---------------------
echo "[2/5] Installing Gravewright and its dependencies (first run can take a few minutes)..."
uv sync --frozen

# --- 3) and 4) Create local configuration + a unique session secret --------
echo "[3/5] Preparing local configuration..."
uv run python scripts/setup_local_env.py

# --- 5) Quick health check (non-fatal), then start the server --------------
echo "[4/5] Checking the installation..."
uv run python -m app.cli doctor || true

echo
echo "[5/5] Starting Gravewright."
echo "       Your browser will open at http://127.0.0.1:8000"
echo "       Keep this window open while you play. Press Ctrl+C to stop."
echo
exec uv run python -m app.cli run --open
