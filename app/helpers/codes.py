from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from app.config import config




JOIN_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTVWXYZ23456789"
JOIN_CODE_USEFUL_LENGTH = 12
JOIN_CODE_CONTEXT = b"gravewright:campaign-join-code:v1"
_JOIN_CODE_SEPARATORS_RE = re.compile(r"[\s-]+")


def generate_removal_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    return "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(2))


def hash_removal_code(code: str) -> str:
    normalized = code.strip().upper()

    return hashlib.sha256(f"{config.session_secret}:{normalized}".encode("utf-8")).hexdigest()


def generate_join_code() -> str:
    """Generate a cryptographically secure V1 campaign join code.

    The returned presentation form is ``XXXX-XXXX-XXXX``. Persistence and logs
    must use neither this value nor its normalized plaintext representation.
    """
    useful = "".join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(JOIN_CODE_USEFUL_LENGTH))
    return "-".join(useful[offset : offset + 4] for offset in range(0, len(useful), 4))


def normalize_join_code(code: str) -> str:
    """Return the canonical 12-character code or raise ``ValueError``.

    Spaces (including tabs/newlines) and hyphens are presentation separators;
    all other characters must belong to :data:`JOIN_CODE_ALPHABET`.
    """
    if not isinstance(code, str):
        raise TypeError("join code must be a string")
    normalized = _JOIN_CODE_SEPARATORS_RE.sub("", code).upper()
    if len(normalized) != JOIN_CODE_USEFUL_LENGTH or any(
        character not in JOIN_CODE_ALPHABET for character in normalized
    ):
        raise ValueError("invalid campaign join code format")
    return normalized


def _join_code_hmac_key(secret: str) -> bytes:
    """Derive a domain-separated key from the configured application secret."""
    return hmac.new(secret.encode("utf-8"), JOIN_CODE_CONTEXT, hashlib.sha256).digest()


def hash_join_code(code: str, *, secret: str | None = None) -> str:
    """Return the deterministic, namespaced HMAC-SHA256 digest for ``code``."""
    normalized = normalize_join_code(code)
    key = _join_code_hmac_key(config.session_secret if secret is None else secret)
    return hmac.new(key, normalized.encode("ascii"), hashlib.sha256).hexdigest()


def join_code_hash_matches(
    code: str,
    expected_digest: str,
    *,
    secret: str | None = None,
) -> bool:
    """Constant-time comparison for the rare case a digest is checked in Python."""
    actual = hash_join_code(code, secret=secret)
    return hmac.compare_digest(actual, expected_digest)
