"""Compatibility status for SDK packages against the running engine version.

A package declares a ``compatibility`` window (``minimum``/``verified``/
``maximum``). We map semver-ish strings to comparable tuples: ``1.x`` treats
the minor/patch as unbounded and a pre-release sorts **below** its release, with
``dev < alpha < beta < rc < final`` and numeric ordering within a channel: then
classify the package as compatible, unverified, or incompatible.
"""

from __future__ import annotations

import re

from app.engine.sdk.diagnostics import SdkError

COMPAT_COMPATIBLE = "compatible"
COMPAT_UNVERIFIED = "unverified"
COMPAT_INCOMPATIBLE = "incompatible"

_BIG = 1_000_000



_FINAL_RANK = 100
_CHANNEL_RANK = {"dev": -1, "nightly": -1, "alpha": 0, "beta": 1, "rc": 2}
_UNKNOWN_CHANNEL_RANK = 50

_PRERELEASE = re.compile(r"^([a-z]+)\.?(\d+)?$", re.IGNORECASE)
_UPDATE_VERSION = re.compile(
    r"^(?:0|[1-9]\d*)(?:\.(?:0|[1-9]\d*)){0,2}"
    r"(?:-(?:dev|nightly|alpha|beta|rc)(?:\.(?:0|[1-9]\d*))?)?$",
    re.IGNORECASE,
)


def update_version_is_valid(version: str) -> bool:
    """Strict version grammar for remote update ordering."""
    return bool(_UPDATE_VERSION.fullmatch((version or "").strip()))


def _core_part(parts: list[str], index: int) -> int:
    if index >= len(parts):
        return 0
    token = parts[index]
    if token in {"x", "*", "X"}:
        return _BIG
    try:
        return int(token)
    except ValueError:
        return 0


def _prerelease_key(prerelease: str) -> tuple[int, int]:
    """Rank a pre-release string as ``(channel_rank, channel_number)``."""
    if not prerelease:
        return (_FINAL_RANK, 0)
    match = _PRERELEASE.match(prerelease)
    if not match:
        return (_UNKNOWN_CHANNEL_RANK, 0)
    channel = match.group(1).lower()
    number = int(match.group(2)) if match.group(2) else 0
    return (_CHANNEL_RANK.get(channel, _UNKNOWN_CHANNEL_RANK), number)


def version_key(version: str) -> tuple[int, int, int, int, int]:
    """A comparable key: ``(major, minor, patch, channel_rank, channel_number)``.

    ``1.0.0-dev.1 < 1.0.0-alpha.1 < 1.0.0-beta.1 < 1.0.0-rc.1 < 1.0.0`` and
    ``1.x`` is an unbounded upper bound for the ``1`` major line.
    """
    version = (version or "").strip()
    core, _, prerelease = version.partition("-")
    parts = core.split(".")
    channel_rank, channel_number = _prerelease_key(prerelease)
    return (
        _core_part(parts, 0),
        _core_part(parts, 1),
        _core_part(parts, 2),
        channel_rank,
        channel_number,
    )


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


def compatibility_error(
    *,
    minimum: str,
    verified: str,
    maximum: str,
    engine_version: str,
    package_id: str | None = None,
) -> SdkError | None:
    """Return a structured :class:`SdkError` when the package is incompatible.

    ``None`` when the package is compatible or merely unverified. Codes are
    stable (``sdk.compatibility.version_too_low`` / ``version_too_high``).
    """
    current = version_key(engine_version)
    if minimum and current < version_key(minimum):
        return SdkError(
            code="sdk.compatibility.version_too_low",
            message=f"engine {engine_version} is below the minimum {minimum}",
            details={"engine_version": engine_version, "minimum": minimum},
            package_id=package_id,
        )
    if maximum and current > version_key(maximum):
        return SdkError(
            code="sdk.compatibility.version_too_high",
            message=f"engine {engine_version} is above the maximum {maximum}",
            details={"engine_version": engine_version, "maximum": maximum},
            package_id=package_id,
        )
    return None
