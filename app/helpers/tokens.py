from __future__ import annotations

import hashlib
import hmac
import secrets

from app.config import config


def create_url_token() -> str:
    return secrets.token_urlsafe(48)


def hash_url_token(token: str) -> str:
    return hmac.new(
        key=config.session_secret.encode("utf-8"),
        msg=token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()