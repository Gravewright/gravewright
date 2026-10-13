"""Owner release alert, remounting and responsive browser regression coverage.

Run with the project Python environment. The database, extensions and storage
are temporary; release discovery is intercepted before any external request.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "test-results" / "update-notification"
PASSWORD = "update-notification-test-password"
ENDPOINT = "/api/admin/updates/notification"
UPDATES_URL = "/inside?section=administration&tab=updates"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def notification(status="available"):
    available = status == "available"
    return {
        "status": status,
        "available": available,
        "currentVersion": "0.2.1",
        "currentVersionLabel": "0.2.1 Alpha",
        "availableVersion": "0.2.2" if available else None,
        "availableVersionLabel": "0.2.2 Alpha" if available else None,
        "channel": "stable",
        "checkedAt": int(time.time()),
        "url": UPDATES_URL,
    }


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = []
    with tempfile.TemporaryDirectory(prefix="gravewright-update-alert-") as temporary:
        work = Path(temporary)
        env = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("GRAVEWRIGHT_", "DJANGO_"))
        }
        address = f"127.0.0.1:{free_port()}"
        base = f"http://{address}"
        for name in ("media", "content", "modules", "api", "django", "runtime"):
            (work / name).mkdir()
        env.update({
            "PYTHON_DOTENV_DISABLED": "1",
            "PYTHONUTF8": "1",
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DJANGO_DEBUG": "true",
            "GRAVEWRIGHT_HOST": "127.0.0.1",
            "GRAVEWRIGHT_PORT": address.rsplit(":", 1)[1],
            "GRAVEWRIGHT_DATABASE": str(work / "browser.sqlite3"),
            "GRAVEWRIGHT_MEDIA_ROOT": str(work / "media"),
            "GRAVEWRIGHT_CONTENT_ROOT": str(work / "content"),
            "GRAVEWRIGHT_MODULES_ROOT": str(work / "modules"),
            "GRAVEWRIGHT_API_MODULES_ROOT": str(work / "api"),
            "GRAVEWRIGHT_DJANGO_MODULES_ROOT": str(work / "django"),
            "GRAVEWRIGHT_MANAGED_STATE": str(work / "runtime"),
            # An accidental unmocked discovery request must fail locally.
            "GRAVEWRIGHT_RELEASES_REPOSITORY": "",
        })
        subprocess.run(
            [sys.executable, "manage.py", "migrate", "--noinput"],
            cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL,
        )
        with (OUTPUT / "server.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen(
                [sys.executable, "manage.py", "runserver", address, "--noreload"],
                cwd=ROOT, env=env, stdout=log, stderr=log,
            )
            try:
                for _ in range(100):
                    try:
                        with urlopen(base, timeout=1):
                            break
                    except OSError:
                        if server.poll() is not None:
                            raise RuntimeError("Django exited; inspect test-results/update-notification/server.log")
                        time.sleep(.1)
                else:
                    raise RuntimeError("Django did not start; inspect test-results/update-notification/server.log")

                with sync_playwright() as pw:
                    browser = pw.chromium.launch()
                    context = browser.new_context(viewport={"width": 1440, "height": 1000})
                    errors = []
                    requests = []
                    held_requests = []
                    response = {"status": 200, "body": notification()}

                    def respond(route):
                        request = route.request
                        requests.append({"method": request.method, "csrf": request.headers.get("x-csrf-token", "")})
                        if response.get("hold"):
                            held_requests.append(route)
                            return
                        route.fulfill(status=response["status"], json=response["body"])

                    context.route("**" + ENDPOINT, respond)
                    # The notification transport is mocked, so its server-side
                    # cache is not populated. Keep Administration's local status
                    # response consistent with the release it would have cached.
                    context.route("**/api/admin/status", lambda route: route.fulfill(json={
                        "updates": {
                            **notification(), "installFormat": "source",
                            "automatic": {"supported": False, "busy": False}, "releases": [],
                        },
                    }))
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(base)
                    page.locator("#owner-name").fill("Release Owner")
                    page.locator("#owner-email").fill("release-owner@example.test")
                    page.locator("#owner-password").fill(PASSWORD)
                    page.get_by_role("button", name="Create administrator", exact=True).click()
                    expect(page.locator("#inside-shell")).to_be_visible()

                    alert = page.locator("[data-update-notification]")
                    toggle = alert.locator("[data-update-toggle]")
                    badge = alert.locator(".gw-update-notification__badge")
                    panel = alert.locator(".gw-update-notification__panel")
                    expect(badge).to_be_visible()
                    expect(toggle).to_have_attribute("title", "Update available")
                    expect(toggle).to_have_attribute("aria-label", "Update available")
                    expect(toggle).to_have_attribute("aria-expanded", "false")
                    expect(panel).to_be_hidden()
                    assert len(requests) == 1, requests
                    assert requests[0]["method"] == "POST" and requests[0]["csrf"], requests
                    controls = toggle.get_attribute("aria-controls")
                    assert controls and panel.get_attribute("id") == controls
                    assert toggle.locator("svg").count() == 1, "The alert must use the product icon set"
                    assert page.locator("dialog").count() == 0, "The alert is a small popover"

                    owner = page.locator(".campaign-hub__owner-copy").bounding_box()
                    bell = toggle.bounding_box()
                    logout = page.locator(".campaign-hub__logout").bounding_box()
                    assert owner["x"] + owner["width"] <= bell["x"] < logout["x"], (owner, bell, logout)
                    assert abs((bell["y"] + bell["height"] / 2) - (logout["y"] + logout["height"] / 2)) <= 2

                    toggle.focus()
                    page.keyboard.press("Enter")
                    expect(panel).to_be_visible()
                    expect(toggle).to_have_attribute("aria-expanded", "true")
                    expect(alert.locator("[data-update-close]")).to_be_focused()
                    expect(alert.locator("[data-update-message]")).to_have_text("A new version of Gravewright is available.")
                    expect(alert.locator("[data-update-current]")).to_have_text("0.2.1 Alpha")
                    expect(alert.locator("[data-update-available]")).to_contain_text("0.2.2 Alpha")
                    expect(alert.locator("[data-update-action]")).to_have_attribute("href", UPDATES_URL)
                    page.screenshot(path=str(OUTPUT / "available-desktop.png"), animations="disabled")
                    page.keyboard.press("Escape")
                    expect(panel).to_be_hidden()
                    expect(toggle).to_be_focused()
                    expect(toggle).to_have_attribute("aria-expanded", "false")
                    toggle.click()
                    page.locator(".campaign-empty h2").click()
                    expect(panel).to_be_hidden()
                    assert len(requests) == 1, "Opening or closing the popover must reuse the cached check"
                    report.append("new-release alert, icon position, versions, CSRF and keyboard/outside dismissal")

                    # Datastar morphs the Inside shell; the indicator must replay
                    # the existing state without issuing another release check.
                    page.get_by_role("button", name="Systems", exact=True).click()
                    expect(page.locator("[data-package-manager]")).to_be_visible()
                    expect(badge).to_be_visible()
                    assert len(requests) == 1, requests
                    toggle.click()
                    expect(alert.locator("[data-update-available]")).to_contain_text("0.2.2 Alpha")
                    page.keyboard.press("Escape")
                    page.get_by_role("button", name="Tables", exact=True).click()
                    expect(page.locator(".campaign-empty")).to_be_visible()
                    expect(badge).to_be_visible()
                    assert len(requests) == 1, requests
                    report.append("cached alert survives Datastar navigation without repeated checks")

                    page.set_viewport_size({"width": 390, "height": 844})
                    toggle.click()
                    expect(panel).to_be_visible()
                    page.wait_for_timeout(150)
                    box = panel.bounding_box()
                    assert 0 <= box["x"] and box["x"] + box["width"] <= 390, box
                    assert 0 <= box["y"] and box["y"] + box["height"] <= 844, box
                    page.screenshot(path=str(OUTPUT / "available-mobile.png"), animations="disabled")
                    page.keyboard.press("Escape")
                    page.set_viewport_size({"width": 1440, "height": 1000})
                    report.append("390px mobile popover stays within the viewport")

                    # Following the notification must select the Updates tab,
                    # rather than leaving the owner at the default campaign tab.
                    toggle.click()
                    alert.locator("[data-update-action]").click()
                    administration = page.locator("[data-administration]")
                    expect(administration).to_be_visible()
                    expect(administration.locator("[data-content=updates]")).to_be_visible()
                    expect(administration.locator("[data-content=campaigns]")).to_be_hidden()
                    expect(administration.locator("[data-tab=updates]")).to_have_class("administration__tab--active")
                    assert len(requests) == 1, requests
                    assert page.locator("[data-update-notification] .gw-update-notification__panel").is_hidden()
                    report.append("notification opens Administration directly on Updates")

                    administration.locator("[data-tab=campaigns]").click()
                    expect(administration.locator("[data-content=campaigns]")).to_be_visible()
                    toggle.click()
                    alert.locator("[data-update-action]").click()
                    expect(administration.locator("[data-content=updates]")).to_be_visible()
                    expect(administration.locator("[data-content=campaigns]")).to_be_hidden()
                    assert len(requests) == 1, requests
                    report.append("notification selects Updates when Administration is already mounted")

                    page.evaluate("value => window.dispatchEvent(new CustomEvent('gravewright:core-update-status', {detail:value}))", notification("current"))
                    expect(badge).to_be_hidden()
                    toggle.click()
                    expect(alert.locator("[data-update-message]")).to_have_text("Gravewright is up to date.")
                    expect(alert.locator("[data-update-action]")).to_be_hidden()
                    page.keyboard.press("Escape")
                    assert len(requests) == 1, requests
                    report.append("manual check status clears a stale badge without a duplicate request")

                    for status, caption in (
                        ("current", "Gravewright is up to date."),
                        ("failed", "Could not check for updates. Try again later."),
                    ):
                        response.update(status=200, body=notification(status))
                        before = len(requests)
                        page.goto(base + "/inside")
                        page.wait_for_function("document.querySelector('[data-update-toggle]')?.getAttribute('aria-busy') !== 'true'")
                        expect(badge).to_be_hidden()
                        toggle.click()
                        expect(panel).to_be_visible()
                        expect(alert.locator("[data-update-message]")).to_have_text(caption)
                        expect(alert.locator("[data-update-available]")).to_be_hidden()
                        expect(alert.locator("[data-update-action]")).to_be_hidden()
                        expect(toggle).to_have_attribute("title", "VTT updates")
                        assert len(requests) == before + 1, requests
                        page.keyboard.press("Escape")
                        report.append(status + " result has no false notification badge or install action")

                    response.update(status=503, body={"error": "request_failed"})
                    page.goto(base + "/inside")
                    toggle.click()
                    expect(alert.locator("[data-update-message]")).to_have_text("Could not check for updates. Try again later.")
                    expect(badge).to_be_hidden()
                    expect(alert.locator("[data-update-action]")).to_be_hidden()
                    report.append("transport failure is displayed without a false update alert")

                    # A manual check is newer than an already pending automatic
                    # request. Deliver the old "available" response afterward:
                    # it must not restore a badge the manual result cleared.
                    response.update(status=200, body=notification(), hold=True)
                    before = len(requests)
                    page.goto(base + "/inside")
                    deadline = time.monotonic() + 10
                    while not held_requests and time.monotonic() < deadline:
                        page.wait_for_timeout(50)
                    assert len(held_requests) == 1, "The delayed automatic check did not start"
                    expect(alert).to_have_attribute("data-update-status", "checking")
                    page.evaluate("value => window.dispatchEvent(new CustomEvent('gravewright:core-update-status', {detail:value}))", notification("current"))
                    expect(alert).to_have_attribute("data-update-status", "current")
                    response["hold"] = False
                    held_requests.pop().fulfill(status=200, json=notification())
                    page.wait_for_timeout(100)
                    expect(alert).to_have_attribute("data-update-status", "current")
                    expect(badge).to_be_hidden()
                    toggle.click()
                    expect(alert.locator("[data-update-message]")).to_have_text("Gravewright is up to date.")
                    expect(alert.locator("[data-update-action]")).to_be_hidden()
                    page.keyboard.press("Escape")
                    assert len(requests) == before + 1, requests
                    report.append("delayed automatic response cannot overwrite a newer manual check")

                    # Virtual time keeps this acceptance check fast while still
                    # exercising the real scheduling and visibility handlers.
                    response.update(status=200, body=notification("current"))
                    page.clock.install()
                    page.goto(base + "/inside")
                    toggle.click()
                    expect(alert.locator("[data-update-message]")).to_have_text("Gravewright is up to date.")
                    page.keyboard.press("Escape")
                    before = len(requests)
                    page.clock.fast_forward(300_001)
                    page.wait_for_function(
                        "document.querySelector('[data-update-notification] [data-update-message]')?.textContent === 'Gravewright is up to date.'"
                    )
                    # The request can still be awaiting the real CSRF endpoint
                    # when the virtual timer finishes, so flush its response.
                    deadline = time.monotonic() + 10
                    while len(requests) == before and time.monotonic() < deadline:
                        page.wait_for_timeout(50)
                    assert len(requests) == before + 1, requests
                    page.evaluate("""() => {
                        Object.defineProperty(document, 'visibilityState', {configurable:true, value:'hidden'});
                        Object.defineProperty(document, 'hidden', {configurable:true, value:true});
                        document.dispatchEvent(new Event('visibilitychange'));
                    }""")
                    before = len(requests)
                    page.clock.fast_forward(3_600_000)
                    page.wait_for_timeout(50)
                    assert len(requests) == before, "A hidden page must not poll for release metadata"
                    page.evaluate("""() => {
                        Object.defineProperty(document, 'visibilityState', {configurable:true, value:'visible'});
                        Object.defineProperty(document, 'hidden', {configurable:true, value:false});
                        document.dispatchEvent(new Event('visibilitychange'));
                    }""")
                    deadline = time.monotonic() + 10
                    while len(requests) == before and time.monotonic() < deadline:
                        page.wait_for_timeout(50)
                    assert len(requests) == before + 1, "Returning to a stale visible page must resume checking"
                    report.append("five-minute refresh pauses while hidden and resumes when visible")

                    player_requests = []
                    player_context = browser.new_context(viewport={"width": 1440, "height": 1000})
                    player_context.route("**" + ENDPOINT, lambda route: (
                        player_requests.append(route.request.method), route.fulfill(json=notification())
                    ))
                    player = player_context.new_page()
                    player.on("pageerror", lambda error: errors.append(str(error)))
                    player.goto(base + "/register")
                    player.locator("#owner-name").fill("Release Player")
                    player.locator("#owner-email").fill("release-player@example.test")
                    player.locator("#owner-password").fill(PASSWORD)
                    player.get_by_role("button", name="Create my account", exact=True).click()
                    expect(player.locator(".player-home")).to_be_visible()
                    expect(player.locator("[data-update-notification]")).to_have_count(0)
                    player.get_by_role("button", name="Player settings", exact=True).click()
                    expect(player.locator(".player-home__profile")).to_be_visible()
                    expect(player.locator("[data-update-notification]")).to_have_count(0)
                    assert not player_requests, player_requests
                    report.append("participants have no host notification or release-check request")
                    assert not errors, errors
                    browser.close()
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=10)
    (OUTPUT / "report.json").write_text(json.dumps({"passed": report}, indent=2) + "\n", encoding="utf-8")
    for result in report:
        print("PASS:", result, flush=True)


if __name__ == "__main__":
    main()
