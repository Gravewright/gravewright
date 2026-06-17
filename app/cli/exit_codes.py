"""Stable process exit codes for the ``grave`` CLI.

These are part of the CLI contract — CI pipelines, scripts and AI tooling depend
on them, so do not renumber. ``argparse`` already exits ``2`` on bad usage.
"""

from __future__ import annotations

EXIT_OK = 0
EXIT_DOCTOR_ERROR = 1  # doctor (or a doctor-backed command) found a problem
EXIT_USAGE = 2  # invalid CLI usage (argparse default)
EXIT_UNSAFE = 3  # refused a destructive/unsafe operation without --yes
EXIT_MISSING_DEPENDENCY = 4  # a required external dependency is absent
EXIT_INCOMPATIBLE = 5  # package incompatibility
