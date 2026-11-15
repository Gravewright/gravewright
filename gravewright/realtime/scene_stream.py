"""Per-socket scheduling; Channels transports GM samples across ASGI workers.

Tiles remain authenticated HTTP resources. WebSocket batches schedule their loading,
not a second copy of the raster or of the scene's private object layers.
"""

import asyncio
import functools
import json
import logging
import math
from contextlib import suppress
from time import monotonic, time

from django.conf import settings

from gravewright.journals.services import JournalError
from gravewright.maps import services as maps
from gravewright.maps.render_priority import RenderPriority
from gravewright.maps.render_scheduler import RenderPriorityScheduler, SchedulerBudget

from . import access
from .gm_guided_prefetch import GmGuidedPrefetchBroker
from .metrics import database_sync_to_async as db


def scene_for(campaign_id, user_id, map_id):
    """``(scene, member)`` when this member may see the scene; raises otherwise."""
    who = maps.member(campaign_id, user_id)
    return maps.scene(map_id, who), who


def viewport(row, payload):
    """Validate a viewport on ``row``: ``(region, columns, rows)``. No database access."""
    fields = ("lod", "firstColumn", "firstRow", "lastColumn", "lastRow", "generation")
    if any(type(payload.get(k)) is not int or payload[k] < 0 for k in fields):
        raise maps.MapError("Invalid viewport.")
    lod, x0, y0, x1, y1, generation = (payload[k] for k in fields)
    if lod > row.max_lod or generation > 2**53 - 1:
        raise maps.MapError("Invalid viewport.")
    columns = math.ceil(math.ceil(row.width / 2**lod) / row.tile_size)
    rows = math.ceil(math.ceil(row.height / 2**lod) / row.tile_size)
    if not (x0 <= x1 < columns and y0 <= y1 < rows):
        raise maps.MapError("Viewport outside scene.")
    if x1 - x0 + 1 > settings.SCENE_VIEWPORT_MAX_WIDTH_CHUNKS or y1 - y0 + 1 > settings.SCENE_VIEWPORT_MAX_HEIGHT_CHUNKS or (x1 - x0 + 1) * (y1 - y0 + 1) > settings.SCENE_VIEWPORT_MAX_AREA_CHUNKS:
        raise maps.MapError("Viewport too large.")
    return {k: payload[k] for k in fields} | {"mapId": str(row.pk)}, columns, rows


def base_region(region):
    scale = 2 ** region["lod"]
    return dict(
        cx0=region["firstColumn"] * scale,
        cy0=region["firstRow"] * scale,
        cx1=(region["lastColumn"] + 1) * scale - 1,
        cy1=(region["lastRow"] + 1) * scale - 1,
    )


logger = logging.getLogger(__name__)


class SceneStreamMixin:
    # Scene answers reused by samples (see scene_answer). TableConsumer sets the TTL
    # to its authorization TTL: both follow the same rule.
    scene_answer_ttl = 2.0
    scene_answer_limit = 32

    def forget_scenes(self):
        """Drop every reused scene answer; a read still running will not be stored."""
        self.scene_generation = getattr(self, "scene_generation", 0) + 1
        self.scene_answers = {}

    async def scene_answer(self, key, read):
        """``read()`` on the database thread, or a recent answer for ``key``.

        Cursor, camera and tile samples arrive many times per second and each one
        resolved the member and scene again. An answer is reused for at most
        ``scene_answer_ttl`` seconds, while this process's access epoch is unchanged
        and until the socket receives its next server event (TableConsumer.__call__
        calls forget_scenes): changes are announced after commit, so an answer read
        before an announcement is never stored after it. A refused read drops every
        answer. The socket's own viewport always reads (see scene_viewport).
        """
        answers = getattr(self, "scene_answers", None)
        if answers is None:
            answers = self.scene_answers = {}
        try:
            entry = answers.get(key)
        except TypeError:  # an unhashable identifier from a client is never reused
            return await db(read)()
        epoch, generation, now = access.epoch(), getattr(self, "scene_generation", 0), monotonic()
        if entry is not None and entry[0] == epoch and now < entry[1]:
            return entry[2]
        try:
            value = await db(read)()
        except (maps.MapError, JournalError):
            self.forget_scenes()
            raise
        self.remember_scene_answer(key, value, epoch, generation, now)
        return value

    def remember_scene_answer(self, key, value, epoch, generation, read_at):
        """Store an answer whose read began at ``read_at`` under ``epoch``/``generation``."""
        if epoch != access.epoch() or generation != getattr(self, "scene_generation", 0):
            return
        answers = getattr(self, "scene_answers", None)
        if answers is None:
            answers = self.scene_answers = {}
        if key not in answers and len(answers) >= self.scene_answer_limit:
            answers.clear()
        answers[key] = (epoch, read_at + self.scene_answer_ttl, value)

    def visible_scene(self, user_id, map_id):
        """Awaitable ``(scene, member)`` for a member who may see ``map_id``."""
        return self.scene_answer(("scene", str(user_id), map_id),
                                 functools.partial(scene_for, self.campaign_id, user_id, map_id))

    def init_stream(self):
        self.scene_generation, self.scene_answers = 0, {}
        self.render_scheduler = RenderPriorityScheduler()
        self.stream_region = None
        self.stream_task = None
        # Automatic per-player prediction; no deployment toggle or policy selection.
        # Confidence/momentum control admission; real tile bytes control ordering.
        self.prefetch_broker = GmGuidedPrefetchBroker(
            policy="utility_per_byte",
            viewport_ttl_ms=15_000,
        )

    async def stop_stream(self, wait=True):
        self.stream_region = None
        if hasattr(self, "render_scheduler"):
            self.render_scheduler.clear()
        task = getattr(self, "stream_task", None)
        if task:
            task.cancel()
            if wait:
                with suppress(asyncio.CancelledError):
                    await task
            else:
                # A cancelled synchronous call still runs to completion; consume its outcome.
                task.add_done_callback(lambda done: done.cancelled() or done.exception())
            self.stream_task = None

    async def scene_viewport(self, payload):
        # The socket's own viewport always reads the database, so a change of access
        # shows here at once; its answer refreshes the one samples reuse.
        epoch, generation, read_at = access.epoch(), getattr(self, "scene_generation", 0), monotonic()
        try:
            try:
                row, who = await db(scene_for)(self.campaign_id, self.user_id, payload.get("mapId"))
            except (maps.MapError, JournalError):
                self.forget_scenes()
                raise
            self.remember_scene_answer(("scene", str(self.user_id), str(row.pk)),
                                       (row, who), epoch, generation, read_at)
            region, columns, rows = viewport(row, payload)
            signals = {
                k: payload.get(k, 0)
                for k in ("camera_speed", "camera_deceleration", "interaction_count")
            }
            if any(
                type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1e6
                for v in signals.values()
            ):
                raise maps.MapError("Invalid camera sample.")
            signals["interaction_count"] = min(3, int(signals["interaction_count"]))
            previous = self.stream_region
            if previous and region["generation"] < previous["generation"]:
                return
            if (
                previous
                and region["generation"] == previous["generation"]
                and previous != region
            ):
                raise maps.MapError("Viewport generation must advance.")
            if monotonic() - getattr(self, "last_viewport", 0) < 0.2:
                return
            self.last_viewport = monotonic()
            self.stream_seen = monotonic()
            self.stream_region = region
            self.stream_version = row.version
            if previous != region:
                self.render_scheduler.clear()
                now = int(time() * 1000)
                cx, cy = (
                    (region["firstColumn"] + region["lastColumn"]) / 2,
                    (region["firstRow"] + region["lastRow"]) / 2,
                )
                for y in range(
                    max(0, region["firstRow"] - 1), min(rows, region["lastRow"] + 2)
                ):
                    for x in range(
                        max(0, region["firstColumn"] - 1),
                        min(columns, region["lastColumn"] + 2),
                    ):
                        visible = (
                            region["firstColumn"] <= x <= region["lastColumn"]
                            and region["firstRow"] <= y <= region["lastRow"]
                        )
                        distance = math.hypot(x - cx, y - cy)
                        priority = (
                            (
                                RenderPriority.HIGH
                                if distance <= 1
                                else RenderPriority.NORMAL
                            )
                            if visible
                            else RenderPriority.LOW
                        )
                        value = {
                            "key": f"{row.pk}:{region['lod']}:{x}:{y}",
                            "priority": int(priority),
                            "order": distance,
                        }
                        self.render_scheduler.enqueue(
                            key=value["key"],
                            payload=value,
                            priority=priority,
                            now_ms=now,
                            scene_id=str(row.pk),
                            scene_epoch=row.version,
                            viewport_generation=region["generation"],
                            kind="tile",
                            byte_size=len(json.dumps(value)),
                            order=round(distance * 1000),
                            expires_at_ms=now + 10_000,
                        )
                self.start_stream_drain()
            if who.role == "gm":
                # The recipient owns its predictor. No process-global broker: Redis
                # group delivery also works when GM and player land on different workers.
                await self.channel_layer.group_send(
                    self.group,
                    {
                        "type": "room.gm_sample",
                        "region": region,
                        "user_id": str(self.user_id),
                        "version": row.version,
                        "signals": signals,
                    },
                )
            else:
                self.prefetch_broker.record_player_viewport(
                    user_id=str(self.user_id),
                    scene_id=str(row.pk),
                    **base_region(region),
                )
        except (maps.MapError, JournalError, ValueError, TypeError) as error:
            await self.emit(
                "scene.viewport.error",
                {"code": getattr(error, "code", "invalid_input")},
            )

    async def room_gm_sample(self, event):
        """Turn a GM camera sample into prefetch hints for this recipient.

        Runs on the socket's sample lane, next to its own viewport samples: only each
        GM's newest sample waits there, never behind commands, and the drain task it
        starts runs on that lane's thread.
        """
        region = self.stream_region
        sample = event["region"]
        if (
            not region
            or sample["mapId"] != region["mapId"]
            or monotonic() - getattr(self, "stream_seen", 0) > 15
        ):
            return
        if not await self.authorized() or self.member.role == "gm":
            return
        try:
            row, _ = await self.visible_scene(self.user_id, region["mapId"])
            _, columns, rows = viewport(row, region)
            # Recheck sender too: queued samples must not survive a role revocation.
            seen, sender = await self.visible_scene(event["user_id"], sample["mapId"])
            viewport(seen, sample)
            if sender.role != "gm" or event["version"] != row.version:
                return
        except maps.MapError, JournalError, ValueError, TypeError:
            return
        hints = self.prefetch_broker.observe_gm_viewport(
            gm_user_id=event["user_id"],
            scene_id=region["mapId"],
            **base_region(sample),
            **event["signals"],
        )
        now = int(time() * 1000)
        scale = 2 ** region["lod"]
        for hint in hints:
            target = dict(
                region,
                firstColumn=min(columns - 1, hint.cx0 // scale),
                firstRow=min(rows - 1, hint.cy0 // scale),
                lastColumn=min(columns - 1, hint.cx1 // scale),
                lastRow=min(rows - 1, hint.cy1 // scale),
            )
            from gravewright.maps.prefetch import candidates

            planned = await db(candidates)(
                region["mapId"], target, hint.utility, hint.policy
            )
            payload = {
                "tiles": planned,
                "confidence": hint.confidence,
                "momentum": hint.momentum,
                "utility": hint.utility,
                "dwell_ms": hint.dwell_ms,
                "distance_chunks": hint.distance_chunks,
                "revisit_count": hint.revisit_count,
                "interaction_count": hint.interaction_count,
                "camera_speed": hint.camera_speed,
                "camera_deceleration": hint.camera_deceleration,
                "recency_score": hint.recency_score,
                "state": "candidate",
                "source": "gm_hint",
                "region": target,
                "expires_at_ms": hint.expires_at_ms,
                "score": hint.score,
                "policy": hint.policy,
                "materialization": "blob_only",
            }
            self.render_scheduler.enqueue(
                key="gm-hint",
                payload=payload,
                priority=RenderPriority.BACKGROUND,
                now_ms=now,
                kind="gm-hint",
                scene_id=region["mapId"],
                scene_epoch=row.version,
                viewport_generation=region["generation"],
                byte_size=len(json.dumps(payload)),
                expires_at_ms=hint.expires_at_ms,
            )
        if hints:
            self.start_stream_drain()

    def start_stream_drain(self):
        if not self.stream_task or self.stream_task.done():
            self.stream_task = asyncio.create_task(self.drain_stream())

    async def drain_stream(self):
        try:
            while self.render_scheduler and self.stream_region:
                region = self.stream_region.copy()
                if not await self.authorized():
                    self.render_scheduler.clear()
                    return
                try:
                    row, _ = await self.visible_scene(self.user_id, region["mapId"])
                    viewport(row, region)
                except maps.MapError, JournalError, ValueError, TypeError:
                    self.render_scheduler.clear()
                    return
                if region != self.stream_region:
                    continue
                now = int(time() * 1000)
                batch = self.render_scheduler.drain(
                    now_ms=now,
                    budget=SchedulerBudget(
                        max_items=64,
                        max_payload_bytes=16_384,
                        max_cost=64,
                        max_elapsed_ms=4,
                    ),
                )
                tiles = []
                for item in batch:
                    if (
                        item.scene_epoch != row.version
                        or item.viewport_generation != region["generation"]
                    ):
                        continue
                    if item.kind == "gm-hint":
                        await self.emit("scene.gm_prefetch.hint", item.payload)
                    else:
                        tiles.append(item.payload)
                if tiles:
                    await self.emit(
                        "scene.viewport.ready", {"region": region, "tiles": tiles}
                    )
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - close the socket on a background task failure
            # A failed stream must not silently leave a live socket without scheduling.
            logger.exception("Scene stream failed for campaign %s", self.campaign_id)
            await self.close(code=1011)
