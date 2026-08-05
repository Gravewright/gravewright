from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import config
from app.helpers.async_blocking import run_blocking
from app.contracts.transport import RealtimeGatewayContract
from app.domain.fog import FogCircleGeom
from app.domain.fog import FogInitialState
from app.domain.fog import FogMode
from app.domain.fog import FogOp
from app.domain.fog import FogPolygonGeom
from app.domain.fog import FogShape
from app.domain.fog import FogSquareGeom
from app.engine.scenes.fog_service import FogService
from app.engine.scenes.fog_service import FogServiceResult
from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.commands import ClientCommand
from app.realtime.envelopes import error_envelope
from app.realtime.envelopes import event_envelope
from app.realtime.events import TransportEvent


_FOG_COMMANDS = frozenset(
    {
        ClientCommand.FOG_ENABLE.value,
        ClientCommand.FOG_DISABLE.value,
        ClientCommand.FOG_PAINT.value,
        ClientCommand.FOG_RESET.value,
    }
)

                                                                              
                                                                          
                                                                               
_MAX_OPS_PER_COMMAND = config.fog_max_ops_per_command
_MAX_POLYGON_POINTS = config.fog_max_polygon_points
                                                                              
_MAX_COORD_ABS = float(config.fog_max_coordinate_abs)
_MAX_SIZE_CELLS = 10_000.0
                                                                                
_REQUIRE_EXPECTED_VERSION = config.fog_require_expected_version


@dataclass(frozen=True)
class FogCommandResult:
    handled: bool
    response: dict[str, Any] | None = None


class FogCommandHandler:
    def __init__(self, *, service: FogService | None = None) -> None:
        self.service = service or FogService()

    async def handle(
        self,
        message: Any,
        *,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None = None,
    ) -> FogCommandResult:
        if not isinstance(message, dict):
            return FogCommandResult(handled=False)

        command = message.get("command")
        if command not in _FOG_COMMANDS:
            return FogCommandResult(handled=False)

        command_id = message.get("id") if isinstance(message.get("id"), str) else None
        room_id = message.get("room_id")
        payload = message.get("payload", {})

        if not isinstance(payload, dict):
            return _invalid(command_id, "Command payload must be an object.")

        if not isinstance(room_id, str) or not room_id:
            return _invalid(command_id, "room_id is required for fog commands.")

        if room_id not in context.room_ids:
            return FogCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

        scene_id = payload.get("scene_id")
        if not isinstance(scene_id, str) or not scene_id:
            return _invalid(command_id, "scene_id is required.")

        scene_state = await run_blocking(self.service.get_state, scene_id)
        if not scene_state.success:
            return _service_error(command_id, scene_state.error_key)
        if scene_state.campaign_id != room_id:
            return _service_error(command_id, "game.scenes.errors.scene_not_in_room")

        match command:
            case ClientCommand.FOG_ENABLE.value:
                return await self._enable(command_id, room_id, scene_id, payload, context, transport)
            case ClientCommand.FOG_DISABLE.value:
                return await self._disable(command_id, room_id, scene_id, context, transport)
            case ClientCommand.FOG_RESET.value:
                return await self._reset(command_id, room_id, scene_id, payload, context, transport)
            case ClientCommand.FOG_PAINT.value:
                return await self._paint(command_id, room_id, scene_id, payload, context, transport)

        return FogCommandResult(handled=False)

    async def _enable(
        self,
        command_id: str | None,
        campaign_id: str,
        scene_id: str,
        payload: dict,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> FogCommandResult:
        initial_raw = payload.get("initial", FogInitialState.HIDE_ALL.value)
        try:
            initial = FogInitialState(initial_raw)
        except ValueError:
            return _invalid(command_id, "initial must be 'hide_all' or 'reveal_all'.")

        result = await run_blocking(
            self.service.enable,
            scene_id=scene_id,
            user_id=context.user_id,
            initial=initial,
        )
        return await self._finalize(command_id, ClientCommand.FOG_ENABLE.value, campaign_id, result, transport)

    async def _disable(
        self,
        command_id: str | None,
        campaign_id: str,
        scene_id: str,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> FogCommandResult:
        result = await run_blocking(self.service.disable, scene_id=scene_id, user_id=context.user_id)
        return await self._finalize(command_id, ClientCommand.FOG_DISABLE.value, campaign_id, result, transport)

    async def _reset(
        self,
        command_id: str | None,
        campaign_id: str,
        scene_id: str,
        payload: dict,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> FogCommandResult:
        to_raw = payload.get("to", FogInitialState.HIDE_ALL.value)
        try:
            to = FogInitialState(to_raw)
        except ValueError:
            return _invalid(command_id, "to must be 'hide_all' or 'reveal_all'.")

        result = await run_blocking(self.service.reset, scene_id=scene_id, user_id=context.user_id, to=to)
        return await self._finalize(command_id, ClientCommand.FOG_RESET.value, campaign_id, result, transport)

    async def _paint(
        self,
        command_id: str | None,
        campaign_id: str,
        scene_id: str,
        payload: dict,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> FogCommandResult:
        ops_raw = payload.get("ops")
        if not isinstance(ops_raw, list) or not ops_raw:
            return _invalid(command_id, "ops must be a non-empty list.")

        if len(ops_raw) > _MAX_OPS_PER_COMMAND:
            return _invalid(command_id, "too many ops in a single paint.")

        expected_version = payload.get("expected_version")
        if _REQUIRE_EXPECTED_VERSION:
            if not isinstance(expected_version, int) or isinstance(expected_version, bool):
                return _invalid(command_id, "expected_version is required and must be an integer.")
        elif expected_version is not None and (
            not isinstance(expected_version, int) or isinstance(expected_version, bool)
        ):
            return _invalid(command_id, "expected_version must be an integer or omitted.")

        ops: list[FogOp] = []
        for raw in ops_raw:
            parsed = _parse_op(raw)
            if parsed is None:
                return _invalid(command_id, "invalid op in ops list.")
            ops.append(parsed)

        result = await run_blocking(
            self.service.paint,
            scene_id=scene_id,
            user_id=context.user_id,
            ops=ops,
            expected_version=expected_version,
        )
        return await self._finalize(command_id, ClientCommand.FOG_PAINT.value, campaign_id, result, transport)

    async def _finalize(
        self,
        command_id: str | None,
        command: str,
        campaign_id: str,
        result: FogServiceResult,
        transport: RealtimeGatewayContract | None,
    ) -> FogCommandResult:
        if not result.success:
            return _service_error(command_id, result.error_key)

        if result.campaign_id != campaign_id:
            return _service_error(command_id, "game.scenes.errors.scene_not_in_room")

        if transport is not None and result.scene_id is not None:
            payload = {
                "room_id": campaign_id,
                "scene_id": result.scene_id,
                "enabled": result.enabled,
                "version": result.version,
                "baseline": result.baseline,
            }
            if result.new_ops is not None:
                payload["new_ops"] = result.new_ops
            else:
                payload["ops"] = result.ops or []
            await transport.to_room(
                room_id=campaign_id,
                event=TransportEvent.FOG_UPDATED,
                payload=payload,
            )

        return FogCommandResult(
            handled=True,
            response=event_envelope(
                event="fog.command.ack",
                room_id=campaign_id,
                payload={
                    "command_id": command_id,
                    "command": command,
                    "success": True,
                    "scene_id": result.scene_id,
                    "version": result.version,
                },
            ),
        )


def _parse_op(raw: Any) -> FogOp | None:
    if not isinstance(raw, dict):
        return None

    mode_raw = raw.get("mode")
    shape_raw = raw.get("shape")
    geom_raw = raw.get("geom")

    try:
        mode = FogMode(mode_raw)
        shape = FogShape(shape_raw)
    except ValueError:
        return None

    if not isinstance(geom_raw, dict):
        return None

    if shape == FogShape.CIRCLE:
        cx = geom_raw.get("center_x_cells")
        cy = geom_raw.get("center_y_cells")
        r = geom_raw.get("radius_cells")
        if not _is_coord(cx) or not _is_coord(cy) or not _is_size(r):
            return None
        return FogOp(mode=mode, shape=shape, geom=FogCircleGeom(float(cx), float(cy), float(r)))

    if shape == FogShape.SQUARE:
        cx = geom_raw.get("center_x_cells")
        cy = geom_raw.get("center_y_cells")
        s = geom_raw.get("size_cells")
        if not _is_coord(cx) or not _is_coord(cy) or not _is_size(s):
            return None
        return FogOp(mode=mode, shape=shape, geom=FogSquareGeom(float(cx), float(cy), float(s)))

    if shape == FogShape.POLYGON:
        pts_raw = geom_raw.get("points_cells")
        if not isinstance(pts_raw, list) or len(pts_raw) < 3:
            return None
        if len(pts_raw) > _MAX_POLYGON_POINTS:
            return None
        pts: list[tuple[float, float]] = []
        for p in pts_raw:
            if not isinstance(p, (list, tuple)) or len(p) != 2:
                return None
            x, y = p[0], p[1]
            if not _is_coord(x) or not _is_coord(y):
                return None
            pts.append((float(x), float(y)))
        return FogOp(mode=mode, shape=shape, geom=FogPolygonGeom(tuple(pts)))

    return None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_coord(value: Any) -> bool:
    return _is_number(value) and abs(float(value)) <= _MAX_COORD_ABS


def _is_size(value: Any) -> bool:
    return _is_number(value) and 0.0 < float(value) <= _MAX_SIZE_CELLS


def _invalid(command_id: str | None, message: str) -> FogCommandResult:
    return FogCommandResult(
        handled=True,
        response=error_envelope(
            command_id=command_id,
            code="invalid_payload",
            message=message,
        ),
    )


def _service_error(command_id: str | None, error_key: str | None) -> FogCommandResult:
    code_map = {
        "permissions.errors.denied": "permission_denied",
        "game.scenes.errors.not_found": "not_found",
        "game.scenes.errors.scene_not_in_room": "not_found",
        "game.fog.errors.disabled": "fog_disabled",
        "game.fog.errors.version_conflict": "version_conflict",
        "game.fog.errors.too_many_ops": "too_many_ops",
    }
    code = code_map.get(error_key or "", "service_error")
    return FogCommandResult(
        handled=True,
        response=error_envelope(
            command_id=command_id,
            code=code,
            message=error_key or "An error occurred.",
        ),
    )
