from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.config import config

TICKET_TTL_SECONDS = 90


def issue_presentation_ticket(*, campaign_id: str, user_id: str,
                              resource_type: str, resource_id: str) -> str:
    payload = {
        "campaign_id": campaign_id, "user_id": user_id,
        "resource_type": resource_type, "resource_id": resource_id,
        "expires_at": int(time.time()) + TICKET_TTL_SECONDS,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).rstrip(b"=")
    signature = hmac.new(
        config.session_secret.encode(), b"gravewright:presentation:v1:" + encoded,
        hashlib.sha256,
    ).digest()
    return f"{encoded.decode()}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def verify_presentation_ticket(ticket: str, *, user_id: str) -> dict[str, Any] | None:
    try:
        encoded_text, signature_text = ticket.split(".", 1)
        encoded = encoded_text.encode()
        expected = hmac.new(
            config.session_secret.encode(), b"gravewright:presentation:v1:" + encoded,
            hashlib.sha256,
        ).digest()
        signature = base64.urlsafe_b64decode(signature_text + "=" * (-len(signature_text) % 4))
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(
            encoded_text + "=" * (-len(encoded_text) % 4)
        ))
        if payload.get("user_id") != user_id or int(payload.get("expires_at", 0)) < int(time.time()):
            return None
        if payload.get("resource_type") not in {"journal", "item", "asset"}:
            return None
        return payload
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        return None
