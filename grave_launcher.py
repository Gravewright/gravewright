"""PyInstaller entry point for the Gravewright `grave` CLI.

Kept at the project root so the `app` package resolves cleanly when frozen.
"""

from __future__ import annotations

from app.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
