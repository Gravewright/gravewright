from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.config import config
from app.contracts.transport import RealtimeGatewayContract
from app.domain.tokens import TokenConditionKind
from app.engine.tokens.token_service import TokenService
from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.commands import ClientCommand
from app.realtime.envelopes import error_envelope
from app.realtime.envelopes import event_envelope


_TOKEN_COMMANDS = frozenset(
    {
        ClientCommand.TOKEN_CREATE.value,
        ClientCommand.TOKEN_CREATE_MANY_FROM_ACTORS.value,
        ClientCommand.TOKEN_MOVE.value,
        ClientCommand.TOKEN_UPDATE_OVERRIDE.value,
        ClientCommand.TOKEN_HIDE.value,
        ClientCommand.TOKEN_REVEAL.value,
        ClientCommand.TOKEN_REMOVE_FROM_SCENE.value,
        ClientCommand.TOKEN_CONDITION_ADD.value,
        ClientCommand.TOKEN_CONDITION_REMOVE.value,
    }
)

                                                                              
                                                                             
                          
_MAX_TOKENS_PER_CREATE = config.token_create_many_max
                                                                             
                                                                           
_MAX_OVERRIDE_KEYS = 64
_MAX_OVERRIDE_BYTES = 64 * 1024
_MAX_CONDITION_LABEL_LEN = 120
_ALLOWED_CONDITION_VISIBILITY = frozenset({"everyone", "gm"})


@dataclass(frozen=True)
class TokenCommandResult:
    handled: bool
    response: dict[str, Any] | None = None


class TokenCommandHandler:
    def __init__(self, *, service: TokenService | None = None) -> None:
        self.service = service or TokenService()

    async def handle(
        self,
        message: Any,
        *,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None = None,
    ) -> TokenCommandResult:
        if not isinstance(message, dict):
            return TokenCommandResult(handled=False)

        command = message.get("command")
        if command not in _TOKEN_COMMANDS:
            return TokenCommandResult(handled=False)

        command_id = message.get("id") if isinstance(message.get("id"), str) else None
        room_id = message.get("room_id")
        payload = message.get("payload", {})

        if not isinstance(payload, dict):
            return TokenCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="invalid_payload",
                    message="Command payload must be an object.",
                ),
            )

        if not isinstance(room_id, str) or not room_id:
            return TokenCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="invalid_payload",
                    message="room_id is required for token commands.",
                ),
            )

        if room_id not in context.room_ids:
            return TokenCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

        match command:
            case ClientCommand.TOKEN_CREATE.value:
                return await self._create_one(command_id, room_id, payload, context, transport)
            case ClientCommand.TOKEN_CREATE_MANY_FROM_ACTORS.value:
                return await self._create_many(command_id, room_id, payload, context, transport)
            case ClientCommand.TOKEN_MOVE.value:
                return await self._move(command_id, room_id, payload, context, transport)
            case ClientCommand.TOKEN_UPDATE_OVERRIDE.value:
                return await self._update_override(command_id, room_id, payload, context, transport)
            case ClientCommand.TOKEN_HIDE.value:
                return await self._set_hidden(command_id, room_id, payload, context, transport, hidden=True)
            case ClientCommand.TOKEN_REVEAL.value:
                return await self._set_hidden(command_id, room_id, payload, context, transport, hidden=False)
            case ClientCommand.TOKEN_REMOVE_FROM_SCENE.value:
                return await self._remove_from_scene(command_id, room_id, payload, context, transport)
            case ClientCommand.TOKEN_CONDITION_ADD.value:
                return await self._condition_add(command_id, room_id, payload, context, transport)
            case ClientCommand.TOKEN_CONDITION_REMOVE.value:
                return await self._condition_remove(command_id, room_id, payload, context, transport)

        return TokenCommandResult(handled=False)               

                                                                        
                              
                                                                        

    async def _create_one(
        self,
        command_id: str | None,
        campaign_id: str,
        payload: dict,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> TokenCommandResult:
        scene_id = payload.get("scene_id")
        actor_id = payload.get("actor_id")
        grid_x = payload.get("grid_x")
        grid_y = payload.get("grid_y")

        if not isinstance(scene_id, str) or not scene_id:
            return _invalid(command_id, "scene_id is required.")
        if not isinstance(actor_id, str) or not actor_id:
            return _invalid(command_id, "actor_id is required.")
        if not isinstance(grid_x, int) or not isinstance(grid_y, int):
            return _invalid(command_id, "grid_x and grid_y are required integers.")

        result = await self.service.create_many_from_actors(
            campaign_id=campaign_id,
            scene_id=scene_id,
            actor_ids=[actor_id],
            origin_x=grid_x,
            origin_y=grid_y,
            user_id=context.user_id,
            transport=transport,
        )

        if not result.success:
            return _service_error(command_id, result.error_key)

        token = (result.tokens or [None])[0]
        return TokenCommandResult(
            handled=True,
            response=_ack(
                command_id=command_id,
                command=ClientCommand.TOKEN_CREATE.value,
                campaign_id=campaign_id,
                extra={
                    "token_id": token.get("token_id") if isinstance(token, dict) else None,
                    "token_count": len(result.tokens or []),
                },
            ),
        )

    async def _create_many(
        self,
        command_id: str | None,
        campaign_id: str,
        payload: dict,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> TokenCommandResult:
        scene_id = payload.get("scene_id")
        actor_ids = payload.get("actor_ids")
        origin = payload.get("origin") or {}

        if not isinstance(scene_id, str) or not scene_id:
            return _invalid(command_id, "scene_id is required.")
        if not isinstance(actor_ids, list) or not actor_ids:
            return _invalid(command_id, "actor_ids must be a non-empty list.")
        if len(actor_ids) > _MAX_TOKENS_PER_CREATE:
            return _invalid(command_id, "too many actor_ids in a single create.")
        if not all(isinstance(s, str) and s for s in actor_ids):
            return _invalid(command_id, "actor_ids must be a list of strings.")

        grid_x = origin.get("grid_x")
        grid_y = origin.get("grid_y")
        if not isinstance(grid_x, int) or not isinstance(grid_y, int):
            return _invalid(command_id, "origin.grid_x and origin.grid_y are required integers.")

        result = await self.service.create_many_from_actors(
            campaign_id=campaign_id,
            scene_id=scene_id,
            actor_ids=actor_ids,
            origin_x=grid_x,
            origin_y=grid_y,
            user_id=context.user_id,
            transport=transport,
        )

        if not result.success:
            return _service_error(command_id, result.error_key)

        return TokenCommandResult(
            handled=True,
            response=_ack(
                command_id=command_id,
                command=ClientCommand.TOKEN_CREATE_MANY_FROM_ACTORS.value,
                campaign_id=campaign_id,
                extra={"token_count": len(result.tokens or [])},
            ),
        )

    async def _move(
        self,
        command_id: str | None,
        campaign_id: str,
        payload: dict,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> TokenCommandResult:
        scene_id = payload.get("scene_id")
        token_id = payload.get("token_id")
        grid_x = payload.get("grid_x")
        grid_y = payload.get("grid_y")
        expected_version = payload.get("expected_version")

        if not isinstance(scene_id, str) or not scene_id:
            return _invalid(command_id, "scene_id is required.")
        if not isinstance(token_id, str) or not token_id:
            return _invalid(command_id, "token_id is required.")
        if not isinstance(grid_x, int) or not isinstance(grid_y, int):
            return _invalid(command_id, "grid_x and grid_y are required integers.")
        if not _valid_optional_version(expected_version):
            return _invalid(command_id, "expected_version must be a non-negative integer when provided.")

        result = await self.service.move(
            campaign_id=campaign_id,
            scene_id=scene_id,
            token_id=token_id,
            grid_x=grid_x,
            grid_y=grid_y,
            user_id=context.user_id,
            expected_version=expected_version,
            transport=transport,
        )

        if not result.success:
            return _service_error(command_id, result.error_key)

        return TokenCommandResult(
            handled=True,
            response=_ack(
                command_id=command_id,
                command=ClientCommand.TOKEN_MOVE.value,
                campaign_id=campaign_id,
                extra={"token_id": token_id, "version": result.token["version"]},
            ),
        )

    async def _update_override(
        self,
        command_id: str | None,
        campaign_id: str,
        payload: dict,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> TokenCommandResult:
        scene_id = payload.get("scene_id")
        token_id = payload.get("token_id")
        overrides = payload.get("overrides")
        expected_version = payload.get("expected_version")

        if not isinstance(scene_id, str) or not scene_id:
            return _invalid(command_id, "scene_id is required.")
        if not isinstance(token_id, str) or not token_id:
            return _invalid(command_id, "token_id is required.")
        if not isinstance(overrides, dict):
            return _invalid(command_id, "overrides must be an object.")
        if len(overrides) > _MAX_OVERRIDE_KEYS:
            return _invalid(command_id, "overrides has too many keys.")
        if _json_size(overrides) > _MAX_OVERRIDE_BYTES:
            return _invalid(command_id, "overrides payload is too large.")
        if not _valid_optional_version(expected_version):
            return _invalid(command_id, "expected_version must be a non-negative integer when provided.")

        result = await self.service.update_override(
            campaign_id=campaign_id,
            scene_id=scene_id,
            token_id=token_id,
            overrides=overrides,
            user_id=context.user_id,
            expected_version=expected_version,
            transport=transport,
        )

        if not result.success:
            return _service_error(command_id, result.error_key)

        return TokenCommandResult(
            handled=True,
            response=_ack(
                command_id=command_id,
                command=ClientCommand.TOKEN_UPDATE_OVERRIDE.value,
                campaign_id=campaign_id,
                extra={"token_id": token_id, "version": result.token["version"]},
            ),
        )

    async def _set_hidden(
        self,
        command_id: str | None,
        campaign_id: str,
        payload: dict,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
        *,
        hidden: bool,
    ) -> TokenCommandResult:
        scene_id = payload.get("scene_id")
        token_id = payload.get("token_id")
        expected_version = payload.get("expected_version")

        if not isinstance(scene_id, str) or not scene_id:
            return _invalid(command_id, "scene_id is required.")
        if not isinstance(token_id, str) or not token_id:
            return _invalid(command_id, "token_id is required.")
        if not _valid_optional_version(expected_version):
            return _invalid(command_id, "expected_version must be a non-negative integer when provided.")

        result = await self.service.set_hidden(
            campaign_id=campaign_id,
            scene_id=scene_id,
            token_id=token_id,
            hidden=hidden,
            user_id=context.user_id,
            expected_version=expected_version,
            transport=transport,
        )

        if not result.success:
            return _service_error(command_id, result.error_key)

        cmd = ClientCommand.TOKEN_HIDE.value if hidden else ClientCommand.TOKEN_REVEAL.value
        return TokenCommandResult(
            handled=True,
            response=_ack(
                command_id=command_id,
                command=cmd,
                campaign_id=campaign_id,
                extra={"token_id": token_id, "version": result.token["version"]},
            ),
        )

    async def _remove_from_scene(
        self,
        command_id: str | None,
        campaign_id: str,
        payload: dict,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> TokenCommandResult:
        scene_id = payload.get("scene_id")
        token_id = payload.get("token_id")

        if not isinstance(scene_id, str) or not scene_id:
            return _invalid(command_id, "scene_id is required.")
        if not isinstance(token_id, str) or not token_id:
            return _invalid(command_id, "token_id is required.")

        result = await self.service.remove_from_scene(
            campaign_id=campaign_id,
            scene_id=scene_id,
            token_id=token_id,
            user_id=context.user_id,
            transport=transport,
        )

        if not result.success:
            return _service_error(command_id, result.error_key)

        return TokenCommandResult(
            handled=True,
            response=_ack(
                command_id=command_id,
                command=ClientCommand.TOKEN_REMOVE_FROM_SCENE.value,
                campaign_id=campaign_id,
                extra={"token_id": token_id},
            ),
        )

    async def _condition_add(
        self,
        command_id: str | None,
        campaign_id: str,
        payload: dict,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> TokenCommandResult:
        token_id = payload.get("token_id")
        condition_id = payload.get("condition_id")
        label = payload.get("label")

        if not isinstance(token_id, str) or not token_id:
            return _invalid(command_id, "token_id is required.")
        if not isinstance(condition_id, str) or not condition_id:
            return _invalid(command_id, "condition_id is required.")
        if not isinstance(label, str) or not label:
            return _invalid(command_id, "label is required.")
        if len(label) > _MAX_CONDITION_LABEL_LEN:
            return _invalid(command_id, "label is too long.")

        kind = payload.get("kind", TokenConditionKind.NEUTRAL)
        if kind not in {k.value for k in TokenConditionKind}:
            return _invalid(command_id, "kind must be positive, negative, or neutral.")

        visible_to = payload.get("visible_to", "everyone")
        if visible_to not in _ALLOWED_CONDITION_VISIBILITY:
            return _invalid(command_id, "visible_to must be 'everyone' or 'gm'.")

        result = await self.service.add_condition(
            campaign_id=campaign_id,
            token_id=token_id,
            condition_id=condition_id,
            label=label,
            icon=payload.get("icon") if isinstance(payload.get("icon"), str) else None,
            duration=payload.get("duration") if isinstance(payload.get("duration"), int) else None,
            source=payload.get("source") if isinstance(payload.get("source"), str) else None,
            kind=kind,
            visible_to=visible_to,
            user_id=context.user_id,
            transport=transport,
        )

        if not result.success:
            return _service_error(command_id, result.error_key)

        return TokenCommandResult(
            handled=True,
            response=_ack(
                command_id=command_id,
                command=ClientCommand.TOKEN_CONDITION_ADD.value,
                campaign_id=campaign_id,
                extra={"token_id": token_id, "condition_id": condition_id},
            ),
        )

    async def _condition_remove(
        self,
        command_id: str | None,
        campaign_id: str,
        payload: dict,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> TokenCommandResult:
        token_id = payload.get("token_id")
        condition_id = payload.get("condition_id")

        if not isinstance(token_id, str) or not token_id:
            return _invalid(command_id, "token_id is required.")
        if not isinstance(condition_id, str) or not condition_id:
            return _invalid(command_id, "condition_id is required.")

        result = await self.service.remove_condition(
            campaign_id=campaign_id,
            token_id=token_id,
            condition_id=condition_id,
            user_id=context.user_id,
            transport=transport,
        )

        if not result.success:
            return _service_error(command_id, result.error_key)

        return TokenCommandResult(
            handled=True,
            response=_ack(
                command_id=command_id,
                command=ClientCommand.TOKEN_CONDITION_REMOVE.value,
                campaign_id=campaign_id,
                extra={"token_id": token_id, "condition_id": condition_id},
            ),
        )


                                                                    
         
                                                                    

def _valid_optional_version(value: Any) -> bool:
    """``expected_version`` is optional; when present it must be a non-negative int."""
    if value is None:
        return True
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _json_size(value: Any) -> int:
    try:
        return len(json.dumps(value, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError):
                                                                                
        return _MAX_OVERRIDE_BYTES + 1


def _invalid(command_id: str | None, message: str) -> TokenCommandResult:
    return TokenCommandResult(
        handled=True,
        response=error_envelope(
            command_id=command_id,
            code="invalid_payload",
            message=message,
        ),
    )


def _service_error(command_id: str | None, error_key: str | None) -> TokenCommandResult:
    code_map = {
        "tokens.errors.permission_denied": "permission_denied",
        "tokens.errors.not_found": "not_found",
        "tokens.errors.locked": "token_locked",
        "tokens.errors.version_conflict": "version_conflict",
        "tokens.errors.no_actors": "invalid_payload",
        "tokens.errors.actor_not_found": "not_found",
        "tokens.errors.scene_not_found": "not_found",
        "tokens.errors.condition_not_found": "not_found",
    }
    code = code_map.get(error_key or "", "service_error")
    return TokenCommandResult(
        handled=True,
        response=error_envelope(
            command_id=command_id,
            code=code,
            message=error_key or "An error occurred.",
        ),
    )


def _ack(
    *,
    command_id: str | None,
    command: str,
    campaign_id: str,
    extra: dict | None = None,
) -> dict:
    return event_envelope(
        event="token.command.ack",
        room_id=campaign_id,
        payload={
            "command_id": command_id,
            "command": command,
            "success": True,
            **(extra or {}),
        },
    )
