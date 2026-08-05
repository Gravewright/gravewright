#!/usr/bin/env python3
"""
Live-session WebSocket load driver.

Simulates a table of players hammering the realtime gateway with the kind of
traffic a real session produces:

    * token.move      — every user nudges its own token around the grid
    * fog.paint       — periodic reveal/hide ops (fog is pre-enabled by seed.py)
    * chat / rolls    — HTTP POST /game/chat, half plain text, half "/roll NdM"
    * reconnect       — every user periodically drops its socket and resumes

Each virtual user owns one pre-seeded token (round-robin) so token moves never
collide on CAS. The driver discovers the live scene over HTTP and reads token
ids / chunk bounds from ``fixtures.json`` written by the seed.

Run headless (defaults target the docker-compose service):

    .venv/bin/python tests/performance/ws_live/ws_live_test.py --host http://app:8000
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
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


FIXTURES_PATH = Path(__file__).resolve().parent / "fixtures.json"

CSRF_RE = re.compile(r'name="_csrf_token"\s+value="([^"]+)"')
ROOM_ID_RE = re.compile(r'data-room-id="([^"]+)"')
SCENE_ID_RE = re.compile(r'data-scene-id="([^"]+)"')
LAYER_ID_RE = re.compile(r'data-scene-layer-id="([^"]+)"')


@dataclass(frozen=True)
class SessionInfo:
    cookie_header: str
    csrf_token: str
    room_id: str
    scene_id: str
    layer_id: str
    scene_epoch: int
    tile_columns: int
    tile_rows: int
    chunk_columns: int
    chunk_rows: int


@dataclass
class Metrics:
    users_started: int = 0
    users_finished: int = 0
    failures: int = 0

    connections_opened: int = 0
    connection_failures: int = 0
    reconnects: int = 0
    resumes: int = 0
    clean_resumes: int = 0
    resync_required: int = 0

    commands_sent: int = 0
    token_moves: int = 0
    fog_paints: int = 0
    chat_messages: int = 0
    rolls: int = 0
    pan_zooms: int = 0

    errors_by_code: dict[str, int] = field(default_factory=dict)
    version_conflicts: int = 0
    http_failures: int = 0
    command_timeouts: int = 0

    move_latencies_ms: list[float] = field(default_factory=list)
    fog_latencies_ms: list[float] = field(default_factory=list)
    chat_latencies_ms: list[float] = field(default_factory=list)
    subscribe_latencies_ms: list[float] = field(default_factory=list)
    resume_latencies_ms: list[float] = field(default_factory=list)
    pan_zoom_latencies_ms: list[float] = field(default_factory=list)

    def note_error(self, code: str) -> None:
        self.errors_by_code[code] = self.errors_by_code.get(code, 0) + 1
        if code in {"version_conflict", "board_version_conflict"}:
            self.version_conflicts += 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "users_started": self.users_started,
            "users_finished": self.users_finished,
            "failures": self.failures,
            "connections_opened": self.connections_opened,
            "connection_failures": self.connection_failures,
            "reconnects": self.reconnects,
            "resumes": self.resumes,
            "clean_resumes": self.clean_resumes,
            "resync_required": self.resync_required,
            "commands_sent": self.commands_sent,
            "token_moves": self.token_moves,
            "fog_paints": self.fog_paints,
            "chat_messages": self.chat_messages,
            "rolls": self.rolls,
            "pan_zooms": self.pan_zooms,
            "version_conflicts": self.version_conflicts,
            "http_failures": self.http_failures,
            "command_timeouts": self.command_timeouts,
        }


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    import math

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


# ---------------------------------------------------------------------------
# HTTP: login, discovery, chat
# ---------------------------------------------------------------------------

def _first_match(pattern: re.Pattern[str], value: str, name: str) -> str:
    match = pattern.search(value)
    if not match:
        raise RuntimeError(f"Could not find {name} in page")
    return match.group(1)


def _cookie_header(cookie_jar: CookieJar) -> str:
    return "; ".join(f"{cookie.name}={cookie.value}" for cookie in cookie_jar)


def _request(opener, url: str, data: dict[str, str] | None = None) -> str:
    encoded = None
    headers = {"Accept": "text/html,application/json"}
    if data is not None:
        encoded = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=encoded, headers=headers)
    with opener.open(request, timeout=20) as response:
        return response.read().decode()


def _load_fixtures(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"{path} not found. Run the matching seed first.")
    return json.loads(path.read_text(encoding="utf-8"))


def discover_session(host: str, email: str, password: str, bounds: dict[str, int]) -> SessionInfo:
    """Log a single account in and discover its active room/scene/layer.

    Each account's /game page reflects its own campaign's active scene, so this
    works for both the single shared account and the sharded per-room accounts.
    """
    cookie_jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    login_page = _request(opener, f"{host}/")
    csrf = _first_match(CSRF_RE, login_page, "_csrf_token")

    _request(
        opener,
        f"{host}/login",
        {"email": email, "password": password, "_csrf_token": csrf},
    )

    game_page = _request(opener, f"{host}/game")
    scene_id = _first_match(SCENE_ID_RE, game_page, "scene_id")
    layer_id = _first_match(LAYER_ID_RE, game_page, "layer_id")
    room_id = _first_match(ROOM_ID_RE, game_page, "room_id")

    # The csrf token on the authenticated /game page is the one paired with the
    # post-login session cookie; reuse it for chat POSTs.
    game_csrf_match = CSRF_RE.search(game_page)
    csrf_token = game_csrf_match.group(1) if game_csrf_match else csrf

    manifest_raw = _request(opener, f"{host}/game/scenes/{scene_id}/manifest")
    manifest = json.loads(manifest_raw)

    return SessionInfo(
        cookie_header=_cookie_header(cookie_jar),
        csrf_token=csrf_token,
        room_id=room_id,
        scene_id=scene_id,
        layer_id=layer_id,
        scene_epoch=int(manifest["scene_epoch"]),
        tile_columns=int(bounds["tile_columns"]),
        tile_rows=int(bounds["tile_rows"]),
        chunk_columns=int(bounds["chunk_columns"]),
        chunk_rows=int(bounds["chunk_rows"]),
    )


def post_chat(host: str, session: SessionInfo, *, campaign_id: str, message: str) -> bool:
    """Fire a chat/roll message over HTTP. Returns True on 2xx."""
    data = urllib.parse.urlencode(
        {
            "campaign_id": campaign_id,
            "message": message,
            "_csrf_token": session.csrf_token,
        }
    ).encode()
    request = urllib.request.Request(
        f"{host}/game/chat",
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "Cookie": session.cookie_header,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return 200 <= response.status < 300
    except urllib.error.HTTPError as exc:
        return 200 <= exc.code < 300
    except Exception:
        return False


# ---------------------------------------------------------------------------
# WebSocket helpers
# ---------------------------------------------------------------------------

def websocket_url(host: str) -> str:
    if host.startswith("https://"):
        return f"wss://{host.removeprefix('https://')}/game/ws"
    return f"ws://{host.removeprefix('http://')}/game/ws"


async def open_ws(host: str, session: SessionInfo, args: argparse.Namespace):
    # The gateway validates the handshake Origin against ALLOWED_HOSTS-derived
    # origins when configured; send the host's own origin so it always matches.
    origin = (args.origin or host).rstrip("/")
    return await websockets.connect(
        websocket_url(host),
        additional_headers={"Cookie": session.cookie_header, "Origin": origin},
        max_size=args.max_ws_message_size,
        open_timeout=args.open_timeout,
        ping_interval=args.ping_interval,
        ping_timeout=args.ping_timeout,
        close_timeout=args.close_timeout,
    )


async def send_command(
    ws,
    metrics: Metrics,
    *,
    command_id: str,
    command: str,
    payload: dict[str, Any],
    room_id: str | None = None,
    scene_id: str | None = None,
) -> None:
    envelope: dict[str, Any] = {
        "type": "command",
        "id": command_id,
        "command": command,
        "payload": payload,
    }
    if room_id is not None:
        envelope["room_id"] = room_id
    if scene_id is not None:
        envelope["scene_id"] = scene_id
    await ws.send(json.dumps(envelope, separators=(",", ":")))
    metrics.commands_sent += 1


async def await_response(
    ws,
    *,
    event_name: str,
    command_id: str,
    timeout_seconds: float,
) -> dict[str, Any] | None:
    """
    Wait for the success event (matching command_id) or a matching error.

    Binary frames and unrelated broadcasts (presence, other users' token/fog
    updates) are drained and ignored. Returns the success payload, or None on
    error/timeout (callers classify via metrics).
    """
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        remaining = max(0.05, deadline - time.monotonic())
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except asyncio.TimeoutError:
            return None

        if isinstance(raw, bytes):
            continue

        try:
            envelope = json.loads(raw)
        except (ValueError, TypeError):
            continue

        if not isinstance(envelope, dict):
            continue

        if envelope.get("type") == "error" and envelope.get("command_id") == command_id:
            return {"__error__": True, "code": envelope.get("code", "unknown")}

        if envelope.get("event") != event_name:
            continue

        payload = envelope.get("payload") or {}
        if payload.get("command_id") != command_id:
            continue

        return payload

    return None


def _viewport(session: SessionInfo, step: int, *, width: int = 2, height: int = 2) -> dict[str, Any]:
    x_span = max(1, session.chunk_columns - width + 1)
    y_span = max(1, session.chunk_rows - height + 1)
    cx0 = step % x_span
    cy0 = (step // x_span) % y_span
    return {
        "viewport_id": "main",
        "layers": [session.layer_id],
        "cx0": cx0,
        "cy0": cy0,
        "cx1": cx0 + width - 1,
        "cy1": cy0 + height - 1,
    }


async def subscribe_viewport(
    ws,
    *,
    metrics: Metrics,
    session: SessionInfo,
    user_index: int,
    generation: int,
) -> None:
    command_id = f"u{user_index}-sub-{generation}"
    started = time.monotonic()
    await send_command(
        ws,
        metrics,
        command_id=command_id,
        command="viewport.subscribe",
        room_id=session.room_id,
        scene_id=session.scene_id,
        payload={**_viewport(session, generation), "generation": generation, "known": {}},
    )
    payload = await await_response(
        ws, event_name="scene.viewport.ready", command_id=command_id, timeout_seconds=20.0
    )
    if payload is None or payload.get("__error__"):
        metrics.command_timeouts += 1
        if isinstance(payload, dict) and payload.get("__error__"):
            metrics.note_error(payload.get("code", "subscribe_error"))
        return
    metrics.subscribe_latencies_ms.append((time.monotonic() - started) * 1000.0)


# Viewport sizes (in chunks) a player cycles through when zooming: tight focus,
# the default frame, and a zoomed-out overview.
_ZOOM_LEVELS = [(1, 1), (2, 2), (3, 3)]


async def do_pan_zoom(
    ws,
    *,
    metrics: Metrics,
    session: SessionInfo,
    user_index: int,
    generation: int,
    seq: int,
) -> None:
    """Re-subscribe the viewport to a fresh region/zoom mid-session.

    Models a user panning the map or changing zoom: it requests a different
    chunk window (panned by ``seq``) at a random zoom level. The gateway drops
    frames tagged with an older generation, so callers must advance the
    generation before each pan/zoom — hence ``generation`` is passed in already
    bumped.
    """
    width, height = random.choice(_ZOOM_LEVELS)
    command_id = f"u{user_index}-pan-{seq}"
    started = time.monotonic()
    await send_command(
        ws,
        metrics,
        command_id=command_id,
        command="viewport.subscribe",
        room_id=session.room_id,
        scene_id=session.scene_id,
        payload={
            **_viewport(session, seq, width=width, height=height),
            "generation": generation,
            "known": {},
        },
    )
    payload = await await_response(
        ws, event_name="scene.viewport.ready", command_id=command_id, timeout_seconds=20.0
    )
    if payload is None or payload.get("__error__"):
        metrics.command_timeouts += 1
        if isinstance(payload, dict) and payload.get("__error__"):
            metrics.note_error(payload.get("code", "pan_zoom_error"))
        return
    metrics.pan_zooms += 1
    metrics.pan_zoom_latencies_ms.append((time.monotonic() - started) * 1000.0)


async def resume_session(
    ws,
    *,
    metrics: Metrics,
    session: SessionInfo,
    user_index: int,
    generation: int,
) -> None:
    command_id = f"u{user_index}-resume-{generation}"
    started = time.monotonic()
    await send_command(
        ws,
        metrics,
        command_id=command_id,
        command="session.resume",
        room_id=session.room_id,
        scene_id=session.scene_id,
        payload={
            "active_scene_id": session.scene_id,
            "scene_epoch": session.scene_epoch,
            "last_event_seq": 0,
            "viewport": {**_viewport(session, generation), "generation": generation},
            "known_chunks": {},
        },
    )
    metrics.resumes += 1
    payload = await await_response(
        ws, event_name="scene.session.resumed", command_id=command_id, timeout_seconds=20.0
    )
    if payload is None or payload.get("__error__"):
        metrics.command_timeouts += 1
        if isinstance(payload, dict) and payload.get("__error__"):
            metrics.note_error(payload.get("code", "resume_error"))
        return
    metrics.resume_latencies_ms.append((time.monotonic() - started) * 1000.0)
    if payload.get("resync_required") is True:
        metrics.resync_required += 1
    else:
        metrics.clean_resumes += 1


async def do_token_move(
    ws,
    *,
    metrics: Metrics,
    session: SessionInfo,
    user_index: int,
    token_id: str,
    seq: int,
) -> None:
    # Stay a couple cells inside the bounds so moves are always valid.
    gx = random.randint(1, max(1, session.tile_columns - 2))
    gy = random.randint(1, max(1, session.tile_rows - 2))
    command_id = f"u{user_index}-move-{seq}"
    started = time.monotonic()
    await send_command(
        ws,
        metrics,
        command_id=command_id,
        command="token.move",
        room_id=session.room_id,
        payload={
            "scene_id": session.scene_id,
            "token_id": token_id,
            "grid_x": gx,
            "grid_y": gy,
        },
    )
    payload = await await_response(
        ws, event_name="token.command.ack", command_id=command_id, timeout_seconds=10.0
    )
    if payload is None:
        metrics.command_timeouts += 1
        return
    if payload.get("__error__"):
        metrics.note_error(payload.get("code", "token_error"))
        return
    metrics.token_moves += 1
    metrics.move_latencies_ms.append((time.monotonic() - started) * 1000.0)


async def do_fog_paint(
    ws,
    *,
    metrics: Metrics,
    session: SessionInfo,
    user_index: int,
    seq: int,
) -> None:
    mode = "reveal" if seq % 2 == 0 else "hide"
    cx = random.uniform(1.0, max(1.0, session.tile_columns - 1.0))
    cy = random.uniform(1.0, max(1.0, session.tile_rows - 1.0))
    command_id = f"u{user_index}-fog-{seq}"
    started = time.monotonic()
    await send_command(
        ws,
        metrics,
        command_id=command_id,
        command="fog.paint",
        room_id=session.room_id,
        payload={
            "scene_id": session.scene_id,
            # expected_version omitted on purpose; the test app runs with
            # FOG_REQUIRE_EXPECTED_VERSION=false so paint is last-write-wins
            # and concurrent painters don't storm version_conflict.
            "ops": [
                {
                    "mode": mode,
                    "shape": "circle",
                    "geom": {
                        "center_x_cells": round(cx, 2),
                        "center_y_cells": round(cy, 2),
                        "radius_cells": float(random.randint(2, 5)),
                    },
                }
            ],
        },
    )
    payload = await await_response(
        ws, event_name="fog.command.ack", command_id=command_id, timeout_seconds=10.0
    )
    if payload is None:
        metrics.command_timeouts += 1
        return
    if payload.get("__error__"):
        metrics.note_error(payload.get("code", "fog_error"))
        return
    metrics.fog_paints += 1
    metrics.fog_latencies_ms.append((time.monotonic() - started) * 1000.0)


_ROLL_EXPRESSIONS = ["/roll 1d20", "/roll 2d6+3", "/r 1d20+5", "/roll 3d6", "/roll 1d100"]
_CHAT_LINES = [
    "Moving up to flank.",
    "I ready an action.",
    "Watch the left corridor.",
    "Holding position.",
    "Anyone have healing?",
]


def chat_payload() -> tuple[str, bool]:
    """Return (message, is_roll). Roughly half plain chat, half dice rolls."""
    if random.random() < 0.5:
        return random.choice(_ROLL_EXPRESSIONS), True
    return random.choice(_CHAT_LINES), False


async def do_chat(
    host: str,
    *,
    metrics: Metrics,
    session: SessionInfo,
) -> None:
    message, is_roll = chat_payload()
    started = time.monotonic()
    ok = await asyncio.to_thread(
        post_chat, host, session, campaign_id=session.room_id, message=message
    )
    if not ok:
        metrics.http_failures += 1
        return
    metrics.chat_latencies_ms.append((time.monotonic() - started) * 1000.0)
    if is_roll:
        metrics.rolls += 1
    else:
        metrics.chat_messages += 1


# ---------------------------------------------------------------------------
# Virtual user
# ---------------------------------------------------------------------------

async def virtual_user(
    user_index: int,
    *,
    email: str,
    password: str,
    token_id: str,
    bounds: dict[str, int],
    host: str,
    run_until: float,
    args: argparse.Namespace,
    metrics: Metrics,
) -> None:
    metrics.users_started += 1
    generation = 1
    first_connection = True
    seq = 0

    try:
        session = await asyncio.to_thread(discover_session, host, email, password, bounds)
    except Exception as exc:
        metrics.failures += 1
        print(f"[user {user_index}] login/discovery failed: {exc}")
        return

    try:
        while time.monotonic() < run_until:
            try:
                ws = await open_ws(host, session, args)
                metrics.connections_opened += 1
            except Exception:
                # Under stress the gateway may refuse/timeout the handshake.
                # A real client retries rather than giving up, so back off and
                # try again until the run ends instead of killing the user.
                metrics.connection_failures += 1
                if time.monotonic() >= run_until:
                    break
                await asyncio.sleep(random.uniform(0.5, 2.0))
                continue

            try:
                async with ws:
                    if first_connection:
                        await subscribe_viewport(
                            ws,
                            metrics=metrics,
                            session=session,
                            user_index=user_index,
                            generation=generation,
                        )
                        first_connection = False
                    else:
                        # Reconnect path: resume the prior scene session.
                        await resume_session(
                            ws,
                            metrics=metrics,
                            session=session,
                            user_index=user_index,
                            generation=generation,
                        )

                    actions_this_connection = 0
                    reconnect_after = random.randint(
                        args.reconnect_every_min_actions,
                        args.reconnect_every_max_actions,
                    )

                    while time.monotonic() < run_until:
                        seq += 1
                        actions_this_connection += 1

                        # Token moves are the bread-and-butter traffic; fog and
                        # chat are interleaved at lower frequency.
                        await do_token_move(
                            ws,
                            metrics=metrics,
                            session=session,
                            user_index=user_index,
                            token_id=token_id,
                            seq=seq,
                        )

                        if seq % args.fog_every == 0:
                            await do_fog_paint(
                                ws,
                                metrics=metrics,
                                session=session,
                                user_index=user_index,
                                seq=seq,
                            )

                        if seq % args.chat_every == 0:
                            await do_chat(host, metrics=metrics, session=session)

                        if seq % args.pan_every == 0:
                            # Advance the generation so the gateway keeps the new
                            # viewport's frames instead of dropping them as stale.
                            generation += 1
                            await do_pan_zoom(
                                ws,
                                metrics=metrics,
                                session=session,
                                user_index=user_index,
                                generation=generation,
                                seq=seq,
                            )

                        await asyncio.sleep(
                            random.uniform(args.min_think, args.max_think)
                        )

                        if actions_this_connection >= reconnect_after:
                            metrics.reconnects += 1
                            generation += 1
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


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_outputs(
    *,
    output: Path,
    args: argparse.Namespace,
    metrics: Metrics,
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
        **snap,
        "errors_by_code": metrics.errors_by_code,
        "commands_per_second": metrics.commands_sent / duration,
        "token_moves_per_second": metrics.token_moves / duration,
        "fog_paints_per_second": metrics.fog_paints / duration,
        "chat_per_second": (metrics.chat_messages + metrics.rolls) / duration,
        "pan_zooms_per_second": metrics.pan_zooms / duration,
        "token_move_latency_ms": summary_stats(metrics.move_latencies_ms),
        "fog_paint_latency_ms": summary_stats(metrics.fog_latencies_ms),
        "chat_latency_ms": summary_stats(metrics.chat_latencies_ms),
        "subscribe_latency_ms": summary_stats(metrics.subscribe_latencies_ms),
        "resume_latency_ms": summary_stats(metrics.resume_latencies_ms),
        "pan_zoom_latency_ms": summary_stats(metrics.pan_zoom_latencies_ms),
    }

    (output / "results_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    with (output / "summary.md").open("w", encoding="utf-8") as f:
        f.write("# WS Live Session — token / fog / chat / reconnect load\n\n")
        f.write("## Result\n\n```txt\n")
        f.write(f"finished:            {finished}\n")
        f.write(f"host:                {args.host}\n")
        f.write(f"users:               {args.users}\n")
        f.write(f"run_time:            {args.run_time}s\n")
        f.write(f"actual_duration:     {duration:.1f}s\n")
        f.write(f"users_started:       {metrics.users_started}\n")
        f.write(f"users_finished:      {metrics.users_finished}\n")
        f.write(f"failures:            {metrics.failures}\n")
        f.write(f"connection_failures: {metrics.connection_failures}\n")
        f.write("```\n\n")

        f.write("## Realtime traffic\n\n```txt\n")
        f.write(f"commands_sent:       {metrics.commands_sent}\n")
        f.write(f"token_moves:         {metrics.token_moves}\n")
        f.write(f"fog_paints:          {metrics.fog_paints}\n")
        f.write(f"chat_messages:       {metrics.chat_messages}\n")
        f.write(f"rolls:               {metrics.rolls}\n")
        f.write(f"pan_zooms:           {metrics.pan_zooms}\n")
        f.write(f"connections_opened:  {metrics.connections_opened}\n")
        f.write(f"reconnects:          {metrics.reconnects}\n")
        f.write(f"resumes:             {metrics.resumes}\n")
        f.write(f"clean_resumes:       {metrics.clean_resumes}\n")
        f.write(f"resync_required:     {metrics.resync_required}\n")
        f.write(f"version_conflicts:   {metrics.version_conflicts}\n")
        f.write(f"command_timeouts:    {metrics.command_timeouts}\n")
        f.write(f"http_failures:       {metrics.http_failures}\n")
        f.write(f"errors_by_code:      {json.dumps(metrics.errors_by_code)}\n")
        f.write("```\n\n")

        f.write("## Latency (ms)\n\n```json\n")
        f.write(
            json.dumps(
                {
                    "token_move": summary["token_move_latency_ms"],
                    "fog_paint": summary["fog_paint_latency_ms"],
                    "chat": summary["chat_latency_ms"],
                    "subscribe": summary["subscribe_latency_ms"],
                    "resume": summary["resume_latency_ms"],
                    "pan_zoom": summary["pan_zoom_latency_ms"],
                },
                indent=2,
            )
        )
        f.write("\n```\n")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def run(args: argparse.Namespace) -> Metrics:
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    # Chat POSTs run on the default thread executor; size it for the user count
    # so HTTP chat doesn't queue behind a tiny default pool under stress.
    from concurrent.futures import ThreadPoolExecutor

    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=args.http_workers, thread_name_prefix="chat")
    )

    fixtures = _load_fixtures(Path(args.fixtures))
    bounds = {
        "tile_columns": fixtures["tile_columns"],
        "tile_rows": fixtures["tile_rows"],
        "chunk_columns": fixtures["chunk_columns"],
        "chunk_rows": fixtures["chunk_rows"],
    }
    password = fixtures["password"]

    # Build one (email, token_id) assignment per virtual user. Multiroom uses a
    # distinct account per player so the gateway fan-out stays scoped to a room;
    # single-room shares one account and spreads the seeded tokens across users.
    if "slots" in fixtures:
        assignments = [(s["email"], s["token_id"]) for s in fixtures["slots"]]
        mode = f"multiroom ({len(assignments)} players)"
    else:
        token_ids = fixtures["token_ids"]
        assignments = [
            (fixtures["email"], token_ids[i % len(token_ids)]) for i in range(args.users)
        ]
        mode = "single-room"
    print(f"[ws-live] fixtures: {mode}; spawning {args.users} users")

    metrics = Metrics()
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
            writer.writerow(
                [
                    "timestamp",
                    "elapsed_seconds",
                    "users_spawned",
                    "tasks_active",
                    "commands_sent",
                    "token_moves",
                    "fog_paints",
                    "chat_messages",
                    "rolls",
                    "pan_zooms",
                    "reconnects",
                    "resumes",
                    "version_conflicts",
                    "command_timeouts",
                    "http_failures",
                    "failures",
                ]
            )

            users_created = 0
            spawn_interval = 1.0 / max(0.001, args.spawn_rate)
            next_spawn = time.monotonic()

            while time.monotonic() < run_until and not stop_requested.is_set():
                now = time.monotonic()

                while users_created < args.users and now >= next_spawn:
                    email, token_id = assignments[users_created % len(assignments)]
                    task = asyncio.create_task(
                        virtual_user(
                            users_created,
                            email=email,
                            password=password,
                            token_id=token_id,
                            bounds=bounds,
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
                        print(f"[ws-live] task error: {exc}")
                tasks -= done

                snap = metrics.snapshot()
                writer.writerow(
                    [
                        int(time.time()),
                        round(time.monotonic() - started_at, 3),
                        users_created,
                        len(tasks),
                        snap["commands_sent"],
                        snap["token_moves"],
                        snap["fog_paints"],
                        snap["chat_messages"],
                        snap["rolls"],
                        snap["pan_zooms"],
                        snap["reconnects"],
                        snap["resumes"],
                        snap["version_conflicts"],
                        snap["command_timeouts"],
                        snap["http_failures"],
                        snap["failures"],
                    ]
                )
                f.flush()

                await asyncio.sleep(5.0)

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        metrics.failures += 1
                        print(f"[ws-live] task error: {result}")

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://app:8000")
    parser.add_argument("--origin", default="", help="WS handshake Origin (defaults to --host)")
    parser.add_argument("--users", type=int, default=15)
    parser.add_argument("--spawn-rate", type=float, default=3.0)
    parser.add_argument("--run-time", type=int, default=1200, help="seconds (default 20 min)")
    parser.add_argument(
        "--time",
        type=float,
        default=0.0,
        help="run time in MINUTES (overrides --run-time when > 0)",
    )

    parser.add_argument("--fog-every", type=int, default=5, help="fog.paint every N token moves")
    parser.add_argument("--chat-every", type=int, default=8, help="chat/roll every N token moves")
    parser.add_argument(
        "--pan-every", type=int, default=6, help="pan/zoom (viewport re-subscribe) every N token moves"
    )
    parser.add_argument("--min-think", type=float, default=0.4)
    parser.add_argument("--max-think", type=float, default=1.5)

    parser.add_argument("--reconnect-every-min-actions", type=int, default=25)
    parser.add_argument("--reconnect-every-max-actions", type=int, default=45)

    parser.add_argument("--open-timeout", type=float, default=30)
    parser.add_argument("--ping-interval", type=float, default=20)
    parser.add_argument("--ping-timeout", type=float, default=20)
    parser.add_argument("--close-timeout", type=float, default=5)
    parser.add_argument("--max-ws-message-size", type=int, default=16 * 1024 * 1024)
    parser.add_argument("--http-workers", type=int, default=64, help="thread pool for chat POSTs")
    parser.add_argument(
        "--fixtures",
        default=str(FIXTURES_PATH),
        help="fixtures json (single-room or multiroom) written by a seed script",
    )

    parser.add_argument("--output", default="tests/performance/ws_live/results")

    args = parser.parse_args()

    # --time is the operator-facing knob (minutes); fold it into run_time
    # (seconds) which the rest of the driver uses.
    if args.time and args.time > 0:
        args.run_time = int(round(args.time * 60))

    try:
        metrics = asyncio.run(run(args))
    except KeyboardInterrupt:
        print("[ws-live] Interrupted.")
        return

    print("[ws-live] Done")
    for key, value in metrics.snapshot().items():
        print(f"  {key:22s} {value}")


if __name__ == "__main__":
    main()
