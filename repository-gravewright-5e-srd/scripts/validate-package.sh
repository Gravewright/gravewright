#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: scripts/validate-package.sh /path/to/gravewright"
  exit 2
fi

GRAVEWRIGHT_ROOT="$1"
PACKAGE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$GRAVEWRIGHT_ROOT/data/packages/rulesets/dnd5e"

mkdir -p "$(dirname "$TARGET")"
rm -rf "$TARGET"
cp -R "$PACKAGE_ROOT" "$TARGET"

cd "$GRAVEWRIGHT_ROOT"
uv run python -m app.cli package validate data/packages/rulesets/dnd5e
uv run python -m app.cli package install dnd5e --enable
uv run python -m app.cli package update dnd5e --json
uv run python -m app.cli doctor --strict --json
