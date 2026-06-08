from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import time
import uuid
from typing import Any

from litestar import websocket
from litestar.connection import WebSocket
from litestar.exceptions import WebSocketDisconnect

from app.business.campaigns.campaign_service import CampaignService
from app.config import config
from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.command_dispatcher import CommandDispatcher
from app.realtime.board_command_handler import BoardCommandHandler
from app.realtime.commands import ClientCommand
from app.realtime.chunk_outbox import ChunkOutbox
from app.realtime.chunk_outbox import OutboundChunkBatch
from app.realtime.envelopes import error_envelope
from app.realtime.envelopes import event_envelope
from app.realtime.ingress_guard import WebSocketIngressGuard
from app.realtime.ingress_guard import is_origin_allowed
from app.observability.diagnostics import emit_diagnostic
from app.observability.diagnostics import sanitize_metric_name
from app.realtime.metrics import realtime_metrics
from app.realtime.presence import PresenceService
from app.realtime.fog_command_handler import FogCommandHandler
from app.realtime.scene_stream import SceneStreamCommandHandler
from app.realtime.token_command_handler import TokenCommandHandler
from app.realtime.transport import RealtimeTransport
from app.realtime.transport import websocket_manager


@dataclass(frozen=True)
class DispatchObservation:
    handler: str
    response_type: str | None = None
    error_code: str | None = None


def _response_error_code(response: dict[str, Any] | None) -> str | None:
    if not isinstance(response, dict):
        return None
    if response.get("type") == "error" and isinstance(response.get("code"), str):
        return str(response["code"])
    payload = response.get("payload")
    if isinstance(payload, dict) and payload.get("success") is False and isinstance(payload.get("code"), str):
        return str(payload["code"])
    return None


def _response_type(response: dict[str, Any] | None) -> str | None:
    if not isinstance(response, dict):
        return None
    value = response.get("type")
    return str(value) if isinstance(value, str) else None


def _observe_response(handler: str, response: dict[str, Any] | None) -> DispatchObservation:
    return DispatchObservation(
        handler=handler,
        response_type=_response_type(response),
        error_code=_response_error_code(response),
    )


def _command_id(message: dict[str, Any]) -> str | None:
    value = message.get("id")
    return value if isinstance(value, str) and value else None


def _command_name(message: dict[str, Any]) -> str:
    value = message.get("command")
    return value if isinstance(value, str) and value else "unknown"


def _room_id(message: dict[str, Any]) -> str | None:
    value = message.get("room_id")
    return value if isinstance(value, str) and value else None



def _members_by_campaign(
    *,
    members: list[Any],
    online_user_ids_by_room: dict[str, set[str]],
) -> dict[str, list[dict[str, str | bool]]]:
    grouped: dict[str, list[dict[str, str | bool]]] = defaultdict(list)

    for member in members:
        campaign_id = member["campaign_id"]
        grouped[campaign_id].append(
            {
                "user_id": member["user_id"],
                "name": member["name"],
                "email": member["email"],
                "role": member["role"],
                "is_online": member["user_id"] in online_user_ids_by_room.get(campaign_id, set()),
            }
        )

    return grouped


@websocket("/game/ws")
async def game_websocket(
    socket: WebSocket,
    campaign_service: CampaignService,
    presence_service: PresenceService,
) -> None:
    user = socket.scope.get("user")

    if user is None:
        await socket.close(code=1008, reason="Authentication required.")
        return

    origin = socket.headers.get("origin")
    if not is_origin_allowed(origin, config.ws_allowed_origins):
        realtime_metrics.increment("ws.origin.rejected")
        await socket.close(code=1008, reason="Origin not allowed.")
        return

    guard = WebSocketIngressGuard()
    command_dispatcher = CommandDispatcher()
    scene_stream = SceneStreamCommandHandler()
    token_handler = TokenCommandHandler()
    fog_handler = FogCommandHandler()
    board_handler = BoardCommandHandler()
    chunk_outbox = ChunkOutbox()
    transport = RealtimeTransport()

    rooms = campaign_service.list_for_user(user["id"])
    room_ids = [room["id"] for room in rooms]
    command_context = ClientCommandContext(
        user_id=user["id"],
        room_ids=tuple(room_ids),
    )

    await socket.accept()

    connection_id = await websocket_manager.connect(
        user_id=user["id"],
        room_ids=room_ids,
        websocket=socket,
    )
    realtime_metrics.gauge_add("ws.connections.active", 1)

    try:
        await presence_service.touch(
            user_id=user["id"],
            room_ids=room_ids,
            transport=transport,
        )

        members = campaign_service.list_members_for_user_campaigns(user["id"])
        online_user_ids_by_room = await websocket_manager.connected_user_ids_by_room(room_ids)
        members_by_campaign_id = _members_by_campaign(
            members=members,
            online_user_ids_by_room=online_user_ids_by_room,
        )

        for room in rooms:
            await presence_service.send_snapshot(
                player_id=user["id"],
                room_id=room["id"],
                players=members_by_campaign_id[room["id"]],
                transport=transport,
            )

        while True:
            raw = await socket.receive_text()

            decision = guard.inspect(raw)
            if decision.should_close:
                realtime_metrics.increment("ws.ingress.closed")
                emit_diagnostic("ws.ingress.closed", user_id=user["id"], reason=decision.close_reason, code=decision.close_code)
                await socket.close(
                    code=decision.close_code or 1008,
                    reason=decision.close_reason or "",
                )
                return
            if decision.error is not None:
                realtime_metrics.increment("ws.ingress.rejected")
                emit_diagnostic("ws.ingress.rejected", user_id=user["id"], error_code=_response_error_code(decision.error))
                await socket.send_json(decision.error)
                continue

            message = decision.message
            command = _command_name(message)
            command_metric = sanitize_metric_name(command)
            command_id = _command_id(message)
            trace_id = command_id or uuid.uuid4().hex
            room_id = _room_id(message)
            started = time.perf_counter()
            realtime_metrics.increment("ws.command.count")
            realtime_metrics.increment(f"ws.command.{command_metric}.count")
            emit_diagnostic(
                "ws.command.received",
                trace_id=trace_id,
                command_id=command_id,
                command=command,
                room_id=room_id,
                user_id=user["id"],
            )
            try:
                observation = await _dispatch_message(
                    socket=socket,
                    message=message,
                    command_context=command_context,
                    scene_stream=scene_stream,
                    token_handler=token_handler,
                    fog_handler=fog_handler,
                    board_handler=board_handler,
                    command_dispatcher=command_dispatcher,
                    chunk_outbox=chunk_outbox,
                    transport=transport,
                )
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                realtime_metrics.observe("ws.command.duration_ms", elapsed_ms)
                realtime_metrics.observe(f"ws.command.{command_metric}.duration_ms", elapsed_ms)
                if observation.error_code:
                    error_metric = sanitize_metric_name(observation.error_code)
                    realtime_metrics.increment("ws.command.error_response")
                    realtime_metrics.increment(f"ws.command.error_response.{error_metric}")
                    if observation.error_code in {"version_conflict", "board_version_conflict"}:
                        realtime_metrics.increment("ws.command.cas_conflict")
                        realtime_metrics.increment(f"ws.command.{command_metric}.cas_conflict")
                emit_diagnostic(
                    "ws.command.completed",
                    trace_id=trace_id,
                    command_id=command_id,
                    command=command,
                    room_id=room_id,
                    user_id=user["id"],
                    handler=observation.handler,
                    response_type=observation.response_type,
                    error_code=observation.error_code,
                    duration_ms=round(elapsed_ms, 3),
                )
            except WebSocketDisconnect:
                raise
            except Exception as exc:                                                          
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                realtime_metrics.increment("ws.command.error")
                realtime_metrics.increment(f"ws.command.{command_metric}.error")
                realtime_metrics.observe("ws.command.duration_ms", elapsed_ms)
                emit_diagnostic(
                    "ws.command.failed",
                    level="exception",
                    trace_id=trace_id,
                    command_id=command_id,
                    command=command,
                    room_id=room_id,
                    user_id=user["id"],
                    duration_ms=round(elapsed_ms, 3),
                    exception=exc.__class__.__name__,
                )
                await socket.send_json(
                    error_envelope(
                        command_id=command_id,
                        code="server_error",
                        message="The command could not be processed.",
                    )
                )

    except WebSocketDisconnect:
        pass
    finally:
        await websocket_manager.disconnect(connection_id)
        realtime_metrics.gauge_add("ws.connections.active", -1)

        if not await websocket_manager.is_user_connected(user["id"]):
            await presence_service.leave(
                user_id=user["id"],
                room_ids=room_ids,
                transport=transport,
            )


async def _dispatch_message(
    *,
    socket: WebSocket,
    message: dict[str, Any],
    command_context: ClientCommandContext,
    scene_stream: SceneStreamCommandHandler,
    token_handler: TokenCommandHandler,
    fog_handler: FogCommandHandler,
    board_handler: BoardCommandHandler,
    command_dispatcher: CommandDispatcher,
    chunk_outbox: ChunkOutbox,
    transport: RealtimeTransport,
) -> DispatchObservation:
    if await _handle_chunk_ack_commands(socket, message, chunk_outbox):
        await _flush_chunk_outbox(socket, chunk_outbox)
        return DispatchObservation(handler="chunk_ack")

    stream_response = await scene_stream.handle(
        message,
        context=command_context,
    )

    if stream_response.handled:
        if stream_response.response is not None:
            await socket.send_json(stream_response.response)
        for batch_id, frame in stream_response.binary_batches:
            accepted = chunk_outbox.enqueue(
                OutboundChunkBatch(
                    batch_id=batch_id,
                    frame=frame,
                    priority=stream_response.batch_priority_by_id.get(batch_id, 1),
                )
            )
            if not accepted:
                await socket.send_json(
                    event_envelope(
                        event="scene.stream.throttle",
                        payload={
                            "batch_id": batch_id,
                            "reason": "outbox_limit",
                            "outbox": chunk_outbox.stats().__dict__,
                        },
                    )
                )
            else:
                realtime_metrics.increment("ws.outbox.bytes", len(frame))
        await _flush_chunk_outbox(socket, chunk_outbox)
        return _observe_response("scene_stream", stream_response.response)

    token_response = await token_handler.handle(
        message,
        context=command_context,
        transport=transport,
    )
    if token_response.handled:
        if token_response.response is not None:
            await socket.send_json(token_response.response)
        return _observe_response("token", token_response.response)

    fog_response = await fog_handler.handle(
        message,
        context=command_context,
        transport=transport,
    )
    if fog_response.handled:
        if fog_response.response is not None:
            await socket.send_json(fog_response.response)
        return _observe_response("fog", fog_response.response)

    board_response = await board_handler.handle(
        message,
        context=command_context,
        transport=transport,
    )
    if board_response.handled:
        if board_response.response is not None:
            await socket.send_json(board_response.response)
        return _observe_response("board", board_response.response)

    response = await command_dispatcher.dispatch(
        message,
        context=command_context,
    )
    await socket.send_json(response)
    return _observe_response("dispatcher", response)


async def _flush_chunk_outbox(socket: WebSocket, outbox: ChunkOutbox) -> None:
    for ready in outbox.ready_to_send():
        await socket.send_bytes(ready.frame)


async def _handle_chunk_ack_commands(
    socket: WebSocket,
    message: object,
    outbox: ChunkOutbox,
) -> bool:
    if not isinstance(message, dict):
        return False

    command = message.get("command")
    if command not in {ClientCommand.CHUNK_ACK.value, ClientCommand.CHUNK_NACK.value}:
        return False

    command_id = message.get("id") if isinstance(message.get("id"), str) else None
    payload = message.get("payload", {})
    if not isinstance(payload, dict):
        await socket.send_json(
            error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="Command payload must be an object.",
            )
        )
        return True

    batch_id = payload.get("batch_id")
    if not isinstance(batch_id, str) or not batch_id:
        await socket.send_json(
            error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="batch_id is required.",
            )
        )
        return True

    if command == ClientCommand.CHUNK_ACK.value:
        accepted = outbox.ack(batch_id)
        realtime_metrics.increment("chunk.ack.count")
    else:
        accepted = outbox.nack(batch_id)
        realtime_metrics.increment("chunk.nack.count")
        if accepted:
            realtime_metrics.increment("chunk.nack.requeued")
        else:
            realtime_metrics.increment("chunk.nack.unknown_batch")

    await socket.send_json(
        event_envelope(
            event="scene.chunk.acknowledged",
            payload={
                "command_id": command_id,
                "batch_id": batch_id,
                "accepted": accepted,
                "outbox": outbox.stats().__dict__,
            },
        )
    )
    return True
