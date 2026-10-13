#!/bin/sh
# Generated immutable launcher; installation and configuration are separate.
set -eu
GW_PYTHON=@@PYTHON@@
GW_DATA=@@DATA@@
GW_UV=@@UV@@
export GW_UV
@@BUILD_ENV@@
if [ -n "${GRAVEWRIGHT_BUILD_TOOLS_PATH:-}" ]; then
    PATH="$GRAVEWRIGHT_BUILD_TOOLS_PATH:${PATH:-/usr/bin:/bin:/usr/sbin:/sbin}"
    export PATH
fi
unset VIRTUAL_ENV PYTHONHOME PYTHONPATH
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
if [ ! -x "$GW_PYTHON" ] || [ ! -f @@BOOTSTRAP@@ ]; then
    printf '%s\n' 'Installation is missing. Run the Gravewright installer first.' >&2
    exit 1
fi
cd @@PROJECT@@
exec "$GW_PYTHON" -X utf8 @@BOOTSTRAP@@ --project @@PROJECT@@ --data-dir "$GW_DATA" @@DEFAULT_ARGS@@ "$@"
