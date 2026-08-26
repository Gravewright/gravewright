from __future__ import annotations

import contextlib
import os
import subprocess
import sys

import pytest
from playwright.sync_api import expect, sync_playwright

import app.persistence.database as db_module
from app.persistence import engine as engine_module
from tests.conftest import seed_member, seed_user
from tests.e2e.test_app_server_e2e import (
    GM_EMAIL,
    GM_PASSWORD,
    PLAYER_EMAIL,
    PLAYER_PASSWORD,
    REPO_ROOT,
    _free_port,
    _seed_database,
    _wait_http_ready,
)


@pytest.fixture(scope="module")
def four_client_server(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("four-client-e2e")
    db_path = tmp_dir / "session.sqlite3"
    seeded = _seed_database(db_path)
    db_module.DATABASE_PATH = db_path.resolve()
    db_module._initialized = False
    engine_module.reset_engine()
    player_b = seed_user(name="Player B", email="player-b-e2e@test.com")
    player_c = seed_user(name="Player C", email="player-c-e2e@test.com")
    seed_member(seeded["campaign_id"], player_b, "player")
    seed_member(seeded["campaign_id"], player_c, "player")
    from app.persistence.repositories.actor_repository import ActorRepository
    from app.persistence.repositories.scene_repository import SceneRepository
    from app.persistence.repositories.token_repository import TokenRepository
    from tests.conftest import seed_scene

    scene = seed_scene(seeded["campaign_id"], name="Four-client Crypt")
    SceneRepository().set_active_scene(campaign_id=seeded["campaign_id"], scene_id=scene["id"])
    ActorRepository().add_owner(actor_id=seeded["actor_id"], user_id=seeded["player_id"])
    player_token = TokenRepository().create(
        scene_id=scene["id"], actor_id=seeded["actor_id"], grid_x=1, grid_y=1,
        name="Player Token", controlled_by_role="owner",
    )
    hidden_token = TokenRepository().create(
        scene_id=scene["id"], actor_id=None, grid_x=4, grid_y=4,
        name="Hidden Stalker", controlled_by_role="gm", hidden=True,
    )
    enemy_actor = ActorRepository().create(
        campaign_id=seeded["campaign_id"], system_id="test", actor_type="npc",
        name="Crypt Ghoul", created_by_user_id=seeded["gm_id"],
    )
    enemy_token = TokenRepository().create(
        scene_id=scene["id"], actor_id=enemy_actor, grid_x=6, grid_y=4,
        name="Crypt Ghoul", controlled_by_role="gm",
    )
    seeded.update(scene_id=scene["id"], player_token=player_token["id"],
                  hidden_token=hidden_token["id"], enemy_actor=enemy_actor,
                  enemy_token=enemy_token["id"])
    engine_module.reset_engine()

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update({
        "APP_ENV": "test",
        "DATABASE_URL": f"sqlite:///{db_path.resolve().as_posix()}",
        "ALLOWED_HOSTS": "*",
        "WS_ALLOWED_ORIGINS": base_url,
        "SESSION_COOKIE_SECURE": "false",
        "ALLOW_METADATA_BOOTSTRAP": "true",
        "GRAVEWRIGHT_TEST_TEMP_ROOT": str(tmp_dir.resolve()),
    })
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(REPO_ROOT), env=env,
    )
    try:
        _wait_http_ready(f"{base_url}/login", proc=proc)
        yield {"base_url": base_url, "player_b": player_b, "player_c": player_c, **seeded}
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=10)
        if proc.poll() is None:
            proc.kill()


def _login(page, base, email):
    page.goto(f"{base}/login")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').fill(GM_PASSWORD)
    page.locator('button[type="submit"]').click()
    page.wait_for_url(f"{base}/inside")


def test_gm_plus_three_players_journal_chat_and_dice(four_client_server):
    s = four_client_server
    base = s["base_url"]
    url = f"{base}/game?room={s['campaign_id']}"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        contexts = [browser.new_context(reduced_motion="reduce") for _ in range(4)]
        try:
            gm, player_a, player_b, player_c = [ctx.new_page() for ctx in contexts]
            for page, email in zip(
                (gm, player_a, player_b, player_c),
                (GM_EMAIL, PLAYER_EMAIL, "player-b-e2e@test.com", "player-c-e2e@test.com"),
            ):
                _login(page, base, email)
                page.goto(url)
            close = gm.locator("[data-onboarding-close]")
            if close.count():
                close.first.click()
            for player in (player_a, player_b, player_c):
                player.reload()
            for page in (gm, player_a, player_b, player_c):
                page.wait_for_function("window.GravewrightRealtime?.isOpen?.() === true")

            # The private journal starts invisible to every player.
            journal = f'.journal-card[data-journal-id="{s["journal_id"]}"]'
            for player in (player_a, player_b, player_c):
                expect(player.locator(journal)).to_have_count(0)

            # GM grants read only to A through the real authenticated browser session.
            status = gm.evaluate(
                """async d => { const body = new URLSearchParams({resource_type:'journal', resource_id:d.journal});
                body.set(`access__${d.player}`, 'read'); const r = await fetch('/game/resource-permissions', {
                method:'POST', credentials:'same-origin', headers:{'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded','x-csrftoken':window.csrfToken()}, body}); return r.status; }""",
                {"journal": s["journal_id"], "player": s["player_id"]},
            )
            assert status == 200
            for player in (player_a, player_b, player_c):
                player.reload()
            expect(player_a.locator(journal)).to_have_count(1)
            expect(player_b.locator(journal)).to_have_count(0)
            expect(player_c.locator(journal)).to_have_count(0)
            player_a.locator(f'[data-panel-toggle="panel-journal-{s["campaign_id"]}"]').click()
            player_a.locator(journal).click()
            expect(player_a.locator(f'[data-modal-id="journal-{s["journal_id"]}"]')).to_be_visible()

            # A public chat line and a public die roll reach all four clients.
            gm.locator(f'[data-panel-toggle="panel-chat-{s["campaign_id"]}"]').click()
            form = gm.locator("[data-chat-form]:visible")
            form.locator('textarea[name="message"]').fill("A porta da cripta se abre.")
            form.locator('button[type="submit"]').click()
            for page in (gm, player_a, player_b, player_c):
                expect(page.get_by_text("A porta da cripta se abre.", exact=True)).to_be_attached()

            gm.locator(f'[data-modal-open="dice-tray-{s["campaign_id"]}"]').click()
            tray = gm.locator(f'[data-modal-id="dice-tray-{s["campaign_id"]}"]')
            tray.locator("[data-dice-formula]").fill("1d20")
            tray.locator('[data-dice-roll="public"]').click()
            for page in (gm, player_a, player_b, player_c):
                expect(page.locator(".chat-message--roll").last).to_be_attached(timeout=10_000)
        finally:
            for context in contexts:
                with contextlib.suppress(Exception):
                    context.close()
            browser.close()


def test_four_clients_items_tokens_combat_lights_and_shaders(four_client_server):
    s = four_client_server
    base, room = s["base_url"], s["campaign_id"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        contexts = [browser.new_context(reduced_motion="reduce") for _ in range(4)]
        errors = [[] for _ in range(4)]
        try:
            pages = [ctx.new_page() for ctx in contexts]
            gm, player_a, player_b, player_c = pages
            for index, (page, email) in enumerate(zip(pages, (GM_EMAIL, PLAYER_EMAIL, "player-b-e2e@test.com", "player-c-e2e@test.com"))):
                page.on("pageerror", lambda error, bucket=errors[index]: bucket.append(str(error)))
                _login(page, base, email)
                page.goto(f"{base}/game?room={room}")
            close = gm.locator("[data-onboarding-close]")
            if close.count(): close.first.click()
            for player in pages[1:]: player.reload()
            for page in pages: page.wait_for_function("window.GravewrightRealtime?.isOpen?.() === true")

            # Item permission is reflected in the actual player directory, and isolated to A.
            item = f'[data-item-card="{s["item_id"]}"]'
            for player in pages[1:]: expect(player.locator(item)).to_have_count(0)
            status = gm.evaluate("""async d=>{const b=new URLSearchParams({resource_type:'item',resource_id:d.item});b.set(`access__${d.player}`,'read');const r=await fetch('/game/resource-permissions',{method:'POST',credentials:'same-origin',headers:{'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded','x-csrftoken':csrfToken()},body:b});return r.status}""", {"item":s["item_id"],"player":s["player_id"]})
            assert status == 200
            for player in pages[1:]: player.reload()
            expect(player_a.locator(item)).to_have_count(1)
            expect(player_b.locator(item)).to_have_count(0)
            expect(player_c.locator(item)).to_have_count(0)
            player_a.locator(f'[data-panel-toggle="panel-items-{room}"]').click()
            expect(player_a.locator(item)).to_be_visible()

            # Hidden GM token is in the GM projection only; normal token is visible to all.
            token_ids_js = """async scene=>{const r=await fetch(`/game/scenes/${scene}/tokens`);const j=await r.json();return j.tokens.map(x=>x.id||x.token_id)}"""
            gm_ids = gm.evaluate(token_ids_js, s["scene_id"])
            assert s["hidden_token"] in gm_ids and s["player_token"] in gm_ids
            for player in pages[1:]:
                ids = player.evaluate(token_ids_js, s["scene_id"])
                assert s["hidden_token"] not in ids and s["player_token"] in ids

            # Player A moves its owned token through the real websocket; all four snapshots converge.
            player_a.evaluate("d=>GravewrightRealtime.sendCommand('token.move',{scene_id:d.scene,token_id:d.token,grid_x:3,grid_y:2},{sceneId:d.scene,roomId:d.room})", {"scene":s["scene_id"],"token":s["player_token"],"room":room})
            snapshot_js = """async d=>{const r=await fetch(`/game/scenes/${d.scene}/tokens`);const j=await r.json();const t=j.tokens.find(x=>(x.id||x.token_id)===d.token);return t&&[t.grid_x,t.grid_y]}"""
            for page in pages:
                page.wait_for_function("async d=>{const r=await fetch(`/game/scenes/${d.scene}/tokens`);const j=await r.json();const t=j.tokens.find(x=>(x.id||x.token_id)===d.token);return t?.grid_x===3&&t?.grid_y===2}", arg={"scene":s["scene_id"],"token":s["player_token"]})
                assert page.evaluate(snapshot_js, {"scene":s["scene_id"],"token":s["player_token"]}) == [3, 2]

            # Combat starts and turn changes are broadcast into every visible combat panel.
            combat = gm.evaluate("""async d=>{const r=await fetch('/game/combat/start',{method:'POST',credentials:'same-origin',headers:{'Accept':'application/json','Content-Type':'application/json','x-csrftoken':csrfToken()},body:JSON.stringify({campaign_id:d.room,scene_id:d.scene,actor_ids:[d.hero,d.enemy]})});return {status:r.status,body:await r.json()}}""", {"room":room,"scene":s["scene_id"],"hero":s["actor_id"],"enemy":s["enemy_actor"]})
            assert combat["status"] == 200 and combat["body"]["active"]
            for page in pages:
                page.locator(f'[data-panel-toggle="panel-combat-{room}"]').click()
                expect(page.locator(f'[data-combat-panel][data-room-id="{room}"]')).to_contain_text("E2E Actor")
                expect(page.locator(f'[data-combat-panel][data-room-id="{room}"]')).to_contain_text("Crypt Ghoul")
            first = combat["body"]["combatants"][0]["id"]
            updated = gm.evaluate("""async d=>{const r=await fetch('/game/combat/turn',{method:'POST',credentials:'same-origin',headers:{'Accept':'application/json','Content-Type':'application/json','x-csrftoken':csrfToken()},body:JSON.stringify({campaign_id:d.room,combatant_id:d.id})});return r.json()}""", {"room":room,"id":first})
            for page in pages:
                page.wait_for_function("d=>document.querySelector(`[data-combat-panel][data-room-id='${d.room}']`)?.textContent.includes(d.name)", arg={"room":room,"name":updated["current_name"]})

            # Create, disable and re-enable light + shader, checking every client's runtime state.
            light = gm.evaluate("""async d=>{const r=await fetch('/game/lights',{method:'POST',credentials:'same-origin',headers:{'Accept':'application/json','Content-Type':'application/json','x-csrftoken':csrfToken()},body:JSON.stringify({campaign_id:d.room,scene_id:d.scene,x:140,y:140,bright_radius:140,dim_radius:280,color:'#ffaa33',intensity:1,enabled:true})});return {status:r.status,body:await r.json()}}""", {"room":room,"scene":s["scene_id"]})
            assert light["status"] == 201
            light_id = light["body"]["light"]["id"]
            shader = gm.evaluate("""async d=>{const presets=await fetch('/game/shader-presets').then(r=>r.json());const p=presets.presets[0];const r=await fetch('/game/shaders/apply-preset',{method:'POST',credentials:'same-origin',headers:{'Accept':'application/json','Content-Type':'application/json','x-csrftoken':csrfToken()},body:JSON.stringify({campaign_id:d.room,scene_id:d.scene,preset_id:p.id,schema_version:p.schemaVersion||p.schema_version||1,x:210,y:210})});return {preset:p,status:r.status,body:await r.json()}}""", {"room":room,"scene":s["scene_id"]})
            assert shader["status"] == 201
            shader_id = (shader["body"].get("instance") or shader["body"].get("shader"))["id"]
            state_js = """async d=>{const [l,s]=await Promise.all([fetch(`/game/lights/${d.scene}?campaign_id=${d.room}`).then(r=>r.json()),fetch(`/game/shaders/${d.scene}?campaign_id=${d.room}`).then(r=>r.json())]);return {light:l.lights.find(x=>x.id===d.light)?.enabled,shader:s.shaders.find(x=>x.id===d.shader)?.enabled}}"""
            for page in pages:
                page.wait_for_function("async d=>{const x=await (" + state_js + ")(d);return x.light===true&&x.shader===true}", arg={"room":room,"scene":s["scene_id"],"light":light_id,"shader":shader_id})
            for endpoint, key, identifier in (("/game/lights/update","light_id",light_id),("/game/shaders/update","shader_id",shader_id)):
                result = gm.evaluate("""async d=>{const r=await fetch(d.endpoint,{method:'POST',credentials:'same-origin',headers:{'Accept':'application/json','Content-Type':'application/json','x-csrftoken':csrfToken()},body:JSON.stringify({campaign_id:d.room,[d.key]:d.id,enabled:false})});return r.status}""", {"endpoint":endpoint,"room":room,"key":key,"id":identifier})
                assert result == 200
            for page in pages:
                page.wait_for_function("async d=>{const x=await (" + state_js + ")(d);return x.light===false&&x.shader===false}", arg={"room":room,"scene":s["scene_id"],"light":light_id,"shader":shader_id})
            assert not any(errors), errors
        finally:
            for context in contexts:
                with contextlib.suppress(Exception): context.close()
            browser.close()


def test_game_decision_modals_share_the_same_usable_visual_language(four_client_server):
    s = four_client_server
    base, room = s["base_url"], s["campaign_id"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
        page = context.new_page()
        try:
            _login(page, base, GM_EMAIL)
            page.goto(f"{base}/game?room={room}")
            close = page.locator("[data-onboarding-close]")
            if close.count(): close.first.click()

            page.locator(f'[data-panel-toggle="panel-journal-{room}"]').click()
            page.locator(f'.journal-card[data-journal-id="{s["journal_id"]}"]').click()
            journal = page.locator(f'[data-modal-id="journal-{s["journal_id"]}"]')
            journal.locator('[data-resource-permissions="journal"]').click()
            permissions = page.locator(f'[data-modal-id="resource-permissions-journal-{s["journal_id"]}"]')
            expect(permissions).to_be_visible()
            expect(permissions.locator(".resource-permissions-intro")).to_be_visible()
            expect(permissions.locator(".resource-permission-row")).to_have_count(3)
            assert permissions.bounding_box()["width"] <= 660
            permissions.locator("[data-modal-close]").click()

            journal.locator('[data-handout-resource="journal"]').click()
            handout = page.locator(f'[data-handout-dialog][data-campaign-id="{room}"]')
            expect(handout).to_be_visible()
            expect(handout.locator(".modal-heading")).to_be_visible()
            expect(handout.locator(".permission-choice--player")).to_have_count(3)
            expect(handout.locator('input[name="players"]').first).to_be_disabled()
            handout.locator('input[name="all_players"]').uncheck()
            expect(handout.locator('input[name="players"]').first).to_be_enabled()
            handout.locator("[data-handout-close]").first.click()
            journal.locator("[data-modal-close]").click()

            page.locator(f'[data-modal-open="panel-hand-{room}"]').click()
            page.locator(f'[data-modal-open="panel-cards-{room}"]').last.click()
            cards = page.locator(f'[data-modal-id="panel-cards-{room}"]')
            drawer = cards.locator(".cards-create-drawer")
            expect(drawer).not_to_have_attribute("open", "")
            drawer.locator("summary").click()
            expect(drawer).to_have_attribute("open", "")
            expect(drawer.locator("[data-card-create-form]")).to_be_visible()

            # The same decision surface stays inside a narrow game viewport.
            page.set_viewport_size({"width": 480, "height": 720})
            journal.locator('[data-handout-resource="journal"]').evaluate("button => button.click()")
            expect(handout).to_be_visible()
            box = handout.bounding_box()
            assert box and box["x"] >= 0 and box["y"] >= 0
            assert box["x"] + box["width"] <= 480 and box["y"] + box["height"] <= 720
        finally:
            context.close()
            browser.close()


def test_editing_scene_updates_the_same_instance(four_client_server):
    s = four_client_server
    base, room, scene_id = s["base_url"], s["campaign_id"], s["scene_id"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(reduced_motion="reduce")
        page = context.new_page()
        try:
            _login(page, base, GM_EMAIL)
            page.goto(f"{base}/game?room={room}")
            close = page.locator("[data-onboarding-close]")
            if close.count(): close.first.click()
            page.locator(f'[data-panel-toggle="panel-scenes-{room}"]').click()
            cards = page.locator(f'[data-scene-panel][data-room-id="{room}"] .scene-card[data-scene-id]')
            before_ids = cards.evaluate_all("nodes => nodes.map(node => node.dataset.sceneId)")
            before_canvases = page.locator(f'[data-map-canvas][data-room-id="{room}"]').count()

            page.evaluate("id => { const button=document.createElement('button'); button.dataset.sceneEdit=id; document.body.appendChild(button); button.click(); button.remove(); }", scene_id)
            modal = page.locator(f'[data-modal-id="scene-edit-{scene_id}"]')
            expect(modal).to_be_visible()
            modal.locator('input[name="grid_color"]').evaluate("input => { input.value='#ff3366'; input.dispatchEvent(new Event('input',{bubbles:true})); input.dispatchEvent(new Event('change',{bubbles:true})); }")
            modal.locator('button[type="submit"]').first.click()
            expect(modal).to_be_hidden()

            after_ids = cards.evaluate_all("nodes => nodes.map(node => node.dataset.sceneId)")
            assert after_ids == before_ids
            assert len(after_ids) == len(set(after_ids))
            assert page.locator(f'[data-map-canvas][data-room-id="{room}"]').count() == before_canvases
            canvas = page.locator(f'[data-map-canvas][data-room-id="{room}"]')
            expect(canvas).to_have_attribute("data-scene-id", scene_id)
            expect(canvas).to_have_attribute("data-scene-grid-color", "#ff3366")
        finally:
            context.close()
            browser.close()


def test_gm_can_map_grid_from_three_visual_samples(four_client_server):
    s = four_client_server
    base, room, scene_id = s["base_url"], s["campaign_id"], s["scene_id"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
        page = context.new_page()
        try:
            _login(page, base, GM_EMAIL)
            page.goto(f"{base}/game?room={room}")
            close = page.locator("[data-onboarding-close]")
            if close.count(): close.first.click()
            page.evaluate("id => { const button=document.createElement('button'); button.dataset.sceneEdit=id; document.body.appendChild(button); button.click(); button.remove(); }", scene_id)
            modal = page.locator(f'[data-modal-id="scene-edit-{scene_id}"]')
            expect(modal).to_be_visible()
            modal.locator("[data-grid-mapper-start]").click()
            expect(page.locator(".scene-grid-mapper-overlay")).to_be_visible()

            camera_before = page.evaluate("() => ({...GravewrightMap.stateFor(GravewrightMap.activeCanvas())})")
            page.mouse.move(900, 500)
            page.mouse.wheel(0, -240)
            page.wait_for_function("before => GravewrightMap.stateFor(GravewrightMap.activeCanvas()).zoom > before", arg=camera_before["zoom"])
            zoomed = page.evaluate("() => ({...GravewrightMap.stateFor(GravewrightMap.activeCanvas())})")
            page.mouse.move(900, 500)
            page.mouse.down(button="right")
            page.mouse.move(940, 530, steps=4)
            page.mouse.up(button="right")
            panned = page.evaluate("() => ({...GravewrightMap.stateFor(GravewrightMap.activeCanvas())})")
            assert panned["offsetX"] != zoomed["offsetX"]
            assert panned["offsetY"] != zoomed["offsetY"]

            calibrated = page.evaluate("""() => GravewrightGridMapper.calculateCalibration([
                {x:8,y:12,width:70.1,height:69.5},
                {x:8+50*69.72,y:12+35*69.72,width:69.2,height:70.3},
                {x:8+100*69.72,y:12+70*69.72,width:70.4,height:69.1}
            ])""")
            assert abs(calibrated["size"] - 69.72) < 0.001
            assert abs(calibrated["offsetX"] - 8) < 0.001
            assert abs(calibrated["offsetY"] - 12) < 0.001
            far_sample = page.evaluate("""() => GravewrightGridMapper.calculateCalibration([
                {x:2499.719,y:100.343,width:100.1,height:99.9},
                {x:1499.663,y:2000.449,width:99.8,height:100.2},
                {x:99.5846,y:3900.555,width:100.0,height:100.1}
            ])""")
            assert 0 <= far_sample["offsetX"] < far_sample["size"]
            assert 0 <= far_sample["offsetY"] < far_sample["size"]
            exact_raster = page.evaluate("""() => GravewrightGridMapper.calculateCalibration([
                {x:0.354,y:0.727,width:99.7,height:100.3},
                {x:1500.2,y:2000.4,width:100.2,height:99.8},
                {x:2899.8,y:3899.6,width:100.2,height:100.4}
            ])""")
            assert exact_raster["size"] == 100
            assert exact_raster["offsetX"] == 0
            assert exact_raster["offsetY"] == 0

            points = page.evaluate("""() => {
                const canvas = GravewrightMap.activeCanvas();
                const state = GravewrightMap.stateFor(canvas);
                const toScreen = (x, y) => ({x: x * state.zoom + state.offsetX, y: y * state.zoom + state.offsetY});
                const rect = canvas.getBoundingClientRect();
                const firstX = Math.ceil(((rect.left + 120 - state.offsetX) / state.zoom) / 70);
                const firstY = Math.ceil(((rect.top + 140 - state.offsetY) / state.zoom) / 70);
                return [[0,0],[2,1],[4,2]].map(([dx,dy]) => {
                    const x = (firstX + dx) * 70, y = (firstY + dy) * 70;
                    return [toScreen(x,y),toScreen(x+70,y+70)];
                });
            }""")
            for start, end in points:
                page.mouse.move(start["x"], start["y"])
                page.mouse.down()
                page.mouse.move(end["x"], end["y"], steps=5)
                page.mouse.up()

            expect(page.locator(".scene-grid-mapper-sample")).to_have_count(3)
            expect(page.locator("[data-grid-mapper-result]")).to_be_visible()
            expect(page.locator(".scene-grid-mapper-preview")).to_be_visible()
            assert page.locator("[data-grid-result-size]").inner_text().endswith("px")
            preview_has_grid = page.locator(".scene-grid-mapper-preview").evaluate("canvas => { const c=canvas.getContext('2d'); return c.getImageData(0,0,canvas.width,canvas.height).data.some(value => value !== 0); }")
            assert preview_has_grid
            anchor_before = page.evaluate("""() => {
                const rect = document.querySelector('.scene-grid-mapper-sample').getBoundingClientRect();
                return GravewrightMap.worldFromScreen(GravewrightMap.activeCanvas(), rect.left, rect.top);
            }""")
            page.mouse.move(850, 520)
            page.mouse.wheel(0, -180)
            page.mouse.down(button="right")
            page.mouse.move(885, 545, steps=4)
            page.mouse.up(button="right")
            page.wait_for_timeout(50)
            anchor_after = page.evaluate("""() => {
                const rect = document.querySelector('.scene-grid-mapper-sample').getBoundingClientRect();
                return GravewrightMap.worldFromScreen(GravewrightMap.activeCanvas(), rect.left, rect.top);
            }""")
            assert abs(anchor_after["worldX"] - anchor_before["worldX"]) < 0.05
            assert abs(anchor_after["worldY"] - anchor_before["worldY"]) < 0.05
            page.locator("[data-grid-mapper-apply]").click()
            expect(modal).to_be_visible()
            assert modal.locator('[name="tile_size"]').input_value() == "70"
            assert modal.locator('[name="grid_offset_x"]').input_value()
            assert modal.locator('[name="grid_offset_y"]').input_value()
        finally:
            context.close()
            browser.close()
