"""Exercise reusable, calculated and exported PDF mappings in a disposable table."""
from __future__ import annotations

import argparse
import base64
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
from pdf_field_actions import ROLL_PROBE, serve as serve_actions


PRIVATE_VALUE = "Synthetic private value that must stay out of mapping JSON."


def repeated_field_pdf():
    """An empty native field with distinct widgets on both pages, owned here."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R /AcroForm 5 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Annots [7 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Annots [8 0 R] >>",
        b"<< /Fields [9 0 R] /DR << /Font << /Helv 6 0 R >> >> /DA (/Helv 20 Tf 0 g) /NeedAppearances true >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Annot /Subtype /Widget /Parent 9 0 R /Rect [30 740 130 770] /P 3 0 R >>",
        b"<< /Type /Annot /Subtype /Widget /Parent 9 0 R /Rect [200 600 380 635] /P 4 0 R >>",
        b"<< /FT /Tx /T (HP) /Kids [7 0 R 8 0 R] /DA (/Helv 20 Tf 0 g) /V () >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    start = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f\r\n".encode())
    for offset in offsets:
        output.extend(f"{offset:010d} 00000 n\r\n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode())
    return bytes(output)


def serve(fixture, port):
    from django.core import management

    original = management.call_command

    def command(name, *args, **kwargs):
        if name == "runserver":
            from django.core.files.base import ContentFile
            from gravewright.actors.models import Actor, Asset
            from gravewright.pdf_system.schema import normalize

            seed_file = fixture / "seed.json"
            seed = json.loads(seed_file.read_text(encoding="utf-8"))
            native = Asset.objects.get(pk=seed["pdfAssets"][2])
            native.file.save("synthetic-repeated-native.pdf", ContentFile(repeated_field_pdf()), save=True)
            actor = Actor.objects.get(pk=seed["actor"])
            fields = actor.data["pdf"]["manualFields"]
            actor.data["fields"]["manual_" + fields[1]["id"].replace("-", "")] = PRIVATE_VALUE
            for label, x, y, value in (("Strength", .1, .18, 5), ("Agility", .32, .21, 3), ("Total", .7, .24, 0)):
                field = {"id": str(uuid4()), "source": "asset:" + seed["pdfAssets"][0],
                         "page": 1, "type": "number", "name": label,
                         "x": x, "y": y, "width": .15, "height": .035}
                fields.append(field)
                actor.data["fields"]["manual_" + field["id"].replace("-", "")] = value
            actor.data = normalize(actor.data)
            actor.save(update_fields=["data"])
            other = Actor.objects.create(
                campaign=actor.campaign, name="Other synthetic character", permissions=actor.permissions,
                data=normalize({"pdf": {"asset": seed["pdfAssets"][1]},
                                "fields": {"operatorText": "Keep this target-only value."},
                                "bars": {"bar_1": {"value": 99, "max": 100}}}),
            )
            seed.update(manualFields=fields, otherActor=str(other.pk))
            seed_file.write_text(json.dumps(seed, indent=2), encoding="utf-8")
        return original(name, *args, **kwargs)

    management.call_command = command
    try:
        serve_actions(fixture, port)
    finally:
        management.call_command = original


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    records, errors, dialogs, failed = [], [], [], []
    campaign = seed["campaign"]
    actor_url = f"/api/containers/{campaign}/actors/{seed['actor']}/sheet"
    definitions = {field["name"]: field for field in seed["manualFields"]}
    key = lambda name: "manual_" + definitions[name]["id"].replace("-", "")
    reference = lambda name: "@{" + key(name) + "}"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({"executable_path": str(executable)} if executable else {}))
        contexts = []

        def client(role):
            context = browser.new_context(base_url=base, viewport={"width": 1440, "height": 1000},
                                          has_touch=role == 'gm')
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
            page.evaluate("args => window.gravewrightActors.open(args.actor,args.token)",
                          {"actor": seed["actor"], "token": token})
            sheet = page.locator(".token-sheet" if token else ".actor-directory__sheet")
            expect(sheet.locator(".pdf-sheet__canvas")).to_have_count(1)
            expect(control(sheet, "Strength")).to_be_visible()
            return sheet

        def close_sheet(sheet):
            sheet.locator("[data-window=close]").click()
            expect(sheet).to_have_count(0)

        def control(sheet, name):
            return sheet.locator(f".pdf-sheet__fields [data-manual-field='{definitions[name]['id']}']")

        def box(sheet, name):
            return sheet.locator(f"[data-pdf-map-field='{definitions[name]['id']}']")

        def read(page, actor=None, token=None):
            url = f"/api/containers/{campaign}/actors/{actor or seed['actor']}/sheet"
            response = page.request.get(url + ("?tokenId=" + token if token else ""))
            assert response.ok, response.text()
            return response.json()

        def wait_value(page, path, value):
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                current = read(page)
                actual = current
                for segment in path:
                    actual = len(actual) if segment == 'length' else actual[segment]
                if actual == value:
                    return current
                time.sleep(.1)
            raise AssertionError((path, actual, value))

        def mapping(sheet, enabled):
            tools = sheet.locator("[data-pdf-mapping-tools]")
            if tools.is_visible() != enabled:
                sheet.locator("[data-pdf=toggleMapping]").click()
            expect(tools).to_be_visible() if enabled else expect(tools).to_be_hidden()

        def configure(page, target):
            target.dblclick()
            modal = page.locator("[data-pdf-field-actions]")
            expect(modal).to_be_visible()
            return modal

        def library(page, sheet):
            sheet.locator("[data-pdf-library-open]").click()
            modal = page.locator("[data-pdf-mapping-library]")
            expect(modal).to_be_visible()
            return modal

        def source(sheet, name):
            sheet.locator('[data-pdf=togglePicker]').click()
            sheet.locator('[data-pdf-sources]').get_by_role('button', name=name, exact=True).click()
            expect(sheet.locator('.pdf-sheet__picker')).to_be_hidden()
            expect(sheet.locator('.pdf-sheet__canvas')).to_have_count(1)

        def finish_library(modal):
            modal.locator("[data-pdf-library-done]").click()
            expect(modal).to_have_count(0)

        def rectangle(sheet, name):
            target = box(sheet, name)
            return target.evaluate("node=>({x:parseFloat(node.style.left),y:parseFloat(node.style.top)})")

        gm = player = None
        try:
            gm = client("gm")
            sheet = open_sheet(gm)
            modal = configure(gm, control(sheet, "Vitality"))
            modal.locator("[data-pdf-action-formula]").fill("1d1 + ")
            modal.locator("[data-pdf-action-reference]").select_option(key("Strength"))
            modal.locator("[data-pdf-action-insert-reference]").click()
            assert reference("Strength") in modal.locator("[data-pdf-action-formula]").input_value()
            modal.locator("[data-pdf-action-formula]").fill("1d1 + " + reference("Strength") + " + " + reference("Agility"))
            modal.locator("[data-pdf-action-label]").fill("Referenced ability check")
            modal.locator("[data-pdf-action-save]").click()
            expect(modal).to_have_count(0)
            modal = configure(gm, control(sheet, "Total"))
            modal.locator("[data-pdf-action-calculation]").fill(reference("Strength") + " + " + reference("Agility"))
            modal.locator("[data-pdf-action-save]").click()
            expect(modal).to_have_count(0)
            expect(control(sheet, "Total")).to_have_value("8")
            expect(control(sheet, "Total")).to_have_js_property("readOnly", True)
            close_sheet(sheet)
            assert read(gm)["data"]["fields"][key("Total")] == 8
            records.append({"case": "field-reference-picker-and-server-calculated-readonly-output"})

            player = client("player")
            player_sheet = open_sheet(player)
            expect(player_sheet.locator("[data-pdf-library-open]")).to_be_hidden()
            expect(control(player_sheet, "Total")).to_have_js_property("readOnly", True)
            control(player_sheet, "Strength").fill("6")
            expect(control(player_sheet, "Total")).to_have_value("9")
            before = player.evaluate("window.__pdfActionRolls.length")
            player_sheet.locator(f"[data-pdf-roll-field='{key('Vitality')}']").click()
            player.wait_for_function("count=>window.__pdfActionRolls.length>count", arg=before)
            rolled = player.evaluate("window.__pdfActionRolls.at(-1)")
            assert rolled["roll"]["result"]["value"]["value"] == 10, rolled
            close_sheet(player_sheet)
            assert read(player)["data"]["fields"][key("Total")] == 9
            records.append({"case": "player-input-recomputes-output-and-native-roll-resolves-other-fields"})

            sheet = open_sheet(gm)
            mapping(sheet, True)
            box(sheet, "Strength").click()
            box(sheet, "Agility").click(modifiers=["Shift"])
            box(sheet, "Total").click(modifiers=["Control"])
            expect(sheet.locator("[data-pdf-map-field][aria-pressed=true]")).to_have_count(3)
            original = {name: rectangle(sheet, name) for name in ("Strength", "Agility", "Total")}
            sheet.locator("[data-pdf-layout-align]").select_option("left")
            aligned = [rectangle(sheet, name)["x"] for name in original]
            assert max(aligned) - min(aligned) < 1, aligned
            box(sheet, "Strength").focus()
            gm.keyboard.press("Control+z")
            for name, prior in original.items():
                assert abs(rectangle(sheet, name)["x"] - prior["x"]) < 1
            canvas = sheet.locator(".pdf-sheet__canvas").bounding_box()
            bounds = box(sheet, "Strength").bounding_box()
            gm.mouse.move(bounds["x"] + bounds["width"] / 2, bounds["y"] + bounds["height"] / 2)
            gm.mouse.down()
            gm.mouse.move(bounds["x"] + bounds["width"] / 2 + .03 * canvas["width"],
                          bounds["y"] + bounds["height"] / 2 + .02 * canvas["height"], steps=5)
            gm.mouse.up()
            for name, prior in original.items():
                assert abs(rectangle(sheet, name)["x"] - prior["x"] - .03 * canvas["width"]) < 2
                assert abs(rectangle(sheet, name)["y"] - prior["y"] - .02 * canvas["height"]) < 2
            box(sheet, "Strength").focus()
            gm.keyboard.press("Control+z")
            for name, prior in original.items():
                assert abs(rectangle(sheet, name)["x"] - prior["x"]) < 1
            gm.keyboard.press("Control+Shift+z")
            sheet.locator("[data-pdf-layout-distribute]").select_option("horizontal")
            positions = [rectangle(sheet, name)["x"] for name in original]
            assert abs((positions[1] - positions[0]) - (positions[2] - positions[1])) < 2
            records.append({"case": "multi-selection-align-group-move-distribute-and-one-gesture-undo-redo"})

            box(sheet, "Strength").focus()
            gm.keyboard.press("Control+d")
            expect(sheet.locator("[data-pdf-map-field]")).to_have_count(8)
            expect(sheet.locator("[data-pdf-map-field][aria-pressed=true]")).to_have_count(3)
            mapping(sheet, False)
            copied = wait_value(gm, ["data", "pdf", "manualFields", "length"], 8)["data"]
            (output / 'copied-layout.json').write_text(json.dumps(copied, indent=2), encoding='utf-8')
            duplicate_ids = {field["name"]: field["id"] for field in copied["pdf"]["manualFields"]
                             if field["id"] not in {row["id"] for row in seed["manualFields"]}}
            duplicate_total_key = "manual_" + duplicate_ids["Total"].replace("-", "")
            duplicate_strength_key = "manual_" + duplicate_ids["Strength"].replace("-", "")
            duplicate_calc = next(row for row in copied["pdf"]["calculatedFields"] if row["field"] == duplicate_total_key)
            assert "@{" + duplicate_strength_key + "}" in duplicate_calc["formula"]
            assert copied["fields"][duplicate_total_key] == 9
            player_sheet = open_sheet(player)
            control(player_sheet, "Strength").fill("13")
            close_sheet(player_sheet)
            sheet.locator("[data-tab=token]").click()
            sheet.locator("[data-tab=ficha]").click()
            expect(control(sheet, "Strength")).to_have_value("13")
            expect(control(sheet, "Total")).to_have_value("16")
            mapping(sheet, True)
            sheet.locator("[data-pdf-layout-action=undo]").click()
            expect(sheet.locator("[data-pdf-map-field]")).to_have_count(5)
            mapping(sheet, False)
            expect(control(sheet, "Strength")).to_have_value("13")
            expect(control(sheet, "Total")).to_have_value("16")
            records.append({"case": "duplicate-remaps-calculation-references-and-undo-preserves-later-player-values"})

            mapping(sheet, True)
            sheet.locator('[data-pdf-map-tool]').select_option('select')
            canvas = sheet.locator('.pdf-sheet__canvas').bounding_box()
            gm.mouse.move(canvas['x'] + .08 * canvas['width'], canvas['y'] + .17 * canvas['height'])
            gm.mouse.down()
            gm.mouse.move(canvas['x'] + .92 * canvas['width'], canvas['y'] + .31 * canvas['height'], steps=4)
            gm.mouse.up()
            expect(sheet.locator('[data-pdf-map-field][aria-pressed=true]')).to_have_count(3)
            box(sheet, 'Agility').click(modifiers=['Shift'])
            box(sheet, 'Total').click(modifiers=['Control'])
            expect(sheet.locator('[data-pdf-map-field][aria-pressed=true]')).to_have_count(1)
            box(sheet, 'Strength').focus()
            gm.keyboard.press('Control+c')
            gm.keyboard.press('Control+v')
            expect(sheet.locator('[data-pdf-map-field]')).to_have_count(6)
            gm.keyboard.press('Control+z')
            expect(sheet.locator('[data-pdf-map-field]')).to_have_count(5)
            records.append({'case': 'marquee-modifier-toggle-and-keyboard-copy-paste-undo'})

            mapping(sheet, True)
            sheet.locator("[data-pdf-layout-snap]").check()
            sheet.locator("[data-pdf-map-tool]").select_option("text")
            sheet.locator('.pdf-sheet__stage').evaluate('stage=>{stage.scrollTop=0;stage.scrollLeft=0;}')
            canvas = sheet.locator(".pdf-sheet__canvas").bounding_box()
            gm.mouse.move(canvas["x"] + .853 * canvas["width"], canvas["y"] + .135 * canvas["height"])
            gm.mouse.down()
            gm.mouse.move(canvas["x"] + .958 * canvas["width"], canvas["y"] + .165 * canvas["height"], steps=4)
            gm.mouse.up()
            expect(sheet.locator("[data-pdf-map-field]")).to_have_count(6)
            x_percent = float(sheet.locator("[data-pdf-map-property=x]").input_value())
            assert abs((x_percent / 100 * 595) / 5 - round((x_percent / 100 * 595) / 5)) < .01
            snapped_box = sheet.locator('[data-pdf-map-field][aria-pressed=true]')
            prior_left = snapped_box.evaluate('node=>parseFloat(node.style.left)')
            snapped_box.press('ArrowRight')
            moved_left = snapped_box.evaluate('node=>parseFloat(node.style.left)')
            assert abs(moved_left - prior_left - 5 * canvas['width'] / 595) < 1
            snapped_box.press('Control+z')
            sheet.locator("[data-pdf-layout-action=undo]").click()
            expect(sheet.locator("[data-pdf-map-field]")).to_have_count(5)
            mapping(sheet, False)
            records.append({"case": "page-local-grid-snapping-and-undo-of-new-field"})

            modal = library(gm, sheet)
            modal.locator("[data-pdf-library-name]").fill("Reusable synthetic mapping")
            modal.locator("[data-pdf-library-create]").click()
            expect(modal.locator("[data-pdf-library-list] option")).to_have_count(1)
            with gm.expect_download() as downloaded:
                modal.locator("[data-pdf-library-export-current]").click()
            bundle_path = output / "mapping.json"
            downloaded.value.save_as(bundle_path)
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            assert PRIVATE_VALUE not in json.dumps(bundle)
            assert "Keep this target-only value." not in json.dumps(bundle)
            finish_library(modal)
            modal = library(gm, sheet)
            expect(modal.locator("[data-pdf-library-list] option")).to_have_count(1)
            modal.locator("[data-pdf-library-name]").fill("Imported synthetic mapping")
            modal.locator("[data-pdf-library-file]").set_input_files(bundle_path)
            expect(modal.locator("[data-pdf-library-list] option")).to_have_count(2)
            records.append({"case": "campaign-library-reopens-and-json-export-import-omits-character-values"})

            modal.locator("[data-pdf-library-list]").select_option(label="Reusable synthetic mapping")
            modal.locator("[data-pdf-library-apply]").click()
            expect(modal.locator("[data-pdf-library-status]")).to_be_visible()
            modal.locator("details summary").click()
            target = modal.locator(f"[data-pdf-library-target][value='{seed['otherActor']}']")
            target.check()
            modal.locator("[data-pdf-library-apply-many]").click()
            expect(modal.locator("[data-pdf-library-status]")).to_be_visible()
            other = read(gm, actor=seed["otherActor"])
            assert other["name"] == "Other synthetic character"
            assert other["data"]["pdf"]["asset"] == seed["pdfAssets"][1]
            assert other["data"]["fields"]["operatorText"] == "Keep this target-only value."
            assert len(other["data"]["pdf"]["manualFields"]) == 5
            assert PRIVATE_VALUE not in json.dumps(other["data"])
            finish_library(modal)
            expect(control(sheet, "Strength")).to_have_value("13")
            records.append({"case": "apply-current-and-bulk-mapping-preserve-other-character-pdf-name-and-values"})

            close_sheet(sheet)
            actor_before_snapshot = read(gm)["data"]
            duplicated = gm.evaluate("""args=>window.gravewrightRealtime.resourceCommand('tokens','duplicate',{
              mapId:args.scene,tokenIds:[args.token]})""",
              {"scene": seed["selectedScene"], "token": seed["token"]})
            snapshot_id = duplicated["createdIds"][0]
            snapshot = next(token for token in duplicated["tokens"] if token["id"] == snapshot_id)
            snapshot_sheet = open_sheet(gm, snapshot)
            mapping(snapshot_sheet, True)
            box(snapshot_sheet, "Strength").click()
            box(snapshot_sheet, "Strength").press("Shift+ArrowRight")
            mapping(snapshot_sheet, False)
            modal = library(gm, snapshot_sheet)
            modal.locator("[data-pdf-library-list]").select_option(label="Reusable synthetic mapping")
            modal.locator("[data-pdf-library-apply]").click()
            expect(modal.locator("[data-pdf-library-status]")).to_be_visible()
            finish_library(modal)
            close_sheet(snapshot_sheet)
            snapshot_data = read(gm, token=snapshot_id)["data"]
            assert read(gm)["data"] == actor_before_snapshot
            assert snapshot_data["fields"][key("Strength")] == 13
            assert snapshot_data["pdf"]["manualFields"] == actor_before_snapshot["pdf"]["manualFields"]
            sheet = open_sheet(gm)
            records.append({"case": "applying-library-mapping-to-snapshot-preserves-source-actor-and-current-values"})

            original_pdf = gm.request.get("/game/actors/asset/" + seed["pdfAssets"][0]).body()
            with gm.expect_download(timeout=60000) as downloaded:
                sheet.locator("[data-pdf=downloadFilled]").click()
            filled_path = output / "filled-sheet.pdf"
            downloaded.value.save_as(filled_path)
            assert filled_path.read_bytes().startswith(b"%PDF-")
            assert gm.request.get("/game/actors/asset/" + seed["pdfAssets"][0]).body() == original_pdf
            gm.route("**/__pdf-workbench-filled.pdf", lambda route: route.fulfill(
                body=filled_path.read_bytes(), content_type="application/pdf"))
            exported = gm.evaluate("""async () => {
              const lib=await import('/static/gravewright_journals/vendor/pdf.mjs');
              lib.GlobalWorkerOptions.workerSrc='/static/gravewright_journals/vendor/pdf.worker.mjs';
              const task=lib.getDocument({url:'/__pdf-workbench-filled.pdf',isEvalSupported:false}),doc=await task.promise;
              let widgets=0;for(let n=1;n<=doc.numPages;n++)widgets+=(await(await doc.getPage(n)).getAnnotations()).filter(a=>a.subtype==='Widget').length;
              const page=await doc.getPage(1),viewport=page.getViewport({scale:.75}),canvas=document.createElement('canvas');
              canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
              await page.render({canvas,viewport}).promise;
              const image=canvas.toDataURL('image/png');const result={pages:doc.numPages,widgets,image};await task.destroy();return result;
            }""")
            assert exported["pages"] == 2 and exported["widgets"] == 0, {key: value for key, value in exported.items() if key != "image"}
            (output / "filled-sheet-preview.png").write_bytes(base64.b64decode(exported["image"].split(",", 1)[1]))
            records.append({"case": "filled-export-renders-all-pages-as-flat-pdf-and-preserves-original-file"})

            original_native = gm.request.get('/game/actors/asset/' + seed['pdfAssets'][2]).body()
            source(sheet, 'Synthetic fillable.pdf')
            native_value = sheet.locator('.pdf-sheet__fields').get_by_label('HP', exact=True)
            expect(native_value).to_be_visible()
            native_value.fill('77')
            with gm.expect_download(timeout=60000) as downloaded:
                sheet.locator('[data-pdf=downloadFilled]').click()
            native_path = output / 'filled-native-repeated.pdf'
            downloaded.value.save_as(native_path)
            assert gm.request.get('/game/actors/asset/' + seed['pdfAssets'][2]).body() == original_native
            gm.route('**/__pdf-workbench-native.pdf', lambda route: route.fulfill(
                body=native_path.read_bytes(), content_type='application/pdf'))
            gm.route('**/__pdf-workbench-native-original.pdf', lambda route: route.fulfill(
                body=original_native, content_type='application/pdf'))
            native_export = gm.evaluate("""async () => {
              const lib=await import('/static/gravewright_journals/vendor/pdf.mjs');
              const task=lib.getDocument({url:'/__pdf-workbench-native.pdf',isEvalSupported:false}),doc=await task.promise;
              const originalTask=lib.getDocument({url:'/__pdf-workbench-native-original.pdf',isEvalSupported:false}),original=await originalTask.promise;
              const result={pages:doc.numPages,widgets:0,dark:[],baseline:[],images:[]};
              const rects=[[30,72,100,30],[200,207,180,35]];
              for(let n=1;n<=doc.numPages;n++) {
                const page=await doc.getPage(n),viewport=page.getViewport({scale:2}),canvas=document.createElement('canvas');
                canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
                result.widgets+=(await page.getAnnotations()).filter(a=>a.subtype==='Widget').length;
                for (const [target,counts] of [[await original.getPage(n),result.baseline],[page,result.dark]]) {
                  await target.render({canvas,viewport}).promise;
                  const pixels=canvas.getContext('2d').getImageData(...rects[n-1].map(value=>value*2)).data;
                  let dark=0;for(let i=0;i<pixels.length;i+=4)if(pixels[i]<100&&pixels[i+1]<100&&pixels[i+2]<100)dark++;
                  counts.push(dark);
                }
                result.images.push(canvas.toDataURL('image/png'));
              }
              await originalTask.destroy();await task.destroy();return result;
            }""")
            for page_number, image in enumerate(native_export['images'], 1):
                (output / f'filled-native-page-{page_number}.png').write_bytes(base64.b64decode(image.split(',', 1)[1]))
            assert native_export['pages'] == 2 and native_export['widgets'] == 0
            assert all(count > baseline + 20 for count, baseline in zip(native_export['dark'], native_export['baseline'])), (
                native_export['dark'], native_export['baseline'])
            source(sheet, 'Synthetic character.pdf')
            expect(control(sheet, 'Strength')).to_have_value('13')
            records.append({'case': 'filled-native-export-paints-repeated-field-on-both-pages-and-preserves-original',
                            'darkPixelsPerNativeWidget': native_export['dark'], 'emptyOriginalPixels': native_export['baseline']})

            modal = configure(gm, control(sheet, "Total"))
            modal.locator("[data-pdf-action-calculation]").fill(reference("Strength") + " / " + reference("Agility"))
            modal.locator("[data-pdf-action-save]").click()
            expect(modal).to_have_count(0)
            control(sheet, "Agility").fill("0")
            sheet.locator("[data-pdf-diagnostics-open]").click()
            diagnostic = gm.locator("[data-pdf-diagnostics]")
            expect(diagnostic).to_be_visible()
            expect(diagnostic).to_contain_text("Total")
            measurements = diagnostic.evaluate(MEASURE)
            assert not measurements['tiny'] and not measurements['overflow'], measurements
            diagnostic.screenshot(path=str(output / "diagnostics-en.png"))
            gm.keyboard.press("Escape")
            expect(diagnostic).to_have_count(0)
            control(sheet, "Agility").fill("3")
            close_sheet(sheet)
            records.append({"case": "diagnostics-reports-calculation-runtime-failure-without-poisoning-saves"})

            for locale in ("en", "pt-BR", "es"):
                change_locale(gm, locale, campaign)
                gm.set_viewport_size({"width": 390, "height": 844})
                gm.reload()
                gm.wait_for_function("!!window.gravewrightActors && !!window.gravewrightRealtime")
                sheet = open_sheet(gm)
                mapping(sheet, True)
                disclosure = sheet.locator('[data-pdf-layout-disclosure]')
                expect(disclosure).to_have_js_property('open', False)
                summary = disclosure.locator('summary')
                summary.focus()
                summary.press('Enter')
                expect(disclosure).to_have_js_property('open', True)
                expect(sheet.locator('[data-pdf-layout-action=copy]')).to_be_visible()
                measurements = sheet.locator('[data-pdf-mapping-tools]').evaluate(MEASURE)
                assert not measurements['tiny'] and not measurements['overflow'], (locale, measurements)
                sheet.screenshot(path=str(output / f'layout-tools-expanded-{locale}-390.png'))
                summary.tap()
                expect(disclosure).to_have_js_property('open', False)
                copy_label = "Copy fields" if locale == "en" else "Copiar campos"
                expect(sheet.locator("[data-pdf-layout-action=copy]")).to_have_text(copy_label)
                measurements = sheet.locator("[data-pdf-mapping-tools]").evaluate(MEASURE)
                assert not measurements["tiny"] and not measurements["overflow"], (locale, measurements)
                sheet.screenshot(path=str(output / f"layout-tools-{locale}-390.png"))
                mapping(sheet, False)
                modal = library(gm, sheet)
                library_titles = {"en": "PDF mapping library", "pt-BR": "Biblioteca de mapeamentos de PDF",
                                  "es": "Biblioteca de mapeos de PDF"}
                expect(modal.locator("header strong")).to_have_text(library_titles[locale])
                measurements = modal.evaluate(MEASURE)
                assert not measurements["tiny"] and not measurements["overflow"], (locale, measurements)
                modal.screenshot(path=str(output / f"mapping-library-{locale}-390.png"))
                finish_library(modal)
                close_sheet(sheet)
                records.append({"case": f"localized-responsive-layout-and-library-{locale}-390"})
        except Exception:
            (output / "browser-diagnostics.json").write_text(json.dumps({
                "completedCases": records, "pageErrors": errors, "nativeDialogs": dialogs, "failedRequests": failed,
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
            "assets": "Generated synthetic flat and fillable PDFs; disposable characters, values and mapping templates."}


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
    output = (args.output or ROOT / "data/pdf-workbench" /
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
