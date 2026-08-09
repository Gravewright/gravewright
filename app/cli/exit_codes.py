"""Stable process exit codes for the ``grave`` CLI.

These are part of the CLI contract — CI pipelines, scripts and AI tooling depend
on them, so do not renumber. ``argparse`` already exits ``2`` on bad usage.
"""

from __future__ import annotations

EXIT_OK = 0
EXIT_DOCTOR_ERROR = 1
EXIT_USAGE = 2
EXIT_UNSAFE = 3
EXIT_MISSING_DEPENDENCY = 4
EXIT_INCOMPATIBLE = 5
