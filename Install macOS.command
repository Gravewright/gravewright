#!/bin/bash
# Finder opens .command files in Terminal. Homebrew is not required.
set -e
GW_ENTRY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
export GW_INSTALL_EXPECT_OS=Darwin
exec /bin/bash "$GW_ENTRY_ROOT/scripts/posix/install.sh" "$@"
