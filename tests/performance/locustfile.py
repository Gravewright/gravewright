"""
Performance test suite for Gravewright.

Covers:
  1. Tile endpoint latency        — TileUser: viewport tile requests (concurrent)
  2. General API throughput       — AuthedUser: game page + light navigation
  3. Upload / retile time         — RetileUser: POST scene update with new tile_size
  4. Memory / CPU under load      — all users run concurrently; monitor via `docker stats`

Run headless (via docker-compose.perf.yml) or interactively:
    locust -f tests/performance/locustfile.py --host http://localhost:8000
"""
from __future__ import annotations

import random
import re
import time

from locust import HttpUser, between, events, tag, task


                                                                               

PERF_EMAIL = "perf@test.local"
PERF_PASSWORD = "Perf1234!"

                                                                                

_scene_meta: dict = {}                                                     


                                                                                

_CSRF_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')
_CAMPAIGN_ID_RE = re.compile(r'data-room-id="([^"]+)"')
_SCENE_ID_RE = re.compile(r'data-scene-id="([^"]+)"')
_LAYER_ID_RE = re.compile(r'data-scene-layer-id="([^"]+)"')
_TILE_VER_RE = re.compile(r'data-scene-tile-version="([^"]+)"')
_TILE_W_RE = re.compile(r'data-scene-width="([^"]+)"')
_TILE_H_RE = re.compile(r'data-scene-height="([^"]+)"')
_TILE_SZ_RE = re.compile(r'data-scene-tile-size="([^"]+)"')
_IMG_SCALE_RE = re.compile(r'data-scene-image-scale="([^"]+)"')


def _login(client) -> bool:
    r = client.get("/", name="GET /login")
    if r.status_code != 200:
        return False
    m = _CSRF_RE.search(r.text)
    if not m:
        return False
    csrf = m.group(1)
    r2 = client.post(
        "/login",
        data={"email": PERF_EMAIL, "password": PERF_PASSWORD, "csrf_token": csrf},
        allow_redirects=True,
        name="POST /login",
    )
    return r2.status_code == 200


def _parse_scene_meta(html: str) -> dict | None:
    scene_id = _SCENE_ID_RE.search(html)
    layer_id = _LAYER_ID_RE.search(html)
    tile_ver = _TILE_VER_RE.search(html)
    tile_w = _TILE_W_RE.search(html)
    tile_h = _TILE_H_RE.search(html)
    tile_sz = _TILE_SZ_RE.search(html)
    img_scale = _IMG_SCALE_RE.search(html)
    campaign_id = _CAMPAIGN_ID_RE.search(html)

    if not (scene_id and layer_id and tile_w and tile_h and tile_sz and campaign_id):
        return None

    lid = layer_id.group(1)
    if not lid:
        return None

    try:
        import math
        float(img_scale.group(1)) if img_scale else 1.0
        base_w = int(tile_w.group(1))
        base_h = int(tile_h.group(1))
        ts = int(tile_sz.group(1))
        tx_max = math.ceil(base_w / ts) - 1
        ty_max = math.ceil(base_h / ts) - 1
        return {
            "scene_id": scene_id.group(1),
            "campaign_id": campaign_id.group(1),
            "layer_id": lid,
            "tile_version": int(tile_ver.group(1)) if tile_ver else 1,
            "tx_max": max(tx_max, 0),
            "ty_max": max(ty_max, 0),
        }
    except (ValueError, AttributeError):
        return None


                                                                                

class BaseAuthedUser(HttpUser):
    abstract = True

    def on_start(self):
        if not _login(self.client):
            self.environment.runner.quit()
            raise RuntimeError("Login failed — check seed.py was run")

        r = self.client.get("/game", name="GET /game page", allow_redirects=True)
        if r.status_code == 200:
            meta = _parse_scene_meta(r.text)
            if meta and not _scene_meta:
                _scene_meta.update(meta)


                                                                                

class TileUser(BaseAuthedUser):
    """Requests random tiles from the viewport — simulates real map panning."""

    weight = 5
    wait_time = between(0.05, 0.3)

    @tag("tiles")
    @task(10)
    def fetch_random_tile(self):
        if not _scene_meta:
            return
        scene_id = _scene_meta["scene_id"]
        layer_id = _scene_meta["layer_id"]
        v = _scene_meta["tile_version"]
        tx = random.randint(0, _scene_meta["tx_max"])
        ty = random.randint(0, _scene_meta["ty_max"])
        url = f"/game/scenes/{scene_id}/layers/{layer_id}/tiles/{tx}/{ty}?v={v}"
        self.client.get(url, name="GET /tiles/{tx}/{ty}")

    @tag("tiles")
    @task(3)
    def fetch_viewport_burst(self):
        """Simulate loading a 5×4 viewport of tiles in one burst."""
        if not _scene_meta:
            return
        scene_id = _scene_meta["scene_id"]
        layer_id = _scene_meta["layer_id"]
        v = _scene_meta["tile_version"]
        ox = random.randint(0, max(0, _scene_meta["tx_max"] - 4))
        oy = random.randint(0, max(0, _scene_meta["ty_max"] - 3))
        for ty in range(oy, min(oy + 4, _scene_meta["ty_max"] + 1)):
            for tx in range(ox, min(ox + 5, _scene_meta["tx_max"] + 1)):
                url = f"/game/scenes/{scene_id}/layers/{layer_id}/tiles/{tx}/{ty}?v={v}"
                self.client.get(url, name="GET /tiles/viewport-burst")


                                                                                

class AuthedUser(BaseAuthedUser):
    """General authenticated user hitting the main game page repeatedly."""

    weight = 3
    wait_time = between(0.5, 2.0)

    @tag("game")
    @task(5)
    def game_page(self):
        self.client.get("/game", name="GET /game page", allow_redirects=True)

    @tag("game")
    @task(2)
    def login_page_unauthenticated(self):
        with self.client.get("/", name="GET /login (unauthed)", catch_response=True) as r:
            if r.status_code in (200, 302):
                r.success()


                                                                                

class RetileUser(BaseAuthedUser):
    """Triggers a retile by changing tile_size via the scene update form.
    Runs infrequently — this is a heavy operation."""

    weight = 1
    wait_time = between(15, 30)

    _tile_sizes = [40, 50, 56, 64, 40]
    _idx = 0

    @tag("retile")
    @task
    def change_tile_size(self):
        if not _scene_meta:
            return

        scene_id = _scene_meta["scene_id"]
        new_size = self._tile_sizes[self._idx % len(self._tile_sizes)]
        self.__class__._idx += 1

        campaign_id = _scene_meta.get("campaign_id", "")
        r = self.client.get("/game", name="GET /game page (pre-retile)", allow_redirects=True)
        csrf = _CSRF_RE.search(r.text) if r.status_code == 200 else None
        if not csrf or not campaign_id:
            return

        t0 = time.perf_counter()
        self.client.post(
            "/game/scenes/update",
            data={
                "csrf_token": csrf.group(1),
                "scene_id": scene_id,
                "campaign_id": campaign_id,
                "name": "Perf Scene",
                "tile_size": str(new_size),
                "grid_visible": "true",
            },
            name="POST /scenes/update (retile)",
            allow_redirects=False,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"[retile] tile_size={new_size} → {elapsed_ms:.0f}ms")


                                                                                

@events.test_stop.add_listener
def on_test_stop(environment, **_kwargs):
    stats = environment.stats
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY  (1 CPU / 4 GB simulation)")
    print("=" * 60)

    rows = [
        ("Endpoint", "Reqs", "Fails", "p50 ms", "p95 ms", "p99 ms", "RPS"),
    ]
    for name, entry in sorted(stats.entries.items(), key=lambda x: x[0]):
        if entry.num_requests == 0:
            continue
        rows.append((
            name[1] if isinstance(name, tuple) else name,
            str(entry.num_requests),
            str(entry.num_failures),
            f"{entry.get_response_time_percentile(0.50):.0f}",
            f"{entry.get_response_time_percentile(0.95):.0f}",
            f"{entry.get_response_time_percentile(0.99):.0f}",
            f"{entry.total_rps:.1f}",
        ))

    col_w = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    for row in rows:
        print("  ".join(cell.ljust(col_w[i]) for i, cell in enumerate(row)))

    total = stats.total
    print(f"\nTotal requests : {total.num_requests}")
    print(f"Total failures : {total.num_failures}")
    print(f"Overall RPS    : {total.total_rps:.1f}")
    print(f"p95 latency    : {total.get_response_time_percentile(0.95):.0f} ms")
    print("=" * 60)
