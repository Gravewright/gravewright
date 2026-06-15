"""Compatibility status for SDK packages against the running engine version.

A package declares a ``compatibility`` window (``minimum``/``verified``/
``maximum``). We map semver-ish strings to comparable tuples — ``1.x`` treats
the minor/patch as unbounded and a pre-release sorts just below its release —
then classify the package as compatible, unverified, or incompatible.
"""

from __future__ import annotations

COMPAT_COMPATIBLE = "compatible"
COMPAT_UNVERIFIED = "unverified"
COMPAT_INCOMPATIBLE = "incompatible"

_BIG = 1_000_000


def version_key(version: str) -> tuple[int, int, int, int]:
    version = (version or "").strip()
    is_release = "-" not in version
    core = version.split("-", 1)[0]
    parts = core.split(".")

    def part(index: int) -> int:
        if index >= len(parts):
            return 0
        token = parts[index]
        if token in {"x", "*"}:
            return _BIG
        try:
            return int(token)
        except ValueError:
            return 0

    return (part(0), part(1), part(2), 1 if is_release else 0)


def compute_compatibility_status(
    *,
    minimum: str,
    verified: str,
    maximum: str,
    engine_version: str,
) -> str:
    current = version_key(engine_version)
    if minimum and current < version_key(minimum):
        return COMPAT_INCOMPATIBLE
    if maximum and current > version_key(maximum):
        return COMPAT_INCOMPATIBLE
    if verified and version_key(verified) == current:
        return COMPAT_COMPATIBLE
    return COMPAT_UNVERIFIED
