from __future__ import annotations

import time
import uuid
from typing import Any


def event_envelope(
    *,
    event: str,
    payload: dict[str, Any],
    room_id: str | None = None,
    envelope_id: str | None = None,
    ts: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    timestamp = int(time.time()) if ts is None else ts

    envelope = {
        "type": "event",
        "id": envelope_id or uuid.uuid4().hex,
        "event": event,
        "room_id": room_id,
        "payload": payload,
        "ts": timestamp,
    }

    if extra:
        envelope.update(extra)

    return envelope


def error_envelope(
    *,
    command_id: str | None,
    code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "type": "error",
        "command_id": command_id,
        "code": code,
        "message": message,
    }
