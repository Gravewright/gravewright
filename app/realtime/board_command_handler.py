from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.business.permissions.permission_service import PermissionService
from app.config import config
from app.helpers.async_blocking import run_blocking
from app.contracts.transport import RealtimeGatewayContract
from app.domain.permissions.permissions import TablePermission
from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.commands import ClientCommand
from app.realtime.envelopes import error_envelope
from app.realtime.envelopes import event_envelope
from app.realtime.events import TransportEvent
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository

                                                                                    
_GM_ROLES = {"gm", "assistant_gm"}

                                                                                 
                                                                                
                                             
_BOARD_COMMAND_PERMISSIONS = {
    ClientCommand.BOARD_PING.value: TablePermission.BOARD_PING,
    ClientCommand.BOARD_AREA_MARKER_UPSERT.value: TablePermission.BOARD_MARKER_CREATE,
    ClientCommand.BOARD_AREA_MARKER_DELETE.value: TablePermission.BOARD_MARKER_DELETE,
    ClientCommand.BOARD_AREA_MARKER_CLEAR.value: TablePermission.BOARD_MARKER_CLEAR,
    ClientCommand.BOARD_DRAW_UPSERT.value: TablePermission.BOARD_DRAW,
    ClientCommand.BOARD_DRAW_CLEAR.value: TablePermission.BOARD_DRAW,
    ClientCommand.BOARD_MEASURE_FLASH.value: TablePermission.GRID_MEASURE,
    ClientCommand.BOARD_MEASURE_DELETE.value: TablePermission.GRID_MEASURE,
    ClientCommand.BOARD_MEASURE_CLEAR.value: TablePermission.GRID_MEASURE,
}


@dataclass(frozen=True)
class BoardCommandResult:
    handled: bool
    response: dict[str, Any] | None = None


class BoardCommandHandler:
    BOARD_COMMANDS = {
        ClientCommand.BOARD_PING.value,
        ClientCommand.BOARD_AREA_MARKER_UPSERT.value,
        ClientCommand.BOARD_AREA_MARKER_DELETE.value,
        ClientCommand.BOARD_AREA_MARKER_CLEAR.value,
        ClientCommand.BOARD_DRAW_UPSERT.value,
        ClientCommand.BOARD_DRAW_CLEAR.value,
        ClientCommand.BOARD_MEASURE_FLASH.value,
        ClientCommand.BOARD_MEASURE_DELETE.value,
        ClientCommand.BOARD_MEASURE_CLEAR.value,
    }

    def __init__(
        self,
        *,
        scenes: SceneRepository | None = None,
        campaigns: CampaignRepository | None = None,
        permissions: PermissionService | None = None,
    ) -> None:
        self.scenes = scenes or SceneRepository()
        self.campaigns = campaigns or CampaignRepository()
        self.permissions = permissions or PermissionService()

    async def _is_gm(self, user_id: str, room_id: str) -> bool:
        role = await run_blocking(
            self.campaigns.get_member_role,
            campaign_id=room_id,
            user_id=user_id,
        )
        return role in _GM_ROLES

    async def _find_board_item(self, scene_id: str, item_id: str) -> dict[str, Any] | None:
        items = await run_blocking(self.scenes.list_board_area_markers, scene_id)
        for item in items:
            if item.get("id") == item_id:
                return item
        return None

    @staticmethod
    def _is_drawing(item: dict[str, Any]) -> bool:
        return item.get("kind") in ("freehand", "text")

    async def _get_board_version(self, scene_id: str) -> int | None:
        getter = getattr(self.scenes, "get_board_version", None)
        if getter is None:
            return None
        return await run_blocking(getter, scene_id)

    async def _broadcast_layer_aware_upsert(
        self,
        transport: RealtimeGatewayContract | None,
        *,
        room_id: str,
        scene_id: str,
        item: dict[str, Any],
        item_id: str,
        payload_key: str,
        upsert_event: TransportEvent,
        user_id: str,
        board_version: int | None = None,
    ) -> None:
        if transport is None:
            return
        full = {
            "room_id": room_id,
            "scene_id": scene_id,
            payload_key: item,
            "user_id": user_id,
        }
        if board_version is not None:
            full["board_version"] = board_version
        if item.get("layer") == "gm":
                                                                                 
            await transport.to_gm(room_id=room_id, event=upsert_event, payload=full)
            await transport.to_players_in_room(
                room_id=room_id,
                event=TransportEvent.BOARD_AREA_MARKER_DELETED,
                payload={
                    "room_id": room_id,
                    "scene_id": scene_id,
                    "marker_id": item_id,
                    "user_id": user_id,
                },
            )
        else:
            await transport.to_room(room_id=room_id, event=upsert_event, payload=full)

    async def handle(
        self,
        message: Any,
        *,
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None = None,
    ) -> BoardCommandResult:
        if not isinstance(message, dict):
            return BoardCommandResult(handled=False)

        command = message.get("command")
        if command not in self.BOARD_COMMANDS:
            return BoardCommandResult(handled=False)

        command_id = message.get("id") if isinstance(message.get("id"), str) else None
        room_id = message.get("room_id")
        payload = message.get("payload", {})

        if not isinstance(payload, dict):
            return _invalid(command_id, "Command payload must be an object.")

        if not isinstance(room_id, str) or not room_id:
            return _invalid(command_id, "room_id is required for board commands.")

        if room_id not in context.room_ids:
            return BoardCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

        required_permission = _BOARD_COMMAND_PERMISSIONS.get(command)
        if required_permission is not None and not await run_blocking(
            self.permissions.can,
            user_id=context.user_id,
            campaign_id=room_id,
            permission=required_permission,
        ):
            return BoardCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

        if command == ClientCommand.BOARD_PING.value:
            return await self._handle_ping(command_id, room_id, payload, context, transport)
        if command == ClientCommand.BOARD_AREA_MARKER_UPSERT.value:
            return await self._handle_area_marker_upsert(command_id, room_id, payload, context, transport)
        if command == ClientCommand.BOARD_AREA_MARKER_DELETE.value:
            return await self._handle_area_marker_delete(command_id, room_id, payload, context, transport)
        if command == ClientCommand.BOARD_AREA_MARKER_CLEAR.value:
            return await self._handle_area_marker_clear(command_id, room_id, payload, context, transport)
        if command == ClientCommand.BOARD_DRAW_UPSERT.value:
            return await self._handle_draw_upsert(command_id, room_id, payload, context, transport)
        if command == ClientCommand.BOARD_DRAW_CLEAR.value:
            return await self._handle_draw_clear(command_id, room_id, payload, context, transport)
        if command == ClientCommand.BOARD_MEASURE_FLASH.value:
            return await self._handle_measure_flash(command_id, room_id, payload, context, transport)
        if command == ClientCommand.BOARD_MEASURE_DELETE.value:
            return await self._handle_measure_delete(command_id, room_id, payload, context, transport)
        if command == ClientCommand.BOARD_MEASURE_CLEAR.value:
            return await self._handle_measure_clear(command_id, room_id, payload, context, transport)

        return BoardCommandResult(handled=False)

    async def _handle_ping(
        self,
        command_id: str | None,
        room_id: str,
        payload: dict[str, Any],
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> BoardCommandResult:
        scene_id = payload.get("scene_id")
        world_x = payload.get("world_x")
        world_y = payload.get("world_y")
        variant = payload.get("variant", "ping")

        if not isinstance(scene_id, str) or not scene_id:
            return _invalid(command_id, "scene_id is required.")
        if not isinstance(world_x, int | float) or not isinstance(world_y, int | float):
            return _invalid(command_id, "world_x and world_y are required numbers.")
        if variant not in {"ping", "focus"}:
            return _invalid(command_id, "variant must be 'ping' or 'focus'.")

        broadcast = {
            "room_id": room_id,
            "scene_id": scene_id,
            "world_x": float(world_x),
            "world_y": float(world_y),
            "variant": variant,
            "user_id": context.user_id,
        }

        if transport is not None:
            await transport.to_room(
                room_id=room_id,
                event=TransportEvent.BOARD_PING,
                payload=broadcast,
            )

        return BoardCommandResult(
            handled=True,
            response=event_envelope(
                event="board.command.ack",
                room_id=room_id,
                payload={
                    "command_id": command_id,
                    "command": ClientCommand.BOARD_PING.value,
                    "success": True,
                    "scene_id": scene_id,
                },
            ),
        )

    async def _handle_area_marker_upsert(
        self,
        command_id: str | None,
        room_id: str,
        payload: dict[str, Any],
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> BoardCommandResult:
        marker = payload.get("marker")
        if not isinstance(marker, dict):
            return _invalid(command_id, "marker is required.")
        expected_board_version = _expected_board_version(payload)
        if isinstance(expected_board_version, str):
            return _invalid(command_id, expected_board_version)

        normalized = _normalize_board_shape(marker, "marker")
        if isinstance(normalized, str):
            return _invalid(command_id, normalized)

        scene = await run_blocking(self.scenes.get_by_id, normalized["scene_id"])
        if scene is None:
            return _invalid(command_id, "scene_id was not found.")
        if scene["campaign_id"] != room_id:
            return BoardCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

                                                                              
                                                        
        existing_items = await run_blocking(self.scenes.list_board_area_markers, normalized["scene_id"])
        is_new = not any(item.get("id") == normalized["id"] for item in existing_items)
        if is_new:
            marker_count = sum(1 for item in existing_items if not self._is_drawing(item))
            if marker_count >= config.board_markers_max_per_scene:
                return _limit_reached(command_id, "This scene has too many markers.")

                                                               
        if await self._is_gm(context.user_id, room_id) and marker.get("layer") == "gm":
            normalized["layer"] = "gm"

        updated_markers = await run_blocking(
            self.scenes.upsert_board_area_marker,
            scene_id=normalized["scene_id"],
            marker=normalized,
            **({"expected_board_version": expected_board_version} if expected_board_version is not None else {}),
        )
        if updated_markers is None:
            return _board_conflict(command_id)
        board_version = await self._get_board_version(normalized["scene_id"])

        await self._broadcast_layer_aware_upsert(
            transport,
            room_id=room_id,
            scene_id=normalized["scene_id"],
            item=normalized,
            item_id=normalized["id"],
            payload_key="marker",
            upsert_event=TransportEvent.BOARD_AREA_MARKER_UPSERTED,
            user_id=context.user_id,
            board_version=board_version,
        )

        return _ack(
            command_id,
            room_id,
            ClientCommand.BOARD_AREA_MARKER_UPSERT.value,
            normalized["scene_id"],
            extra=_board_version_extra(board_version),
        )

    async def _handle_area_marker_delete(
        self,
        command_id: str | None,
        room_id: str,
        payload: dict[str, Any],
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> BoardCommandResult:
        scene_id = payload.get("scene_id")
        marker_id = payload.get("marker_id")
        expected_board_version = _expected_board_version(payload)
        if isinstance(expected_board_version, str):
            return _invalid(command_id, expected_board_version)
        if not isinstance(scene_id, str) or not scene_id:
            return _invalid(command_id, "scene_id is required.")
        if not isinstance(marker_id, str) or not marker_id:
            return _invalid(command_id, "marker_id is required.")

        scene = await run_blocking(self.scenes.get_by_id, scene_id)
        if scene is None:
            return _invalid(command_id, "scene_id was not found.")
        if scene["campaign_id"] != room_id:
            return BoardCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

                                                                              
        existing = await self._find_board_item(scene_id, marker_id)
        if existing is not None and existing.get("kind") in ("freehand", "text"):
            owner = existing.get("owner_id")
            if owner is not None and owner != context.user_id and not await self._is_gm(context.user_id, room_id):
                return BoardCommandResult(
                    handled=True,
                    response=error_envelope(
                        command_id=command_id,
                        code="permission_denied",
                        message="You cannot perform this action.",
                    ),
                )

        updated_markers = await run_blocking(
            self.scenes.delete_board_area_marker,
            scene_id=scene_id,
            marker_id=marker_id,
            **({"expected_board_version": expected_board_version} if expected_board_version is not None else {}),
        )
        if updated_markers is None:
            return _board_conflict(command_id)
        board_version = await self._get_board_version(scene_id)

        broadcast = {
            "room_id": room_id,
            "scene_id": scene_id,
            "marker_id": marker_id,
            "user_id": context.user_id,
        }
        broadcast.update(_board_version_extra(board_version))

        if transport is not None:
            await transport.to_room(
                room_id=room_id,
                event=TransportEvent.BOARD_AREA_MARKER_DELETED,
                payload=broadcast,
            )

        return _ack(
            command_id,
            room_id,
            ClientCommand.BOARD_AREA_MARKER_DELETE.value,
            scene_id,
            extra=_board_version_extra(board_version),
        )

    async def _handle_area_marker_clear(
        self,
        command_id: str | None,
        room_id: str,
        payload: dict[str, Any],
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> BoardCommandResult:
        scene_id = payload.get("scene_id")
        expected_board_version = _expected_board_version(payload)
        if isinstance(expected_board_version, str):
            return _invalid(command_id, expected_board_version)
        if not isinstance(scene_id, str) or not scene_id:
            return _invalid(command_id, "scene_id is required.")

        scene = await run_blocking(self.scenes.get_by_id, scene_id)
        if scene is None:
            return _invalid(command_id, "scene_id was not found.")
        if scene["campaign_id"] != room_id:
            return BoardCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

        is_gm = await self._is_gm(context.user_id, room_id)
        updated = await run_blocking(
            self.scenes.clear_board_area_markers,
            scene_id,
            keep_gm_layer=not is_gm,
            **({"expected_board_version": expected_board_version} if expected_board_version is not None else {}),
        )
        if not updated:
            return _board_conflict(command_id)
        board_version = await self._get_board_version(scene_id)

        broadcast = {
            "room_id": room_id,
            "scene_id": scene_id,
            "user_id": context.user_id,
            "keep_gm_layer": not is_gm,
        }
        broadcast.update(_board_version_extra(board_version))

        if transport is not None:
            await transport.to_room(
                room_id=room_id,
                event=TransportEvent.BOARD_AREA_MARKER_CLEARED,
                payload=broadcast,
            )

        return _ack(
            command_id,
            room_id,
            ClientCommand.BOARD_AREA_MARKER_CLEAR.value,
            scene_id,
            extra=_board_version_extra(board_version),
        )

    async def _handle_draw_upsert(
        self,
        command_id: str | None,
        room_id: str,
        payload: dict[str, Any],
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> BoardCommandResult:
        drawing = payload.get("drawing")
        if not isinstance(drawing, dict):
            return _invalid(command_id, "drawing is required.")
        expected_board_version = _expected_board_version(payload)
        if isinstance(expected_board_version, str):
            return _invalid(command_id, expected_board_version)

        if drawing.get("kind") == "text":
            normalized = _normalize_text(drawing, "drawing")
        else:
            normalized = _normalize_freehand(drawing, "drawing")
        if isinstance(normalized, str):
            return _invalid(command_id, normalized)

        scene = await run_blocking(self.scenes.get_by_id, normalized["scene_id"])
        if scene is None:
            return _invalid(command_id, "scene_id was not found.")
        if scene["campaign_id"] != room_id:
            return BoardCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

        is_gm = await self._is_gm(context.user_id, room_id)
        existing_items = await run_blocking(self.scenes.list_board_area_markers, normalized["scene_id"])
        existing = next(
            (item for item in existing_items if item.get("id") == normalized["id"]), None
        )

                                                                                
                                                                    
        if existing is None:
            own_drawings = sum(
                1
                for item in existing_items
                if self._is_drawing(item) and item.get("owner_id") == context.user_id
            )
            if own_drawings >= config.board_measurements_max_per_user:
                return _limit_reached(command_id, "You have too many drawings on this scene.")

                                                                     
        existing_owner = existing.get("owner_id") if existing is not None else None
        if existing_owner is not None and existing_owner != context.user_id and not is_gm:
            return BoardCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )
        normalized["owner_id"] = existing_owner or context.user_id

                                                                      
        if is_gm and drawing.get("layer") == "gm":
            normalized["layer"] = "gm"

        updated_markers = await run_blocking(
            self.scenes.upsert_board_area_marker,
            scene_id=normalized["scene_id"],
            marker=normalized,
            **({"expected_board_version": expected_board_version} if expected_board_version is not None else {}),
        )
        if updated_markers is None:
            return _board_conflict(command_id)
        board_version = await self._get_board_version(normalized["scene_id"])

        await self._broadcast_layer_aware_upsert(
            transport,
            room_id=room_id,
            scene_id=normalized["scene_id"],
            item=normalized,
            item_id=normalized["id"],
            payload_key="drawing",
            upsert_event=TransportEvent.BOARD_DRAW_UPSERTED,
            user_id=context.user_id,
            board_version=board_version,
        )

        return _ack(
            command_id,
            room_id,
            ClientCommand.BOARD_DRAW_UPSERT.value,
            normalized["scene_id"],
            extra=_board_version_extra(board_version),
        )

    async def _handle_draw_clear(
        self,
        command_id: str | None,
        room_id: str,
        payload: dict[str, Any],
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> BoardCommandResult:
        scene_id = payload.get("scene_id")
        expected_board_version = _expected_board_version(payload)
        if isinstance(expected_board_version, str):
            return _invalid(command_id, expected_board_version)
        if not isinstance(scene_id, str) or not scene_id:
            return _invalid(command_id, "scene_id is required.")

        scene = await run_blocking(self.scenes.get_by_id, scene_id)
        if scene is None:
            return _invalid(command_id, "scene_id was not found.")
        if scene["campaign_id"] != room_id:
            return BoardCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

                                                                            
        owner_filter = None if await self._is_gm(context.user_id, room_id) else context.user_id
        updated_markers = await run_blocking(
            self.scenes.clear_board_drawings,
            scene_id,
            owner_id=owner_filter,
            **({"expected_board_version": expected_board_version} if expected_board_version is not None else {}),
        )
        if updated_markers is None:
            return _board_conflict(command_id)
        board_version = await self._get_board_version(scene_id)

        broadcast = {
            "room_id": room_id,
            "scene_id": scene_id,
            "user_id": context.user_id,
            "owner_id": owner_filter,
        }
        broadcast.update(_board_version_extra(board_version))

        if transport is not None:
            await transport.to_room(
                room_id=room_id,
                event=TransportEvent.BOARD_DRAW_CLEARED,
                payload=broadcast,
            )

        return _ack(
            command_id,
            room_id,
            ClientCommand.BOARD_DRAW_CLEAR.value,
            scene_id,
            extra=_board_version_extra(board_version),
        )

    async def _handle_measure_flash(
        self,
        command_id: str | None,
        room_id: str,
        payload: dict[str, Any],
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> BoardCommandResult:
        measure = payload.get("measure")
        if not isinstance(measure, dict):
            return _invalid(command_id, "measure is required.")

        normalized = _normalize_board_shape(measure, "measure")
        if isinstance(normalized, str):
            return _invalid(command_id, normalized)

        scene = await run_blocking(self.scenes.get_by_id, normalized["scene_id"])
        if scene is None:
            return _invalid(command_id, "scene_id was not found.")
        if scene["campaign_id"] != room_id:
            return BoardCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

        ttl_ms = _normalize_ttl_ms(payload.get("ttl_ms"))
        broadcast = {
            "room_id": room_id,
            "scene_id": normalized["scene_id"],
            "measure": normalized,
            "ttl_ms": ttl_ms,
            "user_id": context.user_id,
        }

        if transport is not None:
            await transport.to_room(
                room_id=room_id,
                event=TransportEvent.BOARD_MEASURE_FLASHED,
                payload=broadcast,
            )

        return _ack(command_id, room_id, ClientCommand.BOARD_MEASURE_FLASH.value, normalized["scene_id"])

    async def _handle_measure_delete(
        self,
        command_id: str | None,
        room_id: str,
        payload: dict[str, Any],
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> BoardCommandResult:
        scene_id = payload.get("scene_id")
        measure_id = payload.get("measure_id")
        if not isinstance(scene_id, str) or not scene_id:
            return _invalid(command_id, "scene_id is required.")
        if not isinstance(measure_id, str) or not measure_id:
            return _invalid(command_id, "measure_id is required.")

        scene = await run_blocking(self.scenes.get_by_id, scene_id)
        if scene is None:
            return _invalid(command_id, "scene_id was not found.")
        if scene["campaign_id"] != room_id:
            return BoardCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

        broadcast = {
            "room_id": room_id,
            "scene_id": scene_id,
            "measure_id": measure_id,
            "user_id": context.user_id,
        }

        if transport is not None:
            await transport.to_room(
                room_id=room_id,
                event=TransportEvent.BOARD_MEASURE_DELETED,
                payload=broadcast,
            )

        return _ack(command_id, room_id, ClientCommand.BOARD_MEASURE_DELETE.value, scene_id)

    async def _handle_measure_clear(
        self,
        command_id: str | None,
        room_id: str,
        payload: dict[str, Any],
        context: ClientCommandContext,
        transport: RealtimeGatewayContract | None,
    ) -> BoardCommandResult:
        scene_id = payload.get("scene_id")
        if not isinstance(scene_id, str) or not scene_id:
            return _invalid(command_id, "scene_id is required.")

        scene = await run_blocking(self.scenes.get_by_id, scene_id)
        if scene is None:
            return _invalid(command_id, "scene_id was not found.")
        if scene["campaign_id"] != room_id:
            return BoardCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

        broadcast = {
            "room_id": room_id,
            "scene_id": scene_id,
            "user_id": context.user_id,
        }

        if transport is not None:
            await transport.to_room(
                room_id=room_id,
                event=TransportEvent.BOARD_MEASURE_CLEARED,
                payload=broadcast,
            )

        return _ack(command_id, room_id, ClientCommand.BOARD_MEASURE_CLEAR.value, scene_id)


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


def _expected_board_version(payload: dict[str, Any]) -> int | str | None:
    value = payload.get("expected_board_version")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return "expected_board_version must be a non-negative integer when provided."
    return value


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


def _normalize_board_shape(raw: dict[str, Any], label: str) -> dict[str, Any] | str:
    shape_id = raw.get("id")
    scene_id = raw.get("scene_id")
    shape = raw.get("shape")
    start = raw.get("start")
    end = raw.get("end")

    if not isinstance(shape_id, str) or not shape_id:
        return f"{label}.id is required."
    if not isinstance(scene_id, str) or not scene_id:
        return f"{label}.scene_id is required."
    if shape not in {"line", "circle", "square", "cone"}:
        return f"{label}.shape must be line, circle, square or cone."
    if not isinstance(start, dict) or not isinstance(end, dict):
        return f"{label}.start and {label}.end are required."

    start_point = _normalize_point(start, f"{label}.start")
    if isinstance(start_point, str):
        return start_point
    end_point = _normalize_point(end, f"{label}.end")
    if isinstance(end_point, str):
        return end_point
    preset = _normalize_preset_id(raw.get("preset_id"), label)
    if isinstance(preset, str):
        return preset

    return {
        "id": shape_id,
        "scene_id": scene_id,
        "shape": shape,
        "start": start_point,
        "end": end_point,
        **preset,
        **_normalize_marker_text(raw.get("text")),
        **_normalize_shape_style(raw.get("style")),
    }


def _normalize_freehand(raw: dict[str, Any], label: str) -> dict[str, Any] | str:
    drawing_id = raw.get("id")
    scene_id = raw.get("scene_id")
    points = raw.get("points")
    if not isinstance(drawing_id, str) or not drawing_id:
        return f"{label}.id is required."
    if not isinstance(scene_id, str) or not scene_id:
        return f"{label}.scene_id is required."
    if not isinstance(points, list) or len(points) < 2 or len(points) > 512:
        return f"{label}.points must contain 2 to 512 points."

    normalized_points: list[dict[str, float]] = []
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            return f"{label}.points[{index}] must be an object."
        normalized = _normalize_point(point, f"{label}.points[{index}]")
        if isinstance(normalized, str):
            return normalized
        normalized_points.append(normalized)

    return {
        "id": drawing_id,
        "scene_id": scene_id,
        "kind": "freehand",
        "points": normalized_points,
        **_normalize_shape_style(raw.get("style")),
    }


def _normalize_text(raw: dict[str, Any], label: str) -> dict[str, Any] | str:
    drawing_id = raw.get("id")
    scene_id = raw.get("scene_id")
    text = raw.get("text")
    position = raw.get("position")
    if not isinstance(drawing_id, str) or not drawing_id:
        return f"{label}.id is required."
    if not isinstance(scene_id, str) or not scene_id:
        return f"{label}.scene_id is required."
    if not isinstance(text, str) or not text.strip():
        return f"{label}.text is required."
    if not isinstance(position, dict):
        return f"{label}.position is required."

    normalized_position = _normalize_point(position, f"{label}.position")
    if isinstance(normalized_position, str):
        return normalized_position

    font_size = raw.get("fontSize")
    if not isinstance(font_size, int | float):
        font_size = 28.0
    font_size = max(8.0, min(200.0, float(font_size)))

    return {
        "id": drawing_id,
        "scene_id": scene_id,
        "kind": "text",
        "position": normalized_position,
        "text": text.strip()[:200],
        "fontSize": font_size,
        **_normalize_shape_style(raw.get("style")),
    }


def _normalize_ttl_ms(raw: Any) -> int:
    if not isinstance(raw, int | float):
        return 6000
    return max(1000, min(60000, int(raw)))


def _normalize_shape_style(raw: Any) -> dict[str, dict[str, str | float]]:
    if not isinstance(raw, dict):
        return {}
    style: dict[str, str | float] = {}
    for key in ("stroke", "fill", "strokeDasharray"):
        value = raw.get(key)
        if isinstance(value, str) and 0 < len(value) <= 64:
            style[key] = value
    stroke_width = raw.get("strokeWidth")
    if isinstance(stroke_width, int | float):
        style["strokeWidth"] = max(1.0, min(12.0, float(stroke_width)))
    return {"style": style} if style else {}


def _normalize_marker_text(raw: Any) -> dict[str, str]:
    if not isinstance(raw, str):
        return {}
    text = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    return {"text": text[:220]} if text else {}


def _normalize_preset_id(raw: Any, label: str) -> dict[str, str] | str:
    if raw is None:
        return {}
    if not isinstance(raw, str):
        return f"{label}.preset_id must be a string."
    preset_id = raw.strip()
    if not preset_id:
        return {}
    if len(preset_id) > 80:
        return f"{label}.preset_id is too long."
    return {"preset_id": preset_id}


def _normalize_point(raw: dict[str, Any], path: str) -> dict[str, float] | str:
    world_x = raw.get("worldX")
    world_y = raw.get("worldY")
    if not isinstance(world_x, int | float) or not isinstance(world_y, int | float):
        return f"{path}.worldX and {path}.worldY are required numbers."
    return {
        "worldX": float(world_x),
        "worldY": float(world_y),
    }


def _invalid(command_id: str | None, message: str) -> BoardCommandResult:
    return BoardCommandResult(
        handled=True,
        response=error_envelope(
            command_id=command_id,
            code="invalid_payload",
            message=message,
        ),
    )
