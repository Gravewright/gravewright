"""Exercise manually mapped, synthetic PDF sheets with disposable campaign data.

The real PDF renderer, actor sheet, permissions and realtime persistence run in
Chromium. Both blank PDFs are generated here; no licensed sheet or operator data
is reused. The shared fixture activates the host's Translator catalogs.
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

from map_builder import ROOT, MEASURE, change_locale, fixture_environment, serve as serve_builder

# Mapping boxes are page annotations: their ellipsized labels deliberately sit
# above the authored rectangle. Keep viewport/font checks on those labels while
# applying the ordinary button-content-width check only to interface buttons.
PDF_MEASURE = MEASURE.replace("el.matches('button')", "el.matches('button:not([data-pdf-map-field])')")


def flat_pdf(title="Synthetic blank character"):
    """Create a two-page, noninteractive PDF containing only authored artwork."""
    streams = []
    for page in (1, 2):
        content = (
            "0.94 0.96 0.98 rg 0 0 595 842 re f\n"
            "0.1 0.18 0.26 rg BT /Helv 20 Tf 30 800 Td "
            f"({title} - page {page}) Tj ET\n"
            "0.4 0.5 0.6 RG 1 w 30 500 535 260 re S\n"
            "0.1 0.18 0.26 rg BT /Helv 12 Tf 30 475 Td "
            "(Synthetic artwork; no native PDF form fields.) Tj ET\n"
        ).encode("ascii")
        streams.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"endstream")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /Helv 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /Helv 5 0 R >> >> /Contents 7 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        *streams,
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    start = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode())
    return bytes(output)


def fillable_pdf():
    """One native HP widget is enough to check coexistence with manual fields."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R /AcroForm 5 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Annots [7 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] >>",
        b"<< /Fields [7 0 R] /DR << /Font << /Helv 6 0 R >> >> /DA (/Helv 12 Tf 0 g) /NeedAppearances true >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Annot /Subtype /Widget /FT /Tx /T (HP) /Rect [30 740 130 770] /P 3 0 R /DA (/Helv 12 Tf 0 g) >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    start = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode())
    return bytes(output)


def serve(fixture, port):
    """Add owned PDF actors to the common, installation-local browser fixture."""
    from django.core import management

    original = management.call_command

    def command(name, *args, **kwargs):
        if name == "runserver":
            from django.core.files.base import ContentFile
            from gravewright.actors.models import Actor, Asset
            from gravewright.campaigns.models import Campaign
            from gravewright.pdf_system.schema import normalize
            from gravewright.tokens.models import Token

            seed_file = fixture / "seed.json"
            seed = json.loads(seed_file.read_text(encoding="utf-8"))
            campaign = Campaign.objects.get(pk=seed["campaign"])
            campaign.system = "gravewright-pdf-system"
            campaign.save(update_fields=["system"])
            player = campaign.memberships.get(role="player").user_id
            assets = []
            for index, title in enumerate(("Synthetic character", "Synthetic alternate"), 1):
                asset = Asset(campaign=campaign, kind="pdf", name=title + ".pdf")
                asset.file.save(f"synthetic-flat-{index}.pdf", ContentFile(flat_pdf(title)), save=True)
                assets.append(str(asset.pk))
            native = Asset(campaign=campaign, kind="pdf", name="Synthetic fillable.pdf")
            native.file.save("synthetic-fillable.pdf", ContentFile(fillable_pdf()), save=True)
            assets.append(str(native.pk))
            data = normalize({"pdf": {"asset": assets[0]}})
            actor = Actor.objects.create(
                campaign=campaign, name="Synthetic mapped hero", data=data,
                permissions={str(player): "owner"},
            )
            token = Token.objects.create(
                scene_id=seed["selectedScene"], actor=actor, grid_x=1, grid_y=1,
            )
            seed.update(actor=str(actor.pk), token=str(token.pk), pdfAssets=assets)
            seed_file.write_text(json.dumps(seed, indent=2), encoding="utf-8")
        return original(name, *args, **kwargs)

    management.call_command = command
    try:
        serve_builder(fixture, port)
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
            context.add_cookies([{**seed["sessions"][role], "url": base}])
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("requestfailed", lambda request: failed.append({"url": request.url, "error": request.failure}))

            def native_dialog(dialog):
                dialogs.append({"type": dialog.type, "message": dialog.message})
                dialog.dismiss()

            page.on("dialog", native_dialog)
            page.goto(f"{base}/game/{campaign}")
            page.wait_for_function("!!window.gravewrightActors && !!window.gravewrightRealtime")
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

        def mapping(sheet, enabled):
            tools = sheet.locator("[data-pdf-mapping-tools]")
            if tools.is_visible() != enabled:
                sheet.locator("[data-pdf=toggleMapping]").click()
            if enabled:
                expect(tools).to_be_visible()
            else:
                expect(tools).to_be_hidden()

        def draw(page, sheet, kind, name, rect, page_number=1):
            mapping(sheet, True)
            sheet.locator("[data-pdf-map-tool]").select_option(kind)
            canvas = sheet.locator(f".pdf-sheet__canvas[data-pdf-page='{page_number}']")
            bounds = canvas.bounding_box()
            assert bounds, "The rendered page must have a client rectangle."
            x, y, width, height = rect
            page.mouse.move(bounds["x"] + x * bounds["width"], bounds["y"] + y * bounds["height"])
            page.mouse.down()
            page.mouse.move(bounds["x"] + (x + width) * bounds["width"],
                            bounds["y"] + (y + height) * bounds["height"], steps=5)
            page.mouse.up()
            properties = sheet.locator("[data-pdf-map-properties]")
            expect(properties).to_be_visible()
            properties.locator("[data-pdf-map-name]").fill(name)
            properties.locator("[data-pdf-map-name]").press("Tab")
            expect(sheet.locator("[data-pdf-map-error]")).to_be_hidden()

        def value(sheet, name):
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

        def assert_positions(sheet, definitions, page_number=1):
            for field in definitions:
                if field["page"] == page_number:
                    expect(value(sheet, field["name"])).to_be_visible()
            canvas = sheet.locator(f".pdf-sheet__canvas[data-pdf-page='{page_number}']").bounding_box()
            for field in definitions:
                if field["page"] != page_number:
                    continue
                bounds = value(sheet, field["name"]).bounding_box()
                assert bounds, field
                for actual, expected in (
                    (bounds["x"], canvas["x"] + field["x"] * canvas["width"]),
                    (bounds["y"], canvas["y"] + field["y"] * canvas["height"]),
                    (bounds["width"], field["width"] * canvas["width"]),
                    (bounds["height"], field["height"] * canvas["height"]),
                ):
                    assert abs(actual - expected) < 2, (field, bounds, canvas, actual, expected)

        gm = player = None
        try:
            gm = client("gm")
            sheet = open_sheet(gm)
            expect(sheet.locator(".pdf-sheet__page")).to_have_text("1 / 2")
            expect(sheet.locator("[data-pdf=toggleMapping]")).to_be_visible()
            expect(sheet.locator(".pdf-sheet__fields > *")).to_have_count(0)
            records.append({"case": "flat-two-page-pdf-opens-with-gm-mapping-control"})

            for kind, name, rect in (
                ("text", "Hero name", (.08, .07, .31, .036)),
                ("number", "Vitality", (.52, .07, .17, .036)),
                ("checkbox", "Prepared", (.08, .15, .04, .03)),
                ("multiline", "Description", (.08, .23, .6, .08)),
            ):
                draw(gm, sheet, kind, name, rect)
            sheet.screenshot(path=str(output / "mapping-en-desktop.png"))
            mapping(sheet, False)
            value(sheet, "Hero name").fill("Aster")
            value(sheet, "Vitality").fill("18")
            value(sheet, "Prepared").check()
            expect(value(sheet, "Description")).to_have_js_property("tagName", "TEXTAREA")
            value(sheet, "Description").fill("Synthetic biography.\nSecond line survives reopening.")
            close_sheet(sheet)
            saved = read(gm)
            definitions = saved["data"]["pdf"]["manualFields"]
            assert len(definitions) == 4, definitions
            assert {field["type"] for field in definitions} == {"text", "number", "checkbox", "multiline"}
            assert all(field["source"] == "asset:" + seed["pdfAssets"][0] and field["page"] == 1 for field in definitions)
            assert all(0 <= field["x"] < 1 and 0 <= field["y"] < 1
                       and 0 < field["width"] <= 1 and 0 < field["height"] <= 1 for field in definitions)
            records.append({"case": "pointer-drawing-all-four-types-and-values-persist"})

            sheet = open_sheet(gm)
            expect(value(sheet, "Hero name")).to_have_value("Aster")
            expect(value(sheet, "Vitality")).to_have_value("18")
            expect(value(sheet, "Prepared")).to_be_checked()
            expect(value(sheet, "Description")).to_have_value("Synthetic biography.\nSecond line survives reopening.")
            assert_positions(sheet, definitions)
            sheet.screenshot(path=str(output / "filled-en-desktop.png"))
            before_width = sheet.locator(".pdf-sheet__canvas").bounding_box()["width"]
            sheet.locator("[data-pdf=in]").click()
            gm.wait_for_function("old => document.querySelector('.pdf-sheet__canvas').getBoundingClientRect().width > old",
                                 arg=before_width)
            assert_positions(sheet, definitions)
            sheet.locator("[data-pdf=out]").click()
            gm.wait_for_function("old => Math.abs(document.querySelector('.pdf-sheet__canvas').getBoundingClientRect().width-old)<2",
                                 arg=before_width)
            assert_positions(sheet, definitions)
            records.append({"case": "reopening-and-zoom-retain-page-relative-field-bounds"})

            numeric = next(field for field in definitions if field["name"] == "Vitality")
            numeric_key = "manual_" + numeric["id"].replace("-", "")
            name_field = next(field for field in definitions if field["name"] == "Hero name")
            name_key = "manual_" + name_field["id"].replace("-", "")
            value(sheet, "Vitality").fill("1000001")
            expect(value(sheet, "Vitality")).to_have_attribute("aria-invalid", "true")
            value(sheet, "Hero name").fill("Aster while the number is invalid")
            gm.wait_for_function("""async args => {
              const response = await fetch(args.url, {cache:'no-store'});
              if(!response.ok)return false;
              const sheet = await response.json();
              return sheet.data.fields[args.key] === args.value;
            }""", arg={"url": actor_url, "key": name_key, "value": "Aster while the number is invalid"}, polling=200)
            assert read(gm)["data"]["fields"][numeric_key] == 18
            expect(value(sheet, "Vitality")).to_have_value("1000001")
            expect(value(sheet, "Vitality")).to_have_attribute("aria-invalid", "true")
            value(sheet, "Vitality").fill("19")
            expect(value(sheet, "Vitality")).not_to_have_attribute("aria-invalid", "true")
            close_sheet(sheet)
            assert read(gm)["data"]["fields"][numeric_key] == 19
            sheet = open_sheet(gm)
            value(sheet, "Vitality").fill("18")
            value(sheet, "Hero name").fill("Aster")
            records.append({"case": "invalid-number-preserves-server-value-and-other-field-autosave"})

            mapping(sheet, True)
            # The Add field action provides keyboard creation independently of
            # pointer dragging; deleting its definition keeps the other fields.
            sheet.locator("[data-pdf-map-tool]").select_option("text")
            sheet.locator("[data-pdf-map-add]").click()
            sheet.locator("[data-pdf-map-name]").fill("Discard this field")
            sheet.locator("[data-pdf-map-delete]").click()
            expect(sheet.locator("[data-pdf-map-field]")).to_have_count(4)
            sheet.locator("[data-pdf-map-tool]").select_option("text")
            canvas = sheet.locator(".pdf-sheet__canvas").bounding_box()
            gm.mouse.move(canvas["x"] + .75 * canvas["width"], canvas["y"] + .15 * canvas["height"])
            gm.mouse.down()
            gm.mouse.move(canvas["x"] + .9 * canvas["width"], canvas["y"] + .2 * canvas["height"], steps=3)
            gm.keyboard.press("Escape")
            gm.mouse.up()
            expect(sheet.locator("[data-pdf-map-field]")).to_have_count(4)
            records.append({"case": "escape-cancels-uncommitted-rectangle"})

            sheet.locator("[data-pdf-map-tool]").select_option("select")
            name_definition = next(field for field in definitions if field["name"] == "Hero name")
            field_box = sheet.locator(f"[data-pdf-map-field='{name_definition['id']}']")
            field_box.click()
            x_property = sheet.locator("[data-pdf-map-property=x]")
            before_x = float(x_property.input_value())
            field_box.focus()
            field_box.press("ArrowRight")
            assert float(x_property.input_value()) > before_x
            field_box.press("ArrowLeft")
            assert abs(float(x_property.input_value()) - before_x) < .01

            bounds = field_box.bounding_box()
            before_x = float(x_property.input_value())
            gm.mouse.move(bounds["x"] + bounds["width"] / 2, bounds["y"] + bounds["height"] / 2)
            gm.mouse.down()
            gm.mouse.move(bounds["x"] + bounds["width"] / 2 + .04 * canvas["width"],
                          bounds["y"] + bounds["height"] / 2 + .02 * canvas["height"], steps=4)
            gm.mouse.up()
            assert float(x_property.input_value()) > before_x + 3
            width_property = sheet.locator("[data-pdf-map-property=width]")
            before_size = float(width_property.input_value())
            handle = field_box.locator("[data-pdf-map-resize]").bounding_box()
            gm.mouse.move(handle["x"] + handle["width"] / 2, handle["y"] + handle["height"] / 2)
            gm.mouse.down()
            gm.mouse.move(handle["x"] + handle["width"] / 2 + .03 * canvas["width"],
                          handle["y"] + handle["height"] / 2 + .015 * canvas["height"], steps=4)
            gm.mouse.up()
            assert float(width_property.input_value()) > before_size + 2
            sheet.locator("[data-pdf-map-name]").fill("Hero name retained")
            sheet.locator("[data-pdf-map-name]").press("Tab")
            mapping(sheet, False)
            expect(value(sheet, "Hero name retained")).to_have_value("Aster")
            mapping(sheet, True)
            field_box.click()
            sheet.locator("[data-pdf-map-name]").fill("Hero name")
            sheet.locator("[data-pdf-map-name]").press("Tab")
            mapping(sheet, False)
            records.append({"case": "keyboard-field-creation-and-delete-preserve-existing-layout"})
            records.append({"case": "move-resize-keyboard-and-renaming-preserve-field-values"})

            sheet.locator("[data-pdf=nextPage]").click()
            expect(sheet.locator(".pdf-sheet__page")).to_have_text("2 / 2")
            expect(value(sheet, "Hero name")).to_have_count(0)
            draw(gm, sheet, "text", "Page two note", (.08, .08, .45, .04), page_number=2)
            mapping(sheet, False)
            value(sheet, "Page two note").fill("Only the second page.")
            sheet.locator("[data-pdf=prevPage]").click()
            expect(sheet.locator(".pdf-sheet__page")).to_have_text("1 / 2")
            expect(value(sheet, "Page two note")).to_have_count(0)
            expect(value(sheet, "Hero name")).to_have_value("Aster")
            sheet.locator("[data-pdf=toggleSpread]").click()
            expect(sheet.locator(".pdf-sheet__canvas")).to_have_count(2)
            expect(value(sheet, "Page two note")).to_have_value("Only the second page.")
            second_bounds = sheet.locator(".pdf-sheet__canvas[data-pdf-page='2']").bounding_box()
            second_field = value(sheet, "Page two note").bounding_box()
            assert abs(second_field["x"] - second_bounds["x"] - .08 * second_bounds["width"]) < 2
            assert abs(second_field["y"] - second_bounds["y"] - .08 * second_bounds["height"]) < 2
            sheet.locator("[data-pdf=toggleSpread]").click()
            expect(sheet.locator(".pdf-sheet__canvas")).to_have_count(1)
            records.append({"case": "two-page-view-keeps-second-page-field-offset"})
            source(sheet, "Synthetic alternate.pdf")
            expect(sheet.locator(".pdf-sheet__fields > *")).to_have_count(0)
            draw(gm, sheet, "text", "Alternate source note", (.08, .08, .45, .04))
            mapping(sheet, False)
            value(sheet, "Alternate source note").fill("Only the alternate PDF.")
            source(sheet, "Synthetic character.pdf")
            expect(value(sheet, "Alternate source note")).to_have_count(0)
            expect(value(sheet, "Hero name")).to_have_value("Aster")
            close_sheet(sheet)
            layout = read(gm)["data"]["pdf"]["manualFields"]
            assert len(layout) == 6, layout
            assert next(field for field in layout if field["name"] == "Page two note")["page"] == 2
            assert next(field for field in layout if field["name"] == "Alternate source note")["source"] == "asset:" + seed["pdfAssets"][1]
            records.append({"case": "manual-layout-and-values-stay-bound-to-pdf-source-and-page"})

            player = client("player")
            player_sheet = open_sheet(player)
            expect(player_sheet.locator("[data-pdf=toggleMapping]")).to_be_hidden()
            expect(player_sheet.locator("[data-pdf-mapping-tools]")).to_be_hidden()
            value(player_sheet, "Hero name").fill("Aster, controlled by player")
            value(player_sheet, "Vitality").fill("23")
            value(player_sheet, "Prepared").uncheck()
            close_sheet(player_sheet)
            after_player = read(player)
            assert after_player["data"]["pdf"]["manualFields"] == layout
            forged = player.evaluate("""async ({url,actor}) => {
              const current = await (await fetch(url)).json();
              current.data.pdf.manualFields[0].x += 0.01;
              try {
                await window.gravewrightRealtime.resourceCommand('actors','sheet.save',{
                  actorId:actor,name:current.name,data:current.data,
                  version:current.version,sheetVersion:current.sheetVersion});
                return {accepted:true};
              } catch(error) { return {accepted:false,code:error.code,message:error.message}; }
            }""", {"url": actor_url, "actor": seed["actor"]})
            assert forged["accepted"] is False and forged["code"] == "forbidden", forged
            assert read(gm)["data"]["pdf"]["manualFields"] == layout
            records.append({"case": "controlled-player-fills-values-but-server-rejects-layout-edits"})

            duplicated = gm.evaluate("""args => window.gravewrightRealtime.resourceCommand('tokens','duplicate',{
              mapId:args.scene,tokenIds:[args.token]})""",
              {"scene": seed["selectedScene"], "token": seed["token"]})
            snapshot_id = duplicated["createdIds"][0]
            snapshot = next(token for token in duplicated["tokens"] if token["id"] == snapshot_id)
            assert snapshot["linkMode"] == "snapshot", snapshot
            snapshot_sheet = open_sheet(gm, snapshot)
            expect(value(snapshot_sheet, "Vitality")).to_have_value("23")
            value(snapshot_sheet, "Vitality").fill("41")
            close_sheet(snapshot_sheet)
            snapshot_data = read(gm, snapshot_id)["data"]
            vitality = next(field for field in layout if field["name"] == "Vitality")
            vitality_key = "manual_" + vitality["id"].replace("-", "")
            assert snapshot_data["fields"][vitality_key] == 41
            assert read(gm)["data"]["fields"][vitality_key] == 23
            assert snapshot_data["pdf"]["manualFields"] == layout
            records.append({"case": "snapshot-token-keeps-mapped-layout-and-independent-field-values"})

            sheet = open_sheet(gm)
            source(sheet, "Synthetic fillable.pdf")
            expect(value(sheet, "HP")).to_be_visible()
            value(sheet, "HP").fill("12")
            draw(gm, sheet, "text", "Manual beside native", (.45, .14, .3, .04))
            mapping(sheet, False)
            expect(value(sheet, "HP")).to_have_value("12")
            value(sheet, "Manual beside native").fill("Native and manual coexist.")
            close_sheet(sheet)
            sheet = open_sheet(gm)
            expect(value(sheet, "HP")).to_have_value("12")
            expect(value(sheet, "Manual beside native")).to_have_value("Native and manual coexist.")
            source(sheet, "Synthetic character.pdf")
            expect(value(sheet, "HP")).to_have_count(0)
            expect(value(sheet, "Vitality")).to_have_value("23")
            gm.keyboard.press("Escape")
            expect(sheet).to_have_count(0)
            records.append({"case": "native-acroform-and-manual-fields-coexist-and-retain-values"})

            translations = {"en": "Map fields", "pt-BR": "Mapear campos", "es": "Mapear campos"}
            for locale, label in translations.items():
                change_locale(gm, locale, campaign)
                gm.set_viewport_size({"width": 390, "height": 844})
                gm.reload()
                gm.wait_for_function("!!window.gravewrightActors && !!window.gravewrightRealtime")
                sheet = open_sheet(gm)
                expect(sheet.locator("[data-pdf=toggleMapping]")).to_contain_text(label)
                mapping(sheet, True)
                selected_box = sheet.locator(f"[data-pdf-map-field='{name_definition['id']}']")
                selected_box.click()
                expect(sheet.locator("[data-pdf-map-properties]")).to_be_visible()
                long_name = "Synthetic authored field name: Áster, João y la exploradora; details remain readable and editable in any language."
                sheet.locator("[data-pdf-map-name]").fill(long_name)
                sheet.locator("[data-pdf-map-name]").press("Tab")
                expect(selected_box).to_have_attribute("aria-label", long_name)
                expect(selected_box.locator(".pdf-sheet__map-label")).to_have_css("text-overflow", "ellipsis")
                # The interface must stay usable at small widths. Authored page
                # contents may scroll inside the sheet's own PDF stage.
                measurements = sheet.evaluate(PDF_MEASURE)
                assert not measurements["tiny"], (locale, measurements)
                assert not measurements["overflow"], (locale, measurements)
                sheet.screenshot(path=str(output / f"mapping-{locale}-390.png"))
                mapping(sheet, False)
                expect(value(sheet, "Vitality")).to_have_value("23")
                close_sheet(sheet)
                records.append({"case": f"translated-responsive-mapping-controls-{locale}-390"})
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
            "assets": "Two generated flat PDFs and one generated fillable PDF with a native HP widget."}


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
    output = (args.output or ROOT / "data/pdf-manual-fields" /
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
