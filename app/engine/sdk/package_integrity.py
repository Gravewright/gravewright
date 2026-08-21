"""Manifest integrity hashing for SDK packages.

The install registry stores a snapshot of the manifest plus a ``manifest_hash``
so drift between the installed snapshot and the current on-disk manifest can be
detected. Disk remains the runtime authority; the hash is for audit/diagnosis.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


VALIDATION_VALID = "valid"
VALIDATION_INVALID = "invalid"
VALIDATION_MISSING = "missing"
VALIDATION_STALE = "stale"
VALIDATION_ERROR = "error"


def compute_manifest_hash(raw: dict) -> str:
    """A stable sha256 over a manifest's canonical JSON form.

    Canonicalised with sorted keys and compact separators so semantically equal
    manifests hash identically regardless of key order or whitespace.
    """
    canonical = json.dumps(raw or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_package_tree_hash(package_dir: Path) -> str:
    """Canonical digest of every regular file in a trusted bundled package."""
    digest = hashlib.sha256()
    for path in sorted((item for item in package_dir.rglob("*") if item.is_file()),
                       key=lambda item: item.relative_to(package_dir).as_posix()):
        relative = path.relative_to(package_dir).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        file_hash = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                file_hash.update(chunk)
        digest.update(file_hash.digest())
    return digest.hexdigest()
