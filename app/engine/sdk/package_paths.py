"""Path safety helpers for Gravewright SDK packages.

Packages are untrusted content. Every relative path a manifest references — and
every path inside an uploaded archive — must be confined to the package
directory. These helpers are the single source of truth for "is this path
safe" so the loader, validator, asset server, and upload pipeline all agree.
"""

from __future__ import annotations

import re
from pathlib import Path

ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_WINDOWS_DRIVE = re.compile(r"^[a-zA-Z]:")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def package_id_is_safe(package_id: object) -> bool:
    """A package id must be lowercase kebab-case with no separators."""
    return isinstance(package_id, str) and bool(ID_PATTERN.match(package_id))


def path_is_safe(path: object) -> bool:
    """Reject anything that could escape the package directory.

    Rejects: empty/non-str, absolute paths, URLs, backslashes, Windows drive
    prefixes, ``.`` / ``..`` traversal, double slashes, trailing slash, colons,
    Windows reserved device names, and segments ending in a space or dot.
    """
    if not path or not isinstance(path, str):
        return False
    if "\\" in path or "://" in path:
        return False
    if path.startswith("/") or _WINDOWS_DRIVE.match(path):
        return False
    if path.endswith("/"):
        return False
    segments = path.split("/")
    for segment in segments:
        if segment in {".", ".."}:
            return False
        if ":" in segment:
            return False
        if segment.endswith((" ", ".")):
            return False
        base_name = segment.split(".", 1)[0].upper()
        if base_name in _WINDOWS_RESERVED_NAMES:
            return False
    # No empty segments (covers leading and double slashes).
    return "" not in segments


def safe_join(base: Path, relative_path: str) -> Path | None:
    """Join ``relative_path`` onto ``base`` only if it stays inside ``base``.

    Returns the resolved path, or ``None`` if the path is unsafe or escapes the
    base directory after resolution (defence in depth against symlinks).
    """
    if not path_is_safe(relative_path):
        return None
    base = base.resolve()
    candidate = (base / relative_path).resolve()
    if base not in candidate.parents:
        return None
    return candidate
