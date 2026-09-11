"""Browser flows and optional pixel comparison against the original compiled Vue UI.

uv run python tests/e2e/maps.py --original /path/to/reference
Uses a temporary database; never creates accounts in the development database.
"""

import argparse
import functools
import json
from io import BytesIO
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "browser-password-123"


def sample_pdf():
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for text in [b"Chronicle", b"The archive"]:
        stream = b"BT /F1 18 Tf 20 240 Td (" + text + b") Tj ET"
        objects.append(
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n")
    start = len(output)
    output.extend(b"xref\n0 8\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        b"trailer\n<< /Size 8 /Root 1 0 R >>\nstartxref\n"
        + str(start).encode()
        + b"\n%%EOF\n"
    )
    return bytes(output)


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path)
    parser.add_argument("--tools-only", action="store_true")
    args = parser.parse_args()
    output = ROOT / "test-results" / "maps"
    output.mkdir(parents=True, exist_ok=True)
    report = []
    with tempfile.TemporaryDirectory(prefix="grave-table-browser-") as temp:
        env = {
            **os.environ,
            "GRAVEWRIGHT_DATABASE": str(Path(temp) / "browser.sqlite3"),
            "GRAVEWRIGHT_MEDIA_ROOT": str(Path(temp) / "media"),
        }
        subprocess.run(
            [sys.executable, "manage.py", "migrate", "--noinput"],
            cwd=ROOT,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        address = f"127.0.0.1:{port()}"
        base = f"http://{address}"
        log = (output / "server.log").open("w")
        server = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", address, "--noreload"],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=log,
        )
        reference_server = None
        try:
            for _ in range(100):
                try:
                    with urlopen(base, timeout=1):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError(
                    "Django did not start; inspect test-results/realtime/server.log"
                )
            if args.original:
                handler = functools.partial(
                    QuietHandler, directory=str(args.original / "dist/frontend")
                )
                reference_server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
                threading.Thread(
                    target=reference_server.serve_forever, daemon=True
                ).start()
                reference_url = f"http://127.0.0.1:{reference_server.server_port}"
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                context = browser.new_context(
                    viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
                )
                context.add_init_script(
                    "window.__sockets=[]; const Native=window.WebSocket; window.WebSocket=class extends Native{constructor(...args){super(...args);window.__sockets.push(this)}}"
                )
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(error.stack or str(error)))
                reference = None
                account = {
                    "name": "Browser Owner",
                    "email": "owner@example.test",
                    "role": "owner",
                }
                rows = []
                temporary_code = ""
                journal_state = {
                    "journals": [],
                    "folders": [],
                    "members": [],
                    "is_gm": True,
                    "handouts_enabled": True,
                }
                map_state = {"maps": [], "folders": [], "activeMapId": None}
                online_members = [
                    {"id": "owner", "name": "Browser Owner", "role": "gm"}
                ]
                reference_sockets = []
                cover_file = BytesIO()
                Image.new("RGB", (640, 360), "#354b66").save(cover_file, "PNG")
                page.goto(base)
                page.locator("#owner-name").fill(account["name"])
                page.locator("#owner-email").fill(account["email"])
                page.locator("#owner-password").fill(PASSWORD)
                page.get_by_role("button", name="Create administrator").click()
                expect(page.locator("#inside-shell")).to_be_visible()
                if reference_server:
                    reference = browser.new_page(
                        viewport={"width": 1440, "height": 1000},
                        reduced_motion="reduce",
                    )

                    def mock_auth(route):
                        path = route.request.url.split(reference_url)[-1].split("?")[0]
                        if path.startswith("/api/maps/"):
                            response = page.request.get(base + path)
                            route.fulfill(
                                status=response.status,
                                body=response.body(),
                                headers={
                                    "Content-Type": response.headers.get(
                                        "content-type", "application/json"
                                    )
                                },
                            )
                            return
                        if path.endswith("/scene-directory"):
                            body = map_state["maps"]
                        elif path.endswith("/blocks"):
                            body = [
                                {
                                    "id": m["blockId"],
                                    "containerId": rows[0]["id"],
                                    "name": m["name"],
                                    "createdAt": 0,
                                    "updatedAt": 0,
                                }
                                for m in map_state["maps"]
                            ]
                        elif path.endswith("/map-folders"):
                            body = map_state["folders"]
                        elif path.endswith("/state"):
                            body = page.request.get(
                                base
                                + "/api/maps/"
                                + map_state["maps"][0]["id"]
                                + "/state"
                            ).json()
                        elif path.endswith("/tokens"):
                            body = []
                        elif path.endswith("/journals"):
                            body = journal_state
                        elif "/library/journals/" in path:
                            action = path.rsplit("/", 1)[-1]
                            if action == "create":
                                body = {
                                    "journal_id": journal_state["journals"][0]["id"]
                                }
                            elif action == "update":
                                payload = route.request.post_data_json
                                j = next(
                                    j
                                    for j in journal_state["journals"]
                                    if j["id"] == payload["journal_id"]
                                )
                                j.update(
                                    title=payload["title"],
                                    visibility=payload["visibility"],
                                    content_doc=payload["data"]["content"],
                                    editable_sections=payload["data"]["sections"],
                                    sections=payload["data"]["sections"],
                                    diary={"gm": payload["data"].get("gm")},
                                )
                                body = {"journal_id": j["id"]}
                            else:
                                body = {}
                        elif path.endswith("/status"):
                            body = {"configured": True}
                        elif path.endswith("/session"):
                            body = {"authenticated": True, "account": account}
                        elif path == "/api/containers":
                            body = rows
                        elif path == "/api/rulesets":
                            body = {
                                "rulesets": [
                                    {
                                        "systemId": "gravewright-pdf-system",
                                        "title": "Gravewright PDF System",
                                        "actorTypes": [
                                            {"id": "character", "label": "Character"}
                                        ],
                                    }
                                ]
                            }
                        elif path.endswith("/map"):
                            body = next(
                                (
                                    m
                                    for m in map_state["maps"]
                                    if m["id"] == map_state["activeMapId"]
                                ),
                                None,
                            )
                        elif path.endswith("/modules"):
                            body = {
                                "modules": [],
                                "moduleSetRevision": "1",
                                "tableId": rows[0]["id"],
                                "replacements": {},
                            }
                        elif path.endswith("/capabilities"):
                            body = {"items": False}
                        elif path.endswith(
                            ("/blocks", "/scene-directory", "/folders", "/journals")
                        ):
                            body = []
                        elif path == "/api/player-preferences":
                            body = {"pingColor": "#f2c679"}
                        elif path.endswith("/invitation") or path.endswith(
                            "/removal-code"
                        ):
                            body = {"code": temporary_code, "expiresAt": 9999999999999}
                        else:
                            body = {"ready": True, "token": "reference"}
                        route.fulfill(status=200, json=body)

                    reference.route(
                        "**/campaigns/*/cover",
                        lambda route: route.fulfill(
                            content_type="image/png", body=cover_file.getvalue()
                        ),
                    )

                    def mock_socket(ws):
                        reference_sockets.append(ws)

                        def received(raw):
                            message = json.loads(raw)
                            if message["type"] == "table.join":
                                ws.send(
                                    json.dumps(
                                        {
                                            "type": "table.joined",
                                            "payload": {
                                                "tableId": rows[0]["id"],
                                                "role": "gm",
                                            },
                                        }
                                    )
                                )
                                ws.send(
                                    json.dumps(
                                        {
                                            "type": "table.presence",
                                            "payload": {"members": online_members},
                                        }
                                    )
                                )

                        ws.on_message(received)

                    reference.route_web_socket("**/ws", mock_socket)
                    reference.route("**/api/**", mock_auth)
                    reference.route("**/__gravewright/csrf", mock_auth)
                    reference.goto(reference_url)
                    expect(reference.locator(".gw-shell")).to_be_visible()

                def capture(name):
                    for width, height in [(1440, 1000), (390, 844)]:
                        label = f"{name}-{width}"
                        # Reflow both pages from the same viewport to normalize cached
                        # compositor layers after a modal changes height.
                        page.set_viewport_size({"width": width + 1, "height": height})
                        page.set_viewport_size({"width": width, "height": height})
                        page.mouse.move(0, 0)
                        page.evaluate("document.activeElement?.blur()")
                        # Let CSS transitions settle after mouse/focus changes.
                        page.wait_for_timeout(250)
                        target = output / f"{label}-django.png"
                        page.screenshot(
                            path=str(target),
                            full_page=True,
                            animations="disabled",
                            caret="hide",
                        )
                        if reference:
                            reference.set_viewport_size(
                                {"width": width + 1, "height": height}
                            )
                            reference.set_viewport_size(
                                {"width": width, "height": height}
                            )
                            reference.mouse.move(0, 0)
                            reference.evaluate("document.activeElement?.blur()")
                            reference.wait_for_timeout(250)
                            original = output / f"{label}-original.png"
                            reference.screenshot(
                                path=str(original),
                                full_page=True,
                                animations="disabled",
                                caret="hide",
                            )
                            a, b = (
                                Image.open(target).convert("RGB"),
                                Image.open(original).convert("RGB"),
                            )
                            assert a.size == b.size, (label, a.size, b.size)
                            difference = ImageChops.difference(a, b)
                            changed = sum(
                                1
                                for pixel in difference.get_flattened_data()
                                if max(pixel) > 8
                            )
                            ratio = changed / (a.width * a.height)
                            difference.save(output / f"{label}-diff.png")
                            report.append(
                                {
                                    "screen": label,
                                    "changed_pixel_ratio": ratio,
                                    "exact_match": difference.getbbox() is None,
                                }
                            )
                            print(label, f"{ratio:.6%} pixels differ", flush=True)
                    page.set_viewport_size({"width": 1440, "height": 1000})
                    if reference:
                        reference.set_viewport_size({"width": 1440, "height": 1000})

                def component(name, selector):
                    if not reference:
                        return
                    # Isolate translucent controls from differing live camera/fog backgrounds.
                    # Full-scene rendering is compared separately by capture('map').
                    for target_page in (page, reference):
                        target_page.locator(".game-table__stage").evaluate(
                            "el=>el.style.visibility='hidden'"
                        )
                    page.mouse.move(0, 0)
                    reference.mouse.move(0, 0)
                    page.wait_for_timeout(150)
                    reference.wait_for_timeout(150)
                    target = output / (name + "-django.png")
                    original = output / (name + "-original.png")
                    page.locator(selector).screenshot(
                        path=str(target), animations="disabled"
                    )
                    reference.locator(selector).screenshot(
                        path=str(original), animations="disabled"
                    )
                    a, b = (
                        Image.open(target).convert("RGB"),
                        Image.open(original).convert("RGB"),
                    )
                    assert a.size == b.size, (name, a.size, b.size)
                    diff = ImageChops.difference(a, b)
                    diff.save(output / (name + "-diff.png"))
                    ratio = sum(
                        1 for pixel in diff.get_flattened_data() if max(pixel) > 8
                    ) / (a.width * a.height)
                    report.append(
                        {
                            "screen": name,
                            "changed_pixel_ratio": ratio,
                            "exact_match": diff.getbbox() is None,
                        }
                    )
                    print(name, f"{ratio:.6%} pixels differ", flush=True)
                    for target_page in (page, reference):
                        target_page.locator(".game-table__stage").evaluate(
                            "el=>el.style.visibility=''"
                        )

                def reload_reference():
                    if not reference:
                        return
                    reference.goto(reference_url)
                    reference.wait_for_timeout(300)
                    if reference.get_by_role(
                        "button", name="Open The Lost Keep", exact=True
                    ).count():
                        reference.get_by_role(
                            "button", name="Open The Lost Keep", exact=True
                        ).click()
                        reference.get_by_role(
                            "button", name="Enter table", exact=True
                        ).click()
                    seated(reference)
                    expect(reference.locator(".game-board canvas")).to_be_visible(
                        timeout=20000
                    )

                def both(name):
                    page.get_by_role("button", name=name, exact=True).click()
                    if reference:
                        reference.get_by_role("button", name=name, exact=True).click()

                def post(target_page, path, data):
                    token = next(
                        c["value"]
                        for c in target_page.context.cookies()
                        if c["name"] == "gravewright-csrf"
                    )
                    return target_page.request.post(
                        base + path, data=data, headers={"X-CSRF-Token": token}
                    )

                def seated(target):
                    expect(target.locator(".game-menubar__presence")).to_have_attribute(
                        "data-presence", "seated", timeout=15000
                    )

                def echo(text, name, identifier):
                    if reference:
                        reference_sockets[-1].send(
                            json.dumps(
                                {
                                    "type": "chat.message",
                                    "payload": {
                                        "id": str(identifier),
                                        "mapId": "",
                                        "tableId": rows[0]["id"],
                                        "from": {"name": name},
                                        "text": text,
                                        "at": identifier,
                                    },
                                }
                            )
                        )

                page.get_by_role("button", name="Begin my first journey").click()
                page.get_by_placeholder("Campaign name").fill("The Lost Keep")
                page.get_by_role("button", name="Create table", exact=True).click()
                expect(page.get_by_role("dialog")).to_have_count(0)
                rows = page.request.get(base + "/api/containers").json()
                invitation = post(
                    page, "/api/containers/" + rows[0]["id"] + "/invitation", {}
                ).json()["code"]
                page.get_by_role(
                    "button", name="Open The Lost Keep", exact=True
                ).click()
                page.get_by_role("button", name="Enter table", exact=True).click()
                seated(page)
                page.wait_for_function("document.querySelector('#table-workspace').dataset.onboardingReady==='true'")
                if page.get_by_role('button',name='Dismiss checklist',exact=True).is_visible():
                    page.get_by_role('button',name='Dismiss checklist',exact=True).click()
                if reference:
                    reference.reload()
                    reference.get_by_role(
                        "button", name="Open The Lost Keep", exact=True
                    ).click()
                    reference.get_by_role(
                        "button", name="Enter table", exact=True
                    ).click()
                    seated(reference)
                both("Scenes")
                capture("directory")
                both("New scene")
                capture("upload")
                if reference:
                    reference.get_by_role(
                        "dialog", name="New scene", exact=True
                    ).get_by_role("button", name="Close", exact=True).click()
                dialog = page.get_by_role("dialog", name="New scene", exact=True)
                dialog.locator("[name=name]").fill("The keep")
                picture = BytesIO()
                Image.new("RGB", (1024, 768), "#354b66").save(picture, "PNG")
                dialog.locator("input[type=file]").set_input_files(
                    {
                        "name": "keep.png",
                        "mimeType": "image/png",
                        "buffer": picture.getvalue(),
                    }
                )
                dialog.get_by_role("button", name="Upload map", exact=True).click()
                expect(dialog).to_have_count(0, timeout=30000)
                expect(page.locator(".game-board canvas")).to_be_visible(timeout=20000)
                expect(page.locator("[data-map-render-error]")).to_be_hidden()
                map_state = page.request.get(
                    base + "/api/containers/" + rows[0]["id"] + "/scenes"
                ).json()
                if reference:
                    reference.goto(reference_url)
                    reference.wait_for_timeout(500)
                    if reference.get_by_role(
                        "button", name="Open The Lost Keep", exact=True
                    ).count():
                        reference.get_by_role(
                            "button", name="Open The Lost Keep", exact=True
                        ).click()
                        reference.get_by_role(
                            "button", name="Enter table", exact=True
                        ).click()
                    seated(reference)
                    expect(reference.locator(".game-board canvas")).to_be_visible(
                        timeout=20000
                    )
                    reference.get_by_role("button", name="Scenes", exact=True).click()
                page.wait_for_timeout(1500)
                # Verify real decoded map pixels as well as visual parity: two failed
                # renderers must not be mistaken for a successful comparison.
                v = page.evaluate("window.gravewrightMaps.board.viewport()")
                surface = page.locator(".game-board__surface").bounding_box()
                screenshot = Image.open(BytesIO(page.screenshot())).convert("RGB")
                pixel = screenshot.getpixel(
                    (
                        round(surface["x"] + v["x"] + 80 * v["scale"]),
                        round(surface["y"] + v["y"] + 80 * v["scale"]),
                    )
                )
                assert max(abs(a - b) for a, b in zip(pixel, (53, 75, 102))) < 4, pixel
                capture("map")
                page.locator(".game-directory__scene").click(button="right")
                page.get_by_role("menuitem", name="Edit", exact=True).click()
                if reference:
                    reference.locator(".game-directory__scene").click(button="right")
                    reference.get_by_role("button", name="Edit", exact=True).click()
                capture("settings")
                settings = page.get_by_role("dialog", name="Edit scene", exact=True)
                settings.locator("[data-calibrate]").click()
                expect(page.locator(".grid-calibration")).to_be_visible()
                viewport = page.evaluate("window.gravewrightMaps.board.viewport()")
                surface = page.locator(".game-board__surface").bounding_box()
                for x, y in [(64, 192), (320, 384), (704, 576)]:
                    sx = surface["x"] + viewport["x"] + x * viewport["scale"]
                    sy = surface["y"] + viewport["y"] + y * viewport["scale"]
                    page.mouse.move(sx, sy)
                    page.mouse.down()
                    page.mouse.move(
                        sx + 64 * viewport["scale"],
                        sy + 64 * viewport["scale"],
                        steps=4,
                    )
                    page.mouse.up()
                expect(page.locator("[data-calibration=apply]")).to_be_enabled()
                page.locator("[data-calibration=apply]").click()
                expect(settings.get_by_label("Grid size", exact=True)).to_have_value(
                    "64"
                )
                settings.get_by_label("Measurement unit", exact=True).fill("m")
                settings.get_by_role("button", name="Save scene", exact=True).click()
                expect(settings).to_have_count(0)
                page.wait_for_timeout(300)
                assert (
                    page.request.get(
                        base + "/api/containers/" + rows[0]["id"] + "/scenes"
                    ).json()["maps"][0]["gridSize"]
                    == 64
                )
                # Camera interactions run through the original Pixi controller.
                before = page.evaluate("window.gravewrightMaps.board.viewport()")
                page.mouse.move(700, 400)
                page.mouse.wheel(0, -200)
                page.wait_for_timeout(100)
                after = page.evaluate("window.gravewrightMaps.board.viewport()")
                assert after["scale"] > before["scale"]
                page.mouse.down(button="right")
                page.mouse.move(760, 430, steps=4)
                page.mouse.up(button="right")
                assert (
                    page.evaluate("window.gravewrightMaps.board.viewport().x")
                    != after["x"]
                )
                # Player follows publication, loses both canvas and file access on GM-only changes.
                player_context = browser.new_context(
                    viewport={"width": 1440, "height": 1000}
                )
                player = player_context.new_page()
                player.on(
                    "pageerror", lambda error: errors.append("player: " + (error.stack or str(error)))
                )
                player.goto(base + "/register")
                player.locator("#owner-name").fill("Browser Player")
                player.locator("#owner-email").fill("player@example.test")
                player.locator("#owner-password").fill(PASSWORD)
                player.get_by_role(
                    "button", name="Create my account", exact=True
                ).click()
                player.get_by_placeholder("XXXX-XXXX", exact=True).fill(invitation)
                player.get_by_role("button", name="Join a table", exact=True).click()
                player.get_by_role(
                    "button", name="Open The Lost Keep", exact=True
                ).click()
                player.get_by_role("button", name="Enter table", exact=True).click()
                seated(player)
                player.wait_for_function("document.querySelector('#table-workspace').dataset.onboardingReady==='true'")
                player.keyboard.press('Escape')
                expect(player.locator(".game-board canvas")).to_be_visible(
                    timeout=20000
                )
                current = page.request.get(
                    base + "/api/containers/" + rows[0]["id"] + "/scenes"
                ).json()["maps"][0]
                # Draw a door through the migrated dock; the player operates it over WebSocket.
                page.locator("#maps-panel [aria-label=Close]").click()
                page.get_by_role("group", name="Layers", exact=True).get_by_role(
                    "button", name="Walls", exact=True
                ).click()
                map_state = page.request.get(
                    base + "/api/containers/" + rows[0]["id"] + "/scenes"
                ).json()
                reload_reference()
                # Compare the newly connected original drawing/measurement controls.
                for target_page in (page, reference):
                    if target_page:
                        target_page.get_by_role('group',name='Layers',exact=True).get_by_role('button',name='Game',exact=True).click()
                        target_page.get_by_role('button',name='Draw',exact=True).first.click()
                component('drawing-tools','.drawing-paint')
                both('Close drawing')
                both('Measure')
                component('measurement-tools','.measure-panel')
                both('Close measurement')
                if args.tools_only:
                    (output/'tools-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
                    assert all(item['changed_pixel_ratio'] < .001 for item in report),report
                    assert not errors,errors
                    browser.close()
                    print('Map tools visual comparison passed.',flush=True)
                    return
                for target_page in (page, reference):
                    if target_page:
                        target_page.get_by_role('group',name='Layers',exact=True).get_by_role('button',name='Walls',exact=True).click()
                page.locator("[data-wall-tool=wall]").click()
                if reference:
                    reference.get_by_role(
                        "group", name="Layers", exact=True
                    ).get_by_role("button", name="Walls", exact=True).click()
                    reference.locator("[data-wall-tool=wall]").click()
                component("wall-picker", ".wall-picker")
                page.get_by_role("dialog", name="Wall types").get_by_role(
                    "button", name="Close picker"
                ).click()
                if reference:
                    reference.get_by_role("dialog", name="Wall types").get_by_role(
                        "button", name="Close picker"
                    ).click()
                page.locator("[data-wall-tool=door]").click()
                page.mouse.move(480, 310)
                page.mouse.down()
                page.mouse.move(610, 310, steps=5)
                page.mouse.up()
                expect(player.locator(".door-controls [role=button]")).to_have_count(1)
                player.locator(".door-controls [role=button]").click()
                expect(page.locator(".door-controls [role=button]")).to_have_attribute(
                    "aria-label", "Porta open"
                )
                page.get_by_role("group", name="Layers", exact=True).get_by_role(
                    "button", name="Lighting", exact=True
                ).click()
                page.locator("[data-effect-tool=light]").click()
                if reference:
                    reference.get_by_role(
                        "group", name="Layers", exact=True
                    ).get_by_role("button", name="Lighting", exact=True).click()
                    reference.locator("[data-effect-tool=light]").click()
                component("light-picker", ".light-picker")
                page.get_by_role("dialog", name="Light types").get_by_role(
                    "button", name="Steady", exact=True
                ).click()
                page.mouse.click(700, 410)
                expect(page.locator("[data-effect-kind=light]")).to_have_count(1)
                page.locator("[data-effect-kind=light]").dblclick()
                expect(page.get_by_role("dialog", name="Light source")).to_be_visible()
                reload_reference()
                if reference:
                    reference.get_by_role(
                        "group", name="Layers", exact=True
                    ).get_by_role("button", name="Lighting", exact=True).click()
                    origin = reference.locator(
                        "[data-effect-kind=light]"
                    ).bounding_box()
                    reference.mouse.dblclick(
                        origin["x"] + origin["width"] / 2,
                        origin["y"] + origin["height"] / 2,
                    )
                component("light-editor", ".light-editor")
                if reference:
                    reference.get_by_role("dialog", name="Light source").get_by_role(
                        "button", name="Close", exact=True
                    ).click()
                page.get_by_role("dialog", name="Light source").get_by_role(
                    "button", name="Close", exact=True
                ).click()
                page.get_by_role("button", name="Scene visibility", exact=True).click()
                if reference:
                    reference.get_by_role(
                        "button", name="Scene visibility", exact=True
                    ).click()
                component("visibility", ".visibility-panel")
                page.get_by_role("button", name="Manual lighting", exact=True).click()
                page.get_by_role("button", name="Hide all", exact=True).click()
                expect(page.locator(".fog-workspace")).to_be_visible()
                expect(page.locator(".visibility-panel fieldset")).to_be_enabled()
                page.mouse.click(900, 500)
                page.wait_for_timeout(400)
                layer_state = page.request.get(
                    base + "/api/maps/" + current["id"] + "/state"
                ).json()
                assert (
                    len(layer_state["lights"]) == 1
                    and len(layer_state["fog"]["ops"]) == 1
                ), layer_state
                assert (
                    player.request.get(
                        base + "/api/maps/" + current["id"] + "/state"
                    ).json()["fog"]["ops"]
                    == layer_state["fog"]["ops"]
                )
                reload_reference()
                if reference:
                    reference.get_by_role(
                        "group", name="Layers", exact=True
                    ).get_by_role("button", name="Lighting", exact=True).click()
                    reference.get_by_role(
                        "button", name="Scene visibility", exact=True
                    ).click()
                component("manual-lighting", ".visibility-panel")
                page.evaluate(
                    "p=>window.gravewrightRealtime.mapCommand('update',p)",
                    {
                        "mapId": current["id"],
                        "version": current["version"],
                        "settings": {"visibility": "gm"},
                    },
                )
                try:
                    expect(player.locator(".game-board canvas")).to_have_count(0)
                except AssertionError:
                    print("Browser errors:", errors, flush=True)
                    print(
                        "Player scene:",
                        player.evaluate(
                            '({current:window.gravewrightMaps.current, connected:document.querySelector(".game-menubar__presence").dataset.presence})'
                        ),
                        flush=True,
                    )
                    raise
                assert (
                    player.request.get(
                        base + "/api/maps/" + current["id"] + "/tiles/0/0/0"
                    ).status
                    == 404
                )
                page.evaluate(
                    "p=>window.gravewrightRealtime.mapCommand('delete',p)",
                    {"mapId": current["id"]},
                )
                expect(page.locator(".game-board canvas")).to_have_count(0)
                assert not errors, errors
                browser.close()
            (output / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
            assert all(item["changed_pixel_ratio"] < 0.001 for item in report), report
            print(
                "Browser map upload, camera, publication and access flows passed; development database untouched.",
                flush=True,
            )
        finally:
            server.terminate()
            server.wait(timeout=10)
            log.close()
            if reference_server:
                reference_server.shutdown()
                reference_server.server_close()


if __name__ == "__main__":
    main()
