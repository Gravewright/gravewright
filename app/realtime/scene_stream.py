from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from app.config import config
from app.helpers.async_blocking import run_blocking
from app.domain.scenes import RenderPriority
from app.engine.scenes.render_scheduler import RenderPriorityScheduler
from app.engine.scenes.render_scheduler import SchedulerBudget
from app.realtime.chunk_batch_encoder import ChunkBatchFrame
from app.realtime.chunk_batch_encoder import ChunkBatchItem
from app.realtime.chunk_batch_encoder import encode_chunk_batch_frame
from app.realtime.chunk_outbox import DEFAULT_MAX_BATCH_BYTES
from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.commands import ClientCommand
from app.realtime.envelopes import error_envelope
from app.realtime.envelopes import event_envelope
from app.realtime.event_log import RoomEventLog
from app.realtime.metrics import RealtimeMetrics
from app.realtime.metrics import realtime_metrics
from app.realtime.viewport_subscriptions import ViewportChunkPayload
from app.realtime.viewport_subscriptions import ViewportSubscriptionService
from app.persistence.repositories.campaign_repository import CampaignRepository

                                                                           
                                                                               
_DEFAULT_DRAIN_MAX_ITEMS = 128
_DEFAULT_DRAIN_MAX_COST = 512
                                                                   
_CHUNK_JOB_TTL_MS = 10_000
_CHUNK_JOB_KIND = "scene-chunk"

                                                                                   
_GM_ROLES = {"gm", "assistant_gm"}

                                                                              
                                                                              
                                                                           
                                                                  
                                                                       
_MAX_VIEWPORT_ID_LEN = 128
_MAX_VIEWPORT_WIDTH_CHUNKS = config.scene_viewport_max_width_chunks
_MAX_VIEWPORT_HEIGHT_CHUNKS = config.scene_viewport_max_height_chunks
                                                                         
_MAX_VIEWPORT_CHUNK_AREA = config.scene_viewport_max_area_chunks
_MAX_VIEWPORT_LAYERS = config.scene_viewport_max_layers
                                                                           
_MAX_KNOWN_CHUNKS = config.scene_viewport_max_known_chunks


@dataclass(frozen=True)
class SceneStreamCommandResult:
    handled: bool
    response: dict[str, Any] | None = None
    binary_batches: tuple[tuple[str, bytes], ...] = ()
    batch_priority_by_id: Mapping[str, int] = field(default_factory=dict)


class SceneStreamCommandHandler:
    def __init__(
        self,
        *,
        subscriptions: ViewportSubscriptionService | None = None,
        event_log: RoomEventLog | None = None,
        metrics: RealtimeMetrics | None = None,
        campaigns: CampaignRepository | None = None,
        scheduler: RenderPriorityScheduler | None = None,
        max_batch_bytes: int = DEFAULT_MAX_BATCH_BYTES,
    ) -> None:
        if max_batch_bytes <= 0:
            raise ValueError("max_batch_bytes must be positive")

        self.subscriptions = subscriptions or ViewportSubscriptionService()
        self.event_log = event_log or RoomEventLog()
        self.metrics = metrics or realtime_metrics
        self.campaigns = campaigns or CampaignRepository()
                                                                                
                                                                          
        self.scheduler = scheduler or RenderPriorityScheduler()
        self.max_batch_bytes = max_batch_bytes

    def _visible_board_markers(
        self,
        *,
        scene_id: str,
        campaign_id: str,
        user_id: str,
    ) -> list[dict[str, Any]]:
        markers = self.subscriptions.scenes.list_board_area_markers(scene_id)
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if role in _GM_ROLES:
            return markers
        return [marker for marker in markers if marker.get("layer") != "gm"]

    async def handle(
        self,
        message: Any,
        *,
        context: ClientCommandContext,
    ) -> SceneStreamCommandResult:
        if not isinstance(message, dict):
            return SceneStreamCommandResult(handled=False)

        command = message.get("command")
        if command not in {
            ClientCommand.VIEWPORT_SUBSCRIBE.value,
            ClientCommand.VIEWPORT_UPDATE.value,
            ClientCommand.SESSION_RESUME.value,
        }:
            return SceneStreamCommandResult(handled=False)

        command_id = message.get("id") if isinstance(message.get("id"), str) else None
        payload = message.get("payload", {})
        if not isinstance(payload, dict):
            return SceneStreamCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="invalid_payload",
                    message="Command payload must be an object.",
                ),
            )

        if command == ClientCommand.SESSION_RESUME.value:
            return await self._handle_session_resume(
                payload=payload,
                command_id=command_id,
                context=context,
            )

        if command == ClientCommand.VIEWPORT_SUBSCRIBE.value:
            self.metrics.increment("viewport.subscribe.count")
        elif command == ClientCommand.VIEWPORT_UPDATE.value:
            self.metrics.increment("viewport.update.rate")

        parsed = self._parse_payload(message=message, payload=payload, command_id=command_id)
        if parsed.get("type") == "error":
            return SceneStreamCommandResult(handled=True, response=parsed)

        scene_id = parsed["scene_id"]
        scene = await run_blocking(self.subscriptions.scenes.get_by_id, scene_id)
        if scene is None:
            return SceneStreamCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="scene_not_found",
                    message="Scene not found.",
                ),
            )

        if scene["campaign_id"] not in context.room_ids:
            return SceneStreamCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

        return await self._resolve_viewport(
            event="scene.viewport.ready",
            user_id=context.user_id,
            scene=scene,
            scene_id=scene_id,
            parsed=parsed,
            command_id=command_id,
        )

    async def _handle_session_resume(
        self,
        *,
        payload: dict[str, Any],
        command_id: str | None,
        context: ClientCommandContext,
    ) -> SceneStreamCommandResult:
        scene_id = payload.get("active_scene_id") or payload.get("scene_id")
        client_scene_epoch = payload.get("scene_epoch")
        last_event_seq = payload.get("last_event_seq", 0)
        viewport = payload.get("viewport")
        known_chunks = payload.get("known_chunks", {})

        if not isinstance(scene_id, str) or not scene_id:
            return SceneStreamCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="invalid_payload",
                    message="active_scene_id is required.",
                ),
            )

        if not isinstance(client_scene_epoch, int) or client_scene_epoch < 0:
            return SceneStreamCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="invalid_payload",
                    message="scene_epoch must be zero or positive.",
                ),
            )

        if not isinstance(last_event_seq, int) or last_event_seq < 0:
            return SceneStreamCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="invalid_payload",
                    message="last_event_seq must be zero or positive.",
                ),
            )

        if not isinstance(viewport, dict):
            return SceneStreamCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="invalid_payload",
                    message="viewport is required.",
                ),
            )

        if not isinstance(known_chunks, dict):
            return SceneStreamCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="invalid_payload",
                    message="known_chunks must map chunk keys to versions.",
                ),
            )

        scene = await run_blocking(self.subscriptions.scenes.get_by_id, scene_id)
        if scene is None:
            return SceneStreamCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="scene_not_found",
                    message="Scene not found.",
                ),
            )

        if scene["campaign_id"] not in context.room_ids:
            return SceneStreamCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code="permission_denied",
                    message="You cannot perform this action.",
                ),
            )

        server_scene_epoch = scene["scene_epoch"]
        if client_scene_epoch != server_scene_epoch:
            self.metrics.increment("ws.resume.success")
            self.metrics.increment("ws.resume.resync_required")
            self.metrics.increment("scene_epoch.mismatch")
            return SceneStreamCommandResult(
                handled=True,
                response=event_envelope(
                    event="scene.session.resumed",
                    room_id=scene["campaign_id"],
                    payload={
                        "command_id": command_id,
                        "resume_ok": True,
                        "resync_required": True,
                        "reason": "scene_epoch_changed",
                        "scene_id": scene_id,
                        "scene_epoch": server_scene_epoch,
                        "client_scene_epoch": client_scene_epoch,
                    },
                ),
            )

        parsed = self._parse_payload(
            message={"scene_id": scene_id},
            payload={**viewport, "known": known_chunks},
            command_id=command_id,
        )
        if parsed.get("type") == "error":
            return SceneStreamCommandResult(handled=True, response=parsed)

        replay = await run_blocking(
            self.event_log.replay_since,
            room_id=scene["campaign_id"],
            after_seq=last_event_seq,
        )
        self.metrics.increment("ws.resume.success")
        self.metrics.increment("event_log.replay.count", len(replay.events))
        if replay.expired:
            self.metrics.increment("event_log.snapshot_fallback.count")

        return await self._resolve_viewport(
            event="scene.session.resumed",
            user_id=context.user_id,
            scene=scene,
            scene_id=scene_id,
            parsed=parsed,
            command_id=command_id,
            extra_payload={
                "resume_ok": True,
                "resync_required": False,
                "events": list(replay.events),
                "event_log": {
                    "expired": replay.expired,
                    "latest_seq": replay.latest_seq,
                    "replayed_count": len(replay.events),
                },
            },
        )

    async def _resolve_viewport(
        self,
        *,
        event: str,
        user_id: str,
        scene: dict[str, Any],
        scene_id: str,
        parsed: dict[str, Any],
        command_id: str | None,
        extra_payload: dict[str, Any] | None = None,
    ) -> SceneStreamCommandResult:
        started_at = time.perf_counter()
        now_ms = int(time.time() * 1000)
        viewport_id = parsed["viewport_id"]
        viewport_generation = parsed["viewport_generation"]

        candidate_result = await run_blocking(
            self.subscriptions.resolve_viewport_chunk_candidates,
            user_id=user_id,
            scene_id=scene_id,
            viewport_id=viewport_id,
            viewport_generation=viewport_generation,
            cx0=parsed["cx0"],
            cy0=parsed["cy0"],
            cx1=parsed["cx1"],
            cy1=parsed["cy1"],
            layer_ids=parsed["layer_ids"],
            known_chunks=parsed["known_chunks"],
            focus_cx=parsed["focus_cx"],
            focus_cy=parsed["focus_cy"],
        )

        if not candidate_result.success:
            return SceneStreamCommandResult(
                handled=True,
                response=error_envelope(
                    command_id=command_id,
                    code=candidate_result.error_key or "stream_error",
                    message="Could not resolve viewport chunks.",
                ),
            )

        scene_epoch = candidate_result.scene_epoch or scene["scene_epoch"]

                                                                               
                                                                   
        self.scheduler.cancel_scope(
            scene_id=scene_id,
            viewport_id=viewport_id,
            older_than_viewport_generation=viewport_generation,
            kind=_CHUNK_JOB_KIND,
        )
        self.scheduler.cancel_scope(
            scene_id=scene_id,
            scene_epoch_not=scene_epoch,
            kind=_CHUNK_JOB_KIND,
        )

        for candidate in candidate_result.chunks:
            self.scheduler.enqueue(
                key=f"chunk:{scene_id}:{candidate.layer_id}:{candidate.cx}:{candidate.cy}",
                payload=candidate,
                priority=candidate.priority,
                now_ms=now_ms,
                kind=_CHUNK_JOB_KIND,
                scene_id=scene_id,
                scene_epoch=candidate.scene_epoch,
                viewport_id=viewport_id,
                viewport_generation=viewport_generation,
                byte_size=candidate.byte_size,
                cost=max(1, candidate.byte_size // 1024),
                order=candidate.priority_distance,
                expires_at_ms=now_ms + _CHUNK_JOB_TTL_MS,
                metadata={
                    "ring": candidate.priority_ring,
                    "distance": candidate.priority_distance,
                },
            )

        drained = self.scheduler.drain(
            now_ms=now_ms,
            budget=SchedulerBudget(
                max_items=_DEFAULT_DRAIN_MAX_ITEMS,
                max_payload_bytes=self.max_batch_bytes * 2,
                max_cost=_DEFAULT_DRAIN_MAX_COST,
            ),
        )

        eligible_jobs = []
        for job in drained:
                                                                              
                                           
            if job.scene_epoch != scene_epoch:
                continue
            if (
                job.viewport_generation is not None
                and job.viewport_generation < viewport_generation
            ):
                continue
            eligible_jobs.append(job)

        payload_chunks = await run_blocking(
            self.subscriptions.read_candidates,
            user_id=user_id,
            candidates=tuple(job.payload for job in eligible_jobs),
        )
        payload_by_key = {
            (chunk.layer_id, chunk.cx, chunk.cy): chunk
            for chunk in payload_chunks
        }

        chunk_payloads: list[ViewportChunkPayload] = []
        batch_items: list[ChunkBatchItem] = []
        batch_priorities: list[int] = []
        for job in eligible_jobs:
            candidate = job.payload
            payload_chunk = payload_by_key.get(
                (candidate.layer_id, candidate.cx, candidate.cy)
            )
            if payload_chunk is None:
                continue

            chunk_payloads.append(payload_chunk)
            batch_items.append(
                ChunkBatchItem(
                    layer_id=payload_chunk.layer_id,
                    cx=payload_chunk.cx,
                    cy=payload_chunk.cy,
                    version=payload_chunk.version,
                    hash=payload_chunk.hash,
                    encoding=payload_chunk.encoding,
                    data=payload_chunk.data,
                )
            )
            batch_priorities.append(int(job.base_priority))

        binary_batches, batch_priority_by_id = self._build_binary_batches(
            scene_id=scene_id,
            scene_epoch=scene_epoch,
            viewport_id=viewport_id,
            viewport_generation=viewport_generation,
            chunks=tuple(batch_items),
            priorities=tuple(batch_priorities),
        )
        batch_ids = [batch_id for batch_id, _frame in binary_batches]
        batch_bytes = sum(len(frame) for _batch_id, frame in binary_batches)
        elapsed_ms = (time.perf_counter() - started_at) * 1000

        self.metrics.increment("chunk.request.missing", candidate_result.missing_count)
        self.metrics.increment("chunk.request.stale", candidate_result.stale_count)
        self.metrics.increment("chunk.candidate.count", len(candidate_result.chunks))
        self.metrics.increment("chunk.scheduler.drained", len(drained))
        self.metrics.increment(
            "chunk.scheduler.deferred", max(0, len(candidate_result.chunks) - len(drained))
        )
        self.metrics.increment("chunk.batch.count", len(binary_batches))
        self.metrics.increment("chunk.batch.bytes", batch_bytes)
        if binary_batches:
            self.metrics.observe("chunk.batch.p95_ms", elapsed_ms)
        self._record_scheduler_metrics(now_ms=now_ms)

        payload = {
            "command_id": command_id,
            **(extra_payload or {}),
            "scene_id": scene_id,
            "scene_epoch": candidate_result.scene_epoch,
            "board_version": scene.get("board_version", 1),
            "board_area_markers": await run_blocking(
                self._visible_board_markers,
                scene_id=scene_id,
                campaign_id=scene["campaign_id"],
                user_id=user_id,
            ),
            "viewport_id": viewport_id,
            "viewport_generation": viewport_generation,
            "batch_id": batch_ids[0] if batch_ids else None,
            "batch_ids": batch_ids,
            "chunk_count": len(chunk_payloads),
            "batch_count": len(binary_batches),
            "missing_chunks": candidate_result.missing_count,
            "stale_chunks": candidate_result.stale_count,
        }

        response = event_envelope(
            event=event,
            room_id=scene["campaign_id"],
            payload=payload,
        )

        return SceneStreamCommandResult(
            handled=True,
            response=response,
            binary_batches=binary_batches,
            batch_priority_by_id=batch_priority_by_id,
        )

    def _record_scheduler_metrics(self, *, now_ms: int) -> None:
                                                                                
                                                                              
                                                    
        snapshot = self.scheduler.snapshot(now_ms=now_ms)
        self.metrics.observe("scheduler.queue.size", snapshot.queued_items)
        self.metrics.observe("scheduler.queue.bytes", snapshot.queued_bytes)
        self.metrics.observe("scheduler.queue.cost", snapshot.queued_cost)
        if snapshot.oldest_item_age_ms is not None:
            self.metrics.observe(
                "scheduler.queue.oldest_age_ms", snapshot.oldest_item_age_ms
            )
        for name in ("immediate", "high", "normal", "low", "background"):
            count = snapshot.by_effective_priority.get(name, 0)
            self.metrics.observe(f"scheduler.queue.{name}", count)

    def _build_binary_batches(
        self,
        *,
        scene_id: str,
        scene_epoch: int,
        viewport_id: str,
        viewport_generation: int,
        chunks: tuple[ChunkBatchItem, ...],
        priorities: tuple[int, ...] = (),
    ) -> tuple[tuple[tuple[str, bytes], ...], dict[str, int]]:
        batches: list[tuple[str, bytes]] = []
        priority_by_id: dict[str, int] = {}
        current: list[ChunkBatchItem] = []
        current_priority = int(RenderPriority.BACKGROUND)

        def flush() -> None:
            nonlocal current, current_priority
            if not current:
                return
            batch_id, frame = self._encode_batch(
                scene_id=scene_id,
                scene_epoch=scene_epoch,
                viewport_id=viewport_id,
                viewport_generation=viewport_generation,
                chunks=tuple(current),
            )
            batches.append((batch_id, frame))
                                                                              
            priority_by_id[batch_id] = current_priority
            current = []
            current_priority = int(RenderPriority.BACKGROUND)

        for index, chunk in enumerate(chunks):
            chunk_priority = priorities[index] if index < len(priorities) else int(
                RenderPriority.NORMAL
            )

            if not current:
                current.append(chunk)
                current_priority = chunk_priority
                continue

            candidate = tuple([*current, chunk])
            candidate_frame = self._encode_batch(
                scene_id=scene_id,
                scene_epoch=scene_epoch,
                viewport_id=viewport_id,
                viewport_generation=viewport_generation,
                chunks=candidate,
            )

            if len(candidate_frame[1]) <= self.max_batch_bytes:
                current.append(chunk)
                current_priority = min(current_priority, chunk_priority)
                continue

            flush()
            current = [chunk]
            current_priority = chunk_priority

        flush()

        return tuple(batches), priority_by_id

    def _encode_batch(
        self,
        *,
        scene_id: str,
        scene_epoch: int,
        viewport_id: str,
        viewport_generation: int,
        chunks: tuple[ChunkBatchItem, ...],
    ) -> tuple[str, bytes]:
        batch_id = uuid.uuid4().hex
        return (
            batch_id,
            encode_chunk_batch_frame(
                ChunkBatchFrame(
                    batch_id=batch_id,
                    scene_id=scene_id,
                    scene_epoch=scene_epoch,
                    viewport_id=viewport_id,
                    viewport_generation=viewport_generation,
                    chunks=chunks,
                )
            ),
        )

    def _parse_payload(
        self,
        *,
        message: dict[str, Any],
        payload: dict[str, Any],
        command_id: str | None,
    ) -> dict[str, Any]:
        scene_id = message.get("scene_id") or payload.get("scene_id")
        viewport_id = payload.get("viewport_id")
        generation = payload.get("generation", payload.get("viewport_generation"))
        layer_ids = payload.get("layers", ())
        known_chunks = payload.get("known", {})

        if not isinstance(scene_id, str) or not scene_id:
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="scene_id is required.",
            )

        if not isinstance(viewport_id, str) or not viewport_id:
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="viewport_id is required.",
            )

        if len(viewport_id) > _MAX_VIEWPORT_ID_LEN:
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="viewport_id is too long.",
            )

        if not isinstance(generation, int) or generation < 0:
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="generation must be zero or positive.",
            )

        if not isinstance(layer_ids, list | tuple) or not all(
            isinstance(layer_id, str) and layer_id for layer_id in layer_ids
        ):
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="layers must be a list of layer ids.",
            )

        if len(layer_ids) > _MAX_VIEWPORT_LAYERS:
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="too many layers requested.",
            )

        if not isinstance(known_chunks, dict) or not all(
            isinstance(key, str) and isinstance(value, int) and value >= 0
            for key, value in known_chunks.items()
        ):
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="known must map chunk keys to versions.",
            )

        if len(known_chunks) > _MAX_KNOWN_CHUNKS:
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="known has too many entries.",
            )

        coords = {}
        for key in ("cx0", "cy0", "cx1", "cy1"):
            value = payload.get(key)
            if not isinstance(value, int) or value < 0:
                return error_envelope(
                    command_id=command_id,
                    code="invalid_payload",
                    message=f"{key} must be zero or positive.",
                )
            coords[key] = value

        if coords["cx1"] < coords["cx0"] or coords["cy1"] < coords["cy0"]:
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="viewport upper bounds must not precede lower bounds.",
            )

        width = coords["cx1"] - coords["cx0"] + 1
        height = coords["cy1"] - coords["cy0"] + 1
        if width > _MAX_VIEWPORT_WIDTH_CHUNKS or height > _MAX_VIEWPORT_HEIGHT_CHUNKS:
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="viewport span exceeds the maximum.",
            )

        if width * height > _MAX_VIEWPORT_CHUNK_AREA:
            return error_envelope(
                command_id=command_id,
                code="invalid_payload",
                message="viewport area exceeds the maximum.",
            )

                                                                              
                                                                       
        focus_cx = payload.get("focus_cx")
        focus_cy = payload.get("focus_cy")
        focus_cx = float(focus_cx) if isinstance(focus_cx, int | float) else None
        focus_cy = float(focus_cy) if isinstance(focus_cy, int | float) else None

        return {
            "scene_id": scene_id,
            "viewport_id": viewport_id,
            "viewport_generation": generation,
            "layer_ids": tuple(layer_ids),
            "known_chunks": known_chunks,
            "focus_cx": focus_cx,
            "focus_cy": focus_cy,
            **coords,
        }
