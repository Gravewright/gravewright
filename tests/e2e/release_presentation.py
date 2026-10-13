"""Offline release notes, safe Markdown and responsive update administration.

Run with the project Python environment. All account/database/storage state is
temporary. Real status responses exercise bundled metadata; only release
discovery and subsequent check results are mocked, without external requests.
"""

import copy
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
PROJECT_VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
OUTPUT = ROOT / "test-results" / "release-presentation"
UPDATES = "/inside?section=administration&tab=updates"
PASSWORD = "release-presentation-test-password"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def notes():
    # The final marker lies beyond the former 4,000-character truncation.
    return "\n\n".join((
        "# Gravewright 0.2.2 — Alpha",
        "## Changes in English",
        "- **English-only improvement** with `offline` notes.",
        "## Português (Brasil)",
        "## Melhorias recentes",
        "- **Melhoria em destaque** com `salvamento automático`.\n- Segunda melhoria.",
        "[Manual relativo](../manual.md) e [Documentação oficial](https://github.com/Gravewright/gravewright).",
        '[Link inseguro](javascript:alert(1)) e [Link de dados](data:text/html,attack).',
        '<img src=x onerror="window.releaseNotesAttack=true"><script>window.releaseNotesAttack=true</script>',
        "```js\nconst example = '<script>not executed</script>';\n```",
        "\n\n".join(f"Parágrafo completo {index}: " + "melhoria documentada " * 12 for index in range(30)),
        "MARCADOR_FINAL_NOTAS_COMPLETAS",
    ))


def release_result(installed, status="available", *, supported=True):
    result = copy.deepcopy(installed)
    result.update({
        "status": status,
        "checkedAt": int(time.time()),
        "automatic": {"supported": supported, "busy": False, "stage": "idle"},
        "releases": [],
    })
    if status == "available":
        result.update({
            "availableVersion": "0.2.2",
            "availableVersionLabel": "0.2.2 Alpha",
            "releaseName": "Gravewright 0.2.2 — Alpha",
            "releaseNotes": notes(),
            "releaseUrl": "https://github.com/Gravewright/gravewright/releases/tag/v0.2.2",
            "artifact": {
                "name": "Gravewright-0.2.2-django.zip",
                "url": "https://github.com/Gravewright/gravewright/releases/download/v0.2.2/Gravewright-0.2.2-django.zip",
                "sha256": "a" * 64,
                "size": 12345,
            },
        })
        result["releases"] = [{
            "version": "0.2.2", "name": result["releaseName"], "notes": result["releaseNotes"],
            "url": result["releaseUrl"], "publishedAt": "2026-10-13T15:00:00Z", "channel": "stable",
            "installed": False, "artifact": result["artifact"],
        }]
    return result


def assert_within_viewport(page, root):
    box = root.bounding_box()
    assert box and box["x"] >= 0 and box["x"] + box["width"] <= page.viewport_size["width"] + 1, box
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Horizontal page overflow"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = []
    with tempfile.TemporaryDirectory(prefix="gravewright-release-presentation-") as temporary:
        work = Path(temporary)
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("GRAVEWRIGHT_", "DJANGO_"))}
        address = f"127.0.0.1:{free_port()}"
        base = f"http://{address}"
        for name in ("media", "content", "modules", "api", "django", "runtime"):
            (work / name).mkdir()
        # A previous completed update must not advertise stale rollback paths.
        (work / "runtime" / "progress.json").write_text(json.dumps({
            "stage": "complete", "version": "0.1.2", "backup": "C:\\old-private-installation\\Gravewright.old",
        }), encoding="utf-8")
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
        subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"],
                       cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
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
                            raise RuntimeError("Django exited; inspect test-results/release-presentation/server.log")
                        time.sleep(.1)
                else:
                    raise RuntimeError("Django did not start")
                with sync_playwright() as pw:
                    browser = pw.chromium.launch()
                    context = browser.new_context(viewport={"width": 1440, "height": 1000})
                    errors, manual_checks, status_requests = [], [], []
                    context.route("**/api/admin/updates/notification", lambda route: route.fulfill(json={
                        "status": "unchecked", "available": False, "currentVersion": PROJECT_VERSION, "url": UPDATES,
                    }))
                    # Never send an update request from this presentation test.
                    context.route("**/api/admin/updates/apply", lambda route: route.abort())
                    state = {"mock_status": None, "check_status": 200, "check_body": None}

                    def status_route(route):
                        status_requests.append(route.request.url)
                        if state["mock_status"] is None:
                            route.continue_()
                        else:
                            route.fulfill(json={"updates": state["mock_status"]})

                    def check_route(route):
                        manual_checks.append({"method": route.request.method,
                                              "csrf": route.request.headers.get("x-csrf-token", "")})
                        route.fulfill(status=state["check_status"], json=state["check_body"])

                    context.route("**/api/admin/status", status_route)
                    context.route("**/api/admin/updates/check", check_route)
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(base)
                    page.locator("#owner-name").fill("Release Owner")
                    page.locator("#owner-email").fill("presentation-owner@example.test")
                    page.locator("#owner-password").fill(PASSWORD)
                    page.get_by_role("button", name="Create administrator", exact=True).click()
                    expect(page.locator("#inside-shell")).to_be_visible()
                    actual = page.request.get(base + "/api/admin/status").json()["updates"]
                    assert actual["status"] == "unchecked", actual
                    assert actual["installedRelease"]["source"] == "bundled", actual
                    assert actual["currentVersion"] == PROJECT_VERSION, actual
                    assert actual["installedRelease"]["name"] == f"Gravewright {PROJECT_VERSION} — Alpha", actual
                    assert len(actual["installedRelease"]["notes"]) > 4000
                    assert "## Português (Brasil)" in actual["installedRelease"]["notes"]
                    page.goto(base + UPDATES)
                    root = page.locator("[data-content=updates]")
                    expect(root).to_be_visible()
                    expect(root.locator("[data-installed-release-name]")).to_have_text(actual["installedRelease"]["name"])
                    expect(root.locator("[data-release-notes-name]")).to_contain_text(actual["installedRelease"]["name"])
                    expect(root.locator("[data-release-notes]")).to_be_visible()
                    expect(root.locator("[data-release-notes] h2").first).to_have_text("Changes")
                    expect(root.locator("[data-release-notes]")).not_to_contain_text("Português (Brasil)")
                    expect(root.locator("[name=channel], [data-form=channel], [data-channel-risk]")).to_have_count(0)
                    expect(root.locator(".administration__install")).to_be_hidden()
                    expect(root.locator("[data-action=apply-update]")).to_be_hidden()
                    assert "old-private-installation" not in root.inner_text()
                    assert not manual_checks, "Opening Updates must display bundled notes without requiring a check"
                    assert_within_viewport(page, root)
                    page.screenshot(path=str(OUTPUT / "installed-desktop.png"), animations="disabled")
                    report.append("real offline status displays the full installed release name and bundled formatted notes before checking")
                    report.append("channel controls and stale completed-update/rollback paths are absent")

                    state["check_body"] = release_result(actual, "current")
                    root.locator("[data-action=check-updates]").click()
                    expect(root.locator("[data-update-summary]")).to_contain_text("Up to date")
                    expect(root.locator(".administration__install")).to_be_hidden()
                    expect(root.locator("[data-action=check-updates]")).to_be_enabled()
                    expect(root.locator("[data-release-notes] h2").first).to_have_text("Changes")
                    report.append("current check keeps installed notes and hides unnecessary install controls")

                    # The page locale is set before module initialization, as if
                    # selected through the official translation provider.
                    page.add_init_script("""new MutationObserver((_, observer) => {
                        if (document.documentElement) {
                            document.documentElement.lang = 'pt-BR'; observer.disconnect();
                        }
                    }).observe(document, {childList:true});""")
                    # Keep discovery fixtures as a genuine 0.2.1 -> 0.2.2
                    # upgrade, independently of the checkout's installed version.
                    installed_fixture = copy.deepcopy(actual)
                    installed_fixture.update(currentVersion="0.2.1", currentVersionLabel="0.2.1")
                    installed_fixture["installedRelease"].update(
                        version="0.2.1", name="Gravewright 0.2.1 — Alpha",
                        notes="# Gravewright 0.2.1 — Alpha\n\n## Changes\nInstalled changes.\n\n## Português (Brasil)\nAlterações instaladas.",
                        url="https://github.com/Gravewright/gravewright/releases/tag/v0.2.1",
                    )
                    available = release_result(installed_fixture)
                    state["mock_status"] = available
                    page.goto(base + UPDATES)
                    expect(root.locator("[data-release-notes-name]")).to_contain_text("Gravewright 0.2.2 — Alpha")
                    expect(root.locator("[data-installed-release-name]")).to_have_text(installed_fixture["installedRelease"]["name"])
                    content = root.locator("[data-release-notes]")
                    expect(content.locator("h2").first).to_have_text("Melhorias recentes")
                    expect(content.locator("strong").first).to_have_text("Melhoria em destaque")
                    expect(content.locator("ul > li")).to_have_count(2)
                    expect(content.locator("code").first).to_have_text("salvamento automático")
                    expect(content).not_to_contain_text("English-only improvement")
                    expect(content).to_contain_text("MARCADOR_FINAL_NOTAS_COMPLETAS")
                    expect(content.locator("img, script, iframe, object, embed")).to_have_count(0)
                    assert not page.evaluate("window.releaseNotesAttack || false")
                    assert not content.locator('a[href^="javascript:"], a[href^="data:"]').count()
                    for link in content.locator("a").all():
                        assert link.get_attribute("href").startswith("https://github.com/"), link.get_attribute("href")
                        assert link.get_attribute("target") == "_blank"
                        assert {"noopener", "noreferrer"}.issubset(set(link.get_attribute("rel").split()))
                    expect(content.get_by_role("link", name="Manual relativo", exact=True)).to_have_attribute(
                        "href", "https://github.com/Gravewright/gravewright/blob/v0.2.2/docs/manual.md")
                    expect(root.locator(".administration__install")).to_be_visible()
                    expect(root.locator("[data-action=apply-update]")).to_be_visible()
                    expect(root.locator("[data-action=apply-update]")).to_be_enabled()
                    checkbox = root.locator("[data-update-keep-old]")
                    expect(checkbox).to_be_checked()
                    expect(checkbox).to_be_enabled()
                    assert_within_viewport(page, root)
                    page.screenshot(path=str(OUTPUT / "available-desktop.png"), animations="disabled")
                    report.append("available release keeps the installed title, previews the candidate notes and offers installation only when supported")
                    report.append("Portuguese notes keep formatting and content beyond 4,000 characters without duplicating English")
                    report.append("release Markdown escapes raw HTML, rejects active links and resolves safe relative documentation links")

                    page.set_viewport_size({"width": 390, "height": 844})
                    assert_within_viewport(page, root)
                    for selector in ("[data-action=check-updates]", "[data-action=apply-update]"):
                        assert_within_viewport(page, root.locator(selector))
                    page.screenshot(path=str(OUTPUT / "available-mobile.png"), animations="disabled", full_page=True)
                    report.append("390px screen keeps version, notes and update actions within the viewport")

                    content.focus()
                    expect(content).to_be_focused()
                    page.keyboard.press("End")
                    page.wait_for_function("element => element.scrollTop + element.clientHeight >= element.scrollHeight - 2",
                                           arg=content.element_handle())
                    final_note = content.get_by_text("MARCADOR_FINAL_NOTAS_COMPLETAS", exact=True).bounding_box()
                    notes_box = content.bounding_box()
                    assert final_note["y"] >= notes_box["y"] and final_note["y"] + final_note["height"] <= notes_box["y"] + notes_box["height"] + 1
                    report.append("bounded long notes remain keyboard accessible through the final paragraph")

                    # History is progressive disclosure; expanding it uses the
                    # same safe formatting instead of an unformatted pre block.
                    history = root.locator("[data-release-history]")
                    expect(history.locator("details[open]")).to_have_count(0)
                    history.locator("details > summary").first.click()
                    expect(history.locator(".release-notes")).to_be_visible()
                    expect(history.locator("script, img, iframe")).to_have_count(0)
                    expect(history.locator(".release-notes")).to_contain_text("MARCADOR_FINAL_NOTAS_COMPLETAS")
                    report.append("release history remains collapsed until requested and uses the safe Markdown presentation")

                    unsupported = release_result(installed_fixture, supported=False)
                    state["mock_status"] = unsupported
                    page.goto(base + UPDATES)
                    expect(root.locator("[data-release-notes-name]")).to_contain_text("Gravewright 0.2.2 — Alpha")
                    expect(root.locator("[data-action=apply-update]")).to_be_hidden()
                    report.append("unsupported installations preview releases without offering a nonfunctional install action")

                    state["check_body"] = release_result(installed_fixture, "failed")
                    root.locator("[data-action=check-updates]").click()
                    expect(root.locator("[data-update-summary]")).to_contain_text("Não foi possível verificar atualizações")
                    expect(root.locator("[data-release-notes-name]")).to_contain_text(installed_fixture["installedRelease"]["name"])
                    expect(root.locator("[data-action=apply-update]")).to_be_hidden()
                    expect(root.locator("[data-action=check-updates]")).to_be_enabled()
                    expect(content).not_to_be_empty()
                    report.append("failed discovery falls back to bundled installed notes and leaves the check action usable")

                    state.update(check_status=503, check_body={"error": "request_failed"})
                    root.locator("[data-action=check-updates]").click()
                    expect(page.locator("[data-administration] > [role=alert]")).to_be_visible()
                    expect(content).not_to_be_empty()
                    expect(root.locator("[data-action=check-updates]")).to_be_enabled()
                    assert all(item["method"] == "POST" and item["csrf"] for item in manual_checks), manual_checks
                    assert len(manual_checks) == 3, manual_checks
                    assert len(status_requests) >= 3, status_requests
                    assert not errors, errors
                    report.append("transport errors preserve notes; manual checks use authenticated POST/CSRF without JavaScript errors")
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
