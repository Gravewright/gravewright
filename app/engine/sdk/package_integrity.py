"""Manifest integrity hashing for SDK packages.

The install registry stores a snapshot of the manifest plus a ``manifest_hash``
so drift between the installed snapshot and the current on-disk manifest can be
detected. Disk remains the runtime authority; the hash is for audit/diagnosis.
"""

from __future__ import annotations

import hashlib
import json

# Validation status persisted alongside the hash.
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
