"""Replay a GM + players table session against the Runner server and measure latency.

The scenario uses a disposable copy of a campaign database and media, starts the
Runner's Daphne entry point with measurement hooks (realtime_session_server.py) and
drives real browsers: the board's own camera heartbeat, pointer sharing and
subscriptions run as they do for players, while scripted actions reproduce a
session's command mix (sheet saves, token drags and moves, rolls, chat, camera pans)
at configurable rates. Both sides record timings; realtime_session_report.py turns
them into a report.

Example (copies the campaign from an existing installation's data folder once):

    uv run --locked python tests/e2e/realtime_session.py \\
        --data-from <installation>/data --workdir <empty-or-existing-dir> \\
        --duration 1200 --browser-executable <chromium-headless-shell>

The source data folder is only read. Each run gets its own copy under
``<workdir>/runs/`` so before/after comparisons start from the same state.
"""

import argparse
import asyncio
import json
import os
import random
import re
import secrets
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]

# Per-minute rates, taken from the busiest 10-minute windows of the 2026-11-14 session
# receipts (sheet saves dominate; rolls and chat came from the chat log).
DEFAULT_RATES = {
    "gm": {"sheet": 0.9, "move": 0.4, "roll": 0.3, "chat": 0.1, "pan": 4.0, "zoom": 0.5},
    "player": {"sheet": 0.8, "move": 0.25, "roll": 0.3, "chat": 0.06, "pan": 1.0, "zoom": 0.2},
}
POINTER_ACTIVE = {"gm": 0.5, "player": 0.4}
# The 2026-11-14 GM previewed scenes, took the group to the combat scene, brought it
# back, and later switched briefly again (maps receipts). Fractions of the session.
SCENE_SCRIPT = {
    "today": [(0.15, "navigate", "combat"), (0.155, "navigate", "home"), (0.16, "navigate", "combat"),
              (0.165, "navigate", None), (0.18, "activate", "combat"), (0.45, "activate", "home"),
              (0.85, "activate", "combat"), (0.88, "activate", "home")],
    "none": [],
}

HOOK = r"""
(() => {
  const now = () => performance.timeOrigin + performance.now();
  const log = [];
  window.__gwDrain = () => log.splice(0, log.length);
  window.__gwTokens = new Map();
  window.__gwJoined = false;
  let connections = 0;
  const short = value => typeof value === 'string' ? value.slice(0, 8) : value;
  const marker = text => { const found = typeof text === 'string' && text.match(/\[gw:([a-z0-9]+)\]/); return found ? found[1] : undefined; };
  function remember(rows, mapId, full) {
    if (!Array.isArray(rows)) return;
    if (full) for (const [id, row] of window.__gwTokens) if (row.mapId === mapId) window.__gwTokens.delete(id);
    for (const row of rows) if (row && row.id) window.__gwTokens.set(row.id, {...(window.__gwTokens.get(row.id) || {}), ...row, mapId: row.mapId || mapId});
  }
  function received(record, type, p) {
    if (type === 'error' || type.endsWith('.error') || type.endsWith('.ack')) { record.rid = p.requestId; if (p.code) record.code = p.code; }
    if (type === 'table.joined') window.__gwJoined = true;
    if (type === 'tokens.state') {
      const rows = p.tokens || (p.upserts && p.upserts.tokens) || [];
      record.full = !p.delta;
      record.tk = rows.map(r => [short(r.id), r.gridX, r.gridY, r.version]);
      remember(rows, p.mapId, !p.delta);
      if (p.removes && p.removes.tokens) for (const id of p.removes.tokens) window.__gwTokens.delete(id);
    }
    if (type === 'tokens.ack' && p.result && Array.isArray(p.result.tokens)) remember(p.result.tokens, null, false);
    if (type === 'token.drag') { record.stream = short(p.stream); record.phase = p.phase; record.pos = (p.positions || []).map(r => [short(r.id), r.gridX, r.gridY]); }
    if (type === 'maps.cursor') { record.pos = p.position ? [p.position.x, p.position.y] : null; record.who = short(p.userId); }
    if (type === 'chat.message') { record.mid = p.id; record.mark = marker(p.html) || marker(p.text); record.roll = !!p.roll; }
    if (type === 'chat.history') record.n = (p.messages || []).length;
    if (type === 'table.presence') record.n = (p.members || []).length;
    if (type === 'resources.state') record.module = p.module;
  }
  function sent(record, type, p) {
    if (p.requestId) record.rid = p.requestId;
    if (type.endsWith('.command')) record.action = p.action;
    if (type === 'tokens.command' && p.data && p.action === 'move') record.move = [short(p.data.id), p.data.gridX, p.data.gridY];
    if (type === 'maps.cursor') record.pos = p.position ? [p.position.x, p.position.y] : null;
    if (type === 'token.drag') { record.stream = short(p.stream); record.phase = p.phase; record.pos = (p.positions || []).map(r => [short(r.id), r.gridX, r.gridY]); }
    if (type === 'chat.say') record.mark = marker(p.text);
    if (type === 'scene.viewport') record.gen = p.generation;
    if (type === 'resources.sync') record.module = p.module;
  }
  const Native = window.WebSocket;
  window.WebSocket = class extends Native {
    constructor(...args) {
      super(...args);
      const conn = this.__gwConn = ++connections;
      log.push({t: now(), ev: 'connecting', conn});
      this.addEventListener('open', () => log.push({t: now(), ev: 'open', conn}));
      this.addEventListener('close', event => { window.__gwJoined = false; log.push({t: now(), ev: 'close', conn, code: event.code}); });
      this.addEventListener('message', event => {
        const t = now();
        let message;
        try { message = JSON.parse(event.data); } catch { return; }
        const record = {t, ev: 'recv', conn, type: message.type, bytes: event.data.length};
        try { received(record, message.type || '', message.payload || {}); } catch {}
        log.push(record);
      });
    }
    send(data) {
      try {
        const message = JSON.parse(data);
        const record = {t: now(), ev: 'send', conn: this.__gwConn, type: message.type, bytes: data.length};
        sent(record, message.type || '', message.payload || {});
        log.push(record);
      } catch {}
      return super.send(data);
    }
  };
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const outcome = async action => {
    const started = now();
    try { await action(); return {ok: true, ms: now() - started}; }
    catch (error) { return {ok: false, ms: now() - started, error: String(error && error.message || error).slice(0, 120)}; }
  };
  window.__gwBot = {
    ready: () => window.__gwJoined && !!window.gravewrightMaps?.current && window.__gwTokens.size > 0,
    tokens: () => [...window.__gwTokens.entries()].filter(([, row]) => row.mapId === window.gravewrightMaps?.current?.id).map(([id, row]) => ({id, ...row})),
    board() {
      const canvases = [...document.querySelectorAll('canvas')].map(c => c.getBoundingClientRect()).filter(r => r.width > 200 && r.height > 200);
      canvases.sort((a, b) => b.width * b.height - a.width * a.height);
      const r = canvases[0];
      return r ? {x: r.x, y: r.y, width: r.width, height: r.height} : null;
    },
    move(id, gridX, gridY, steps) {
      return outcome(async () => {
        const row = window.__gwTokens.get(id);
        const mapId = window.gravewrightMaps.current.id;
        const stream = crypto.randomUUID();
        const path = [];
        for (let step = 1; step <= steps; step++) {
          const x = Number((row.gridX + (gridX - row.gridX) * step / steps).toFixed(4));
          const y = Number((row.gridY + (gridY - row.gridY) * step / steps).toFixed(4));
          path.push({gridX: x, gridY: y});
          window.gravewrightRealtime.tokenDrag({mapId, stream, phase: 'update', positions: [{id, gridX: x, gridY: y, version: row.version, path: [[x, y]]}]});
          await sleep(110 + Math.random() * 60);
        }
        try {
          await window.gravewrightRealtime.resourceCommand('tokens', 'move', {mapId, id, gridX, gridY, expectedVersion: row.version, path: path.slice(0, -1)});
        } finally {
          window.gravewrightRealtime.tokenDrag({mapId, stream, phase: 'end'});
        }
      });
    },
    sheet(actorId, tokenId, delta) {
      return outcome(async () => {
        const campaign = document.getElementById('table-workspace').dataset.tableId;
        const query = tokenId ? `?tokenId=${tokenId}` : '';
        const response = await fetch(`/api/containers/${campaign}/actors/${actorId}/sheet${query}`, {cache: 'no-store'});
        if (!response.ok) throw new Error('sheet ' + response.status);
        const sheet = await response.json();
        const bars = sheet.data && sheet.data.bars;
        const slot = bars && Object.keys(bars).find(key => bars[key] && Number.isFinite(bars[key].value));
        if (slot) {
          const bar = bars[slot];
          const max = Number.isFinite(bar.max) ? bar.max : bar.value + 1;
          bar.value = Math.max(0, Math.min(max, bar.value + delta));
        }
        await window.gravewrightRealtime.resourceCommand('actors', 'sheet.save', {
          actorId, ...(tokenId ? {tokenId} : {}), name: sheet.name, version: sheet.version, sheetVersion: sheet.sheetVersion, data: sheet.data,
        });
      });
    },
    say(text) { window.gravewrightRealtime.say(text); return {ok: true}; },
    openSheet(tokenId) {
      const row = window.__gwTokens.get(tokenId);
      if (!row || !window.gravewrightActors) return {ok: false, error: 'no token or actors workspace'};
      window.gravewrightActors.open(row.actorId, {...row});
      return {ok: true};
    },
    sheetsOpen: () => document.querySelectorAll('.token-sheet, .actor-directory__sheet').length,
  };
})();
"""


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def copy_database(source, target):
    with closing(sqlite3.connect(f"file:{source}?mode=ro", uri=True)) as src, \
            closing(sqlite3.connect(target)) as dst:
        src.backup(dst)


def prepare_fixture(args):
    """Copy the database, media and public Marketplace keys once; later runs reuse them."""
    fixture = args.workdir / "fixture"
    source = args.data_from.resolve() if args.data_from else None
    if not (fixture / "gravewright.sqlite3").exists():
        if source is None:
            raise SystemExit("No fixture in the work directory; pass --data-from <data folder>.")
        if not (source / "gravewright.sqlite3").is_file():
            raise SystemExit(f"{source} has no gravewright.sqlite3.")
        fixture.mkdir(parents=True)
        copy_database(source / "gravewright.sqlite3", fixture / "gravewright.sqlite3")
        shutil.copytree(source / "media", fixture / "media", symlinks=True)
    keys = fixture / "marketplace" / "trusted-keys.json"
    if source is not None and not keys.exists():
        # Installed packages are verified against these public keys before serving.
        found = sorted((source / "marketplace").glob("*/trusted-keys.json"))
        if found:
            keys.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(found[0], keys)
    return fixture


def environment(run, port, fixture):
    """The Runner tunnel profile (as in the measured installation), with isolated paths."""
    values = {}
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"')
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("DJANGO_", "GRAVEWRIGHT_")) and key not in values}
    env.update(values)
    tmp = run / "runner-data" / "tmp"
    for name in ("staticfiles", "compendiums", "tmp", "xdg-cache"):
        (run / "runner-data" / name).mkdir(parents=True, exist_ok=True)
    env.update(
        DEFAULT_LOCALE="pt-BR",
        DJANGO_SETTINGS_MODULE="config.runner", DJANGO_DEBUG="false",
        DJANGO_SECRET_KEY=secrets.token_urlsafe(64), DJANGO_ALLOWED_HOSTS="*",
        DJANGO_SECURE_COOKIES="false", DATABASE_ECHO="false",
        GRAVEWRIGHT_HOST="127.0.0.1", GRAVEWRIGHT_PORT=str(port),
        GRAVEWRIGHT_PUBLIC_ORIGIN="", GRAVEWRIGHT_ALLOW_TUNNELS="true",
        GRAVEWRIGHT_REDIS_URL="", TRUSTED_PROXIES="127.0.0.1/32,::1/128",
        GRAVEWRIGHT_DATABASE=str(run / "gravewright.sqlite3"),
        GRAVEWRIGHT_MEDIA_ROOT=str(run / "media"),
        GRAVEWRIGHT_MODULES_ROOT=str(run / "media" / "modules"),
        GRAVEWRIGHT_RUNNER_DATA=str(run / "runner-data"),
        GRAVEWRIGHT_RUNNER_TOKEN=secrets.token_urlsafe(32),
        # No network: no marketplace or release checks during the measurement.
        GRAVEWRIGHT_MARKETPLACE_URL="", GRAVEWRIGHT_RELEASES_REPOSITORY="",
        GRAVEWRIGHT_MARKETPLACE_KEYS_FILE=str(fixture / "marketplace" / "trusted-keys.json")
        if (fixture / "marketplace" / "trusted-keys.json").exists() else "",
        PYTHONUTF8="1", PYTHONPATH=str(ROOT),
        TMPDIR=str(tmp), TMP=str(tmp), TEMP=str(tmp),
        XDG_CACHE_HOME=str(run / "runner-data" / "xdg-cache"),
    )
    return env


SEED = r"""
import json, sys
import django
django.setup()
from django.conf import settings
from django.test import Client
from gravewright.campaigns.models import Campaign, Membership
from gravewright.chat.models import Message
from gravewright.maps.models import Broadcast
from gravewright.tokens.models import Token
from gravewright.tokens.services import control
request = json.loads(sys.argv[1])
campaign = Campaign.objects.get(pk=request["campaign"]) if request["campaign"] else max(
    Campaign.objects.all(), key=lambda c: Message.objects.filter(campaign=c).order_by("-id").values_list("id", flat=True).first() or 0)
gm = Membership.objects.filter(campaign=campaign, role="gm").order_by("pk").first()
if request["players"]:
    players = list(Membership.objects.filter(campaign=campaign, role="player", pk__in=request["players"]).order_by("pk"))
else:
    def last(member):
        return Message.objects.filter(campaign=campaign, author_id=member.user_id).order_by("-id").values_list("id", flat=True).first() or 0
    players = sorted(Membership.objects.filter(campaign=campaign, role="player"), key=last, reverse=True)[:request["count"]]
    players.sort(key=lambda m: m.pk)
scene = Broadcast.objects.get(campaign=campaign).scene
tokens = list(Token.objects.filter(scene=scene).select_related("actor"))
from gravewright.combat.models import Encounter
from gravewright.maps.models import Scene
others = list(Scene.objects.filter(campaign=campaign, visibility="players").exclude(pk=scene.pk))
active = set(Encounter.objects.filter(scene__in=others, active=True).values_list("scene_id", flat=True))
others.sort(key=lambda row: (row.pk not in active, row.name))
result = {"campaign": str(campaign.pk), "scene": str(scene.pk), "cookie": settings.SESSION_COOKIE_NAME,
          "combat_scene": str(others[0].pk) if others else None,
          "scene_width": scene.width, "scene_height": scene.height, "participants": []}
for member in [gm, *players]:
    label = "gm" if member.role == "gm" else f"p{member.pk}"
    client = Client()
    client.force_login(member.user)
    result["participants"].append({
        "label": label, "role": member.role, "user": str(member.user_id), "member": member.pk,
        "session": client.session.session_key,
        "tokens": [{"id": str(t.pk), "actor": str(t.actor_id)} for t in tokens if control(t, member)],
    })
print(json.dumps(result))
"""


def run_manage(env, *args, log):
    subprocess.run([sys.executable, "manage.py", *args], cwd=ROOT, env=env, check=True,
                   stdout=log, stderr=log)


def wait_ready(base, server, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError("Server exited during startup; see server-console.log")
        try:
            urlopen(base + "/", timeout=2).close()
            return
        except HTTPError:
            return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError("Server did not become ready")


class Participant:
    def __init__(self, info, page, rates, active, rng, deadline, started, logfile, duration):
        self.info, self.page, self.rates, self.active = info, page, rates, active
        self.rng, self.deadline, self.started, self.duration = rng, deadline, started, duration
        self.log = logfile
        self.label = info["label"]
        self.actions = []
        self.board = None
        self.board_checked = 0.0
        self.open_sheet_windows = False

    def phase_factor(self, kind):
        """Exploration, then combat (rolls, sheets, moves), then talk."""
        progress = (time.monotonic() - self.started) / self.duration
        if progress < 0.35:
            return {"pan": 1.5, "move": 1.2, "roll": 0.4, "sheet": 0.6}.get(kind, 1.0)
        if progress < 0.8:
            return {"pan": 0.8, "move": 1.0, "roll": 1.6, "sheet": 1.4}.get(kind, 1.0)
        return {"pan": 0.6, "move": 0.4, "roll": 0.5, "sheet": 0.6, "chat": 2.5}.get(kind, 1.0)

    def schedule(self, kind, now):
        rate = self.rates.get(kind, 0) * self.phase_factor(kind)
        return now + (self.rng.expovariate(rate / 60) if rate > 0 else float("inf"))

    async def drain(self):
        try:
            records = await self.page.evaluate("window.__gwDrain ? window.__gwDrain() : []")
        except Exception:  # noqa: BLE001 - page navigating; drained on the next pass
            return
        for record in records:
            self.log.write(json.dumps({"label": self.label, **record}) + "\n")

    async def refresh_board(self):
        self.board = await self.page.evaluate("window.__gwBot.board()")
        self.board_checked = time.monotonic()

    def point(self):
        b = self.board
        return (b["x"] + b["width"] * self.rng.uniform(0.15, 0.85),
                b["y"] + b["height"] * self.rng.uniform(0.15, 0.85))

    async def wander(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            x, y = self.point()
            await self.page.mouse.move(x, y, steps=self.rng.randint(6, 16))
            await asyncio.sleep(self.rng.uniform(0.05, 0.4))

    async def pan(self):
        x, y = self.point()
        await self.page.mouse.move(x, y)
        await self.page.mouse.down(button="right")
        await self.page.mouse.move(x + self.rng.uniform(-260, 260), y + self.rng.uniform(-180, 180),
                                   steps=self.rng.randint(12, 28))
        await self.page.mouse.up(button="right")

    async def zoom(self):
        x, y = self.point()
        await self.page.mouse.move(x, y)
        await self.page.mouse.wheel(0, self.rng.choice([-240, 240]))

    async def act(self, kind):
        started = time.time()
        result = {"ok": True}
        if time.monotonic() - self.board_checked > 15:
            # Scene changes can replace the board canvas.
            await self.refresh_board()
        if kind == "pan":
            await self.pan()
        elif kind == "zoom":
            await self.zoom()
        elif kind in ("move", "sheet"):
            tokens = await self.page.evaluate("window.__gwBot.tokens()")
            own = {t["id"] for t in self.info["tokens"]}
            choices = [t for t in tokens if t["id"] in own]
            if not choices and kind == "sheet" and self.info["tokens"]:
                # Another scene without this character's token: edit the actor sheet itself.
                actor = self.rng.choice(self.info["tokens"])["actor"]
                result = await self.page.evaluate(
                    "([actor, delta]) => window.__gwBot.sheet(actor, null, delta)",
                    [actor, self.rng.choice([-3, -2, -1, 1, 2])])
            elif not choices:
                result = {"ok": None, "error": "no controlled token on this scene"}
            else:
                token = self.rng.choice(choices)
                if kind == "move":
                    dx, dy = self.rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (2, 0), (0, 2), (-2, 0), (0, -2)])
                    gx = max(0, round(token["gridX"]) + dx)
                    gy = max(0, round(token["gridY"]) + dy)
                    result = await self.page.evaluate(
                        "([id, x, y, steps]) => window.__gwBot.move(id, x, y, steps)",
                        [token["id"], gx, gy, self.rng.randint(3, 7)])
                else:
                    result = await self.page.evaluate(
                        "([actor, token, delta]) => window.__gwBot.sheet(actor, token, delta)",
                        [token["actorId"], token["id"], self.rng.choice([-3, -2, -1, 1, 2])])
        elif kind == "roll":
            expression = self.rng.choice(["1d20+5", "1d20+3", "2d6+3", "1d8+2", "1d20"])
            result = await self.page.evaluate("t => window.__gwBot.say(t)", "/r " + expression)
        elif kind == "chat":
            mark = secrets.token_hex(4)
            text = self.rng.choice(["Vou checar a porta.", "Alguém tem luz?", "Ataco o mais próximo.",
                                    "Fico de guarda.", "Rolando percepção."])
            result = await self.page.evaluate("t => window.__gwBot.say(t)", f"{text} [gw:{mark}]")
        self.actions.append({"t": started, "label": self.label, "kind": kind, **(result or {})})

    async def open_sheets(self):
        """Keep sheets open like players do; the GM keeps the first character open."""
        ids = [t["id"] for t in self.info["tokens"]][: 1]
        for token in ids:
            result = await self.page.evaluate("id => window.__gwBot.openSheet(id)", token)
            self.actions.append({"t": time.time(), "label": self.label, "kind": "open-sheet", **result})
        await asyncio.sleep(1)
        count = await self.page.evaluate("window.__gwBot.sheetsOpen()")
        self.actions.append({"t": time.time(), "label": self.label, "kind": "sheets-visible", "ok": count > 0, "count": count})

    async def play(self):
        if self.open_sheet_windows:
            await self.open_sheets()
        await self.refresh_board()
        now = time.monotonic()
        due = {kind: self.schedule(kind, now) for kind in self.rates}
        while time.monotonic() < self.deadline:
            kind = min(due, key=due.get)
            wait = min(due[kind], self.deadline) - time.monotonic()
            if wait > 0:
                if self.board and self.rng.random() < self.active:
                    await self.wander(min(wait, self.rng.uniform(1, 4)))
                else:
                    await asyncio.sleep(min(wait, self.rng.uniform(1, 4)))
                continue
            if time.monotonic() >= self.deadline:
                break
            try:
                await self.act(kind)
            except Exception as error:  # noqa: BLE001 - recorded, the session continues
                self.actions.append({"t": time.time(), "label": self.label, "kind": kind,
                                     "ok": False, "error": repr(error)[:160]})
            due[kind] = self.schedule(kind, time.monotonic())


def path_pattern(url):
    path = urlsplit(url).path
    path = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", ":id", path)
    path = re.sub(r"/[0-9a-f]{32,}", "/:hash", path)
    path = re.sub(r"/\d+(?=/|$)", "/:n", path)
    return "/static/…" if path.startswith("/static/") else path


async def open_participant(browser, base, data, info, viewport, http_log):
    context = await browser.new_context(viewport=viewport, locale="pt-BR")
    await context.add_cookies([{"name": data["cookie"], "value": info["session"], "url": base}])
    await context.add_init_script(HOOK)
    page = await context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)[:300]))

    def finished(request, failed=False):
        timing = request.timing
        http_log.write(json.dumps({
            "label": info["label"], "t": timing.get("startTime") or time.time() * 1000,
            "method": request.method, "path": path_pattern(request.url), "type": request.resource_type,
            "ms": round(timing["responseEnd"], 1) if timing.get("responseEnd", -1) >= 0 else None,
            "failed": failed,
        }) + "\n")

    page.on("requestfinished", finished)
    page.on("requestfailed", lambda request: finished(request, True))
    await page.goto(f"{base}/game/{data['campaign']}")
    await page.wait_for_function("window.__gwBot && window.__gwBot.ready()", timeout=90_000)
    return context, page, errors


async def session(args, base, data, run):
    from playwright.async_api import async_playwright

    rng = random.Random(args.seed)
    viewport = {"width": 1440, "height": 900}
    client_log = (run / "client.jsonl").open("w", buffering=1, encoding="utf-8")
    http_log = (run / "client-http.jsonl").open("w", buffering=1, encoding="utf-8")
    events = []
    async with async_playwright() as playwright:
        launch = {"args": ["--disable-background-timer-throttling",
                           "--disable-renderer-backgrounding",
                           "--disable-backgrounding-occluded-windows"]}
        if args.browser_executable:
            launch["executable_path"] = str(args.browser_executable)
        browser = await playwright.chromium.launch(**launch)
        opened = []
        for info in data["participants"]:
            context, page, errors = await open_participant(browser, base, data, info, viewport, http_log)
            opened.append((info, context, page, errors))
            events.append({"t": time.time(), "event": "joined", "label": info["label"]})
            await asyncio.sleep(args.arrival_gap)
        started = time.monotonic()
        deadline = started + args.duration
        participants = []
        for info, _, page, _ in opened:
            kind = "gm" if info["role"] == "gm" else "player"
            rates = {name: rate * args.rate_scale for name, rate in DEFAULT_RATES[kind].items()}
            participant = Participant(
                info, page, rates, POINTER_ACTIVE[kind],
                random.Random(rng.random()), deadline, started, client_log, args.duration)
            participant.open_sheet_windows = args.open_sheets
            participants.append(participant)
        events.append({"t": time.time(), "event": "play-start"})

        async def drains():
            while time.monotonic() < deadline + 5:
                for participant in participants:
                    await participant.drain()
                await asyncio.sleep(2)

        async def reload_player():
            if args.reload_at <= 0 or len(participants) < 2:
                return
            await asyncio.sleep(args.duration * args.reload_at)
            target = participants[1]
            await target.drain()
            events.append({"t": time.time(), "event": "reload", "label": target.label})
            await target.page.reload()
            await target.page.wait_for_function("window.__gwBot && window.__gwBot.ready()", timeout=120_000)
            events.append({"t": time.time(), "event": "reloaded", "label": target.label})
            await target.refresh_board()

        async def scene_changes():
            script = SCENE_SCRIPT[args.scene_script] if data.get("combat_scene") else []
            gm = next((p for p in participants if p.info["role"] == "gm"), None)
            targets = {"combat": data.get("combat_scene"), "home": data["scene"], None: None}
            for fraction, action, target in script:
                await asyncio.sleep(max(0, started + args.duration * fraction - time.monotonic()))
                result = await gm.page.evaluate(
                    "([action, data]) => window.gravewrightRealtime.mapCommand(action, data)"
                    ".then(() => ({ok: true}), error => ({ok: false, error: String(error && error.message)}))",
                    [action, {"mapId": targets[target]}])
                events.append({"t": time.time(), "event": f"scene-{action}", "target": target, **result})

        await asyncio.gather(drains(), reload_player(), scene_changes(), *(p.play() for p in participants))
        events.append({"t": time.time(), "event": "play-end"})
        for participant in participants:
            await participant.drain()
        page_errors = {info["label"]: errors for info, _, _, errors in opened}
        await browser.close()
    client_log.close()
    http_log.close()
    actions = [action for participant in participants for action in participant.actions]
    return events, actions, page_errors


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--data-from", type=Path)
    parser.add_argument("--campaign")
    parser.add_argument("--players", help="Comma-separated player membership ids (default: most recent chat authors)")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--duration", type=float, default=1200)
    parser.add_argument("--arrival-gap", type=float, default=6)
    parser.add_argument("--reload-at", type=float, default=0.6,
                        help="Fraction of the session when the first player reloads the page (0 disables)")
    parser.add_argument("--seed", type=int, default=20261114)
    parser.add_argument("--journal-mode", choices=("wal", "delete"),
                        help="SQLite journal for this run (default: the project's configuration)")
    parser.add_argument("--scene-script", choices=sorted(SCENE_SCRIPT), default="today",
                        help="GM scene previews and activations during the session")
    parser.add_argument("--open-sheets", action="store_true",
                        help="Players keep their character sheet open; the GM keeps one open")
    parser.add_argument("--rate-scale", type=float, default=1.0,
                        help="Multiply every scripted action rate (1 = the measured session)")
    parser.add_argument("--label", default="session")
    parser.add_argument("--browser-executable", type=Path)
    args = parser.parse_args()
    args.workdir = args.workdir.resolve()
    fixture = prepare_fixture(args)
    run = args.workdir / "runs" / f"{datetime.now():%Y%m%d-%H%M%S}-{args.label}"
    run.mkdir(parents=True)
    copy_database(fixture / "gravewright.sqlite3", run / "gravewright.sqlite3")
    shutil.copytree(fixture / "media", run / "media", symlinks=True)
    port = free_port()
    env = environment(run, port, fixture)
    if args.journal_mode:
        env["DATABASE_JOURNAL_MODE"] = args.journal_mode
    with (run / "prepare.log").open("w") as log:
        run_manage(env, "check", log=log)
        run_manage(env, "migrate", "--noinput", log=log)
        run_manage(env, "collectstatic", "--noinput", log=log)
    request = {"campaign": args.campaign, "count": args.count,
               "players": [int(v) for v in args.players.split(",")] if args.players else None}
    data = json.loads(subprocess.check_output(
        [sys.executable, "-c", SEED, json.dumps(request)], cwd=ROOT, env=env, text=True))
    labels = {p["user"]: p["label"] for p in data["participants"]}
    with closing(sqlite3.connect(run / "gravewright.sqlite3")) as db:
        journal = db.execute("pragma journal_mode").fetchone()[0]
    meta = {
        "args": {k: str(v) for k, v in vars(args).items()}, "port": port, "journal_mode": journal,
        "rates": DEFAULT_RATES, "pointer_active": POINTER_ACTIVE, "python": sys.version,
        "participants": [{k: v for k, v in p.items() if k != "session"} for p in data["participants"]],
        "campaign": data["campaign"], "scene": data["scene"],
        "git": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True).stdout.strip(),
    }
    (run / "meta.json").write_text(json.dumps(meta, indent=2))
    base = f"http://127.0.0.1:{port}"
    server_env = {**env, "GW_MEASURE_DIR": str(run), "GW_MEASURE_LABELS": json.dumps(labels)}
    with (run / "server-console.log").open("w") as console:
        server = subprocess.Popen([sys.executable, str(Path(__file__).with_name("realtime_session_server.py"))],
                                  cwd=ROOT, env=server_env, stdout=console, stderr=console)
        try:
            wait_ready(base, server)
            events, actions, page_errors = asyncio.run(session(args, base, data, run))
        finally:
            server.send_signal(signal.SIGINT)
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()
    meta.update(events=events, page_errors=page_errors)
    (run / "meta.json").write_text(json.dumps(meta, indent=2))
    with (run / "actions.jsonl").open("w") as out:
        for action in sorted(actions, key=lambda a: a["t"]):
            out.write(json.dumps(action) + "\n")
    subprocess.run([sys.executable, str(Path(__file__).with_name("realtime_session_report.py")), str(run)],
                   cwd=ROOT, check=False)
    print(run)


if __name__ == "__main__":
    main()
