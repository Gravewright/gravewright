"""
Performance test suite for Gravewright.

Covers:
  1. Tile endpoint latency        — TileUser: viewport tile requests (concurrent)
  2. General API throughput       — AuthedUser: game page + light navigation
  3. Upload / retile time         — RetileUser: POST scene update with new tile_size
  4. Memory / CPU under load      — all users run concurrently; monitor via `docker stats`

Run headless via docker-compose.perf.yml or interactively:

    locust -f tests/performance/locustfile.py --host http://localhost:8000
"""
from __future__ import annotations

import html as html_lib
import math
import random
import re
import time

from locust import HttpUser, between, events, tag, task
from locust.exception import StopUser


PERF_EMAIL = "perf@test.local"
PERF_PASSWORD = "Perf1234!"


# Shared scene metadata discovered after login.
_scene_meta: dict = {}

# Avoid spamming the console with the same diagnostic from many users.
_login_debug_printed = False
_meta_debug_printed = False


_INPUT_RE = re.compile(r"<input\b[^>]*>", re.IGNORECASE)


def _input_value(html: str, name: str) -> str | None:
    """
    Extract an <input name="..."> value regardless of attribute order.

    Handles:
        <input name="_csrf_token" value="...">
        <input type="hidden" name="_csrf_token" value="...">
        <input value="..." name="_csrf_token">
    """
    for match in _INPUT_RE.finditer(html):
        tag = match.group(0)

        if not re.search(
            rf'\bname\s*=\s*["\']{re.escape(name)}["\']',
            tag,
            re.IGNORECASE,
        ):
            continue

        value = re.search(
            r'\bvalue\s*=\s*["\']([^"\']*)["\']',
            tag,
            re.IGNORECASE,
        )

        if not value:
            return None

        return html_lib.unescape(value.group(1))

    return None


def _attr_value(html: str, attr_name: str) -> str | None:
    """
    Extract a generic HTML attribute value regardless of tag.

    Example:
        data-scene-id="abc"
        data-scene-id='abc'
    """
    match = re.search(
        rf'\b{re.escape(attr_name)}\s*=\s*["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if not match:
        return None
    return html_lib.unescape(match.group(1))


def _print_once(kind: str, message: str, body: str | None = None) -> None:
    global _login_debug_printed, _meta_debug_printed

    if kind == "login":
        if _login_debug_printed:
            return
        _login_debug_printed = True

    if kind == "meta":
        if _meta_debug_printed:
            return
        _meta_debug_printed = True

    print(message)

    if body:
        print("----- first 1000 chars -----")
        print(body[:1000])
        print("----------------------------")


def _looks_like_login_page(html: str) -> bool:
    body = html.lower()

    return (
        "gravewright - login" in body
        or 'aria-label="login"' in body
        or "auth-panel--login" in body
        or 'name="password"' in body
    )


def _login(client) -> bool:
    with client.get("/", name="GET /login", catch_response=True) as r:
        if r.status_code != 200:
            r.failure(f"login page returned HTTP {r.status_code}")
            _print_once(
                "login",
                f"[login] GET / failed: HTTP {r.status_code}",
                r.text,
            )
            return False

        # Litestar renders the CSRF token as <input name="_csrf_token" ...>
        # (see litestar.response.template). Keep support optional, but extract
        # the correct field name so the POST is not rejected with HTTP 403.
        csrf = _input_value(r.text, "_csrf_token")
        r.success()

    data = {
        "email": PERF_EMAIL,
        "password": PERF_PASSWORD,
    }

    if csrf:
        data["_csrf_token"] = csrf

    with client.post(
        "/login",
        data=data,
        allow_redirects=True,
        name="POST /login",
        catch_response=True,
    ) as r2:
        if r2.status_code != 200:
            r2.failure(f"login POST returned HTTP {r2.status_code}")
            _print_once(
                "login",
                f"[login] POST /login failed: HTTP {r2.status_code}",
                r2.text,
            )
            return False

        # Detect "login failed but returned 200 login page again".
        if _looks_like_login_page(r2.text):
            r2.failure("login POST returned login page again")
            _print_once(
                "login",
                "[login] POST /login appears to have returned the login page again",
                r2.text,
            )
            return False

        r2.success()
        return True


def _parse_scene_meta(html: str) -> dict | None:
    scene_id = _attr_value(html, "data-scene-id")
    layer_id = _attr_value(html, "data-scene-layer-id")
    tile_ver = _attr_value(html, "data-scene-tile-version")
    tile_w = _attr_value(html, "data-scene-width")
    tile_h = _attr_value(html, "data-scene-height")
    tile_sz = _attr_value(html, "data-scene-tile-size")
    img_scale = _attr_value(html, "data-scene-image-scale")
    campaign_id = _attr_value(html, "data-room-id")

    if not (scene_id and layer_id and tile_w and tile_h and tile_sz and campaign_id):
        return None

    try:
        base_w = int(tile_w)
        base_h = int(tile_h)
        ts = int(tile_sz)
        float(img_scale) if img_scale else 1.0

        tx_max = math.ceil(base_w / ts) - 1
        ty_max = math.ceil(base_h / ts) - 1

        return {
            "scene_id": scene_id,
            "campaign_id": campaign_id,
            "layer_id": layer_id,
            "tile_version": int(tile_ver) if tile_ver else 1,
            "tx_max": max(tx_max, 0),
            "ty_max": max(ty_max, 0),
        }
    except (ValueError, TypeError):
        return None


class BaseAuthedUser(HttpUser):
    abstract = True

    def on_start(self):
        if not _login(self.client):
            self.environment.process_exit_code = 1
            if self.environment.runner:
                self.environment.runner.quit()
            raise StopUser("Login failed — check seed.py, login route, or credentials")

        with self.client.get(
            "/game",
            name="GET /game page",
            allow_redirects=True,
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"game page returned HTTP {r.status_code}")
                _print_once(
                    "meta",
                    f"[meta] GET /game failed: HTTP {r.status_code}",
                    r.text,
                )
                return

            meta = _parse_scene_meta(r.text)

            if meta:
                if not _scene_meta:
                    _scene_meta.update(meta)
                    print(f"[meta] scene discovered: {_scene_meta}")
                r.success()
                return

            # Do not stop the whole test here because general /game throughput can
            # still be measured, but tile/retile tasks will no-op until metadata exists.
            r.failure("scene metadata not found in /game page")
            _print_once(
                "meta",
                "[meta] scene metadata not found in /game page",
                r.text,
            )


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
    """General authenticated user hitting authenticated pages repeatedly."""

    weight = 3
    wait_time = between(0.5, 2.0)

    @tag("game")
    @task(5)
    def game_page(self):
        self.client.get("/game", name="GET /game page", allow_redirects=True)

    @tag("game")
    @task(2)
    def home_page_authenticated(self):
        self.client.get("/", name="GET / home", allow_redirects=True)


class RetileUser(BaseAuthedUser):
    """
    Triggers a retile by changing tile_size via the scene update form.

    Runs infrequently — this is a heavy operation.
    """

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
        campaign_id = _scene_meta.get("campaign_id", "")

        if not campaign_id:
            return

        new_size = self._tile_sizes[self.__class__._idx % len(self._tile_sizes)]
        self.__class__._idx += 1

        with self.client.get(
            "/game",
            name="GET /game page (pre-retile)",
            allow_redirects=True,
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"pre-retile /game returned HTTP {r.status_code}")
                return

            # Scene update is a POST guarded by Litestar CSRF; grab the
            # _csrf_token hidden input rendered in the /game page.
            csrf = _input_value(r.text, "_csrf_token")
            r.success()

        data = {
            "scene_id": scene_id,
            "campaign_id": campaign_id,
            "name": "Perf Scene",
            "tile_size": str(new_size),
            "grid_visible": "true",
        }

        if csrf:
            data["_csrf_token"] = csrf

        t0 = time.perf_counter()

        with self.client.post(
            "/game/scenes/update",
            data=data,
            name="POST /scenes/update (retile)",
            allow_redirects=False,
            catch_response=True,
        ) as r2:
            elapsed_ms = (time.perf_counter() - t0) * 1000

            if r2.status_code not in (200, 302, 303):
                r2.failure(f"retile returned HTTP {r2.status_code}")
                print(
                    f"[retile] failed tile_size={new_size} "
                    f"HTTP {r2.status_code} → {elapsed_ms:.0f}ms"
                )
                return

            r2.success()
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

    for name, entry in sorted(stats.entries.items(), key=lambda x: str(x[0])):
        if entry.num_requests == 0:
            continue

        rows.append(
            (
                name[1] if isinstance(name, tuple) else str(name),
                str(entry.num_requests),
                str(entry.num_failures),
                f"{entry.get_response_time_percentile(0.50):.0f}",
                f"{entry.get_response_time_percentile(0.95):.0f}",
                f"{entry.get_response_time_percentile(0.99):.0f}",
                f"{entry.total_rps:.1f}",
            )
        )

    col_w = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]

    for row in rows:
        print("  ".join(cell.ljust(col_w[i]) for i, cell in enumerate(row)))

    total = stats.total

    print(f"\nTotal requests : {total.num_requests}")
    print(f"Total failures : {total.num_failures}")
    print(f"Overall RPS    : {total.total_rps:.1f}")
    print(f"p95 latency    : {total.get_response_time_percentile(0.95):.0f} ms")
    print("=" * 60)