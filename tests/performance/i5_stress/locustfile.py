"""
MAXIMUM STRESS TEST — Gravewright
=================================

This simulates a scenario that will practically never happen in a real session:

  • 500 concurrent players in the same room
      (reality: 5-20 players per session)
  • 8 000 x 6 000 px map, 32 px tiles → 47 000 tiles
      (reality: 2 000 x 1 500 px, 50-100 px tiles)
  • Constant viewport panning — no idle time
      (reality: players look at the map, barely move)
  • 20×15 = 300 tile viewport bursts
      (reality: a 1920×1080 canvas at 1x zoom needs ≈ 10×8 tiles)
  • 10 GMs simultaneously triggering retile
      (reality: 1 GM, retile happens once per session at most)
  • 5 minute sustained load at full spawn
      (reality: a few requests per minute)

Goal: find the saturation point, not to pass — failure is expected and informative.
"""
from __future__ import annotations

import random
import re
import time

from locust import HttpUser, between, constant, events, tag, task


                                                                                

STRESS_EMAIL = "stress@test.local"
STRESS_PASSWORD = "StressMax1!"

                                                                                

_scene_meta: dict = {}

                                                                                

_CSRF_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')
_CAMPAIGN_ID_RE = re.compile(r'data-room-id="([^"]+)"')
_SCENE_ID_RE = re.compile(r'data-scene-id="([^"]+)"')
_LAYER_ID_RE = re.compile(r'data-scene-layer-id="([^"]+)"')
_TILE_VER_RE = re.compile(r'data-scene-tile-version="([^"]+)"')
_TILE_W_RE = re.compile(r'data-scene-width="([^"]+)"')
_TILE_H_RE = re.compile(r'data-scene-height="([^"]+)"')
_TILE_SZ_RE = re.compile(r'data-scene-tile-size="([^"]+)"')


def _login(client) -> bool:
    r = client.get("/", name="GET /login")
    if r.status_code != 200:
        return False
    m = _CSRF_RE.search(r.text)
    if not m:
        return False
    r2 = client.post(
        "/login",
        data={"email": STRESS_EMAIL, "password": STRESS_PASSWORD, "csrf_token": m.group(1)},
        allow_redirects=True,
        name="POST /login",
    )
    return r2.status_code == 200


def _parse_meta(html: str) -> dict | None:
    matches = {
        "scene_id": _SCENE_ID_RE.search(html),
        "layer_id": _LAYER_ID_RE.search(html),
        "campaign_id": _CAMPAIGN_ID_RE.search(html),
        "tile_ver": _TILE_VER_RE.search(html),
        "tile_w": _TILE_W_RE.search(html),
        "tile_h": _TILE_H_RE.search(html),
        "tile_sz": _TILE_SZ_RE.search(html),
    }
    if not all(matches.values()):
        return None
    lid = matches["layer_id"].group(1)
    if not lid:
        return None
    try:
        import math
        w = int(matches["tile_w"].group(1))
        h = int(matches["tile_h"].group(1))
        ts = int(matches["tile_sz"].group(1))
        return {
            "scene_id": matches["scene_id"].group(1),
            "campaign_id": matches["campaign_id"].group(1),
            "layer_id": lid,
            "tile_version": int(matches["tile_ver"].group(1)),
            "tx_max": math.ceil(w / ts) - 1,
            "ty_max": math.ceil(h / ts) - 1,
        }
    except (ValueError, AttributeError):
        return None


                                                                                

class StressBase(HttpUser):
    abstract = True

    def on_start(self):
        if not _login(self.client):
            raise RuntimeError("Login failed — run seed.py first")
        r = self.client.get("/game", name="GET /game page", allow_redirects=True)
        if r.status_code == 200:
            meta = _parse_meta(r.text)
            if meta and not _scene_meta:
                _scene_meta.update(meta)


                                                                                
                                              
                                                                        

class TileBombardier(StressBase):
    """Fires 20×15 viewport bursts with essentially no pause."""
    weight = 8
    wait_time = constant(0)                                      

    @tag("tiles")
    @task(15)
    def viewport_burst(self):
        if not _scene_meta:
            return
        sid = _scene_meta["scene_id"]
        lid = _scene_meta["layer_id"]
        v = _scene_meta["tile_version"]
        tx_max = _scene_meta["tx_max"]
        ty_max = _scene_meta["ty_max"]

        ox = random.randint(0, max(0, tx_max - 19))
        oy = random.randint(0, max(0, ty_max - 14))
        for ty in range(oy, min(oy + 15, ty_max + 1)):
            for tx in range(ox, min(ox + 20, tx_max + 1)):
                self.client.get(
                    f"/game/scenes/{sid}/layers/{lid}/tiles/{tx}/{ty}?v={v}",
                    name="GET /tile (20x15 burst)",
                )

    @tag("tiles")
    @task(5)
    def scatter_random(self):
        """Random tiles anywhere on the map — simulates teleporting / scene sharing."""
        if not _scene_meta:
            return
        sid = _scene_meta["scene_id"]
        lid = _scene_meta["layer_id"]
        v = _scene_meta["tile_version"]
        for _ in range(50):
            tx = random.randint(0, _scene_meta["tx_max"])
            ty = random.randint(0, _scene_meta["ty_max"])
            self.client.get(
                f"/game/scenes/{sid}/layers/{lid}/tiles/{tx}/{ty}?v={v}",
                name="GET /tile (random scatter)",
            )


                                                                                
                                                                   

class PageHammer(StressBase):
    """Hammers the full game page HTML render."""
    weight = 3
    wait_time = between(0.1, 0.5)

    @tag("page")
    @task
    def game_page(self):
        self.client.get("/game", name="GET /game page", allow_redirects=True)


                                                                                
                                                                     
                                                      

class ParallelRetiler(StressBase):
    """Triggers retile as fast as possible — simulates 10 GMs spamming tile_size changes."""
    weight = 1
    wait_time = between(2, 5)                                             

    _sizes = [32, 40, 48, 32, 56, 32, 40, 48, 56, 32]
    _idx = 0

    @tag("retile")
    @task
    def retile(self):
        if not _scene_meta:
            return

        new_size = self._sizes[self.__class__._idx % len(self._sizes)]
        self.__class__._idx += 1

        r = self.client.get("/game", name="GET /game (retile-csrf)", allow_redirects=True)
        csrf = _CSRF_RE.search(r.text) if r.status_code == 200 else None
        if not csrf:
            return

        t0 = time.perf_counter()
        resp = self.client.post(
            "/game/scenes/update",
            data={
                "csrf_token": csrf.group(1),
                "scene_id": _scene_meta["scene_id"],
                "campaign_id": _scene_meta["campaign_id"],
                "name": "Max Stress Scene",
                "tile_size": str(new_size),
                "grid_visible": "true",
            },
            name="POST /scenes/update (retile)",
            allow_redirects=False,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"[retile] size={new_size} status={resp.status_code} {elapsed_ms:.0f}ms")


                                                                                

@events.test_stop.add_listener
def on_test_stop(environment, **_kwargs):
    stats = environment.stats
    total = stats.total

    print("\n" + "=" * 70)
    print("MAX STRESS RESULTS — 500 users / 8000×6000 map / 47 000 tiles")
    print("=" * 70)

    header = ("Endpoint", "Reqs", "Fails%", "p50", "p95", "p99", "p999", "RPS")
    rows = [header]

    for name, entry in sorted(stats.entries.items(), key=lambda x: -x[1].num_requests):
        if entry.num_requests == 0:
            continue
        fail_pct = f"{100*entry.num_failures/entry.num_requests:.1f}%"
        rows.append((
            name[1] if isinstance(name, tuple) else name,
            str(entry.num_requests),
            fail_pct,
            f"{entry.get_response_time_percentile(0.50):.0f}ms",
            f"{entry.get_response_time_percentile(0.95):.0f}ms",
            f"{entry.get_response_time_percentile(0.99):.0f}ms",
            f"{entry.get_response_time_percentile(0.999):.0f}ms",
            f"{entry.total_rps:.0f}",
        ))

    col_w = [max(len(r[i]) for r in rows) + 1 for i in range(len(rows[0]))]
    sep = "  ".join("-" * w for w in col_w)
    for i, row in enumerate(rows):
        print("  ".join(cell.ljust(col_w[j]) for j, cell in enumerate(row)))
        if i == 0:
            print(sep)

    print(f"\nTotal requests : {total.num_requests:,}")
    print(f"Total failures : {total.num_failures:,} ({100*total.num_failures/max(total.num_requests,1):.2f}%)")
    print(f"Peak RPS       : {total.total_rps:.0f} req/s")
    print(f"p50 latency    : {total.get_response_time_percentile(0.50):.0f} ms")
    print(f"p95 latency    : {total.get_response_time_percentile(0.95):.0f} ms")
    print(f"p99 latency    : {total.get_response_time_percentile(0.99):.0f} ms")
    print(f"p99.9 latency  : {total.get_response_time_percentile(0.999):.0f} ms")
    print("=" * 70)
