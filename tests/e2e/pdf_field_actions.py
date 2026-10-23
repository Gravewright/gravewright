"""Exercise PDF field actions through native actor sheets and real chat rolls.

Extends the disposable manual-PDF fixture with synthetic numeric/text fields.
No operator database, document, module installation or licensed sheet is reused.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen
from uuid import uuid4

from map_builder import ROOT, MEASURE, change_locale, fixture_environment
from pdf_manual_fields import fillable_pdf, serve as serve_pdf


ROLL_PROBE = """(() => {
  window.__pdfActionRolls = [];
  window.__pdfActionRollRequests = [];
  const Native = window.WebSocket;
  window.WebSocket = class extends Native {
    constructor(...args) {
      super(...args);
      this.addEventListener('message', event => {
        try {
          const message = JSON.parse(event.data);
          if(message.type === 'chat.message' && message.payload?.roll)
            window.__pdfActionRolls.push(message.payload);
        } catch {}
      });
    }
    send(...args) {
      try {
        const message = JSON.parse(args[0]);
        if(message.type === 'dice.roll') window.__pdfActionRollRequests.push(message.payload);
      } catch {}
      return super.send(...args);
    }
  };
})();"""


def serve(fixture, port):
    from django.core import management

    original = management.call_command

    def command(name, *args, **kwargs):
        if name == "runserver":
            from django.core.files.base import ContentFile
            from gravewright.actors.models import Actor, Asset
            from gravewright.maps.models import Broadcast
            from gravewright.pdf_system.schema import normalize

            seed_file = fixture / "seed.json"
            seed = json.loads(seed_file.read_text(encoding="utf-8"))
            actor = Actor.objects.get(pk=seed["actor"])
            other_native = Asset(campaign=actor.campaign, kind="pdf", name="Other HP sheet.pdf")
            other_native.file.save("synthetic-other-hp.pdf", ContentFile(fillable_pdf()), save=True)
            seed["pdfAssets"].append(str(other_native.pk))
            definitions = []
            for kind, label, rect in (
                ("number", "Vitality", (.1, .08, .2, .04)),
                ("text", "Hero name", (.4, .08, .4, .04)),
            ):
                definitions.append({
                    "id": str(uuid4()), "source": "asset:" + seed["pdfAssets"][0],
                    "page": 1, "type": kind, "name": label,
                    **dict(zip(("x", "y", "width", "height"), rect)),
                })
            actor.data["pdf"]["manualFields"] = definitions
            actor.data["fields"] = {
                "manual_" + field["id"].replace("-", ""): 10 if field["type"] == "number" else "Aster"
                for field in definitions
            }
            actor.data = normalize(actor.data)
            actor.save(update_fields=["data"])
            # Both clients observe the same real scene-scoped chat stream.
            Broadcast.objects.filter(campaign_id=seed["campaign"]).update(scene_id=seed["selectedScene"])
            seed.update(broadcastScene=seed["selectedScene"], manualFields=definitions)
            seed_file.write_text(json.dumps(seed, indent=2), encoding="utf-8")
        return original(name, *args, **kwargs)

    management.call_command = command
    try:
        serve_pdf(fixture, port)
    finally:
        management.call_command = original


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    records, errors, dialogs, failed = [], [], [], []
    campaign = seed["campaign"]
    actor_url = f"/api/containers/{campaign}/actors/{seed['actor']}/sheet"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({"executable_path": str(executable)} if executable else {}))
        contexts = []

        def client(role):
            context = browser.new_context(base_url=base, viewport={"width": 1440, "height": 1000})
            contexts.append(context)
            context.add_init_script(ROLL_PROBE)
            context.add_cookies([{**seed["sessions"][role], "url": base}])
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("requestfailed", lambda request: failed.append({"url": request.url, "error": request.failure}))

            def native_dialog(dialog):
                dialogs.append({"type": dialog.type, "message": dialog.message})
                dialog.dismiss()

            page.on("dialog", native_dialog)
            response = page.goto(f"{base}/game/{campaign}")
            assert response.ok, response.status
            page.wait_for_function("!!window.gravewrightActors && !!window.gravewrightRealtime")
            expect(page.locator(".game-menubar__presence")).to_have_attribute("data-presence", "seated")
            return page

        def open_sheet(page, token=None):
            page.evaluate("args => window.gravewrightActors.open(args.actor, args.token)",
                          {"actor": seed["actor"], "token": token})
            sheet = page.locator(".token-sheet" if token else ".actor-directory__sheet")
            expect(sheet.locator(".pdf-sheet__canvas")).to_have_count(1)
            return sheet

        def close_sheet(sheet):
            sheet.locator("[data-window=close]").click()
            expect(sheet).to_have_count(0)

        def field(sheet, name):
            return sheet.locator(".pdf-sheet__fields").get_by_label(name, exact=True)

        def read(page, token_id=None):
            response = page.request.get(actor_url + ("?tokenId=" + token_id if token_id else ""))
            assert response.ok, response.text()
            return response.json()

        def source(sheet, name):
            sheet.locator("[data-pdf=togglePicker]").click()
            sheet.locator("[data-pdf-sources]").get_by_role("button", name=name, exact=True).click()
            expect(sheet.locator(".pdf-sheet__picker")).to_be_hidden()
            expect(sheet.locator(".pdf-sheet__canvas")).to_have_count(1)

        def action_dialog(page, target):
            target.dblclick()
            modal = page.locator("[data-pdf-field-actions]")
            expect(modal).to_be_visible()
            expect(modal).to_have_attribute("role", "dialog")
            return modal

        def roll_count(page):
            return page.evaluate("window.__pdfActionRolls.length")

        def expect_roll(page, before, expected, label):
            page.wait_for_function("count => window.__pdfActionRolls.length > count", arg=before)
            result = page.evaluate("window.__pdfActionRolls.at(-1)")
            assert result["roll"]["result"]["value"]["value"] == expected, result
            assert result["roll"]["label"] == label, result
            assert "@value" not in result["roll"]["expression"], result
            expect(page.locator(f"[data-message-id='{result['id']}'] .dice-result")).to_have_count(1)
            return result

        gm = player = None
        try:
            gm = client("gm")
            sheet = open_sheet(gm)
            expect(field(sheet, "Vitality")).to_have_value("10")
            expect(field(sheet, "Hero name")).to_have_value("Aster")
            modal = action_dialog(gm, field(sheet, "Vitality"))
            records.append({"case": "gm-double-click-opens-native-field-action-modal"})
            expect(modal.locator("[data-pdf-action-roll]")).to_be_hidden()
            modal.locator("[data-pdf-action-bar]").select_option("bar1Value")
            modal.locator("[data-pdf-action-formula]").fill("1d1 + @value")
            modal.locator("[data-pdf-action-label]").fill("Vitality check")
            modal.locator("[data-pdf-action-save]").click()
            expect(modal).to_have_count(0)
            expect(field(sheet, "Vitality")).to_have_value("10")
            close_sheet(sheet)
            saved = read(gm)
            vitality = seed["manualFields"][0]
            vitality_key = "manual_" + vitality["id"].replace("-", "")
            name_key = "manual_" + seed["manualFields"][1]["id"].replace("-", "")
            actions = saved["data"]["pdf"]["fieldActions"]
            assert actions == [{"source": "asset:" + seed["pdfAssets"][0], "field": vitality_key,
                                "roll": {"formula": "1d1 + @value", "label": "Vitality check"}}], actions
            assert saved["data"]["token"]["bars"]["bar1Value"] == vitality_key
            assert saved["data"]["bars"]["bar_1"]["value"] == 10
            assert saved["data"]["pdf"]["manualFields"] == seed["manualFields"]
            records.append({"case": "gm-saves-source-bound-roll-and-token-bar-with-existing-value"})

            sheet = open_sheet(gm)
            expect(field(sheet, "Vitality")).to_have_value("10")
            modal = action_dialog(gm, field(sheet, "Vitality"))
            expect(modal.locator("[data-pdf-action-formula]")).to_have_value("1d1 + @value")
            expect(modal.locator("[data-pdf-action-bar]")).to_have_value("bar1Value")
            expect(modal.locator("[data-pdf-action-label]")).to_have_value("Vitality check")
            modal.locator("[data-pdf-action-bar]").select_option("")
            modal.locator("[data-pdf-action-save]").click()
            expect(modal).to_have_count(0)
            expect(field(sheet, "Vitality")).to_have_value("10")
            assert read(gm)["data"]["fields"][vitality_key] == 10
            modal = action_dialog(gm, field(sheet, "Vitality"))
            expect(modal.locator("[data-pdf-action-bar]")).to_have_value("")
            modal.locator("[data-pdf-action-bar]").select_option("bar1Value")
            modal.locator("[data-pdf-action-save]").click()
            expect(modal).to_have_count(0)
            expect(field(sheet, "Vitality")).to_have_value("10")
            records.append({"case": "binding-and-unbinding-token-bar-preserve-manual-field-value"})
            modal = action_dialog(gm, field(sheet, "Vitality"))
            before = roll_count(gm)
            modal.locator("[data-pdf-action-formula]").fill("1d1 + 200")
            modal.locator("[data-pdf-action-roll]").click()
            expect_roll(gm, before, 11, "Vitality check")
            expect(modal).to_be_visible()
            modal.locator("[data-pdf-action-cancel]").click()
            expect(modal).to_have_count(0)
            assert read(gm)["data"]["pdf"]["fieldActions"] == actions
            records.append({"case": "gm-runs-saved-native-dice-action-without-applying-modal-draft"})

            modal = action_dialog(gm, field(sheet, "Vitality"))
            gm.evaluate("""() => {
              const realtime = window.gravewrightRealtime;
              window.__pdfActionNativeRoll = realtime.roll;
              realtime.roll = function(...args) {
                return new Promise((resolve,reject) => {
                  window.__pdfActionReleaseRoll = () => {
                    window.__pdfActionNativeRoll.apply(realtime,args).then(resolve,reject);
                  };
                });
              };
            }""")
            before = roll_count(gm)
            modal.locator("[data-pdf-action-roll]").click()
            gm.wait_for_function("typeof window.__pdfActionReleaseRoll === 'function'")
            expect(modal.locator("[data-pdf-action-close]")).to_be_enabled()
            expect(modal.locator("[data-pdf-action-cancel]")).to_be_enabled()
            gm.keyboard.press("Escape")
            expect(modal).to_have_count(0)
            expect(sheet).to_be_visible()
            gm.evaluate("""() => {
              window.gravewrightRealtime.roll = window.__pdfActionNativeRoll;
              window.__pdfActionReleaseRoll();
            }""")
            expect_roll(gm, before, 11, "Vitality check")
            expect(modal).to_have_count(0)
            expect(sheet.locator(".pdf-sheet__error")).to_be_hidden()
            records.append({"case": "escape-closes-pending-roll-modal-and-late-native-result-reaches-chat-once"})

            modal = action_dialog(gm, field(sheet, "Vitality"))
            presets = {
                "d20": "1d20+@value", "highest": "2d20kh1+@value",
                "lowest": "2d20kl1+@value", "2d6": "2d6+@value",
                "exploding": "1d6!", "fudge": "4dF+@value",
            }
            for preset, formula in presets.items():
                modal.locator(f"[data-pdf-action-preset='{preset}']").click()
                assert modal.locator("[data-pdf-action-formula]").input_value().replace(" ", "") == formula
            gm.keyboard.press("Escape")
            expect(modal).to_have_count(0)
            expect(sheet).to_be_visible()
            expect(field(sheet, "Vitality")).to_be_focused()
            assert read(gm)["data"]["pdf"]["fieldActions"] == actions
            records.append({"case": "six-presets-fill-draft-and-escape-restores-focus-without-saving"})

            field(sheet, "Vitality").press("F2")
            modal = gm.locator("[data-pdf-field-actions]")
            expect(modal).to_be_visible()
            expect(modal.locator("[data-pdf-action-formula]")).to_have_value("1d1 + @value")
            modal.locator("[data-pdf-action-close]").click()
            expect(modal).to_have_count(0)
            records.append({"case": "keyboard-f2-opens-field-configuration-and-close-preserves-draft"})

            modal = action_dialog(gm, field(sheet, "Vitality"))
            modal.locator("[data-pdf-action-formula]").fill("1d6 + @missing")
            modal.locator("[data-pdf-action-save]").click()
            expect(modal.locator("[data-pdf-action-error]")).to_be_visible()
            expect(modal).to_be_visible()
            assert read(gm)["data"]["pdf"]["fieldActions"] == actions
            modal.locator("[data-pdf-action-cancel]").click()
            field(sheet, "Hero name").fill("Aster after invalid formula")
            close_sheet(sheet)
            assert read(gm)["data"]["fields"][name_key] == "Aster after invalid formula"
            records.append({"case": "invalid-formula-stays-in-modal-and-does-not-break-field-autosave"})

            sheet = open_sheet(gm)
            sheet.locator("[data-pdf=toggleMapping]").click()
            expect(sheet.locator("[data-pdf-mapping-tools]")).to_be_visible()
            modal = action_dialog(gm, sheet.locator(f"[data-pdf-map-field='{vitality['id']}']"))
            expect(modal.locator("[data-pdf-action-formula]")).to_have_value("1d1 + @value")
            modal.locator("[data-pdf-action-cancel]").click()
            sheet.locator("[data-pdf=toggleMapping]").click()
            close_sheet(sheet)
            assert read(gm)["data"]["pdf"]["manualFields"] == seed["manualFields"]
            records.append({"case": "double-click-mapping-box-configures-without-moving-or-resizing-layout"})

            sheet = open_sheet(gm)
            source(sheet, "Synthetic fillable.pdf")
            expect(field(sheet, "HP")).to_have_value("10")
            modal = action_dialog(gm, field(sheet, "HP"))
            modal.locator("[data-pdf-action-bar]").select_option("bar2Value")
            modal.locator("[data-pdf-action-formula]").fill("1d1 + @value")
            modal.locator("[data-pdf-action-label]").fill("Native HP check")
            modal.locator("[data-pdf-action-save]").click()
            expect(modal).to_have_count(0)
            expect(field(sheet, "HP")).to_have_value("10")
            field(sheet, "HP").fill("7")
            source(sheet, "Synthetic alternate.pdf")
            expect(sheet.locator("[data-pdf-roll-field]")).to_have_count(0)
            source(sheet, "Synthetic character.pdf")
            expect(field(sheet, "Vitality")).to_have_value("10")
            close_sheet(sheet)
            saved = read(gm)
            actions = saved["data"]["pdf"]["fieldActions"]
            assert len(actions) == 2 and {action["source"] for action in actions} == {
                "asset:" + seed["pdfAssets"][0], "asset:" + seed["pdfAssets"][2]}, actions
            assert saved["data"]["bars"]["bar_2"]["value"] == 7
            records.append({"case": "native-acroform-field-action-and-bar-mapping-stay-source-bound"})

            player = client("player")
            player_sheet = open_sheet(player)
            expect(field(player_sheet, "Vitality")).to_have_value("10")
            expect(player_sheet.locator("[data-pdf=toggleMapping]")).to_be_hidden()
            # The accessible button and double-click both submit to the native
            # dice service; each gesture produces exactly one real chat entry.
            before = roll_count(player)
            player_sheet.locator(f"[data-pdf-roll-field='{vitality_key}']").click()
            first_roll = expect_roll(player, before, 11, "Vitality check")
            player.wait_for_function("count => window.__pdfActionRolls.length === count", arg=before + 1)
            field(player_sheet, "Vitality").fill("14")
            before = roll_count(player)
            field(player_sheet, "Vitality").dblclick()
            second_roll = expect_roll(player, before, 15, "Vitality check")
            assert first_roll["id"] != second_roll["id"]
            expect(player.locator("[data-pdf-field-actions]")).to_have_count(0)
            close_sheet(player_sheet)
            assert read(player)["data"]["bars"]["bar_1"]["value"] == 14
            records.append({"case": "controlled-player-button-and-double-click-roll-current-value-into-native-chat"})

            forged = player.evaluate("""async ({url,actor}) => {
              const current = await (await fetch(url)).json();
              current.data.pdf.fieldActions[0].roll.formula = '1d1 + 500';
              try {
                await window.gravewrightRealtime.resourceCommand('actors','sheet.save',{
                  actorId:actor,name:current.name,data:current.data,
                  version:current.version,sheetVersion:current.sheetVersion});
                return {accepted:true};
              } catch(error) { return {accepted:false,code:error.code,message:error.message}; }
            }""", {"url": actor_url, "actor": seed["actor"]})
            assert forged["accepted"] is False and forged["code"] == "forbidden", forged
            assert read(gm)["data"]["pdf"]["fieldActions"] == actions
            records.append({"case": "server-rejects-controlled-player-forged-action-configuration"})

            duplicated = gm.evaluate("""args => window.gravewrightRealtime.resourceCommand('tokens','duplicate',{
              mapId:args.scene,tokenIds:[args.token]})""",
              {"scene": seed["selectedScene"], "token": seed["token"]})
            snapshot_id = duplicated["createdIds"][0]
            snapshot = next(token for token in duplicated["tokens"] if token["id"] == snapshot_id)
            snapshot_sheet = open_sheet(player, snapshot)
            expect(field(snapshot_sheet, "Vitality")).to_have_value("14")
            field(snapshot_sheet, "Vitality").fill("22")
            before = roll_count(player)
            field(snapshot_sheet, "Vitality").dblclick()
            expect_roll(player, before, 23, "Vitality check")
            close_sheet(snapshot_sheet)
            snapshot_data = read(player, snapshot_id)["data"]
            assert snapshot_data["bars"]["bar_1"]["value"] == 22
            assert read(player)["data"]["bars"]["bar_1"]["value"] == 14
            assert snapshot_data["pdf"]["fieldActions"] == actions
            records.append({"case": "snapshot-token-copies-action-and-rolls-its-own-independent-value"})

            sheet = open_sheet(gm)
            source(sheet, "Synthetic fillable.pdf")
            modal = action_dialog(gm, field(sheet, "HP"))
            modal.locator("[data-pdf-action-formula]").fill("1d1 + 500")
            # Simulate a source refresh racing the open modal. Browser input is
            # correctly inert behind it, so invoke the actual existing picker
            # handlers rather than bypassing controller or server validation.
            sheet.locator("[data-pdf=togglePicker]").evaluate("button => button.click()")
            sheet.locator("[data-pdf-sources]").get_by_role("button", name="Other HP sheet.pdf", exact=True).evaluate(
                "button => button.click()")
            gm.wait_for_function("""async args => {
              const current = await (await fetch(args.url, {cache:'no-store'})).json();
              return current.data.pdf.asset === args.asset;
            }""", arg={"url": actor_url, "asset": seed["pdfAssets"][3]}, polling=200)
            expect(field(sheet, "HP")).to_have_value("7")
            before_requests = gm.evaluate("window.__pdfActionRollRequests.length")
            modal.locator("[data-pdf-action-save]").click()
            expect(modal.locator("[data-pdf-action-error]")).to_have_text(
                "This field is no longer available. Reopen the character sheet.")
            modal.locator("[data-pdf-action-roll]").click()
            expect(modal.locator("[data-pdf-action-error]")).to_be_visible()
            assert gm.evaluate("window.__pdfActionRollRequests.length") == before_requests
            assert read(gm)["data"]["pdf"]["fieldActions"] == actions
            modal.locator("[data-pdf-action-cancel]").click()
            source(sheet, "Synthetic character.pdf")
            close_sheet(sheet)
            records.append({"case": "open-modal-rejects-save-and-roll-after-switch-to-same-named-field-in-other-pdf"})

            for locale, title in (("en", "Field actions"), ("pt-BR", "Ações do campo"), ("es", "Acciones del campo")):
                change_locale(gm, locale, campaign)
                gm.set_viewport_size({"width": 390, "height": 844})
                gm.reload()
                gm.wait_for_function("!!window.gravewrightActors && !!window.gravewrightRealtime")
                sheet = open_sheet(gm)
                modal = action_dialog(gm, field(sheet, "Vitality"))
                expect(modal.locator("header strong")).to_have_text(title)
                bar_labels = {"en": "Bar 1 · Current", "pt-BR": "Barra 1 · Atual", "es": "Barra 1 · Actual"}
                expect(modal.locator("[data-pdf-action-bar] option:checked")).to_have_text(bar_labels[locale])
                measurements = modal.evaluate(MEASURE)
                assert not measurements["tiny"], (locale, measurements)
                assert not measurements["overflow"], (locale, measurements)
                modal.screenshot(path=str(output / f"field-actions-{locale}-390.png"))
                gm.keyboard.press("Escape")
                expect(modal).to_have_count(0)
                expect(sheet).to_be_visible()
                close_sheet(sheet)
                records.append({"case": f"localized-field-action-modal-{locale}-390"})
        except Exception:
            (output / "browser-diagnostics.json").write_text(json.dumps({
                "completedCases": records, "pageErrors": errors,
                "nativeDialogs": dialogs, "failedRequests": failed,
            }, indent=2, ensure_ascii=False), encoding="utf-8")
            for name, page in (("gm", gm), ("player", player)):
                if page:
                    page.screenshot(path=str(output / f"failure-{name}.png"), full_page=True)
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    assert not [request for request in failed if request["error"] != "net::ERR_ABORTED"], failed
    return {"passed": True, "cases": records, "pageErrors": errors,
            "nativeDialogs": dialogs, "failedRequests": failed,
            "assets": "Generated flat PDFs with manual fields and a generated native HP widget."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--browser-executable", type=Path)
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--fixture", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(args.fixture, args.port)
        return
    output = (args.output or ROOT / "data/pdf-field-actions" /
              datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")).resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("Use a fresh, empty output directory.")
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / "fixture"
    fixture.mkdir()
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", 0))
        port = connection.getsockname()[1]
    fixture_environment(fixture, port)
    executable = sys._base_executable if os.name == "nt" else sys.executable
    command = [executable, "-B", "-X", "utf8", str(Path(__file__).resolve())]
    base = f"http://127.0.0.1:{port}"
    with (output / "server.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen([*command, "--serve", "--fixture", str(fixture), "--port", str(port)],
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
                raise RuntimeError("Fixture did not become ready.")
            seed = json.loads((fixture / "seed.json").read_text(encoding="utf-8"))
            report = check_browser(base, seed, output, args.browser_executable)
            (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            print(json.dumps({"passed": True, "cases": len(report["cases"]), "report": str(output / "report.json")}))
        except Exception:
            (output / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            (output / "server-exit.json").write_text(json.dumps({"pid": server.pid, "exitCode": server.returncode}), encoding="utf-8")


if __name__ == "__main__":
    main()
