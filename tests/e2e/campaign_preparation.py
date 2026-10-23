"""Exercise campaign-manager preparation tools in a browser with synthetic data.

Covers the session planner, timeline and calendar, quest columns, connections,
player preview, journal trash and the reference picker without a table socket.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen

from map_builder import ROOT, fixture_environment
from campaign_management import serve


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    errors, dialogs, cases = [], [], []
    campaign = seed["campaign"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({"executable_path": str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={"width": 1440, "height": 1000})
        context.add_cookies([{**seed["sessions"]["gm"], "url": base}])
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(error.stack or str(error)))
        page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        console = []
        page.on("console", lambda message: console.append(message.text) if message.type == "error" else None)
        try:
            run_cases(page, campaign, output, cases, expect)
        except Exception:
            alert = page.locator("[data-manager-error]")
            (output / "page-state.json").write_text(json.dumps({
                "errors": errors, "console": console, "alert": alert.text_content() if alert.is_visible() else "",
            }, indent=2), encoding="utf-8")
            page.screenshot(path=str(output / "failure.png"), full_page=True)
            raise
        browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {"cases": cases}


def run_cases(page, campaign, output, cases, expect):
    def section(name):
        page.locator(f'[data-manager-section="{name}"]').click()
        expect(page.locator(f'[data-manager-view="{name}"]')).to_be_visible()

    def shoot(name):
        page.screenshot(path=str(output / f"{name}.png"), full_page=True)

    def command(action, payload):
        return page.evaluate("""([action, payload]) => window.gravewrightRealtime.journalCommand(action, payload,
            { requestId: crypto.randomUUID() })""", [action, payload])

    page.goto(f"/campaigns/{campaign}/manage")
    expect(page.locator('[data-manager-ready="true"]')).to_be_attached(timeout=30000)
    expect(page.locator('[data-widget="pins"]')).to_be_visible()
    expect(page.locator('[data-widget="diagnostics"]')).to_be_visible()
    shoot("dashboard-1440")
    cases.append("dashboard widgets render, including system sheet diagnostics")

    # The picker searches over HTTP in the manager; it previously required the table socket.
    page.evaluate("import('/static/gravewright_table/references.js').then(module => module.pickReference(() => {}))")
    picker = page.locator('[data-window-key="reference-picker"]')
    picker.locator("input").fill("Synthetic")
    expect(picker.locator(".document-reference-results button").first).to_be_visible()
    picker.locator("[data-cancel]").click()
    cases.append("Insert reference finds documents without joining the table")

    section("sessions")
    page.locator("[data-session-create]").click()
    modal = page.locator('[data-window-key="manager-session-create"]')
    modal.locator('[name="title"]').fill("Synthetic session with a deliberately long title for layout review")
    modal.locator('[name="date"]').fill(date.today().isoformat())
    modal.locator('[type="submit"]').click()
    editor = page.locator("[data-session-editor]")
    expect(editor.locator(".campaign-prep__editor")).to_be_visible()
    editor.get_by_role("button", name="Add note").click()
    note = page.locator('[data-window-key="manager-session-note"]')
    note.locator('[name="label"]').fill("Open with the storm over the harbor")
    note.locator('[type="submit"]').click()
    editor.locator(".campaign-prep__inline input").fill("Print the synthetic handout")
    editor.locator(".campaign-prep__inline button").click()
    editor.locator("textarea").fill("Private twist: the lighthouse keeper lies.")
    editor.get_by_role("button", name="Save changes").click()
    expect(editor.get_by_role("button", name="Saved")).to_be_visible()
    shoot("sessions-1440")
    editor.get_by_role("button", name="Finish session").click()
    finish = page.locator('[data-window-key="manager-session-finish"]')
    finish.locator('[name="summary"]').fill("The party escaped the harbor.")
    expect(finish.locator('[name="pending"]')).to_have_value("Open with the storm over the harbor\nPrint the synthetic handout")
    finish.locator('[type="submit"]').click()
    expect(editor.get_by_role("button", name="Reopen session")).to_be_visible()
    cases.append("session plan saves steps, checklist and notes, then records a summary and pending work")

    section("timeline")
    page.locator("[data-event-create]").click()
    event = page.locator('[data-window-key="manager-event"]')
    event.locator('[name="title"]').fill("Harbor fire")
    event.locator('[name="worldDate"]').fill("Third day of Frostfall")
    event.locator('[name="date"]').fill(date.today().isoformat())
    event.locator('[name="upcoming"]').check()
    event.locator('[type="submit"]').click()
    expect(page.locator(".campaign-prep__event")).to_contain_text("Harbor fire")
    page.locator('[data-timeline-mode="calendar"]').click()
    expect(page.locator(".campaign-prep__day--today")).to_contain_text("Harbor fire")
    expect(page.locator(".campaign-prep__day--today")).to_contain_text("Synthetic session")
    shoot("timeline-calendar-1440")
    cases.append("timeline events appear in the list and calendar with session dates")

    quest = command("create", {"title": "Synthetic column quest", "journal_type": "quest"})["journal_id"]
    command("create", {"title": "Synthetic prerequisite quest", "journal_type": "quest"})
    section("quests")
    card = page.locator(f'[data-manager-quest-id="{quest}"]')
    expect(page.locator('.campaign-prep__column[data-status="available"]').locator(card)).to_be_visible()
    card.locator("strong").first.drag_to(page.locator('.campaign-prep__column[data-status="active"] h3'))
    expect(page.locator('.campaign-prep__column[data-status="active"]').locator(f'[data-manager-quest-id="{quest}"]')).to_be_visible()
    card = page.locator(f'[data-manager-quest-id="{quest}"]')
    card.get_by_role("button", name="Prerequisites").click()
    choice = page.locator('[data-window-key="manager-quest-prerequisites"]')
    choice.get_by_label("Synthetic prerequisite quest").check()
    choice.locator('[type="submit"]').click()
    expect(page.locator(f'[data-manager-quest-id="{quest}"] .campaign-prep__badge--warn')).to_be_visible()
    shoot("quests-1440")
    cases.append("quests move between columns and show unmet prerequisites")

    page.locator(f'[data-manager-quest-id="{quest}"]').get_by_role("button", name="Where used").click()
    expect(page.locator("[data-connections-body]")).to_contain_text("Synthetic column quest")
    expect(page.locator("[data-connections-body]")).to_contain_text("Synthetic prerequisite quest")
    cases.append("connections list a quest's links and usages")

    section("player-view")
    chooser = page.locator("[data-player-choice]")
    chooser.select_option(index=1)
    expect(page.locator("[data-player-body] .campaign-prep__preview")).to_be_visible()
    shoot("player-view-1440")
    cases.append("view as player renders the native player projection")

    doomed = command("create", {"title": "Synthetic deleted journal", "journal_type": "diary"})["journal_id"]
    command("delete", {"journal_id": doomed})
    section("history")
    trash = page.locator("[data-history-trash]")
    expect(trash).to_contain_text("Synthetic deleted journal")
    trash.get_by_role("button", name="Restore").click()
    expect(trash).not_to_contain_text("Synthetic deleted journal")
    page.locator(".journal-window, [data-journal-window], .game-window").first.wait_for(state="attached", timeout=10000)
    assert page.evaluate("id => window.gravewrightRealtime.states.get('journals').journals.some(doc => doc.id === id)", doomed)
    shoot("history-1440")
    cases.append("a deleted journal is restored from the trash with its identifier")

    page.keyboard.press("Escape")
    page.set_viewport_size({"width": 390, "height": 860})
    for name in ("overview", "sessions", "timeline", "quests"):
        section(name)
        width = page.evaluate("document.documentElement.scrollWidth")
        assert width <= 390, (name, width)
        shoot(f"{name}-390")
    cases.append("phone-width layouts have no horizontal page scroll")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(args.fixture, args.port)
        return
    output = (args.output or ROOT / 'data/campaign-preparation' /
              datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError('Use a fresh, empty output directory.')
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / 'fixture'
    fixture.mkdir()
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        port = connection.getsockname()[1]
    fixture_environment(fixture, port)
    executable = sys._base_executable if os.name == 'nt' else sys.executable
    command = [executable, '-B', '-X', 'utf8', str(Path(__file__).resolve())]
    base = f'http://127.0.0.1:{port}'
    with (output / 'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen([*command, '--serve', '--fixture', str(fixture), '--port', str(port)],
                                  cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=log)
        try:
            for _ in range(300):
                if server.poll() is not None:
                    raise RuntimeError(f"Fixture exited; inspect {output / 'server.log'}")
                try:
                    with urlopen(base, timeout=1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Fixture did not become ready.')
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
            report = check_browser(base, seed, output, args.browser_executable)
            (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps({'passed': True, 'cases': len(report['cases']), 'report': str(output / 'report.json')}))
        except Exception:
            (output / 'failure.txt').write_text(traceback.format_exc(), encoding='utf-8')
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == '__main__':
    main()
