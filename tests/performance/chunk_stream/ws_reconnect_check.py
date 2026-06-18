#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import random
import re
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
class Metrics:
    commands_sent: int = 0
    binary_frames: int = 0
    chunks_received: int = 0
    payload_bytes: int = 0
    acks_sent: int = 0
    reconnects: int = 0
    resumes: int = 0
    failures: int = 0
    users_started: int = 0
    users_finished: int = 0
    subscribe_latencies_ms: list[float] = field(default_factory=list)
    resume_latencies_ms: list[float] = field(default_factory=list)
    first_binary_latencies_ms: list[float] = field(default_factory=list)
    batch_payload_bytes: list[int] = field(default_factory=list)

    def merge(self, other: "Metrics") -> None:
        self.commands_sent += other.commands_sent
        self.binary_frames += other.binary_frames
        self.chunks_received += other.chunks_received
        self.payload_bytes += other.payload_bytes
        self.acks_sent += other.acks_sent
        self.reconnects += other.reconnects
        self.resumes += other.resumes
        self.failures += other.failures
        self.users_started += other.users_started
        self.users_finished += other.users_finished
        self.subscribe_latencies_ms.extend(other.subscribe_latencies_ms)
        self.resume_latencies_ms.extend(other.resume_latencies_ms)
        self.first_binary_latencies_ms.extend(other.first_binary_latencies_ms)
        self.batch_payload_bytes.extend(other.batch_payload_bytes)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = min(len(values) - 1, max(0, math.ceil((pct / 100.0) * len(values)) - 1))
    return float(values[idx])


def summary_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0, "max": 0}
    return {
        "count": len(values),
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

    if version != 1 or frame_type != 1 or header_end > len(frame):
        raise RuntimeError("Binary frame header is invalid")

    header = json.loads(frame[CHUNK_HEADER_BYTES:header_end].decode())
    payload = frame[header_end:]
    total_chunk_bytes = sum(chunk["length"] for chunk in header["chunks"])

    if total_chunk_bytes != len(payload):
        raise RuntimeError("Binary frame payload length mismatch")

    return {"header": header, "payload_bytes": len(payload)}


async def send_command(
    ws,
    *,
    metrics: Metrics,
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


async def recv_ready_and_frames(
    ws,
    *,
    session: SessionInfo,
    metrics: Metrics,
    event_name: str,
    command_id: str,
    started_at: float,
    timeout_seconds: float = 20,
    ack: bool = True,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    expected_batches: int | None = None
    first_binary_seen = False

    while time.monotonic() < deadline:
        raw = await asyncio.wait_for(ws.recv(), timeout=max(0.1, deadline - time.monotonic()))

        if isinstance(raw, bytes):
            if not first_binary_seen:
                metrics.first_binary_latencies_ms.append((time.monotonic() - started_at) * 1000.0)
                first_binary_seen = True

            frame = decode_chunk_frame(raw)
            header = frame["header"]

            if header["scene_id"] != session.scene_id:
                raise RuntimeError("Binary frame scene_id mismatch")
            if int(header["scene_epoch"]) != int(session.scene_epoch):
                raise RuntimeError("Binary frame scene_epoch mismatch")

            metrics.binary_frames += 1
            metrics.chunks_received += len(header["chunks"])
            metrics.payload_bytes += frame["payload_bytes"]
            metrics.batch_payload_bytes.append(frame["payload_bytes"])

            if ack:
                await send_command(
                    ws,
                    metrics=metrics,
                    command_id=f"ack-{header['batch_id']}",
                    command="chunk.ack",
                    payload={"batch_id": header["batch_id"], "applied": True},
                )
                metrics.acks_sent += 1

            if expected_batches is not None and metrics.binary_frames >= expected_batches:
                                                                                          
                pass

            continue

        envelope = json.loads(raw)
        payload = envelope.get("payload") or {}

        if envelope.get("event") == event_name and payload.get("command_id") == command_id:
            expected_batches = int(payload.get("batch_count", 0))
            if event_name.endswith("resumed"):
                metrics.resume_latencies_ms.append((time.monotonic() - started_at) * 1000.0)
            else:
                metrics.subscribe_latencies_ms.append((time.monotonic() - started_at) * 1000.0)

                                                                                                               
                                                                                          
            end_drain = time.monotonic() + min(3.0, timeout_seconds)
            local_frames = 0
            while local_frames < expected_batches and time.monotonic() < end_drain:
                try:
                    raw2 = await asyncio.wait_for(ws.recv(), timeout=max(0.1, end_drain - time.monotonic()))
                except asyncio.TimeoutError:
                    break

                if not isinstance(raw2, bytes):
                    continue

                if not first_binary_seen:
                    metrics.first_binary_latencies_ms.append((time.monotonic() - started_at) * 1000.0)
                    first_binary_seen = True

                frame = decode_chunk_frame(raw2)
                header = frame["header"]
                metrics.binary_frames += 1
                metrics.chunks_received += len(header["chunks"])
                metrics.payload_bytes += frame["payload_bytes"]
                metrics.batch_payload_bytes.append(frame["payload_bytes"])
                local_frames += 1

                if ack:
                    await send_command(
                        ws,
                        metrics=metrics,
                        command_id=f"ack-{header['batch_id']}",
                        command="chunk.ack",
                        payload={"batch_id": header["batch_id"], "applied": True},
                    )
                    metrics.acks_sent += 1

            return payload

    raise TimeoutError(f"Timed out waiting for {event_name}/{command_id}")


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
                                            
    x_span = max(1, max_cx - width)
    y_span = max(1, max_cy - height)
    cx0 = step % x_span
    cy0 = (step // max(1, x_span)) % y_span

    return {
        "viewport_id": "main",
        "generation": generation,
        "layers": [layer_id],
        "cx0": cx0,
        "cy0": cy0,
        "cx1": cx0 + width - 1,
        "cy1": cy0 + height - 1,
    }


async def virtual_user(
    user_index: int,
    *,
    session: SessionInfo,
    host: str,
    run_until: float,
    mode: str,
    viewport_width_chunks: int,
    viewport_height_chunks: int,
    ack: bool,
    slow_client_ratio: float,
    max_cx: int,
    max_cy: int,
) -> Metrics:
    metrics = Metrics(users_started=1)
    ws_url = websocket_url(host)
    known_chunks: dict[str, int] = {}
    is_slow = random.random() < slow_client_ratio
    generation = 1
    step = user_index

    try:
        async with websockets.connect(
            ws_url,
            additional_headers={"Cookie": session.cookie_header},
            max_size=16 * 1024 * 1024,
        ) as ws:
            viewport = viewport_for_step(
                layer_id=session.layer_id,
                generation=generation,
                step=step,
                width=viewport_width_chunks,
                height=viewport_height_chunks,
                max_cx=max_cx,
                max_cy=max_cy,
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
            await recv_ready_and_frames(
                ws,
                session=session,
                metrics=metrics,
                event_name="scene.viewport.ready",
                command_id=command_id,
                started_at=started_at,
                ack=ack,
            )

            while time.monotonic() < run_until:
                if is_slow:
                    await asyncio.sleep(random.uniform(0.5, 2.0))
                else:
                    await asyncio.sleep(random.uniform(0.08, 0.18))

                generation += 1
                step += 1

                if mode in {"pan", "pan-reconnect"}:
                    viewport = viewport_for_step(
                        layer_id=session.layer_id,
                        generation=generation,
                        step=step,
                        width=viewport_width_chunks,
                        height=viewport_height_chunks,
                        max_cx=max_cx,
                        max_cy=max_cy,
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
                                                                                                     
                                                                           
                    try:
                        await recv_ready_and_frames(
                            ws,
                            session=session,
                            metrics=metrics,
                            event_name="scene.viewport.ready",
                            command_id=command_id,
                            started_at=started_at,
                            timeout_seconds=5,
                            ack=ack,
                        )
                    except TimeoutError:
                                                                                                               
                        pass

                if mode == "pan-reconnect" and generation % 20 == 0:
                    break

        if mode == "pan-reconnect" and time.monotonic() < run_until:
            metrics.reconnects += 1
            async with websockets.connect(
                ws_url,
                additional_headers={"Cookie": session.cookie_header},
                max_size=16 * 1024 * 1024,
            ) as ws:
                generation += 1
                viewport = viewport_for_step(
                    layer_id=session.layer_id,
                    generation=generation,
                    step=step,
                    width=viewport_width_chunks,
                    height=viewport_height_chunks,
                    max_cx=max_cx,
                    max_cy=max_cy,
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
                await recv_ready_and_frames(
                    ws,
                    session=session,
                    metrics=metrics,
                    event_name="scene.session.resumed",
                    command_id=command_id,
                    started_at=started_at,
                    timeout_seconds=10,
                    ack=ack,
                )

        metrics.users_finished = 1
        return metrics

    except Exception as exc:
        metrics.failures += 1
        print(f"[user {user_index}] ERROR: {exc}")
        return metrics


async def run(args: argparse.Namespace) -> Metrics:
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    print("[load] Discovering session...")
    session = await asyncio.to_thread(login_and_discover, args.host.rstrip("/"))
    print(f"[load] scene={session.scene_id} layer={session.layer_id} epoch={session.scene_epoch}")

    metrics = Metrics()
    run_until = time.monotonic() + args.run_time
    tasks: set[asyncio.Task[Metrics]] = set()

    users_created = 0
    spawn_interval = 1.0 / max(1.0, args.spawn_rate)
    next_spawn = time.monotonic()

    timeseries_path = output / "results_timeseries.csv"
    with timeseries_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "users_spawned",
            "tasks_active",
            "commands_sent",
            "binary_frames",
            "chunks_received",
            "payload_bytes",
            "acks_sent",
            "reconnects",
            "resumes",
            "failures",
        ])

        while time.monotonic() < run_until:
            now = time.monotonic()

            while users_created < args.users and now >= next_spawn:
                task = asyncio.create_task(
                    virtual_user(
                        users_created,
                        session=session,
                        host=args.host.rstrip("/"),
                        run_until=run_until,
                        mode=args.mode,
                        viewport_width_chunks=args.viewport_width_chunks,
                        viewport_height_chunks=args.viewport_height_chunks,
                        ack=args.ack,
                        slow_client_ratio=args.slow_client_ratio,
                        max_cx=args.max_cx,
                        max_cy=args.max_cy,
                    )
                )
                tasks.add(task)
                users_created += 1
                next_spawn += spawn_interval

            done = {t for t in tasks if t.done()}
            for task in done:
                metrics.merge(task.result())
            tasks -= done

            writer.writerow([
                int(time.time()),
                users_created,
                len(tasks),
                metrics.commands_sent,
                metrics.binary_frames,
                metrics.chunks_received,
                metrics.payload_bytes,
                metrics.acks_sent,
                metrics.reconnects,
                metrics.resumes,
                metrics.failures,
            ])
            f.flush()

            await asyncio.sleep(1.0)

        if tasks:
            results = await asyncio.gather(*tasks)
            for result in results:
                metrics.merge(result)

    summary = {
        "users": args.users,
        "spawn_rate": args.spawn_rate,
        "run_time": args.run_time,
        "mode": args.mode,
        "commands_sent": metrics.commands_sent,
        "binary_frames": metrics.binary_frames,
        "chunks_received": metrics.chunks_received,
        "payload_bytes": metrics.payload_bytes,
        "acks_sent": metrics.acks_sent,
        "reconnects": metrics.reconnects,
        "resumes": metrics.resumes,
        "failures": metrics.failures,
        "users_started": metrics.users_started,
        "users_finished": metrics.users_finished,
        "failure_rate": metrics.failures / max(1, metrics.users_started),
        "subscribe_latency_ms": summary_stats(metrics.subscribe_latencies_ms),
        "resume_latency_ms": summary_stats(metrics.resume_latencies_ms),
        "first_binary_latency_ms": summary_stats(metrics.first_binary_latencies_ms),
        "batch_payload_bytes": summary_stats([float(v) for v in metrics.batch_payload_bytes]),
        "bytes_per_user": metrics.payload_bytes / max(1, metrics.users_started),
        "chunks_per_user": metrics.chunks_received / max(1, metrics.users_started),
    }

    (output / "results_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    with (output / "summary.md").open("w", encoding="utf-8") as f:
        f.write("# Gate WS-P — WebSocket Chunk Stream Load Test\n\n")
        f.write("```txt\n")
        for key in [
            "users",
            "spawn_rate",
            "run_time",
            "mode",
            "commands_sent",
            "binary_frames",
            "chunks_received",
            "payload_bytes",
            "acks_sent",
            "reconnects",
            "resumes",
            "failures",
            "users_started",
            "users_finished",
            "failure_rate",
            "bytes_per_user",
            "chunks_per_user",
        ]:
            f.write(f"{key}: {summary[key]}\n")
        f.write("```\n\n")
        f.write("## Latency\n\n")
        f.write("```json\n")
        f.write(json.dumps({
            "subscribe_latency_ms": summary["subscribe_latency_ms"],
            "resume_latency_ms": summary["resume_latency_ms"],
            "first_binary_latency_ms": summary["first_binary_latency_ms"],
            "batch_payload_bytes": summary["batch_payload_bytes"],
        }, indent=2))
        f.write("\n```\n")

    return metrics


def parse_bool(value: str) -> bool:
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
    parser.add_argument("--ack", type=parse_bool, default=True)
    parser.add_argument("--slow-client-ratio", type=float, default=0.0)
    parser.add_argument("--max-cx", type=int, default=8)
    parser.add_argument("--max-cy", type=int, default=6)
    parser.add_argument("--output", default="tests/performance/chunk_stream/load/latest")
    args = parser.parse_args()

    metrics = asyncio.run(run(args))
    print("[load] Done")
    print(f"  users_started:  {metrics.users_started}")
    print(f"  failures:       {metrics.failures}")
    print(f"  commands_sent:  {metrics.commands_sent}")
    print(f"  binary_frames:  {metrics.binary_frames}")
    print(f"  chunks_received:{metrics.chunks_received}")
    print(f"  payload_bytes:  {metrics.payload_bytes}")


if __name__ == "__main__":
    main()
