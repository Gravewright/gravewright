from __future__ import annotations

import hashlib
import secrets

from app.config import config


def generate_removal_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    return "-".join(
        "".join(secrets.choice(alphabet) for _ in range(4))
        for _ in range(2)
    )


def hash_removal_code(code: str) -> str:
    normalized = code.strip().upper()

    return hashlib.sha256(
        f"{config.session_secret}:{normalized}".encode("utf-8")
    ).hexdigest()