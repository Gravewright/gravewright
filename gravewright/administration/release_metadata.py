"""Bounded HTTPS reads and versions for native product release checks."""

import re
from urllib.request import Request, urlopen

_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-.]([0-9A-Za-z.-]+))?$")
_PYTHON_PRERELEASE = re.compile(r"^(\d+\.\d+\.\d+)(a|b|rc)(\d+)$")


def normalize_version(value):
    """Bridge Python package prereleases to the public release/tag notation."""
    value = value.strip()
    if value.lower().startswith('v'):
        value = value[1:]
    if match := _PYTHON_PRERELEASE.fullmatch(value):
        base, phase, number = match.groups()
        phase = {'a': 'alpha', 'b': 'beta', 'rc': 'rc'}[phase]
        return f'{base}-{phase}.{int(number)}'
    return value


def version_label(value):
    """Present the public release name while preserving numbered later previews."""
    value = normalize_version(value)
    match = re.fullmatch(r'(\d+\.\d+\.\d+)-(alpha|beta|rc)(?:\.(\d+))?', value)
    if not match:
        return value
    base, phase, number = match.groups()
    label = {'alpha': 'Alpha', 'beta': 'Beta', 'rc': 'RC'}[phase]
    suffix = f' ({number})' if number and int(number) else ''
    return f'{label} {base}{suffix}'


def update_version_is_valid(value):
    return isinstance(value, str) and _PATTERN.fullmatch(normalize_version(value)) is not None


def version_key(value):
    match = _PATTERN.fullmatch(normalize_version(value))
    if not match:
        raise ValueError("Invalid release version")
    major, minor, patch, suffix = match.groups()
    # Numeric prerelease identifiers compare numerically: alpha.10 > alpha.2.
    identifiers = tuple((0, int(part)) if part.isascii() and part.isdecimal()
                        else (1, part) for part in (suffix or '').split('.'))
    return (int(major), int(minor), int(patch), suffix is None, identifiers)


def fetch_bytes(url, limit):
    if not url.startswith("https://"):
        raise ValueError("HTTPS required")
    with urlopen(
        Request(url, headers={"User-Agent": "Gravewright"}), timeout=15
    ) as response:
        if not response.url.startswith("https://"):
            raise ValueError("HTTPS required")
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Release metadata exceeds limit")
    return data
