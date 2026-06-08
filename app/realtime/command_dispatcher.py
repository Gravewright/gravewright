from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.realtime.commands import ClientCommand
from app.realtime.envelopes import error_envelope
from app.realtime.envelopes import event_envelope


@dataclass(frozen=True)
class ClientCommandContext:
    user_id: str
    room_ids: tuple[str, ...]


@dataclass(frozen=True)
class ParsedClientCommand:
    command_id: str | None
    command: str
    room_id: str | None
    payload: dict[str, Any]


class CommandDispatcher:
    async def dispatch(
        self,
        message: Any,
        *,
        context: ClientCommandContext,
    ) -> dict[str, Any]:
        parsed = self._parse_message(message)

        if isinstance(parsed, dict):
            return parsed

        if parsed.room_id is not None and parsed.room_id not in context.room_ids:
            return error_envelope(
                command_id=parsed.command_id,
                code="permission_denied",
                message="You cannot perform this action.",
            )

        if parsed.command == ClientCommand.PING.value:
            return event_envelope(
                event="pong",
                room_id=parsed.room_id,
                payload={},
            )

        return error_envelope(
            command_id=parsed.command_id,
            code="unknown_command",
            message="Unknown command.",
        )

    def _parse_message(self, message: Any) -> ParsedClientCommand | dict[str, Any]:
        if not isinstance(message, dict):
            return error_envelope(
                command_id=None,
                code="invalid_payload",
                message="Command envelope must be an object.",
            )

        if message.get("type") == "ping":
            return ParsedClientCommand(
                command_id=None,
                command=ClientCommand.PING.value,
                room_id=None,
                payload={},
            )

        command_id = message.get("id")

        if message.get("type") != "command":
            return error_envelope(
                command_id=command_id if isinstance(command_id, str) else None,
                code="invalid_payload",
                message="Command envelope type must be 'command'.",
            )

        command = message.get("command")
        room_id = message.get("room_id")
        payload = message.get("payload", {})

        if not isinstance(command_id, str) or not command_id:
            return error_envelope(
                command_id=None,
                code="invalid_payload",
                message="Command id is required.",
            )

        if not isinstance(command, str) or not command:
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="Command name is required.",
            )

        if room_id is not None and not isinstance(room_id, str):
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="Command room_id must be a string.",
            )

        if not isinstance(payload, dict):
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="Command payload must be an object.",
            )

        return ParsedClientCommand(
            command_id=command_id,
            command=command,
            room_id=room_id,
            payload=payload,
        )
