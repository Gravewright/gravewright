from __future__ import annotations

import pytest

from app.domain.roles import PlayerRole
from app.domain.scenes import SceneChunkEncoding
from app.domain.scenes import SceneLayerKind
from app.domain.scenes import SceneLayerVisibility
from app.engine.scenes.scene_chunk_service import SceneChunkService
from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.chunk_outbox import ChunkOutbox
from app.realtime.chunk_outbox import OutboundChunkBatch
from app.realtime.scene_stream import SceneStreamCommandHandler
from app.realtime.events import TransportEvent
from app.realtime.metrics import RealtimeMetrics
from app.realtime.viewport_subscriptions import ViewportSubscriptionService
from app.realtime.chunk_batch_encoder import decode_chunk_batch_frame
from app.actions.game.websocket import _handle_chunk_ack_commands
from tests.conftest import seed_campaign
from tests.conftest import seed_member
from tests.conftest import seed_user


def create_scene_stack(db):
    gm_id = seed_user(name="GM", email="stream-gm@test.com")
    player_id = seed_user(name="Player", email="stream-player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    scene = SceneRepository().create(
        campaign_id=campaign_id,
        name="Warehouse",
        width=1400,
        height=1400,
        tile_size=70,
        chunk_size=16,
    )
    layer = SceneLayerRepository().create(
        scene_id=scene["id"],
        name="Ground",
        kind=SceneLayerKind.RASTER_TILE_REFS,
        visibility=SceneLayerVisibility.VISIBLE,
        display_order=0,
        encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
    )

    return campaign_id, gm_id, player_id, scene, layer


def make_handler(
    tmp_path,
    *,
    max_batch_bytes: int | None = None,
    metrics: RealtimeMetrics | None = None,
):
    chunk_service = SceneChunkService(
        storage=LocalChunkStorage(root=tmp_path / "scenes"),
    )
    subscriptions = ViewportSubscriptionService(chunk_service=chunk_service)
    handler_kwargs = {"subscriptions": subscriptions}
    if metrics is not None:
        handler_kwargs["metrics"] = metrics
    if max_batch_bytes is not None:
        handler_kwargs["max_batch_bytes"] = max_batch_bytes
    return chunk_service, SceneStreamCommandHandler(**handler_kwargs)


class FakeSocket:
    def __init__(self):
        self.json_messages = []

    async def send_json(self, message):
        self.json_messages.append(message)


class FakeRequest:
    headers = {"accept": "application/json"}


@pytest.mark.asyncio
async def test_scene_stream_viewport_subscribe_returns_json_ack_and_binary_batch(db, tmp_path):
    campaign_id, gm_id, player_id, scene, layer = create_scene_stack(db)
    chunk_service, handler = make_handler(tmp_path)
    await chunk_service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=b"chunk-data",
        user_id=gm_id,
    )
    SceneRepository().upsert_board_area_marker(
        scene_id=scene["id"],
        marker={
            "id": "marker-1",
            "scene_id": scene["id"],
            "shape": "line",
            "start": {"worldX": 10, "worldY": 20},
            "end": {"worldX": 30, "worldY": 20},
        },
    )

    result = await handler.handle(
        {
            "type": "command",
            "id": "cmd-1",
            "command": "viewport.subscribe",
            "scene_id": scene["id"],
            "payload": {
                "viewport_id": "main",
                "generation": 1,
                "layers": [layer["id"]],
                "cx0": 0,
                "cy0": 0,
                "cx1": 0,
                "cy1": 0,
                "known": {},
            },
        },
        context=ClientCommandContext(user_id=player_id, room_ids=(campaign_id,)),
    )

    assert result.handled
    assert result.response["event"] == "scene.viewport.ready"
    assert result.response["payload"]["command_id"] == "cmd-1"
    assert result.response["payload"]["chunk_count"] == 1
    assert result.response["payload"]["batch_count"] == 1
    assert result.response["payload"]["board_area_markers"] == [
        {
            "id": "marker-1",
            "scene_id": scene["id"],
            "shape": "line",
            "start": {"worldX": 10.0, "worldY": 20.0},
            "end": {"worldX": 30.0, "worldY": 20.0},
        }
    ]
    assert len(result.binary_batches) == 1

    batch_id, encoded_frame = result.binary_batches[0]
    frame = decode_chunk_batch_frame(encoded_frame)
    assert batch_id == frame.batch_id
    assert result.response["payload"]["batch_id"] == batch_id
    assert result.response["payload"]["batch_ids"] == [batch_id]
    assert frame.scene_id == scene["id"]
    assert frame.viewport_id == "main"
    assert frame.viewport_generation == 1
    assert [(chunk.layer_id, chunk.cx, chunk.cy, chunk.data) for chunk in frame.chunks] == [
        (layer["id"], 0, 0, b"chunk-data")
    ]


@pytest.mark.asyncio
async def test_scene_stream_filters_gm_layer_markers_for_players(db, tmp_path):
    campaign_id, gm_id, player_id, scene, layer = create_scene_stack(db)
    _chunk_service, handler = make_handler(tmp_path)
    repo = SceneRepository()
    repo.upsert_board_area_marker(
        scene_id=scene["id"],
        marker={
            "id": "marker-game",
            "scene_id": scene["id"],
            "shape": "line",
            "start": {"worldX": 1, "worldY": 1},
            "end": {"worldX": 2, "worldY": 2},
        },
    )
    repo.upsert_board_area_marker(
        scene_id=scene["id"],
        marker={
            "id": "marker-gm",
            "scene_id": scene["id"],
            "shape": "line",
            "layer": "gm",
            "start": {"worldX": 3, "worldY": 3},
            "end": {"worldX": 4, "worldY": 4},
        },
    )

    def subscribe(user_id):
        return handler.handle(
            {
                "type": "command",
                "id": "cmd-1",
                "command": "viewport.subscribe",
                "scene_id": scene["id"],
                "payload": {
                    "viewport_id": "main",
                    "generation": 1,
                    "layers": [layer["id"]],
                    "cx0": 0,
                    "cy0": 0,
                    "cx1": 0,
                    "cy1": 0,
                    "known": {},
                },
            },
            context=ClientCommandContext(user_id=user_id, room_ids=(campaign_id,)),
        )

    player_result = await subscribe(player_id)
    player_ids = [m["id"] for m in player_result.response["payload"]["board_area_markers"]]
    assert player_ids == ["marker-game"]

    gm_result = await subscribe(gm_id)
    gm_ids = sorted(m["id"] for m in gm_result.response["payload"]["board_area_markers"])
    assert gm_ids == ["marker-game", "marker-gm"]


@pytest.mark.asyncio
async def test_scene_stream_session_resume_with_current_epoch_returns_missing_chunks(
    db, tmp_path
):
    campaign_id, gm_id, player_id, scene, layer = create_scene_stack(db)
    chunk_service, handler = make_handler(tmp_path)
    await chunk_service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=b"resume-chunk",
        user_id=gm_id,
    )

    result = await handler.handle(
        {
            "type": "command",
            "id": "resume-1",
            "command": "session.resume",
            "payload": {
                "active_scene_id": scene["id"],
                "scene_epoch": scene["scene_epoch"],
                "last_event_seq": 0,
                "viewport": {
                    "viewport_id": "main",
                    "generation": 2,
                    "layers": [layer["id"]],
                    "cx0": 0,
                    "cy0": 0,
                    "cx1": 0,
                    "cy1": 0,
                },
                "known_chunks": {},
            },
        },
        context=ClientCommandContext(user_id=player_id, room_ids=(campaign_id,)),
    )

    assert result.handled
    assert result.response["event"] == "scene.session.resumed"
    assert result.response["payload"]["resume_ok"] is True
    assert result.response["payload"]["resync_required"] is False
    assert result.response["payload"]["chunk_count"] == 1
    assert len(result.binary_batches) == 1

    frame = decode_chunk_batch_frame(result.binary_batches[0][1])
    assert frame.scene_epoch == scene["scene_epoch"]
    assert frame.viewport_generation == 2
    assert [(chunk.layer_id, chunk.cx, chunk.cy, chunk.data) for chunk in frame.chunks] == [
        (layer["id"], 0, 0, b"resume-chunk")
    ]


@pytest.mark.asyncio
async def test_scene_stream_session_resume_requests_resync_when_epoch_changed(db, tmp_path):
    campaign_id, _gm_id, player_id, scene, _layer = create_scene_stack(db)
    _chunk_service, handler = make_handler(tmp_path)

    result = await handler.handle(
        {
            "type": "command",
            "id": "resume-1",
            "command": "session.resume",
            "payload": {
                "active_scene_id": scene["id"],
                "scene_epoch": scene["scene_epoch"] - 1,
                "last_event_seq": 0,
                "viewport": {
                    "viewport_id": "main",
                    "generation": 2,
                    "layers": [],
                    "cx0": 0,
                    "cy0": 0,
                    "cx1": 0,
                    "cy1": 0,
                },
                "known_chunks": {},
            },
        },
        context=ClientCommandContext(user_id=player_id, room_ids=(campaign_id,)),
    )

    assert result.handled
    assert result.binary_batches == ()
    assert result.response["event"] == "scene.session.resumed"
    assert result.response["payload"] == {
        "command_id": "resume-1",
        "resume_ok": True,
        "resync_required": True,
        "reason": "scene_epoch_changed",
        "scene_id": scene["id"],
        "scene_epoch": scene["scene_epoch"],
        "client_scene_epoch": scene["scene_epoch"] - 1,
    }


@pytest.mark.asyncio
async def test_scene_stream_session_resume_replays_room_events_after_sequence(db, tmp_path):
    campaign_id, gm_id, player_id, scene, layer = create_scene_stack(db)
    chunk_service, handler = make_handler(tmp_path)
    first_seq = handler.event_log.append(
        room_id=campaign_id,
        event=TransportEvent.SCENE_ACTIVATED,
        payload={"room_id": campaign_id, "scene_id": scene["id"]},
    )
    second_seq = handler.event_log.append(
        room_id=campaign_id,
        event=TransportEvent.SCENE_CHUNK_UPDATED,
        payload={
            "room_id": campaign_id,
            "scene_id": scene["id"],
            "layer_id": layer["id"],
            "cx": 0,
            "cy": 0,
            "version": 7,
        },
    )
    await chunk_service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=b"event-log-chunk",
        user_id=gm_id,
    )

    result = await handler.handle(
        {
            "type": "command",
            "id": "resume-2",
            "command": "session.resume",
            "payload": {
                "active_scene_id": scene["id"],
                "scene_epoch": scene["scene_epoch"],
                "last_event_seq": first_seq,
                "viewport": {
                    "viewport_id": "main",
                    "generation": 3,
                    "layers": [layer["id"]],
                    "cx0": 0,
                    "cy0": 0,
                    "cx1": 0,
                    "cy1": 0,
                },
                "known_chunks": {},
            },
        },
        context=ClientCommandContext(user_id=player_id, room_ids=(campaign_id,)),
    )

    assert result.handled
    assert result.response["payload"]["event_log"] == {
        "expired": False,
        "latest_seq": second_seq,
        "replayed_count": 1,
    }
    assert result.response["payload"]["events"][0]["event_seq"] == second_seq
    assert result.response["payload"]["events"][0]["event"] == (
        TransportEvent.SCENE_CHUNK_UPDATED.value
    )


@pytest.mark.asyncio
async def test_scene_stream_splits_large_viewport_into_multiple_binary_batches(db, tmp_path):
    campaign_id, gm_id, player_id, scene, layer = create_scene_stack(db)
    chunk_service, handler = make_handler(tmp_path, max_batch_bytes=700)

    for cx in range(3):
        await chunk_service.write_chunk(
            scene_id=scene["id"],
            layer_id=layer["id"],
            cx=cx,
            cy=0,
            data=b"x" * 20,
            user_id=gm_id,
        )

    result = await handler.handle(
        {
            "type": "command",
            "id": "cmd-1",
            "command": "viewport.subscribe",
            "scene_id": scene["id"],
            "payload": {
                "viewport_id": "main",
                "generation": 1,
                "layers": [layer["id"]],
                "cx0": 0,
                "cy0": 0,
                "cx1": 2,
                "cy1": 0,
                "known": {},
            },
        },
        context=ClientCommandContext(user_id=player_id, room_ids=(campaign_id,)),
    )

    assert result.handled
    assert result.response["payload"]["chunk_count"] == 3
    assert result.response["payload"]["batch_count"] > 1
    assert result.response["payload"]["batch_ids"] == [
        batch_id for batch_id, _frame in result.binary_batches
    ]
    assert all(len(frame) <= 700 for _batch_id, frame in result.binary_batches)

    decoded_chunks = [
        (chunk.cx, chunk.cy, chunk.data)
        for _batch_id, encoded_frame in result.binary_batches
        for chunk in decode_chunk_batch_frame(encoded_frame).chunks
    ]
                                                                          
    assert decoded_chunks == [
        (1, 0, b"x" * 20),
        (0, 0, b"x" * 20),
        (2, 0, b"x" * 20),
    ]


@pytest.mark.asyncio
async def test_scene_stream_orders_center_chunks_before_edge_chunks(db, tmp_path):
    campaign_id, gm_id, player_id, scene, layer = create_scene_stack(db)
    chunk_service, handler = make_handler(tmp_path)

    for cx in range(5):
        await chunk_service.write_chunk(
            scene_id=scene["id"],
            layer_id=layer["id"],
            cx=cx,
            cy=0,
            data=bytes([cx]) * 8,
            user_id=gm_id,
        )

    result = await handler.handle(
        {
            "type": "command",
            "id": "cmd-1",
            "command": "viewport.subscribe",
            "scene_id": scene["id"],
            "payload": {
                "viewport_id": "main",
                "generation": 1,
                "layers": [layer["id"]],
                "cx0": 0,
                "cy0": 0,
                "cx1": 4,
                "cy1": 0,
                "known": {},
            },
        },
        context=ClientCommandContext(user_id=player_id, room_ids=(campaign_id,)),
    )

    assert result.handled
    assert result.response["payload"]["chunk_count"] == 5

    sent_cx = [
        chunk.cx
        for _batch_id, encoded_frame in result.binary_batches
        for chunk in decode_chunk_batch_frame(encoded_frame).chunks
    ]
                                                                                 
                                                                  
    assert sent_cx == [2, 1, 3, 0, 4]


@pytest.mark.asyncio
async def test_scene_stream_assigns_batch_priority_from_best_chunk(db, tmp_path):
    campaign_id, gm_id, player_id, scene, layer = create_scene_stack(db)
    chunk_service, handler = make_handler(tmp_path)
    await chunk_service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=b"center",
        user_id=gm_id,
    )

    result = await handler.handle(
        {
            "type": "command",
            "id": "cmd-1",
            "command": "viewport.subscribe",
            "scene_id": scene["id"],
            "payload": {
                "viewport_id": "main",
                "generation": 1,
                "layers": [layer["id"]],
                "cx0": 0,
                "cy0": 0,
                "cx1": 0,
                "cy1": 0,
                "known": {},
            },
        },
        context=ClientCommandContext(user_id=player_id, room_ids=(campaign_id,)),
    )

    from app.domain.scenes import RenderPriority

    batch_id = result.binary_batches[0][0]
    assert result.batch_priority_by_id[batch_id] == int(RenderPriority.HIGH)


@pytest.mark.asyncio
async def test_scene_stream_records_chunk_stream_metrics(db, tmp_path):
    campaign_id, gm_id, player_id, scene, layer = create_scene_stack(db)
    metrics = RealtimeMetrics()
    chunk_service, handler = make_handler(tmp_path, metrics=metrics)
    await chunk_service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=b"metric-chunk",
        user_id=gm_id,
    )

    await handler.handle(
        {
            "type": "command",
            "id": "cmd-1",
            "command": "viewport.subscribe",
            "scene_id": scene["id"],
            "payload": {
                "viewport_id": "main",
                "generation": 1,
                "layers": [layer["id"]],
                "cx0": 0,
                "cy0": 0,
                "cx1": 0,
                "cy1": 0,
                "known": {},
            },
        },
        context=ClientCommandContext(user_id=player_id, room_ids=(campaign_id,)),
    )

    snapshot = metrics.snapshot()
    assert snapshot["counters"]["viewport.subscribe.count"] == 1
    assert snapshot["counters"]["chunk.request.missing"] == 1
    assert snapshot["counters"]["chunk.batch.count"] == 1
    assert snapshot["counters"]["chunk.batch.bytes"] > 0
    assert snapshot["histograms"]["chunk.batch.p95_ms"]["count"] == 1


@pytest.mark.asyncio
async def test_scene_stream_ignores_non_stream_commands(db, tmp_path):
    _campaign_id, _gm_id, player_id, _scene, _layer = create_scene_stack(db)
    _chunk_service, handler = make_handler(tmp_path)

    result = await handler.handle(
        {
            "type": "command",
            "id": "cmd-1",
            "command": "ping",
            "payload": {},
        },
        context=ClientCommandContext(user_id=player_id, room_ids=()),
    )

    assert not result.handled


@pytest.mark.asyncio
async def test_scene_stream_rejects_scene_outside_connection_rooms(db, tmp_path):
    _campaign_id, _gm_id, player_id, scene, layer = create_scene_stack(db)
    _chunk_service, handler = make_handler(tmp_path)

    result = await handler.handle(
        {
            "type": "command",
            "id": "cmd-1",
            "command": "viewport.update",
            "scene_id": scene["id"],
            "payload": {
                "viewport_id": "main",
                "generation": 1,
                "layers": [layer["id"]],
                "cx0": 0,
                "cy0": 0,
                "cx1": 0,
                "cy1": 0,
                "known": {},
            },
        },
        context=ClientCommandContext(user_id=player_id, room_ids=("other-room",)),
    )

    assert result.handled
    assert result.response["type"] == "error"
    assert result.response["code"] == "permission_denied"


@pytest.mark.asyncio
async def test_chunk_ack_command_releases_outbox_inflight():
    outbox = ChunkOutbox(max_batch_bytes=20, max_inflight_batches=1, max_queue_bytes=100)
    socket = FakeSocket()
    outbox.enqueue(OutboundChunkBatch(batch_id="batch-1", frame=b"1234"))
    assert outbox.ready_to_send()[0].batch_id == "batch-1"

    handled = await _handle_chunk_ack_commands(
        socket,
        {
            "type": "command",
            "id": "ack-1",
            "command": "chunk.ack",
            "payload": {"batch_id": "batch-1", "applied": True},
        },
        outbox,
    )

    assert handled
    assert outbox.stats().inflight_batches == 0
    assert socket.json_messages[-1]["event"] == "scene.chunk.acknowledged"
    assert socket.json_messages[-1]["payload"]["accepted"] is True


@pytest.mark.asyncio
async def test_chunk_nack_command_requeues_outbox_batch():
    outbox = ChunkOutbox(max_batch_bytes=20, max_inflight_batches=1, max_queue_bytes=100)
    socket = FakeSocket()
    outbox.enqueue(OutboundChunkBatch(batch_id="batch-1", frame=b"1234"))
    assert outbox.ready_to_send()[0].batch_id == "batch-1"

    handled = await _handle_chunk_ack_commands(
        socket,
        {
            "type": "command",
            "id": "nack-1",
            "command": "chunk.nack",
            "payload": {"batch_id": "batch-1", "reason": "decode_failed"},
        },
        outbox,
    )

    assert handled
    assert outbox.stats().queued_batches == 1
    assert socket.json_messages[-1]["payload"]["accepted"] is True
