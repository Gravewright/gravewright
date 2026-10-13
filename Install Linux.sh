#!/bin/bash
# Run from any working directory; paths and arguments remain separate values.
set -e
GW_ENTRY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
export GW_INSTALL_EXPECT_OS=Linux
exec /bin/bash "$GW_ENTRY_ROOT/scripts/posix/install.sh" "$@"
