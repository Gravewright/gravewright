#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import random
import re
import signal
import statistics
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any

import websockets


STREAM_EMAIL = "chunkstream@test.local"
STREAM_PASSWORD = "ChunkStream1!"

CSRF_RE = re.compile(r'name="_csrf_token"\s+value="([^"]+)"')
ROOM_ID_RE = re.compile(r'data-room-id="([^"]+)"')
SCENE_ID_RE = re.compile(r'data-scene-id="([^"]+)"')
LAYER_ID_RE = re.compile(r'data-scene-layer-id="([^"]+)"')

CHUNK_MAGIC = b"GWCB"
CHUNK_HEADER_BYTES = 12


@dataclass(frozen=True)
class SessionInfo:
    cookie_header: str
    room_id: str
    scene_id: str
    layer_id: str
    scene_epoch: int


@dataclass
class SharedMetrics:
    users_started: int = 0
    users_finished: int = 0
    failures: int = 0

    commands_sent: int = 0
    binary_frames: int = 0
    chunks_received: int = 0
    payload_bytes: int = 0
    acks_sent: int = 0

    connections_opened: int = 0
    connection_failures: int = 0
    reconnects: int = 0
    resumes: int = 0

    viewport_subscribes: int = 0
    viewport_updates: int = 0
    clean_resumes: int = 0
    resync_required: int = 0

    stale_or_missing_chunks_reported: int = 0

    subscribe_latencies_ms: list[float] = field(default_factory=list)
    update_latencies_ms: list[float] = field(default_factory=list)
    resume_latencies_ms: list[float] = field(default_factory=list)
    first_binary_latencies_ms: list[float] = field(default_factory=list)
    batch_payload_bytes: list[float] = field(default_factory=list)
    chunks_per_frame: list[float] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        return {
            "users_started": self.users_started,
            "users_finished": self.users_finished,
            "failures": self.failures,
            "commands_sent": self.commands_sent,
            "binary_frames": self.binary_frames,
            "chunks_received": self.chunks_received,
            "payload_bytes": self.payload_bytes,
            "acks_sent": self.acks_sent,
            "connections_opened": self.connections_opened,
            "connection_failures": self.connection_failures,
            "reconnects": self.reconnects,
            "resumes": self.resumes,
            "viewport_subscribes": self.viewport_subscribes,
            "viewport_updates": self.viewport_updates,
            "clean_resumes": self.clean_resumes,
            "resync_required": self.resync_required,
            "stale_or_missing_chunks_reported": self.stale_or_missing_chunks_reported,
        }


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil((pct / 100.0) * len(ordered)) - 1))
    return float(ordered[index])


def summary_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0, "max": 0}
    return {
        "count": float(len(values)),
        "avg": float(statistics.fmean(values)),
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "max": float(max(values)),
    }


def _request(opener, url: str, data: dict[str, str] | None = None) -> str:
    encoded = None
    headers = {"Accept": "text/html,application/json"}

    if data is not None:
        encoded = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    request = urllib.request.Request(url, data=encoded, headers=headers)

    with opener.open(request, timeout=20) as response:
        return response.read().decode()


def _first_match(pattern: re.Pattern[str], value: str, name: str) -> str:
    match = pattern.search(value)
    if not match:
        raise RuntimeError(f"Could not find {name} in page")
    return match.group(1)


def _cookie_header(cookie_jar: CookieJar) -> str:
    return "; ".join(f"{cookie.name}={cookie.value}" for cookie in cookie_jar)


def login_and_discover(host: str) -> SessionInfo:
    cookie_jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    login_page = _request(opener, f"{host}/")
    csrf = _first_match(CSRF_RE, login_page, "csrf_token")

    _request(
        opener,
        f"{host}/login",
        {
            "email": STREAM_EMAIL,
            "password": STREAM_PASSWORD,
            "_csrf_token": csrf,
        },
    )

    game_page = _request(opener, f"{host}/game")

    scene_id = _first_match(SCENE_ID_RE, game_page, "scene_id")
    layer_id = _first_match(LAYER_ID_RE, game_page, "layer_id")
    room_id = _first_match(ROOM_ID_RE, game_page, "room_id")

    manifest_raw = _request(opener, f"{host}/game/scenes/{scene_id}/manifest")
    manifest = json.loads(manifest_raw)

    return SessionInfo(
        cookie_header=_cookie_header(cookie_jar),
        room_id=room_id,
        scene_id=scene_id,
        layer_id=layer_id,
        scene_epoch=int(manifest["scene_epoch"]),
    )


def websocket_url(host: str) -> str:
    if host.startswith("https://"):
        return f"wss://{host.removeprefix('https://')}/game/ws"
    return f"ws://{host.removeprefix('http://')}/game/ws"


def decode_chunk_frame(frame: bytes) -> dict[str, Any]:
    if len(frame) < CHUNK_HEADER_BYTES:
        raise RuntimeError("Binary frame is too short")

    if frame[:4] != CHUNK_MAGIC:
        raise RuntimeError("Binary frame magic mismatch")

    version = frame[4]
    frame_type = frame[5]
    header_len = int.from_bytes(frame[8:12], "little", signed=False)
    header_end = CHUNK_HEADER_BYTES + header_len

    if version != 1:
        raise RuntimeError(f"Unsupported binary frame version: {version}")

    if frame_type != 1:
        raise RuntimeError(f"Unsupported binary frame type: {frame_type}")

    if header_end > len(frame):
        raise RuntimeError("Binary frame header is invalid")

    header = json.loads(frame[CHUNK_HEADER_BYTES:header_end].decode())
    payload = frame[header_end:]

    total_chunk_bytes = sum(int(chunk["length"]) for chunk in header["chunks"])
    if total_chunk_bytes != len(payload):
        raise RuntimeError(
            f"Binary frame payload length mismatch: header={total_chunk_bytes}, payload={len(payload)}"
        )

    return {"header": header, "payload_bytes": len(payload)}


def viewport_for_step(
    *,
    layer_id: str,
    generation: int,
    step: int,
    width: int,
    height: int,
    max_cx: int,
    max_cy: int,
) -> dict[str, Any]:
    """
    The server API uses inclusive chunk ranges:
      cx0=0, cx1=2 means 3 columns.

    max_cx/max_cy are chunk counts, not max indexes.
    Example:
      max_cx=8, width=5 -> valid starts: 0,1,2,3
    """
    x_span = max(1, max_cx - width + 1)
    y_span = max(1, max_cy - height + 1)

    cx0 = step % x_span
    cy0 = (step // x_span) % y_span

    return {
        "viewport_id": "main",
        "generation": generation,
        "layers": [layer_id],
        "cx0": cx0,
        "cy0": cy0,
        "cx1": cx0 + width - 1,
        "cy1": cy0 + height - 1,
    }


async def send_command(
    ws,
    *,
    metrics: SharedMetrics,
    command_id: str,
    command: str,
    payload: dict[str, Any],
    scene_id: str | None = None,
    room_id: str | None = None,
) -> None:
    envelope: dict[str, Any] = {
        "type": "command",
        "id": command_id,
        "command": command,
        "payload": payload,
    }

    if scene_id is not None:
        envelope["scene_id"] = scene_id

    if room_id is not None:
        envelope["room_id"] = room_id

    await ws.send(json.dumps(envelope, separators=(",", ":")))
    metrics.commands_sent += 1


async def process_binary_frame(
    ws,
    raw: bytes,
    *,
    session: SessionInfo,
    metrics: SharedMetrics,
    known_chunks: dict[str, int],
    ack: bool,
    started_at: float,
    first_binary_seen: dict[str, bool],
) -> int:
    if not first_binary_seen["value"]:
        metrics.first_binary_latencies_ms.append((time.monotonic() - started_at) * 1000.0)
        first_binary_seen["value"] = True

    frame = decode_chunk_frame(raw)
    header = frame["header"]

    if header["scene_id"] != session.scene_id:
        raise RuntimeError("Binary frame scene_id mismatch")

    if int(header["scene_epoch"]) != int(session.scene_epoch):
        raise RuntimeError("Binary frame scene_epoch mismatch")

    chunks = header["chunks"]
    payload_bytes = int(frame["payload_bytes"])

    metrics.binary_frames += 1
    metrics.chunks_received += len(chunks)
    metrics.payload_bytes += payload_bytes
    metrics.batch_payload_bytes.append(float(payload_bytes))
    metrics.chunks_per_frame.append(float(len(chunks)))

                                                                              
                                                                           
                                      
    for chunk in chunks:
        key = f"{chunk['layer_id']}:{chunk['cx']}:{chunk['cy']}"
        known_chunks[key] = int(chunk["version"])

    if ack:
        await send_command(
            ws,
            metrics=metrics,
            command_id=f"ack-{header['batch_id']}",
            command="chunk.ack",
            payload={"batch_id": header["batch_id"], "applied": True},
        )
        metrics.acks_sent += 1

    return len(chunks)


async def recv_event_and_drain_frames(
    ws,
    *,
    session: SessionInfo,
    metrics: SharedMetrics,
    known_chunks: dict[str, int],
    event_name: str,
    command_id: str,
    started_at: float,
    timeout_seconds: float,
    ack: bool,
    require_event: bool,
    latency_bucket: str,
) -> dict[str, Any] | None:
    """
    Waits for an event tied to command_id while accepting binary frames in any order.

    The server may send:
      - binary frames before ready event
      - ready event before binary frames
      - no ready event for viewport.update, depending on implementation

    For subscribe/resume we require the event.
    For update we can accept timeout as non-fatal if frames arrived.
    """
    deadline = time.monotonic() + timeout_seconds
    first_binary_seen = {"value": False}
    local_frames = 0
    ready_payload: dict[str, Any] | None = None

    while time.monotonic() < deadline:
        remaining = max(0.1, deadline - time.monotonic())

        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except asyncio.TimeoutError:
            break

        if isinstance(raw, bytes):
            await process_binary_frame(
                ws,
                raw,
                session=session,
                metrics=metrics,
                known_chunks=known_chunks,
                ack=ack,
                started_at=started_at,
                first_binary_seen=first_binary_seen,
            )
            local_frames += 1
            continue

        envelope = json.loads(raw)
        payload = envelope.get("payload") or {}

        if envelope.get("event") != event_name:
            continue

        if payload.get("command_id") != command_id:
            continue

        ready_payload = payload
        elapsed_ms = (time.monotonic() - started_at) * 1000.0

        if latency_bucket == "subscribe":
            metrics.subscribe_latencies_ms.append(elapsed_ms)
        elif latency_bucket == "update":
            metrics.update_latencies_ms.append(elapsed_ms)
        elif latency_bucket == "resume":
            metrics.resume_latencies_ms.append(elapsed_ms)

        batch_count = int(payload.get("batch_count", 0))
        chunk_count = int(payload.get("chunk_count", 0))
        missing_chunks = int(payload.get("missing_chunks", 0) or 0)
        stale_chunks = int(payload.get("stale_chunks", 0) or 0)

        metrics.stale_or_missing_chunks_reported += missing_chunks + stale_chunks

        if event_name == "scene.session.resumed":
            if payload.get("resync_required") is True:
                metrics.resync_required += 1
            else:
                metrics.clean_resumes += 1

                                                                 
                                                                                
        drain_deadline = time.monotonic() + min(5.0, timeout_seconds)
        while local_frames < batch_count and time.monotonic() < drain_deadline:
            try:
                raw2 = await asyncio.wait_for(
                    ws.recv(),
                    timeout=max(0.1, drain_deadline - time.monotonic()),
                )
            except asyncio.TimeoutError:
                break

            if not isinstance(raw2, bytes):
                continue

            await process_binary_frame(
                ws,
                raw2,
                session=session,
                metrics=metrics,
                known_chunks=known_chunks,
                ack=ack,
                started_at=started_at,
                first_binary_seen=first_binary_seen,
            )
            local_frames += 1

                                                                               
                                                                            
        _ = chunk_count
        return ready_payload

    if require_event:
        raise TimeoutError(f"Timed out waiting for {event_name}/{command_id}")

    return ready_payload


async def open_ws(host: str, session: SessionInfo, args: argparse.Namespace):
    return await websockets.connect(
        websocket_url(host),
        additional_headers={"Cookie": session.cookie_header},
        max_size=args.max_ws_message_size,
        open_timeout=args.open_timeout,
        ping_interval=args.ping_interval,
        ping_timeout=args.ping_timeout,
        close_timeout=args.close_timeout,
    )


async def subscribe_initial_viewport(
    ws,
    *,
    user_index: int,
    session: SessionInfo,
    metrics: SharedMetrics,
    known_chunks: dict[str, int],
    generation: int,
    step: int,
    args: argparse.Namespace,
) -> None:
    viewport = viewport_for_step(
        layer_id=session.layer_id,
        generation=generation,
        step=step,
        width=args.viewport_width_chunks,
        height=args.viewport_height_chunks,
        max_cx=args.max_cx,
        max_cy=args.max_cy,
    )
    command_id = f"u{user_index}-subscribe-{generation}"
    started_at = time.monotonic()

    await send_command(
        ws,
        metrics=metrics,
        command_id=command_id,
        command="viewport.subscribe",
        scene_id=session.scene_id,
        room_id=session.room_id,
        payload={**viewport, "known": known_chunks},
    )
    metrics.viewport_subscribes += 1

    await recv_event_and_drain_frames(
        ws,
        session=session,
        metrics=metrics,
        known_chunks=known_chunks,
        event_name="scene.viewport.ready",
        command_id=command_id,
        started_at=started_at,
        timeout_seconds=args.command_timeout,
        ack=args.ack,
        require_event=True,
        latency_bucket="subscribe",
    )


async def resume_session(
    ws,
    *,
    user_index: int,
    session: SessionInfo,
    metrics: SharedMetrics,
    known_chunks: dict[str, int],
    generation: int,
    step: int,
    args: argparse.Namespace,
) -> None:
    viewport = viewport_for_step(
        layer_id=session.layer_id,
        generation=generation,
        step=step,
        width=args.viewport_width_chunks,
        height=args.viewport_height_chunks,
        max_cx=args.max_cx,
        max_cy=args.max_cy,
    )
    command_id = f"u{user_index}-resume-{generation}"
    started_at = time.monotonic()

    await send_command(
        ws,
        metrics=metrics,
        command_id=command_id,
        command="session.resume",
        scene_id=session.scene_id,
        room_id=session.room_id,
        payload={
            "active_scene_id": session.scene_id,
            "scene_epoch": session.scene_epoch,
            "last_event_seq": 0,
            "viewport": viewport,
            "known_chunks": known_chunks,
        },
    )
    metrics.resumes += 1

    await recv_event_and_drain_frames(
        ws,
        session=session,
        metrics=metrics,
        known_chunks=known_chunks,
        event_name="scene.session.resumed",
        command_id=command_id,
        started_at=started_at,
        timeout_seconds=args.command_timeout,
        ack=args.ack,
        require_event=True,
        latency_bucket="resume",
    )


async def update_viewport(
    ws,
    *,
    user_index: int,
    session: SessionInfo,
    metrics: SharedMetrics,
    known_chunks: dict[str, int],
    generation: int,
    step: int,
    args: argparse.Namespace,
) -> None:
    viewport = viewport_for_step(
        layer_id=session.layer_id,
        generation=generation,
        step=step,
        width=args.viewport_width_chunks,
        height=args.viewport_height_chunks,
        max_cx=args.max_cx,
        max_cy=args.max_cy,
    )
    command_id = f"u{user_index}-update-{generation}"
    started_at = time.monotonic()

    await send_command(
        ws,
        metrics=metrics,
        command_id=command_id,
        command="viewport.update",
        scene_id=session.scene_id,
        room_id=session.room_id,
        payload={**viewport, "known": known_chunks},
    )
    metrics.viewport_updates += 1

    await recv_event_and_drain_frames(
        ws,
        session=session,
        metrics=metrics,
        known_chunks=known_chunks,
        event_name=args.viewport_update_event,
        command_id=command_id,
        started_at=started_at,
        timeout_seconds=args.update_timeout,
        ack=args.ack,
        require_event=args.require_update_event,
        latency_bucket="update",
    )


async def virtual_user(
    user_index: int,
    *,
    session: SessionInfo,
    host: str,
    run_until: float,
    args: argparse.Namespace,
    metrics: SharedMetrics,
) -> None:
    metrics.users_started += 1

    known_chunks: dict[str, int] = {}
    is_slow = random.random() < args.slow_client_ratio
    generation = 1
    step = user_index
    first_connection = True
    updates_on_connection = 0

    try:
        while time.monotonic() < run_until:
            try:
                ws = await open_ws(host, session, args)
                metrics.connections_opened += 1
            except Exception as exc:
                metrics.connection_failures += 1
                raise RuntimeError(f"opening handshake failed: {exc}") from exc

            try:
                async with ws:
                    if first_connection or args.mode == "subscribe":
                        await subscribe_initial_viewport(
                            ws,
                            user_index=user_index,
                            session=session,
                            metrics=metrics,
                            known_chunks=known_chunks,
                            generation=generation,
                            step=step,
                            args=args,
                        )
                        first_connection = False
                    else:
                        await resume_session(
                            ws,
                            user_index=user_index,
                            session=session,
                            metrics=metrics,
                            known_chunks=known_chunks,
                            generation=generation,
                            step=step,
                            args=args,
                        )

                    if args.mode == "subscribe":
                                                                       
                        while time.monotonic() < run_until:
                            await asyncio.sleep(1.0)
                        break

                    updates_on_connection = 0
                    reconnect_after = random.randint(
                        args.reconnect_every_min_updates,
                        args.reconnect_every_max_updates,
                    )

                    while time.monotonic() < run_until:
                        if is_slow:
                            await asyncio.sleep(random.uniform(args.slow_min_sleep, args.slow_max_sleep))
                        else:
                            await asyncio.sleep(random.uniform(args.fast_min_sleep, args.fast_max_sleep))

                        generation += 1
                        step += 1
                        updates_on_connection += 1

                        await update_viewport(
                            ws,
                            user_index=user_index,
                            session=session,
                            metrics=metrics,
                            known_chunks=known_chunks,
                            generation=generation,
                            step=step,
                            args=args,
                        )

                        if args.mode == "pan-reconnect" and updates_on_connection >= reconnect_after:
                            metrics.reconnects += 1
                            generation += 1
                            break

                    if args.mode != "pan-reconnect":
                        break

            except websockets.ConnectionClosed:
                if time.monotonic() < run_until:
                    metrics.reconnects += 1
                generation += 1

        metrics.users_finished += 1

    except asyncio.CancelledError:
        raise
    except Exception as exc:
        metrics.failures += 1
        print(f"[user {user_index}] ERROR: {exc}")


def write_outputs(
    *,
    output: Path,
    args: argparse.Namespace,
    metrics: SharedMetrics,
    started_at: float,
    finished: bool,
) -> None:
    duration = max(0.001, time.monotonic() - started_at)
    snap = metrics.snapshot()

    summary = {
        "finished": finished,
        "host": args.host,
        "users": args.users,
        "spawn_rate": args.spawn_rate,
        "run_time": args.run_time,
        "actual_duration_seconds": duration,
        "mode": args.mode,
        "viewport_width_chunks": args.viewport_width_chunks,
        "viewport_height_chunks": args.viewport_height_chunks,
        "ack": args.ack,
        "slow_client_ratio": args.slow_client_ratio,
        **snap,
        "failure_rate_by_started_users": metrics.failures / max(1, metrics.users_started),
        "connection_failure_rate_by_started_users": metrics.connection_failures / max(1, metrics.users_started),
        "commands_per_second": metrics.commands_sent / duration,
        "binary_frames_per_second": metrics.binary_frames / duration,
        "chunks_per_second": metrics.chunks_received / duration,
        "payload_bytes_per_second": metrics.payload_bytes / duration,
        "payload_mb_total": metrics.payload_bytes / (1024 * 1024),
        "payload_kb_per_started_user": (metrics.payload_bytes / 1024) / max(1, metrics.users_started),
        "chunks_per_started_user": metrics.chunks_received / max(1, metrics.users_started),
        "frames_per_started_user": metrics.binary_frames / max(1, metrics.users_started),
        "subscribe_latency_ms": summary_stats(metrics.subscribe_latencies_ms),
        "update_latency_ms": summary_stats(metrics.update_latencies_ms),
        "resume_latency_ms": summary_stats(metrics.resume_latencies_ms),
        "first_binary_latency_ms": summary_stats(metrics.first_binary_latencies_ms),
        "batch_payload_bytes": summary_stats(metrics.batch_payload_bytes),
        "chunks_per_frame": summary_stats(metrics.chunks_per_frame),
    }

    (output / "results_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    with (output / "summary.md").open("w", encoding="utf-8") as f:
        f.write("# Gate WS-P — WebSocket Chunk Stream Load Test\n\n")
        f.write("## Result\n\n")
        f.write("```txt\n")
        f.write(f"finished: {finished}\n")
        f.write(f"host: {args.host}\n")
        f.write(f"users: {args.users}\n")
        f.write(f"spawn_rate: {args.spawn_rate}\n")
        f.write(f"run_time: {args.run_time}\n")
        f.write(f"actual_duration_seconds: {duration:.2f}\n")
        f.write(f"mode: {args.mode}\n")
        f.write(f"failures: {metrics.failures}\n")
        f.write(f"connection_failures: {metrics.connection_failures}\n")
        f.write(f"users_started: {metrics.users_started}\n")
        f.write(f"users_finished: {metrics.users_finished}\n")
        f.write("```\n\n")

        f.write("## Stream\n\n")
        f.write("```txt\n")
        f.write(f"commands_sent: {metrics.commands_sent}\n")
        f.write(f"binary_frames: {metrics.binary_frames}\n")
        f.write(f"chunks_received: {metrics.chunks_received}\n")
        f.write(f"payload_bytes: {metrics.payload_bytes}\n")
        f.write(f"payload_mb_total: {summary['payload_mb_total']:.2f}\n")
        f.write(f"payload_kb_per_started_user: {summary['payload_kb_per_started_user']:.2f}\n")
        f.write(f"chunks_per_started_user: {summary['chunks_per_started_user']:.2f}\n")
        f.write(f"frames_per_started_user: {summary['frames_per_started_user']:.2f}\n")
        f.write(f"acks_sent: {metrics.acks_sent}\n")
        f.write(f"reconnects: {metrics.reconnects}\n")
        f.write(f"resumes: {metrics.resumes}\n")
        f.write(f"clean_resumes: {metrics.clean_resumes}\n")
        f.write(f"resync_required: {metrics.resync_required}\n")
        f.write("```\n\n")

        f.write("## Latency and payload distribution\n\n")
        f.write("```json\n")
        f.write(json.dumps({
            "subscribe_latency_ms": summary["subscribe_latency_ms"],
            "update_latency_ms": summary["update_latency_ms"],
            "resume_latency_ms": summary["resume_latency_ms"],
            "first_binary_latency_ms": summary["first_binary_latency_ms"],
            "batch_payload_bytes": summary["batch_payload_bytes"],
            "chunks_per_frame": summary["chunks_per_frame"],
        }, indent=2))
        f.write("\n```\n")


async def run(args: argparse.Namespace) -> SharedMetrics:
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    print("[load] Discovering session...")
    session = await asyncio.to_thread(login_and_discover, args.host.rstrip("/"))
    print(f"[load] scene={session.scene_id} layer={session.layer_id} epoch={session.scene_epoch}")

    metrics = SharedMetrics()
    started_at = time.monotonic()
    run_until = started_at + args.run_time
    tasks: set[asyncio.Task[None]] = set()

    stop_requested = asyncio.Event()

    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(getattr(signal, signame), stop_requested.set)
        except (NotImplementedError, RuntimeError, ValueError):
            pass

    timeseries_path = output / "results_timeseries.csv"
    finished = False

    try:
        with timeseries_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "elapsed_seconds",
                "users_spawned",
                "tasks_active",
                "users_started",
                "users_finished",
                "failures",
                "connection_failures",
                "commands_sent",
                "binary_frames",
                "chunks_received",
                "payload_bytes",
                "acks_sent",
                "reconnects",
                "resumes",
            ])

            users_created = 0
            spawn_interval = 1.0 / max(0.001, args.spawn_rate)
            next_spawn = time.monotonic()

            while time.monotonic() < run_until and not stop_requested.is_set():
                now = time.monotonic()

                while users_created < args.users and now >= next_spawn:
                    task = asyncio.create_task(
                        virtual_user(
                            users_created,
                            session=session,
                            host=args.host.rstrip("/"),
                            run_until=run_until,
                            args=args,
                            metrics=metrics,
                        )
                    )
                    tasks.add(task)
                    users_created += 1
                    next_spawn += spawn_interval

                done = {task for task in tasks if task.done()}
                for task in done:
                    try:
                        await task
                    except Exception as exc:
                        metrics.failures += 1
                        print(f"[load] task error: {exc}")
                tasks -= done

                snap = metrics.snapshot()
                writer.writerow([
                    int(time.time()),
                    round(time.monotonic() - started_at, 3),
                    users_created,
                    len(tasks),
                    snap["users_started"],
                    snap["users_finished"],
                    snap["failures"],
                    snap["connection_failures"],
                    snap["commands_sent"],
                    snap["binary_frames"],
                    snap["chunks_received"],
                    snap["payload_bytes"],
                    snap["acks_sent"],
                    snap["reconnects"],
                    snap["resumes"],
                ])
                f.flush()

                await asyncio.sleep(1.0)

            if tasks:
                done_results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in done_results:
                    if isinstance(result, Exception):
                        metrics.failures += 1
                        print(f"[load] task error: {result}")

        finished = not stop_requested.is_set()

    finally:
        if tasks:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        write_outputs(
            output=output,
            args=args,
            metrics=metrics,
            started_at=started_at,
            finished=finished,
        )

    return metrics


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.lower() in {"1", "true", "yes", "y", "on"}


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--host", default="http://localhost:8003")
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--spawn-rate", type=float, default=10)
    parser.add_argument("--run-time", type=int, default=60)
    parser.add_argument("--mode", choices=["subscribe", "pan", "pan-reconnect"], default="pan-reconnect")

    parser.add_argument("--viewport-width-chunks", type=int, default=5)
    parser.add_argument("--viewport-height-chunks", type=int, default=4)
    parser.add_argument("--max-cx", type=int, default=8)
    parser.add_argument("--max-cy", type=int, default=6)

    parser.add_argument("--ack", type=parse_bool, default=True)
    parser.add_argument("--slow-client-ratio", type=float, default=0.0)
    parser.add_argument("--fast-min-sleep", type=float, default=0.08)
    parser.add_argument("--fast-max-sleep", type=float, default=0.18)
    parser.add_argument("--slow-min-sleep", type=float, default=0.5)
    parser.add_argument("--slow-max-sleep", type=float, default=2.0)

    parser.add_argument("--reconnect-every-min-updates", type=int, default=20)
    parser.add_argument("--reconnect-every-max-updates", type=int, default=35)

    parser.add_argument("--viewport-update-event", default="scene.viewport.ready")
    parser.add_argument("--require-update-event", type=parse_bool, default=False)

    parser.add_argument("--open-timeout", type=float, default=30)
    parser.add_argument("--command-timeout", type=float, default=20)
    parser.add_argument("--update-timeout", type=float, default=5)
    parser.add_argument("--ping-interval", type=float, default=20)
    parser.add_argument("--ping-timeout", type=float, default=20)
    parser.add_argument("--close-timeout", type=float, default=5)
    parser.add_argument("--max-ws-message-size", type=int, default=16 * 1024 * 1024)

    parser.add_argument("--output", default="tests/performance/chunk_stream/load/latest")

    args = parser.parse_args()

    try:
        metrics = asyncio.run(run(args))
    except KeyboardInterrupt:
        print("[load] Interrupted.")
        return

    print("[load] Done")
    print(f"  users_started:       {metrics.users_started}")
    print(f"  users_finished:      {metrics.users_finished}")
    print(f"  failures:            {metrics.failures}")
    print(f"  connection_failures: {metrics.connection_failures}")
    print(f"  commands_sent:       {metrics.commands_sent}")
    print(f"  binary_frames:       {metrics.binary_frames}")
    print(f"  chunks_received:     {metrics.chunks_received}")
    print(f"  payload_bytes:       {metrics.payload_bytes}")
    print(f"  reconnects:          {metrics.reconnects}")
    print(f"  resumes:             {metrics.resumes}")
    print(f"  clean_resumes:       {metrics.clean_resumes}")
    print(f"  resync_required:     {metrics.resync_required}")


if __name__ == "__main__":
    main()
