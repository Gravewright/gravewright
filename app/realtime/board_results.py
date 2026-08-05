"""Board command result/ack envelope builders.

Extracted from ``board_command_handler`` (maintenance plan, Etapa 8) to separate
result construction from dispatch/authorization/handlers. Behavior is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.realtime.envelopes import error_envelope
from app.realtime.envelopes import event_envelope


@dataclass(frozen=True)
class BoardCommandResult:
    handled: bool
    response: dict[str, Any] | None = None


def _board_version_extra(board_version: int | None) -> dict[str, int]:
    if board_version is None:
        return {}
    return {"board_version": board_version}


def _ack(
    command_id: str | None,
    room_id: str,
    command: str,
    scene_id: str,
    *,
    extra: dict[str, Any] | None = None,
) -> BoardCommandResult:
    return BoardCommandResult(
        handled=True,
        response=event_envelope(
            event="board.command.ack",
            room_id=room_id,
            payload={
                "command_id": command_id,
                "command": command,
                "success": True,
                "scene_id": scene_id,
                **(extra or {}),
            },
        ),
    )


def _board_conflict(command_id: str | None) -> BoardCommandResult:
    return BoardCommandResult(
        handled=True,
        response=error_envelope(
            command_id=command_id,
            code="board_version_conflict",
            message="Board state changed. Refresh the board and retry the command.",
        ),
    )


def _limit_reached(command_id: str | None, message: str) -> BoardCommandResult:
    return BoardCommandResult(
        handled=True,
        response=error_envelope(
            command_id=command_id,
            code="limit_reached",
            message=message,
        ),
    )


def _invalid(command_id: str | None, message: str) -> BoardCommandResult:
    return BoardCommandResult(
        handled=True,
        response=error_envelope(
            command_id=command_id,
            code="invalid_payload",
            message=message,
        ),
    )
