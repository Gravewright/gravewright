"""Isolated browser acceptance for managed-update progress and reconnection.

Only a temporary account/database/storage is used. Every update request and
status response is intercepted: this scenario never replaces application files
or starts the update supervisor. Network failures are expected test fixtures;
the browser can still report those failed requests in its developer tools.
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
OUTPUT = ROOT / "test-results" / "update-progress"
UPDATES = "/inside?section=administration&tab=updates"
PASSWORD = "update-progress-test-password"
INSTALLED, TARGET = "0.2.1", "0.2.2"


def free_port():
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", 0))
        return connection.getsockname()[1]


def release_status(stage="idle", *, busy=False, current=INSTALLED, **progress):
    available = current != TARGET
    return {
        "currentVersion": current, "currentVersionLabel": current,
        "installedRelease": {
            "version": current, "name": f"Gravewright {current} — Alpha",
            "notes": f"# Gravewright {current} — Alpha\n\nInstalled release notes.",
            "url": f"https://github.com/Gravewright/gravewright/releases/tag/v{current}",
        },
        "status": "available" if available else "current",
        "availableVersion": TARGET if available else None,
        "availableVersionLabel": f"{TARGET} Alpha" if available else None,
        "releaseName": f"Gravewright {TARGET} — Alpha",
        "releaseNotes": f"# Gravewright {TARGET} — Alpha\n\nUpdate progress improvement.",
        "releaseUrl": f"https://github.com/Gravewright/gravewright/releases/tag/v{TARGET}",
        "checkedAt": int(time.time()), "installFormat": "source", "releases": [],
        "automatic": {"supported": True, "busy": busy, "stage": stage, **progress},
    }


def wait_count(page, values, expected):
    deadline = time.monotonic() + 10
    while len(values) < expected and time.monotonic() < deadline:
        page.evaluate("0")
        time.sleep(.025)
    assert len(values) == expected, (len(values), expected)


def viewport_contains(page, locator):
    rectangle = locator.bounding_box()
    assert rectangle and rectangle["x"] >= 0 and rectangle["y"] >= 0, rectangle
    assert rectangle["x"] + rectangle["width"] <= page.viewport_size["width"] + 1, rectangle
    assert rectangle["y"] + rectangle["height"] <= page.viewport_size["height"] + 1, rectangle


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = []
    with tempfile.TemporaryDirectory(prefix="gravewright-update-progress-") as temporary:
        work = Path(temporary)
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("GRAVEWRIGHT_", "DJANGO_"))}
        for name in ("media", "content", "modules", "api", "django", "runtime"):
            (work / name).mkdir()
        address = f"127.0.0.1:{free_port()}"
        base = f"http://{address}"
        env.update({
            "PYTHON_DOTENV_DISABLED": "1", "PYTHONUTF8": "1",
            "DJANGO_SETTINGS_MODULE": "config.settings", "DJANGO_DEBUG": "true",
            "GRAVEWRIGHT_HOST": "127.0.0.1", "GRAVEWRIGHT_PORT": address.rsplit(":", 1)[1],
            "GRAVEWRIGHT_DATABASE": str(work / "browser.sqlite3"),
            "GRAVEWRIGHT_MEDIA_ROOT": str(work / "media"),
            "GRAVEWRIGHT_CONTENT_ROOT": str(work / "content"),
            "GRAVEWRIGHT_MODULES_ROOT": str(work / "modules"),
            "GRAVEWRIGHT_API_MODULES_ROOT": str(work / "api"),
            "GRAVEWRIGHT_DJANGO_MODULES_ROOT": str(work / "django"),
            "GRAVEWRIGHT_MANAGED_STATE": str(work / "runtime"),
            "GRAVEWRIGHT_RELEASES_REPOSITORY": "",
        })
        subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], cwd=ROOT,
                       env=env, check=True, stdout=subprocess.DEVNULL)
        with (OUTPUT / "server.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen([sys.executable, "manage.py", "runserver", address, "--noreload"],
                                      cwd=ROOT, env=env, stdout=log, stderr=log)
            try:
                for _ in range(100):
                    try:
                        with urlopen(base, timeout=1):
                            break
                    except OSError:
                        if server.poll() is not None:
                            raise RuntimeError("Django exited; inspect test-results/update-progress/server.log")
                        time.sleep(.1)
                else:
                    raise RuntimeError("Django did not start")
                with sync_playwright() as pw:
                    browser = pw.chromium.launch()
                    context = browser.new_context(viewport={"width": 1440, "height": 1000},
                                                  reduced_motion="reduce")
                    errors, status_requests, applications, notification_requests, navigations = [], [], [], [], []
                    settled_status = []
                    state = {"status": release_status(), "offline": False, "apply_error": False,
                             "held_apply": None, "hold_apply": False, "lost_apply": None}

                    def status_route(route):
                        status_requests.append(route.request.url)
                        if state["offline"]:
                            route.abort("connectionrefused")
                        else:
                            route.fulfill(json={"updates": state["status"]})

                    def apply_route(route):
                        applications.append({
                            "method": route.request.method,
                            "csrf": route.request.headers.get("x-csrf-token", ""),
                            "body": route.request.post_data_json,
                        })
                        if state["apply_error"]:
                            route.fulfill(status=409, json={"error": "release_changed"})
                        elif state["lost_apply"]:
                            if state["lost_apply"] in {"accepted", "truncated", "server_error"}:
                                state["status"] = release_status("queued", busy=True, version=TARGET)
                            # Model an ambiguous POST: its response is lost,
                            # independently of whether the server accepted it.
                            if state["lost_apply"] == "truncated":
                                route.fulfill(status=202, content_type="application/json", body='{"stage":')
                            elif state["lost_apply"] == "server_error":
                                route.fulfill(status=500, json={"error": "audit_failed_after_enqueue"})
                            else:
                                route.abort("connectionreset")
                        elif state["hold_apply"]:
                            state["held_apply"] = route
                        else:
                            state["status"] = release_status("queued", busy=True, version=TARGET)
                            route.fulfill(status=202, json=state["status"]["automatic"])

                    def notification_route(route):
                        notification_requests.append(route.request.url)
                        route.fulfill(json={"status": "available", "available": True,
                                            "currentVersion": INSTALLED, "availableVersion": TARGET,
                                            "url": UPDATES})

                    context.route("**/api/admin/status", status_route)
                    context.route("**/api/admin/updates/apply", apply_route)
                    context.route("**/api/admin/updates/notification", notification_route)
                    context.route("**/api/admin/updates/check", lambda route: route.fulfill(json=state["status"]))
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("framenavigated", lambda frame: navigations.append(frame.url) if frame == page.main_frame else None)
                    for event in ("requestfinished", "requestfailed"):
                        page.on(event, lambda request: settled_status.append(request.url)
                                if request.url.endswith("/api/admin/status") else None)
                    page.goto(base)
                    page.locator("#owner-name").fill("Update Progress Owner")
                    page.locator("#owner-email").fill("progress-owner@example.test")
                    page.locator("#owner-password").fill(PASSWORD)
                    page.get_by_role("button", name="Create administrator", exact=True).click()
                    expect(page.locator("#inside-shell")).to_be_visible()
                    now = int(time.time() * 1000)
                    page.clock.install(time=now)
                    page.clock.pause_at(now + 10)

                    def open_updates(value=None):
                        state.update(status=value or release_status(), offline=False,
                                     apply_error=False, hold_apply=False, held_apply=None, lost_apply=None)
                        page.goto(base + UPDATES)
                        expect(page.locator("[data-content=updates]")).to_be_visible()
                        expect(page.locator("[data-action=check-updates]")).to_be_enabled()

                    def advance_status(milliseconds, value=None):
                        if value is not None:
                            state["status"] = value
                        count, settled = len(status_requests), len(settled_status)
                        page.clock.fast_forward(milliseconds)
                        wait_count(page, status_requests, count + 1)
                        wait_count(page, settled_status, settled + 1)
                        page.evaluate("Promise.resolve()")

                    def start_update():
                        page.locator("[data-action=apply-update]").click()
                        expect(page.locator("[data-update-progress]")).to_be_visible()
                        expect(page.locator("[data-update-stage]")).to_contain_text("queue", ignore_case=True)

                    modal = page.locator("[data-update-progress]")
                    bar = modal.locator("[data-update-progress-bar]")

                    # Historical completion must not reopen a modal or reload
                    # the page merely because the owner visits Administration.
                    open_updates(release_status("complete", current=TARGET, version=TARGET,
                                                backup="C:\\private-old-installation\\Gravewright.old"))
                    before = len(navigations)
                    expect(modal).to_have_count(0)
                    page.clock.fast_forward(60_000)
                    assert len(navigations) == before
                    assert "private-old-installation" not in page.locator("body").inner_text()
                    report.append("historical completion stays quiet and exposes no private rollback paths")

                    open_updates()
                    state["hold_apply"] = True
                    page.locator("[data-action=apply-update]").click()
                    expect(modal).to_be_visible()
                    assert modal.evaluate("element => element.localName") == "section"
                    expect(modal).to_have_attribute("role", "dialog")
                    expect(modal).to_have_attribute("aria-modal", "true")
                    expect(page.locator("dialog")).to_have_count(0)
                    assert page.locator("#inside-shell").evaluate("element => !!element.closest('[inert]')")
                    assert modal.evaluate("element => element.contains(document.activeElement)")
                    expect(bar).not_to_have_attribute("value", "100")
                    page.keyboard.press("Escape")
                    expect(modal).to_be_visible()
                    page.keyboard.press("Tab")
                    assert modal.evaluate("element => element.contains(document.activeElement)")
                    assert state["held_apply"] is not None
                    state["status"] = release_status("queued", busy=True, version=TARGET)
                    state["held_apply"].fulfill(status=202, json=state["status"]["automatic"])
                    state["held_apply"] = None
                    expect(modal.locator("[data-update-stage]")).to_contain_text("queue", ignore_case=True)
                    assert applications[-1]["method"] == "POST" and applications[-1]["csrf"]
                    assert applications[-1]["body"] == {"version": TARGET, "keep_old": True}
                    report.append("accepted update uses CSRF and an immediate project modal with trapped focus and blocked Escape")

                    advance_status(1500, release_status("download", busy=True, received=250, total=1000))
                    expect(bar).to_have_attribute("value", "25")
                    expect(modal.locator("[data-update-progress-value]")).to_contain_text("25%")
                    expect(modal.locator('[data-step=download]')).to_have_attribute("data-state", "active")
                    expect(modal.locator("[data-update-close]")).to_be_hidden()
                    page.screenshot(path=str(OUTPUT / "download-desktop.png"), animations="disabled")
                    advance_status(1500, release_status("dependencies", busy=True))
                    expect(bar).not_to_have_attribute("value", "25")
                    assert bar.get_attribute("value") is None
                    expect(modal.locator('[data-step=download]')).to_have_attribute("data-state", "done")
                    expect(modal.locator('[data-step=dependencies]')).to_have_attribute("data-state", "active")
                    assert "%" not in modal.locator("[data-update-progress-value]").inner_text()
                    report.append("download uses true received bytes while other confirmed stages remain indeterminate")

                    page.set_viewport_size({"width": 390, "height": 844})
                    viewport_contains(page, modal)
                    assert modal.evaluate("element => element.scrollWidth <= element.clientWidth + 1")
                    page.screenshot(path=str(OUTPUT / "progress-mobile.png"), animations="disabled")
                    page.set_viewport_size({"width": 1440, "height": 1000})
                    report.append("progress modal fits a 390px viewport with reduced motion enabled")

                    state["offline"] = True
                    advance_status(1500)
                    expect(modal.locator("[data-update-stage]")).to_contain_text("server", ignore_case=True)
                    assert bar.get_attribute("value") is None
                    before = len(status_requests)
                    page.clock.fast_forward(9000)
                    page.evaluate("0")
                    assert len(status_requests) == before, "Disconnected update must not poll every two seconds"
                    advance_status(1000)
                    before = len(status_requests)
                    page.clock.fast_forward(19_000)
                    page.evaluate("0")
                    assert len(status_requests) == before
                    advance_status(1000)
                    before = len(status_requests)
                    page.clock.fast_forward(29_000)
                    page.evaluate("0")
                    assert len(status_requests) == before
                    advance_status(1000)
                    report.append("expected restart failures back off to 10, 20 and 30 seconds instead of console-spamming every two seconds")

                    page.evaluate("""() => {
                        Object.defineProperty(document, 'hidden', {configurable:true, value:true});
                        Object.defineProperty(document, 'visibilityState', {configurable:true, value:'hidden'});
                        document.dispatchEvent(new Event('visibilitychange'));
                    }""")
                    before, bell_before = len(status_requests), len(notification_requests)
                    page.clock.fast_forward(600_000)
                    page.evaluate("0")
                    assert len(status_requests) == before
                    assert len(notification_requests) == bell_before
                    page.evaluate("""() => {
                        Object.defineProperty(document, 'hidden', {configurable:true, value:false});
                        Object.defineProperty(document, 'visibilityState', {configurable:true, value:'visible'});
                        Object.defineProperty(navigator, 'onLine', {configurable:true, value:false});
                        document.dispatchEvent(new Event('visibilitychange'));
                        window.dispatchEvent(new Event('offline'));
                    }""")
                    page.clock.fast_forward(60_000)
                    page.evaluate("0")
                    assert len(status_requests) == before
                    page.evaluate("""() => {
                        Object.defineProperty(navigator, 'onLine', {configurable:true, value:true});
                        window.dispatchEvent(new Event('online'));
                    }""")
                    state["offline"] = False
                    advance_status(2000, release_status("restart", busy=True))
                    expect(modal.locator('[data-step=restart]')).to_have_attribute("data-state", "active")
                    report.append("hidden/offline pages suspend probes and the release bell; returning online resumes safely")

                    # A completed job is not sufficient while the server still
                    # identifies itself as the old version or holds the lock.
                    before = len(navigations)
                    advance_status(1500, release_status("complete", busy=True, current=TARGET, version=TARGET))
                    page.evaluate("0")
                    assert len(navigations) == before
                    advance_status(1500, release_status("complete", current=INSTALLED, version=TARGET))
                    expect(modal).to_be_visible()
                    assert len(navigations) == before
                    state["status"] = release_status("complete", current=TARGET, version=TARGET)
                    # This long-running fixture offers manual confirmation.
                    # Wait for the correct status before advancing its reload
                    # timer so assertions do not race a destroyed JS context.
                    reconnect = modal.locator("[data-update-reconnect]")
                    expect(reconnect).to_be_visible()
                    count = len(status_requests)
                    reconnect.click()
                    page.clock.fast_forward(1)
                    wait_count(page, status_requests, count + 1)
                    expect(modal.locator("[data-update-stage]")).to_contain_text("complete", ignore_case=True)
                    # Visibility/connectivity events must not cancel the
                    # terminal reload timer when there is no active probe.
                    page.evaluate("""() => {
                        document.dispatchEvent(new Event('visibilitychange'));
                        window.dispatchEvent(new Event('online'));
                    }""")
                    with page.expect_navigation(wait_until="domcontentloaded"):
                        page.clock.fast_forward(1500)
                    assert len(navigations) == before + 1, navigations
                    expect(modal).to_have_count(0)
                    page.clock.fast_forward(120_000)
                    assert len(navigations) == before + 1, "Successful update must reload only once"
                    report.append("success reloads once only after the job ends and the target version is confirmed, including visibility/connectivity changes")

                    for stage in ("rolled_back", "failed"):
                        open_updates()
                        start_update()
                        before = len(navigations)
                        advance_status(1500, release_status(stage, error="PrivateFailure", backup="C:\\private-recovery"))
                        expect(modal.locator("[data-update-close]")).to_be_visible()
                        if stage == "rolled_back":
                            expect(modal).to_contain_text("previous version", ignore_case=True)
                            expect(modal).to_contain_text("failed", ignore_case=True)
                        else:
                            expect(modal.locator("[data-update-stage]")).to_contain_text("could not", ignore_case=True)
                        assert "private-recovery" not in modal.inner_text()
                        assert "PrivateFailure" not in modal.inner_text()
                        page.clock.fast_forward(60_000)
                        assert len(navigations) == before
                        page.keyboard.press("Escape")
                        expect(modal).to_have_count(0)
                        assert not page.locator("#inside-shell").evaluate("element => !!element.closest('[inert]')")
                    report.append("rollback and failed updates explain the result, restore interaction and never reload or expose private paths")

                    open_updates()
                    state["apply_error"] = True
                    page.locator("[data-action=apply-update]").click()
                    expect(modal).to_be_visible()
                    expect(modal.locator("[data-update-close]")).to_be_visible()
                    expect(modal.locator("[data-update-hint]")).to_contain_text("start", ignore_case=True)
                    before = len(status_requests)
                    page.clock.fast_forward(60_000)
                    page.evaluate("0")
                    assert len(status_requests) == before
                    modal.locator("[data-update-close]").click()
                    expect(modal).to_have_count(0)
                    report.append("rejected update requests remain actionable and do not start a reconnect loop")

                    open_updates()
                    state["lost_apply"] = "accepted"
                    applications_before = len(applications)
                    page.locator("[data-action=apply-update]").click()
                    expect(modal).to_be_visible()
                    expect(modal.locator("[data-update-hint]")).to_contain_text("does not send the update again")
                    expect(modal.locator("[data-update-close]")).to_be_hidden()
                    assert modal.get_attribute("data-state") != "failed"
                    assert bar.get_attribute("value") is None
                    wait_count(page, applications, applications_before + 1)
                    before = len(status_requests)
                    page.clock.fast_forward(9000)
                    page.evaluate("0")
                    assert len(status_requests) == before
                    advance_status(1000)
                    expect(modal.locator("[data-update-stage]")).to_contain_text("queue", ignore_case=True)
                    assert len(applications) == applications_before + 1
                    advance_status(1500, release_status("dependencies", busy=True, version=TARGET))
                    expect(modal.locator('[data-step=dependencies]')).to_have_attribute("data-state", "active")
                    advance_status(1500, release_status("failed"))
                    expect(modal.locator("[data-update-close]")).to_be_visible()
                    modal.locator("[data-update-close]").click()
                    report.append("lost POST response confirms the accepted job through status without declaring failure or submitting twice")

                    # An accepted job can outlive a malformed success response
                    # or a later server error (for example an audit write).
                    # Neither response proves that enqueueing was rejected.
                    for response in ("truncated", "server_error"):
                        open_updates()
                        state["lost_apply"] = response
                        applications_before = len(applications)
                        page.locator("[data-action=apply-update]").click()
                        expect(modal).to_be_visible()
                        expect(modal.locator("[data-update-hint]")).to_contain_text("does not send the update again")
                        expect(modal.locator("[data-update-close]")).to_be_hidden()
                        assert modal.get_attribute("data-state") != "failed"
                        wait_count(page, applications, applications_before + 1)
                        advance_status(10_000)
                        expect(modal.locator("[data-update-stage]")).to_contain_text("queue", ignore_case=True)
                        assert len(applications) == applications_before + 1
                        advance_status(1500, release_status("dependencies", busy=True, version=TARGET))
                        expect(modal.locator('[data-step=dependencies]')).to_have_attribute("data-state", "active")
                        assert len(applications) == applications_before + 1
                        advance_status(1500, release_status("failed"))
                        expect(modal.locator("[data-update-close]")).to_be_visible()
                        modal.locator("[data-update-close]").click()
                    report.append("truncated HTTP 202 and HTTP 500 after enqueue confirm the accepted job without a duplicate update request")

                    # Supervisor progress snapshots after 'queued' currently
                    # omit the version. A healthy busy preparation snapshot
                    # must not be mistaken for proof that no job was accepted.
                    open_updates()
                    state["lost_apply"] = "accepted"
                    applications_before = len(applications)
                    page.locator("[data-action=apply-update]").click()
                    expect(modal.locator("[data-update-hint]")).to_contain_text("does not send the update again")
                    wait_count(page, applications, applications_before + 1)
                    advance_status(10_000, release_status("dependencies", busy=True))
                    expect(modal.locator('[data-step=dependencies]')).to_have_attribute("data-state", "active")
                    assert len(applications) == applications_before + 1
                    advance_status(1500, release_status("failed"))
                    expect(modal.locator("[data-update-close]")).to_be_visible()
                    modal.locator("[data-update-close]").click()
                    report.append("a lost POST response also recovers a busy intermediate snapshot that omits the target version")

                    open_updates()
                    state["lost_apply"] = "absent"
                    applications_before = len(applications)
                    page.locator("[data-action=apply-update]").click()
                    expect(modal).to_be_visible()
                    expect(modal.locator("[data-update-hint]")).to_contain_text("does not send the update again")
                    expect(modal.locator("[data-update-close]")).to_be_hidden()
                    wait_count(page, applications, applications_before + 1)
                    advance_status(10_000)
                    expect(modal.locator("[data-update-close]")).to_be_hidden()
                    advance_status(5000)
                    expect(modal.locator("[data-update-close]")).to_be_hidden()
                    advance_status(5000)
                    expect(modal.locator("[data-update-close]")).to_be_visible()
                    expect(modal.locator("[data-update-hint]")).to_contain_text("no update to this version is running")
                    assert len(applications) == applications_before + 1
                    before = len(status_requests)
                    page.clock.fast_forward(60_000)
                    page.evaluate("0")
                    assert len(status_requests) == before
                    modal.locator("[data-update-close]").click()
                    report.append("three healthy no-job confirmations make a lost unaccepted POST actionable without a duplicate update request")

                    open_updates()
                    start_update()
                    state["offline"] = True
                    advance_status(1500)
                    for delay in (10_000, 20_000, *([30_000] * 7)):
                        advance_status(delay)
                    expect(modal.locator("[data-update-reconnect]")).to_be_visible()
                    before = len(status_requests)
                    page.clock.fast_forward(600_000)
                    page.evaluate("0")
                    assert len(status_requests) == before, "Repeated failures must pause instead of polling forever"
                    assert "%" not in modal.locator("[data-update-progress-value]").inner_text()
                    state["offline"] = False
                    state["status"] = release_status("rolled_back")
                    modal.locator("[data-update-reconnect]").click()
                    advance_status(1)
                    expect(modal.locator("[data-update-close]")).to_be_visible()
                    report.append("ten failed probes pause without inventing failure or percentage; explicit reconnection recovers the real result")

                    # A removed Administration root must dispose pending work,
                    # even if a Datastar navigation replaces the page shell.
                    modal.locator("[data-update-close]").click()
                    open_updates()
                    start_update()
                    page.evaluate("document.querySelector('[data-administration]').remove()")
                    before = len(status_requests)
                    page.clock.fast_forward(60_000)
                    page.evaluate("0")
                    assert len(status_requests) == before
                    expect(modal).to_have_count(0)
                    assert not errors, errors
                    report.append("removing the administration root disposes update polling without uncaught JavaScript errors")
                    browser.close()
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=10)
    (OUTPUT / "report.json").write_text(json.dumps({"passed": report}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for result in report:
        print("PASS:", result, flush=True)


if __name__ == "__main__":
    main()
