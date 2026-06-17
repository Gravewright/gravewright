"""Package-neutral end-to-end test for the live application server.

Exercises the real operator + HTTP path that in-process TestClient checks can
only approximate, without depending on any bundled SDK package (no ruleset, no
addon):

    seed a GM + campaign in a temp SQLite file -> boot a real ``uvicorn`` server
    in a subprocess pointed at that file -> drive it over genuine HTTP -> a real
    CSRF-protected form login succeeds -> the authenticated dashboard renders the
    seeded campaign -> a protected route redirects anonymous browsers to /login
    -> the SDK runtime script is served as a static asset.

The server is a separate process speaking real HTTP, so this covers ASGI
startup, routing, session + CSRF middleware, template rendering, and static
serving end to end. It is browserless (pure ``urllib``), so it runs everywhere
and needs no Selenium/geckodriver.
"""

from __future__ import annotations

import contextlib
import http.cookiejar
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

GM_EMAIL = "gm-e2e@test.com"
GM_PASSWORD = "Password1!"  # matches tests.conftest.seed_user
CAMPAIGN_TITLE = "E2E Neutral Campaign"

# Litestar CSRFConfig defaults (see main.py): cookie name + request header name.
CSRF_COOKIE = "csrftoken"
CSRF_HEADER = "x-csrftoken"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_http_ready(url: str, *, proc: subprocess.Popen, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"uvicorn exited early with code {proc.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status < 500:
                    return
        except (urllib.error.URLError, ConnectionError, OSError) as err:
            last_err = err
        time.sleep(0.25)
    raise RuntimeError(f"server at {url} not ready in {timeout}s: {last_err}")


def _seed_database(db_path: Path) -> str:
    """Seed a GM + campaign (no packages) into ``db_path``; return campaign id.

    Writes go to the same SQLite file the subprocess server reads.
    """
    import app.persistence.database as db_module
    from app.persistence import engine as engine_module

    db_module.DATABASE_PATH = db_path.resolve()
    db_module._initialized = False
    engine_module.reset_engine()

    from tests.conftest import seed_campaign, seed_user

    gm_id = seed_user(name="GM", email=GM_EMAIL)
    campaign_id = seed_campaign(gm_id, title=CAMPAIGN_TITLE)

    # Release the SQLite file so the subprocess server can open it cleanly.
    engine_module.reset_engine()
    return campaign_id


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    """Boot a real server with a seeded GM + campaign and yield its base URL."""
    tmp_dir = tmp_path_factory.mktemp("e2e")
    db_path = tmp_dir / "e2e.sqlite3"
    campaign_id = _seed_database(db_path)

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "DATABASE_URL": f"sqlite:///{db_path.resolve().as_posix()}",
            # The allowed-hosts middleware full-matches the Host header including
            # the port; with an ephemeral port a fixed host never matches, so the
            # local test server trusts any host (safe: APP_ENV=test, loopback only).
            "ALLOWED_HOSTS": "*",
            "SESSION_COOKIE_SECURE": "false",
        }
    )

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(REPO_ROOT),
        env=env,
    )
    try:
        _wait_http_ready(f"{base_url}/login", proc=proc)
        yield {"base_url": base_url, "campaign_id": campaign_id}
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=10)
        if proc.poll() is None:
            proc.kill()


def _opener(*, follow_redirects: bool = True) -> tuple[urllib.request.OpenerDirector, http.cookiejar.CookieJar]:
    jar = http.cookiejar.CookieJar()
    handlers: list = [urllib.request.HTTPCookieProcessor(jar)]
    if not follow_redirects:
        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):  # noqa: ANN002, ANN003
                return None

        handlers.append(_NoRedirect)
    return urllib.request.build_opener(*handlers), jar


def _cookie(jar: http.cookiejar.CookieJar, name: str) -> str | None:
    return next((c.value for c in jar if c.name == name), None)


def _get(opener, url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"Accept": "text/html"})
    with opener.open(req, timeout=15) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def test_real_login_flow_renders_dashboard(live_server):
    base_url = live_server["base_url"]
    opener, jar = _opener()

    # 1. The login page renders and arms the CSRF cookie.
    status, body = _get(opener, f"{base_url}/login")
    assert status == 200
    assert 'name="email"' in body and 'name="password"' in body
    token = _cookie(jar, CSRF_COOKIE)
    assert token, "login GET did not set a CSRF cookie"

    # 2. A genuine CSRF-protected form login succeeds and follows the redirect
    #    to the authenticated dashboard, which lists the seeded campaign.
    form = urllib.parse.urlencode({"email": GM_EMAIL, "password": GM_PASSWORD}).encode()
    req = urllib.request.Request(
        f"{base_url}/login",
        data=form,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html",
            CSRF_HEADER: token,
        },
    )
    with opener.open(req, timeout=15) as resp:
        final_url = resp.geturl()
        dashboard = resp.read().decode("utf-8", "replace")
        assert resp.status == 200

    assert final_url.endswith("/inside"), final_url
    assert CAMPAIGN_TITLE in dashboard


def test_protected_route_redirects_anonymous_to_login(live_server):
    base_url = live_server["base_url"]
    opener, _ = _opener()

    # No session: a browser navigation to a guarded page lands back on /login.
    status, body = _get(opener, f"{base_url}/inside")
    assert status == 200
    assert 'name="password"' in body  # the login form, not the dashboard
    assert CAMPAIGN_TITLE not in body


def test_sdk_runtime_is_served_as_static_asset(live_server):
    base_url = live_server["base_url"]
    opener, _ = _opener()

    # The SDK browser runtime is served even with zero packages installed.
    with opener.open(f"{base_url}/static/js/sdk/gravewright-sdk.js", timeout=15) as resp:
        assert resp.status == 200
        body = resp.read().decode("utf-8", "replace")
    assert "window.GravewrightSDK" in body
