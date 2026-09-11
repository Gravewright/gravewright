"""Token + editable PDF browser regression, with temporary database and media."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

from maps import port
from PIL import Image, ImageChops
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def editable_pdf():
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R /AcroForm 5 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Annots [7 0 R 8 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] >>",
        b"<< /Fields [7 0 R 8 0 R] /DR << /Font << /Helv 6 0 R >> >> /DA (/Helv 12 Tf 0 g) /NeedAppearances true >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Annot /Subtype /Widget /FT /Tx /T (HP) /Rect [30 740 130 770] /P 3 0 R /DA (/Helv 12 Tf 0 g) >>",
        b"<< /Type /Annot /Subtype /Widget /FT /Tx /T (Energy) /Rect [150 740 250 770] /P 3 0 R /DA (/Helv 12 Tf 0 g) >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(str(i).encode() + b" 0 obj\n" + obj + b"\nendobj\n")
    start = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
    )
    return bytes(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path)
    args = parser.parse_args()
    output = ROOT / "test-results/tokens-pdf"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="grave-tokens-") as temp:
        if args.original:
            subprocess.run(
                ["node", "tests/e2e/reference_tokens.cjs", str(args.original), temp],
                cwd=ROOT,
                check=True,
            )
        env = {
            **os.environ,
            "GRAVEWRIGHT_DATABASE": str(Path(temp) / "db.sqlite3"),
            "GRAVEWRIGHT_MEDIA_ROOT": str(Path(temp) / "media"),
        }
        subprocess.run(
            [sys.executable, "manage.py", "migrate", "--noinput"],
            cwd=ROOT,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        script = """
import os,json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django;django.setup()
from django.test import Client
from django.conf import settings
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign,Membership
owner=User.objects.create_user('owner@example.test','browser-password-123',name='Browser Owner',role='owner')
player=User.objects.create_user('player@example.test','browser-password-123',name='Player')
c=Campaign.objects.create(owner=owner,name='Tokens and PDF')
Membership.objects.create(campaign=c,user=owner,role='gm');Membership.objects.create(campaign=c,user=player,role='player')
result={'campaign':str(c.pk),'playerId':str(player.pk),'cookie':settings.SESSION_COOKIE_NAME}
for key,user in [('gm',owner),('player',player)]:
 client=Client();client.force_login(user);result[key]=client.session.session_key
print(json.dumps(result))
"""
        data = json.loads(
            subprocess.check_output(
                [sys.executable, "-c", script], cwd=ROOT, env=env, text=True
            )
        )
        base = f"http://127.0.0.1:{port()}"
        log = (output / "server.log").open("w")
        server = subprocess.Popen(
            [
                sys.executable,
                "manage.py",
                "runserver",
                base.removeprefix("http://"),
                "--noreload",
            ],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            for _ in range(100):
                try:
                    urlopen(base, timeout=1)
                    break
                except OSError:
                    time.sleep(0.1)
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                contexts = []
                errors = []
                for role in ("gm", "player"):
                    ctx = browser.new_context(
                        viewport={"width": 1440, "height": 1000},
                        reduced_motion="reduce",
                    )
                    ctx.add_cookies(
                        [{"name": data["cookie"], "value": data[role], "url": base}]
                    )
                    contexts.append(ctx)
                gm = contexts[0].new_page()
                player = contexts[1].new_page()
                for page in (gm, player):
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.goto(base + "/game/" + data["campaign"])
                    page.wait_for_function(
                        "window.gravewrightRealtime && document.querySelector('#table-workspace').dataset.tableId"
                    )
                    page.wait_for_function(
                        "document.querySelector('.game-menubar__presence--seated') !== null || document.querySelector('#table-workspace').textContent.includes('Browser Owner')"
                    )
                comparisons = []

                def compare(kind, target, value, name):
                    if not args.original:
                        return
                    ref = contexts[0].new_page()
                    ref.set_viewport_size(gm.viewport_size)
                    styles = gm.locator("link[rel=stylesheet]").evaluate_all(
                        "(nodes)=>nodes.map(n=>n.href)"
                    )
                    markup = (
                        '<!doctype html><html lang="en"><head>'
                        + "".join(
                            f'<link rel="stylesheet" href="{url}">' for url in styles
                        )
                        + '</head><body><div id="reference"></div></body></html>'
                    )
                    ref.route(
                        "**/__reference__",
                        lambda route: route.fulfill(
                            body=markup, content_type="text/html"
                        ),
                    )
                    ref.goto(base + "/__reference__")
                    ref.add_script_tag(path=str(Path(temp) / "reference.js"))
                    ref.add_style_tag(path=str(Path(temp) / "reference.css"))
                    bounds = target.bounding_box()
                    if kind == "pdf":
                        ref.evaluate(
                            """({value,bounds})=>{const host=document.querySelector('#reference'),wrap=document.createElement('gravewright-pdf-system-sheet');host.replaceWith(wrap);Object.assign(wrap.style,{width:bounds.width+'px',height:bounds.height+'px',position:'fixed',left:'0',top:'0'});const assets={url:p=>p.startsWith('vendor/')?'/static/gravewright_journals/'+p:'/static/gravewright_pdf_system/'+p,json:async p=>(await fetch('/static/gravewright_pdf_system/'+p)).json(),bytes:async p=>(await fetch('/static/gravewright_pdf_system/'+p)).arrayBuffer()};window.mountReference('pdf',{actorId:value.id,block:{context:{role:'gm'},assets,host:{async call(name){if(name==='actor.read')return {...value,tableId:value.containerId,type:'character',revision:String(value.version)};if(name==='actor.data.read')return {data:value.data,revision:String(value.sheetVersion)};if(name==='asset.list')return{items:[]};if(name==='asset.download'){const r=await fetch('/game/actors/asset/'+value.data.pdf.asset);return{blob:await r.blob()}}}}}},wrap)}""",
                            {"value": value, "bounds": bounds},
                        )
                        expect(ref.locator(".pdf-sheet__canvas")).to_have_count(1)
                        ref.get_by_role("tab", name="Token", exact=True).click()
                        reference = ref.locator(".pdf-sheet")
                    else:
                        ref.evaluate(
                            "p=>window.mountReference('token',p,document.querySelector('#reference'))",
                            value,
                        )
                        reference = ref.locator(".token-editor")
                    for page in (gm, ref):
                        page.evaluate("document.activeElement?.blur()")
                        page.add_style_tag(
                            content=".game-table__stage{visibility:hidden!important} *{caret-color:transparent!important}"
                        )
                    target.screenshot(path=str(output / (name + "-django.png")))
                    reference.screenshot(path=str(output / (name + "-original.png")))
                    a = Image.open(output / (name + "-django.png")).convert("RGB")
                    b = Image.open(output / (name + "-original.png")).convert("RGB")
                    if a.size != b.size:
                        for tag, loc in [("django", target), ("original", reference)]:
                            (output / (name + "-" + tag + "-layout.json")).write_text(
                                json.dumps(
                                    loc.evaluate(
                                        "e=>[e,...e.querySelectorAll('form,fieldset,header,footer,label,small,p')].map(n=>({tag:n.tagName,cls:n.className,rect:n.getBoundingClientRect().toJSON(),style:Object.fromEntries(['display','gap','margin','padding','height','boxSizing'].map(k=>[k,getComputedStyle(n)[k]]))}))"
                                    ),
                                    indent=2,
                                )
                            )
                    assert a.size == b.size, (name, a.size, b.size)
                    diff = ImageChops.difference(a, b)
                    count = sum(max(pixel) > 20 for pixel in diff.get_flattened_data())
                    ratio = count / (a.width * a.height)
                    diff.save(output / (name + "-diff.png"))
                    comparisons.append(
                        {"component": name, "different_pixels": count, "ratio": ratio}
                    )
                    (output / "comparison.json").write_text(
                        json.dumps(comparisons, indent=2)
                    )
                    ref.close()
                    gm.add_style_tag(
                        content=".game-table__stage{visibility:visible!important}"
                    )
                    assert ratio < 0.01, (name, ratio)

                gm.get_by_role("button", name="Actors", exact=True).click()
                expect(gm.locator("#actors-panel")).to_be_visible()
                gm.locator("[data-template-upload]").set_input_files(
                    {
                        "name": "Character.pdf",
                        "mimeType": "application/pdf",
                        "buffer": editable_pdf(),
                    }
                )
                gm.wait_for_function(
                    "document.querySelector('[data-templates]').textContent.includes('Character.pdf')"
                )
                gm.locator("[data-actor-panel=create]").click()
                form = gm.locator("#table-workspace ~ .directory-dialog")
                form = gm.get_by_role("dialog", name="New character")
                form.locator("[name=name]").fill("Aster")
                form.get_by_role("button", name="Create character").click()
                expect(gm.locator(".actor-directory__actor")).to_have_count(1)
                gm.locator(".actor-directory__actor").click()
                sheet = gm.locator(".actor-directory__sheet")
                expect(sheet).to_be_visible()
                expect(sheet.locator(".pdf-sheet__canvas")).to_have_count(1)
                expect(
                    sheet.get_by_role("spinbutton", name="HP", exact=True)
                ).to_be_visible()
                sheet.get_by_role("spinbutton", name="HP", exact=True).fill("17")
                sheet.get_by_title("Next page", exact=True).click()
                expect(sheet.locator(".pdf-sheet__page")).to_have_text("2 / 2")
                sheet.get_by_title("Previous page", exact=True).click()
                expect(
                    sheet.get_by_role("spinbutton", name="HP", exact=True)
                ).to_have_value("17")
                sheet.get_by_role("tab", name="Token", exact=True).click()
                sheet.locator("[data-bar=bar2Value]").select_option("Energy")
                sheet.get_by_role("tab", name="Character sheet", exact=True).click()
                sheet.get_by_role("spinbutton", name="Energy", exact=True).fill("9")
                gm.wait_for_timeout(700)
                sheet.get_by_role("tab", name="Token", exact=True).click()
                sheet.locator("[data-field=size]").fill("2")
                sheet.locator("[data-field=name]").fill("Aster Prime")
                gm.wait_for_timeout(700)
                expect(sheet.locator(".pdf-sheet__error")).to_be_hidden()
                sheet.screenshot(path=str(output / "pdf-token.png"))
                catalog = gm.request.get(
                    base + f"/api/containers/{data['campaign']}/actors"
                ).json()
                a = catalog["actors"][0]
                value = gm.request.get(
                    base + f"/api/containers/{data['campaign']}/actors/{a['id']}/sheet"
                ).json()
                compare("pdf", sheet.locator(".pdf-sheet"), value, "pdf-token")
                sheet.get_by_role("tab", name="Notes", exact=True).click()
                sheet.locator("[data-note=bio] [contenteditable=true]").fill(
                    "Biography survives reload."
                )
                gm.wait_for_timeout(700)
                sheet.get_by_role("button", name="Close character sheet").click()
                gm.locator(".actor-directory__actor").click()
                expect(gm.locator("[data-field=name]")).to_have_value("Aster Prime")
                gm.locator(".actor-directory__sheet").get_by_role(
                    "tab", name="Notes", exact=True
                ).click()
                expect(gm.locator("[data-note=bio]")).to_contain_text(
                    "Biography survives reload."
                )
                gm.locator(".actor-directory__sheet").get_by_role(
                    "button", name="Close character sheet"
                ).click()
                actors = gm.request.get(
                    base + f"/api/containers/{data['campaign']}/actors"
                ).json()
                aid = actors["actors"][0]["id"]
                saved = gm.request.get(
                    base + f"/api/containers/{data['campaign']}/actors/{aid}/sheet"
                ).json()
                assert saved["data"]["bars"]["bar_1"]["value"] == 17
                assert saved["data"]["bars"]["bar_2"]["value"] == 9
                assert "Energy" not in saved["data"]["fields"]
                gm.evaluate(
                    "async p=>window.gravewrightRealtime.resourceCommand('actors','actor.permissions',{id:p.id,permissions:{[p.player]:'owner'}})",
                    {"id": aid, "player": data["playerId"]},
                )
                image = BytesIO()
                Image.new("RGB", (1400, 1000), "#354b66").save(image, "PNG")
                csrf = next(
                    c["value"]
                    for c in contexts[0].cookies()
                    if c["name"] == "gravewright-csrf"
                )
                response = gm.request.post(
                    base + f"/api/containers/{data['campaign']}/scene-upload",
                    multipart={
                        "name": "Test map",
                        "map": {
                            "name": "map.png",
                            "mimeType": "image/png",
                            "buffer": image.getvalue(),
                        },
                        "activate": "true",
                    },
                    headers={"X-CSRF-Token": csrf},
                )
                assert response.status == 201, response.text()
                scene = response.json()
                expect(gm.locator(".token-workspace")).to_have_count(1)
                expect(player.locator(".token-workspace")).to_have_count(1)
                origin = gm.locator(".actor-directory__actor").bounding_box()
                destination = gm.evaluate(
                    "()=>{const v=window.gravewrightMaps.board.viewport(),m=window.gravewrightMaps.current;return{x:v.x+2*m.gridSize*m.imageScale*v.scale,y:v.y+2*m.gridSize*m.imageScale*v.scale}}"
                )
                gm.mouse.move(origin["x"] + 40, origin["y"] + 20)
                gm.mouse.down()
                gm.mouse.move(destination["x"], destination["y"], steps=15)
                gm.wait_for_timeout(100)
                gm.mouse.up()
                expect(
                    gm.get_by_role("button", name="Token: Aster Prime", exact=True)
                ).to_be_visible()
                expect(
                    player.get_by_role("button", name="Token: Aster Prime", exact=True)
                ).to_be_visible()
                # Hide directory before map gestures; panels must not intercept the token.
                gm.locator("[data-actor-panel=close]").click()
                target = player.get_by_role(
                    "button", name="Token: Aster Prime", exact=True
                )
                gm.evaluate(
                    "window.motionPackets=[];window.addEventListener('gravewright:token.drag',e=>window.motionPackets.push(e.detail))"
                )
                box = target.bounding_box()
                step = player.evaluate(
                    "window.gravewrightMaps.current.gridSize*window.gravewrightMaps.current.imageScale*window.gravewrightMaps.board.viewport().scale"
                )
                x = box["x"] + box["width"] / 2
                y = box["y"] + box["height"] / 2
                player.mouse.move(x, y)
                player.mouse.down()
                player.mouse.move(x + step, y, steps=5)
                player.wait_for_timeout(350)
                gm.wait_for_function("window.motionPackets.some(p=>p.phase==='update')")
                before = gm.request.get(
                    base
                    + f"/api/containers/{data['campaign']}/maps/{scene['id']}/tokens"
                ).json()["tokens"]
                assert before[0]["gridX"] == 2
                player.mouse.up()
                expect(player.locator('.token-workspace__status')).to_be_hidden(timeout=15000)
                after = gm.request.get(
                    base
                    + f"/api/containers/{data['campaign']}/maps/{scene['id']}/tokens"
                ).json()["tokens"]
                assert after[0]["gridX"] == 3
                player.keyboard.press("Control+z")
                expect(player.locator('.token-workspace__status')).to_be_hidden(timeout=15000)
                expect(target).to_have_attribute('x','140',timeout=15000)
                target.click()
                player.keyboard.press("ArrowRight")
                expect(player.locator('.token-workspace__status')).to_be_hidden(timeout=15000)
                tokens = gm.request.get(
                    base
                    + f"/api/containers/{data['campaign']}/maps/{scene['id']}/tokens"
                ).json()["tokens"]
                assert tokens[0]["gridX"] == 3, tokens
                player.keyboard.press("Control+z")
                expect(player.locator('.token-workspace__status')).to_be_hidden(timeout=15000)
                tokens = gm.request.get(
                    base
                    + f"/api/containers/{data['campaign']}/maps/{scene['id']}/tokens"
                ).json()["tokens"]
                assert tokens[0]["gridX"] == 2
                target.dblclick()
                expect(player.locator(".token-sheet")).to_be_visible()
                player.locator(".token-sheet").get_by_role(
                    "button", name="Close character sheet"
                ).click()
                gm.get_by_role("button", name="Token: Aster Prime", exact=True).click(
                    button="right"
                )
                gm.get_by_role("menuitem", name="Vision", exact=True).click()
                expect(gm.get_by_role("dialog", name="Token vision")).to_be_visible()
                gm.get_by_role("dialog", name="Token vision").screenshot(
                    path=str(output / "token-vision.png")
                )
                tokens = gm.request.get(
                    base
                    + f"/api/containers/{data['campaign']}/maps/{scene['id']}/tokens"
                ).json()["tokens"]
                compare(
                    "token",
                    gm.get_by_role("dialog", name="Token vision"),
                    {
                        "tokens": tokens,
                        "mode": "vision",
                        "busy": False,
                        "error": "",
                        "dynamic": False,
                        "measureValue": 1,
                        "measureUnit": "",
                    },
                    "token-vision",
                )
                gm.get_by_role("dialog", name="Token vision").get_by_role(
                    "button", name="Close editor"
                ).click()
                for action, mode, title in [
                    ("Configure", "configure", "Configure token"),
                    ("Conditions", "conditions", "Conditions"),
                ]:
                    gm.get_by_role(
                        "button", name="Token: Aster Prime", exact=True
                    ).click(button="right")
                    gm.get_by_role("menuitem", name=action, exact=True).click()
                    compare(
                        "token",
                        gm.get_by_role("dialog", name=title, exact=True),
                        {
                            "tokens": tokens,
                            "mode": mode,
                            "busy": False,
                            "error": "",
                            "dynamic": False,
                            "measureValue": 1,
                            "measureUnit": "",
                        },
                        "token-" + mode,
                    )
                    gm.get_by_role("dialog", name=title, exact=True).get_by_role(
                        "button", name="Close editor"
                    ).click()
                gm.get_by_role("button", name="Token: Aster Prime", exact=True).click(
                    button="right"
                )
                gm.get_by_role("menuitem", name="Hide selection").click()
                expect(
                    player.get_by_role("button", name="Token: Aster Prime", exact=True)
                ).to_have_count(0)
                # Duplicate tokens edit their own PDF data, preserving the actor.
                original_token = tokens[0]
                gm.evaluate(
                    "p=>window.gravewrightRealtime.resourceCommand('tokens','hidden',p)",
                    {
                        "mapId": scene["id"],
                        "tokenIds": [original_token["id"]],
                        "hidden": False,
                    },
                )
                gm.get_by_role("button", name="Token: Aster Prime", exact=True).click()
                gm.keyboard.press("Control+c")
                gm.keyboard.press("Control+v")
                expect(
                    gm.get_by_role("button", name="Token: Aster Prime", exact=True)
                ).to_have_count(2)
                gm.get_by_role("button", name="Token: Aster Prime", exact=True).nth(
                    1
                ).dblclick()
                copy_sheet = gm.locator(".token-sheet")
                expect(copy_sheet).to_contain_text("Independent copy")
                expect(
                    copy_sheet.get_by_role("spinbutton", name="HP", exact=True)
                ).to_be_visible()
                copy_sheet.get_by_role("spinbutton", name="HP", exact=True).fill("29")
                copy_sheet.get_by_role("tab", name="Token", exact=True).click()
                copy_sheet.locator("[data-field=name]").fill("Aster Copy")
                expect(copy_sheet.locator("[data-upload=token]")).to_be_disabled()
                gm.wait_for_timeout(700)
                copy_sheet.get_by_role("button", name="Close character sheet").click()
                saved_actor = gm.request.get(
                    base + f"/api/containers/{data['campaign']}/actors/{aid}/sheet"
                ).json()
                assert saved_actor["data"]["bars"]["bar_1"]["value"] == 17
                result = gm.request.get(
                    base
                    + f"/api/containers/{data['campaign']}/maps/{scene['id']}/tokens"
                ).json()["tokens"]
                copied = next(t for t in result if t["name"] == "Aster Copy")
                assert copied["bars"]["bar_1"]["value"] == 29
                gm.get_by_role("button", name="Token: Aster Copy", exact=True).click()
                gm.keyboard.press("Delete")
                gm.get_by_role("dialog", name="Remove tokens", exact=True).get_by_role(
                    "button", name="Remove", exact=True
                ).click()
                expect(
                    gm.get_by_role("button", name="Token: Aster Copy", exact=True)
                ).to_have_count(0)
                gm.set_viewport_size({"width": 390, "height": 844})
                gm.evaluate("id=>window.gravewrightActors.open(id)", aid)
                mobile = gm.locator(".actor-directory__sheet")
                expect(mobile.locator(".pdf-sheet__canvas")).to_have_count(1)
                mobile.get_by_role("tab", name="Token", exact=True).click()
                compare(
                    "pdf", mobile.locator(".pdf-sheet"), saved_actor, "pdf-token-mobile"
                )
                mobile.get_by_role("button", name="Close character sheet").click()
                gm.set_viewport_size({"width": 1440, "height": 1000})
                gm.screenshot(path=str(output / "map-tokens.png"))
                assert not errors, errors
                print(
                    "PASS: actor, PDF, notes, permissions, token placement, movement, undo, sheet, vision editor and hidden filtering"
                )
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=10)
            log.close()


if __name__ == "__main__":
    main()
