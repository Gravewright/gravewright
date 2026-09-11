"""Exercise the local Runner using temporary data and the real Daphne server.

Run ``uv run --locked python tests/e2e/runner.py`` after installing Playwright
Chromium. This tests the Python runtime on the current OS; the Windows bootstrap
and shortcut also need a Windows smoke test. No development data is modified.
"""

from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

from dotenv import dotenv_values
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "gravewright_runner.py"
PASSWORD = "runner-browser-password-123"
EMAIL = "runner-owner@example.test"


def free_port():
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", 0))
        return connection.getsockname()[1]


def digest(path):
    if not path.exists():
        return None
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def project_data_state():
    """Compare fingerprints without disclosing the existing development data."""
    files = [ROOT / ".env"]
    if (ROOT / "data").is_dir():
        files.extend(path for path in (ROOT / "data").rglob("*") if path.is_file())
    return {str(path.relative_to(ROOT)): digest(path) for path in files}


def http_request(port, path, *, headers=None, method="GET", body=None):
    # Connect directly: inherited HTTP(S)_PROXY must not influence local tests.
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def wait_ready(server, port, log_path):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError(f"Runner exited with {server.returncode}; inspect {log_path}")
        try:
            if http_request(port, "/api/auth/status")[0] == 200:
                return
        except OSError:
            pass
        time.sleep(0.1)
    raise RuntimeError(f"Runner did not become ready; inspect {log_path}")


def stop(server, port):
    if server.poll() is None:
        server.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
    try:
        server.wait(timeout=15)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=5)
        raise AssertionError("Runner did not stop after its console interrupt") from None
    with socket.socket() as connection:
        connection.settimeout(1)
        assert connection.connect_ex(("127.0.0.1", port)) != 0, "Runner left its port listening"


def command(data, port, *extra):
    # Match the BAT's interpreter flags: a parent's -X utf8 is not inherited
    # by newly started interpreters on Windows' legacy system code page.
    return [sys.executable, "-X", "utf8", str(RUNNER), "--data-dir", str(data),
            "--port", str(port), "--no-browser", *extra]


def start(data, port, env, log):
    return subprocess.Popen(
        command(data, port), cwd=ROOT.parent, env=env, stdout=log, stderr=log,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )


def json_request(page, path, *, data=None, token=None):
    return page.evaluate(
        """async ({path, data, token}) => {
            const headers = {};
            if (data !== null) headers['Content-Type'] = 'application/json';
            if (token !== null) headers['X-CSRF-Token'] = token;
            const response = await fetch(path, {
                method: data === null ? 'GET' : 'POST', headers,
                body: data === null ? undefined : JSON.stringify(data),
            });
            const text = await response.text();
            return {status: response.status, body: text ? JSON.parse(text) : null};
        }""",
        {"path": path, "data": data, "token": token},
    )


def handshake_status(port, campaign, origin, cookie=""):
    headers = [
        f"GET /ws/tables/{campaign}/ HTTP/1.1", f"Host: 127.0.0.1:{port}",
        "Upgrade: websocket", "Connection: Upgrade", "Sec-WebSocket-Version: 13",
        "Sec-WebSocket-Key: " + base64.b64encode(os.urandom(16)).decode("ascii"),
        "Cookie: " + cookie,
    ]
    if origin is not None:
        headers.append("Origin: " + origin)
    with socket.create_connection(("127.0.0.1", port), timeout=5) as connection:
        connection.sendall(("\r\n".join(headers) + "\r\n\r\n").encode("ascii"))
        response = b""
        while b"\r\n" not in response:
            chunk = connection.recv(4096)
            if not chunk:
                raise AssertionError("WebSocket handshake closed without a response")
            response += chunk
        return int(response.split(b" ", 2)[1])


def check_static_and_private(port, data):
    asset = "/static/gravewright_web/vendor/datastar-1.0.3.js"
    status, headers, body = http_request(port, asset)
    assert status == 200 and len(body) > 1000, (status, len(body))
    assert {name.lower(): value for name, value in headers.items()}["x-content-type-options"] == "nosniff"
    for path in ("/", asset):
        assert http_request(port, path, headers={"Host": "foreign.example.test"})[0] == 400
    marker = "RUNNER_PRIVATE_MEDIA_MUST_NOT_BE_PUBLIC"
    (data / "media" / "private-probe.txt").write_text(marker, encoding="utf-8")
    for path in ("/.env", "/gravewright.sqlite3", "/media/private-probe.txt",
                 "/static/../media/private-probe.txt", "/static/%2e%2e/media/private-probe.txt"):
        status, _, body = http_request(port, path)
        assert status in (400, 404), (path, status)
        assert marker.encode() not in body


def browser_setup(browser, base, port):
    contexts = [browser.new_context(viewport={"width": 1440, "height": 1000}) for _ in range(2)]
    errors = []
    for context in contexts:
        context.add_init_script("""
            window.runnerFrames = [];
            const Native = window.WebSocket;
            window.WebSocket = class extends Native {
                constructor(...args) {
                    super(...args);
                    this.addEventListener('message', event => {
                        window.runnerFrames.push(JSON.parse(event.data));
                    });
                }
            };
        """)
    owner, observer = [context.new_page() for context in contexts]
    for page in (owner, observer):
        page.on("pageerror", lambda error: errors.append(str(error)))
    owner.goto(base)
    owner.locator("#owner-name").fill("Runner Owner")
    owner.locator("#owner-email").fill(EMAIL)
    owner.locator("#owner-password").fill(PASSWORD)
    owner.get_by_role("button", name="Create administrator", exact=True).click()
    expect(owner.locator("#inside-shell")).to_be_visible()
    cookies = {cookie["name"]: cookie for cookie in contexts[0].cookies()}
    assert cookies["gravewright-session"]["httpOnly"]
    assert cookies["gravewright-session"]["sameSite"] == "Strict"
    assert not cookies["gravewright-session"]["secure"]
    token = cookies["gravewright-csrf"]["value"]
    payload = {"name": "Runner persistent table", "system": "gravewright-pdf-system"}
    assert json_request(owner, "/api/containers", data=payload, token="forged")["status"] == 403
    created = json_request(owner, "/api/containers", data=payload, token=token)
    assert created["status"] == 201, created
    campaign = created["body"]["id"]
    cookie = "; ".join(f"{name}={value['value']}" for name, value in cookies.items())
    assert handshake_status(port, campaign, base) == 403  # No authenticated session.
    for origin in (None, "http://foreign.example.test", base.replace("http:", "https:")):
        assert handshake_status(port, campaign, origin, cookie) == 403, origin
    bad_status, _, _ = http_request(port, "/api/containers", method="POST",
        headers={"Cookie": cookie, "Content-Type": "application/json", "X-CSRF-Token": token,
                 "Origin": "http://foreign.example.test"}, body=json.dumps(payload))
    assert bad_status == 403
    observer.goto(base)
    observer.locator("#owner-email").fill(EMAIL)
    observer.locator("#owner-password").fill(PASSWORD)
    observer.get_by_role("button", name="Enter Gravewright", exact=True).click()
    expect(observer.locator("#inside-shell")).to_be_visible()
    for page in (owner, observer):
        page.goto(base + "/game/" + campaign)
        expect(page.locator(".game-menubar__presence")).to_have_attribute("data-presence", "seated", timeout=15000)
        page.wait_for_function("runnerFrames.some(frame => frame.type === 'table.joined')")
        page.get_by_role("button", name="Chat", exact=True).click()
    owner.locator("#chat-form textarea").fill("Runner chat survives restart")
    owner.get_by_role("button", name="Send", exact=True).click()
    for page in (owner, observer):
        expect(page.locator("#chat-log article")).to_contain_text("Runner chat survives restart")
        page.wait_for_function("runnerFrames.some(frame => frame.type === 'chat.message')")
    assert not errors, errors
    return contexts, owner, campaign


def main():
    original = project_data_state()
    output = ROOT / "test-results" / "runner"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="grave-runner-") as temporary:
        work = Path(temporary)
        data = work / "runner data ç"
        ignored_data = work / "must-not-be-used"
        env = {
            **os.environ, "PYTHONUNBUFFERED": "1", "DJANGO_SETTINGS_MODULE": "config.does_not_exist",
            "DJANGO_DEBUG": "true", "DJANGO_SECRET_KEY": "django-insecure-inherited-must-be-ignored",
            "DJANGO_ALLOWED_HOSTS": "*", "GRAVEWRIGHT_HOST": "0.0.0.0",
            "GRAVEWRIGHT_PUBLIC_ORIGIN": "https://foreign.example.test", "DJANGO_SECURE_COOKIES": "true",
            "GRAVEWRIGHT_DATABASE": str(ignored_data / "database.sqlite3"),
            "GRAVEWRIGHT_MEDIA_ROOT": str(ignored_data / "media"),
            "GRAVEWRIGHT_REDIS_URL": "redis://127.0.0.1:1/0", "TRUSTED_PROXIES": "0.0.0.0/0",
        }
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            occupied_data = work / "occupied"
            result = subprocess.run(command(occupied_data, occupied.getsockname()[1]),
                                    cwd=ROOT.parent, env=env, capture_output=True, text=True, timeout=30)
            assert result.returncode != 0, "Occupied port was accepted"
            assert not (occupied_data / "gravewright.sqlite3").exists(), "Port failure migrated the database"
        print("Occupied port rejected before migrations.", flush=True)
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        with (output / "first-start.log").open("w", encoding="utf-8") as log:
            server = start(data, port, env, log)
            try:
                wait_ready(server, port, output / "first-start.log")
                for name in ("gravewright.sqlite3", "media", "compendiums", "staticfiles", "logs/runner.log"):
                    assert (data / name).exists(), name
                configuration = dotenv_values(data / ".env", interpolate=False)
                secret = configuration["DJANGO_SECRET_KEY"]
                assert secret and len(secret) >= 32 and not secret.startswith("django-insecure-")
                config_digest = digest(data / ".env")
                duplicate = subprocess.run(command(data, free_port()), cwd=ROOT.parent, env=env,
                                           capture_output=True, text=True, timeout=30)
                assert duplicate.returncode != 0, "A second Runner used the same data directory"
                assert json.loads(http_request(port, "/api/auth/status")[2])["configured"] is False
                check_static_and_private(port, data)
                with sync_playwright() as pw, pw.chromium.launch() as browser:
                    contexts, owner, campaign = browser_setup(browser, base, port)
                    print("Isolated setup, static assets, HTTP security and two real WebSocket sessions passed.", flush=True)
                    for context in contexts:
                        for page in context.pages:
                            page.goto("about:blank")
                    stop(server, port)
                    with (output / "restart.log").open("w", encoding="utf-8") as restart_log:
                        server = start(data, port, env, restart_log)
                        wait_ready(server, port, output / "restart.log")
                        assert digest(data / ".env") == config_digest, "Restart changed the user's configuration"
                        owner.goto(base + "/game/" + campaign)
                        expect(owner.locator(".game-menubar__presence")).to_have_attribute("data-presence", "seated", timeout=15000)
                        assert json_request(owner, "/api/auth/session")["body"]["authenticated"]
                        owner.get_by_role("button", name="Chat", exact=True).click()
                        expect(owner.locator("#chat-log article")).to_contain_text("Runner chat survives restart")
                        assert (data / "media/private-probe.txt").exists()
                        for context in contexts:
                            context.close()
                        stop(server, port)
                print("Restart preserved configuration, authenticated session, campaign, chat and media.", flush=True)
            finally:
                try:
                    if server.poll() is None:
                        stop(server, port)
                finally:
                    # Preserve the full startup traceback before the temporary
                    # data directory disappears, even if shutdown also fails.
                    for application_log in (data / "logs").glob("runner.log*"):
                        shutil.copy2(application_log, output / application_log.name)
        assert not ignored_data.exists(), "Inherited production storage settings were used"
        assert project_data_state() == original, "The Runner changed development data or project .env"
    print("Runner checks passed with temporary user data; Windows bootstrap needs its own Windows smoke test.", flush=True)


if __name__ == "__main__":
    main()
