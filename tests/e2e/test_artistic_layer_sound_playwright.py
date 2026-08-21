from __future__ import annotations
import re
import base64,contextlib,os,subprocess,sys
import pytest
from playwright.sync_api import expect,sync_playwright
from tests.e2e.test_app_server_e2e import GM_EMAIL,GM_PASSWORD,PLAYER_EMAIL,PLAYER_PASSWORD,REPO_ROOT,_free_port,_seed_database,_wait_http_ready
from tests.e2e.test_multiplayer_playwright import _close,_login


@pytest.fixture(scope="module")
def sound_server(tmp_path_factory):
    tmp=tmp_path_factory.mktemp("native-sound");db_path=tmp/"e2e.sqlite3";seeded=_seed_database(db_path)
    import app.persistence.database as db_module
    from app.persistence import engine as engine_module
    from app.engine.audio.sound_domain_service import SoundDomainService
    from app.persistence.repositories.asset_repository import AssetRepository
    from app.persistence.repositories.actor_repository import ActorRepository
    from app.persistence.repositories.scene_repository import SceneRepository
    from app.persistence.repositories.token_repository import TokenRepository
    from tests.conftest import seed_scene
    db_module.DATABASE_PATH=db_path.resolve();db_module._initialized=False;engine_module.reset_engine()
    scene=seed_scene(seeded["campaign_id"],name="Sound Scene");seeded["scene_id"]=scene["id"];SceneRepository().set_active_scene(campaign_id=seeded["campaign_id"],scene_id=scene["id"])
    ActorRepository().add_owner(actor_id=seeded["actor_id"],user_id=seeded["player_id"]);token=TokenRepository().create(scene_id=scene["id"],actor_id=seeded["actor_id"],grid_x=1,grid_y=1,controlled_by_role="owner");seeded["listener_token_id"]=token["id"]
    gm_token=TokenRepository().create(scene_id=scene["id"],actor_id=None,grid_x=1,grid_y=1,controlled_by_user_ids=[seeded["gm_id"]],controlled_by_role="gm");seeded["gm_listener_token_id"]=gm_token["id"]
    audio=tmp/"rain.ogg";audio.write_bytes(b"OggS"+b"audio"*64)
    asset=AssetRepository().create(campaign_id=seeded["campaign_id"],owner_user_id=seeded["gm_id"],filename="rain.ogg",content_type="audio/ogg",byte_size=audio.stat().st_size,storage_path=str(audio),hash="e2e")
    image=tmp/"art.png";image.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="));image_asset=AssetRepository().create(campaign_id=seeded["campaign_id"],owner_user_id=seeded["gm_id"],filename="art.png",content_type="image/png",byte_size=image.stat().st_size,storage_path=str(image),hash="image",width=1,height=1)
    upload_audio=tmp/"storm.ogg";upload_audio.write_bytes(b"OggS"+b"storm"*80)
    sound=SoundDomainService().create_sound(campaign_id=seeded["campaign_id"],user_id=seeded["gm_id"],values={"name":"Rain","assetId":asset["id"],"kind":"sound-effect","defaultLoop":True})
    ambient=SoundDomainService().create_sound(campaign_id=seeded["campaign_id"],user_id=seeded["gm_id"],values={"name":"Rain ambience","assetId":asset["id"],"kind":"ambience","defaultLoop":True})
    assert sound.success and ambient.success;seeded["ambient_sound_id"]=ambient.value["id"];engine_module.reset_engine()
    port=_free_port();base=f"http://127.0.0.1:{port}";env=os.environ.copy();env.update({"APP_ENV":"test","DATABASE_URL":f"sqlite:///{db_path.resolve().as_posix()}","ALLOWED_HOSTS":"*","WS_ALLOWED_ORIGINS":base,"SESSION_COOKIE_SECURE":"false","ALLOW_METADATA_BOOTSTRAP":"true","GRAVEWRIGHT_TEST_TEMP_ROOT":str(tmp.resolve())})
    proc=subprocess.Popen([sys.executable,"-m","uvicorn","main:app","--host","127.0.0.1","--port",str(port),"--log-level","warning"],cwd=str(REPO_ROOT),env=env)
    try:_wait_http_ready(f"{base}/login",proc=proc);yield {"base_url":base,"sound_id":sound.value["id"],"image_id":image_asset["id"],"upload_audio":str(upload_audio),**seeded}
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):proc.wait(timeout=10)
        if proc.poll() is None:proc.kill()


def test_artistic_layer_places_and_restores_spatial_sound(sound_server):
    s=sound_server
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);ctx=browser.new_context();page=ctx.new_page()
        page_errors=[];page.on("pageerror",lambda error:page_errors.append(str(error)))
        try:
            _login(page,s["base_url"],GM_EMAIL,GM_PASSWORD);page.goto(f"{s['base_url']}/game?room={s['campaign_id']}")
            close=page.locator("[data-onboarding-close]"); close.first.click() if close.count() else None
            personal_toggle=page.locator("[data-personal-audio-toggle]");expect(personal_toggle).to_be_visible();toggle_box=personal_toggle.bounding_box();assert toggle_box["x"]<80 and toggle_box["y"]>page.viewport_size["height"]-80,toggle_box
            personal_toggle.click();personal=page.locator("[data-personal-audio-popover]");expect(personal).to_be_visible();personal_box=personal.bounding_box();assert personal_box["width"]<=225 and personal_box["height"]<=210,personal_box;expect(personal.locator("[data-mixer-channel]")).to_have_count(3);master=personal.locator('[data-mixer-channel="master"]');ambience=personal.locator('[data-mixer-channel="ambience"]');effects=personal.locator('[data-mixer-channel="sfx"]');master.evaluate("el=>{el.value='.9';el.dispatchEvent(new Event('input',{bubbles:true}));}");ambience.evaluate("el=>{el.value='1';el.dispatchEvent(new Event('input',{bubbles:true}));}");assert page.evaluate("[GravewrightAudioRuntime.preference('master'),GravewrightAudioRuntime.preference('ambience'),GravewrightAudioRuntime.preference('music')]")==[.9,.9,.9];master.evaluate("el=>{el.value='.3';el.dispatchEvent(new Event('input',{bubbles:true}));}");expect(personal.locator('[data-mixer-output="master"]')).to_have_text("30%");expect(ambience).to_have_value("0.3");expect(ambience).to_have_attribute("max","0.3");expect(effects).to_have_value("0.3");expect(effects).to_have_attribute("max","0.3");assert page.evaluate("[GravewrightAudioRuntime.preference('master'),GravewrightAudioRuntime.preference('ambience'),GravewrightAudioRuntime.preference('music'),GravewrightAudioRuntime.preference('sfx')]")==[.3,.3,.3,.3];personal.locator("[data-personal-audio-close]").click();expect(personal).to_be_hidden()
            artistic=page.locator('.room-workspace.is-active [data-active-layer="composition"]');expect(artistic).to_be_visible();artistic.click()
            for domain in ("images","sounds"):expect(page.locator(f'[data-artistic-domain="{domain}"]').first).to_be_attached()
            for domain in ("lights","shaders","particles"):expect(page.locator(f'[data-artistic-domain="{domain}"]')).to_have_count(0)
            page.locator('[data-artistic-domain="sounds"]:visible').click();expect(page.locator("[data-sound-panel]")).to_be_visible();active_tools=page.locator('[data-tool-dock]:not([hidden]) .tool-dock-btn[aria-pressed="true"]:visible');expect(active_tools).to_have_count(1);expect(active_tools).to_have_attribute("data-tool","sound");page.locator('[data-open-sound-modal="ambient"]').click();ambient_modal=page.locator('[data-sound-product-modal="ambient"]:not([hidden])');expect(ambient_modal).to_be_visible();expect(ambient_modal.locator(".sound-mixer-rail,[data-mixer-channel]")).to_have_count(0);ambient_preview=ambient_modal.locator(f'[data-sound-id="{s["ambient_sound_id"]}"] [data-sound-preview]');expect(ambient_preview).to_be_visible()
            with page.expect_response(lambda response:response.url.endswith("/game/sounds/play")) as started_info:ambient_preview.click()
            started=started_info.value.json();assert started["state"] in {"pending-user-unlock","playing"};expect(ambient_preview.locator("i")).to_have_class("ph ph-pause")
            with page.expect_response(lambda response:response.url.endswith("/game/sounds/pause")) as paused_info:ambient_preview.click()
            paused=paused_info.value.json();assert paused["id"]==started["id"] and paused["state"]=="paused";expect(ambient_preview.locator("i")).to_have_class("ph ph-play")
            with page.expect_response(lambda response:response.url.endswith("/game/sounds/play")) as resumed_info:ambient_preview.click()
            resumed=resumed_info.value.json();assert resumed["id"]==started["id"] and resumed["state"]=="playing";expect(ambient_preview.locator("i")).to_have_class("ph ph-pause");ambient_modal.locator("[data-modal-close]").click()
            page.locator('[data-artistic-domain="sounds"]:visible').click();diagnostic=page.evaluate("async id=>{const r=await fetch('/game/sounds/'+id);return [r.status,await r.text()]}",s["campaign_id"]);assert diagnostic[0]==200,diagnostic
            page.locator('[data-open-sound-modal="effect"]').click();effect_modal=page.locator('[data-sound-product-modal="effect"]:not([hidden])');expect(effect_modal).to_be_visible();expect(effect_modal.locator(".sound-window-toolbar")).to_have_count(0);expect(effect_modal.locator("[data-place-spatial-sound]")).to_be_visible();effect_modal.locator("[data-place-spatial-sound]").click();expect(page.locator("[data-spatial-placement-hint]")).to_be_visible()
            canvas=page.locator(".room-workspace.is-active [data-map-canvas]");box=canvas.bounding_box();target_x=box["x"]+box["width"]/2;target_y=box["y"]+box["height"]/2;page.mouse.move(target_x,target_y);page.mouse.down();page.mouse.move(target_x+90,target_y);page.mouse.up()
            inspector=page.locator(".spatial-sound-inspector:not([hidden])");expect(inspector).to_be_visible();expect(page.locator("[data-spatial-placement-hint]")).to_be_hidden();expect(inspector.locator('[data-spatial-sound-source]')).to_have_value("Rain");expect(inspector.locator('[name="radius"]')).not_to_have_value("350.0");expect(inspector.locator('[name="constrainedByWalls"]')).to_be_checked();expect(inspector.locator(".dialog-help")).not_to_have_count(0)
            persisted_before_save=page.evaluate("""async d=>(await (await fetch(`/game/sounds/${d.campaign}/scenes/${d.scene}`)).json())""",{"campaign":s["campaign_id"],"scene":s["scene_id"]})
            assert len(persisted_before_save)==1 and persisted_before_save[0]["id"]!="new",persisted_before_save
            created_version=persisted_before_save[0]["version"]
            inspector.locator("[data-modal-close]").click();page.reload();close=page.locator("[data-onboarding-close]");close.first.click() if close.count() else None
            page.locator('.room-workspace.is-active [data-active-layer="composition"]').click();page.locator('[data-artistic-domain="sounds"]:visible').click();page.locator('[data-open-sound-modal="effect"]').click();effect_modal=page.locator('[data-sound-product-modal="effect"]:not([hidden])');expect(effect_modal.locator('[data-spatial-id]')).to_have_count(1);effect_modal.locator('[data-spatial-id]').dblclick();inspector=page.locator(".spatial-sound-inspector:not([hidden])");expect(inspector).to_be_visible()
            modal_paint=inspector.evaluate("""modal=>{const rect=modal.getBoundingClientRect();const hit=document.elementFromPoint(rect.right-4,rect.top+80);return{background:getComputedStyle(modal).backgroundColor,hitInside:modal.contains(hit),layerZ:Number(getComputedStyle(modal.parentElement).zIndex),boardZ:Number(getComputedStyle(document.querySelector('.game-board')).zIndex)||0};}""")
            assert modal_paint["background"]=="rgb(24, 29, 35)",modal_paint
            assert modal_paint["hitInside"] and modal_paint["layerZ"]>modal_paint["boardZ"],modal_paint
            inspector.locator("[data-spatial-inspector-save]").click()
            expect(page.locator("[data-spatial-id]")).to_have_count(1)
            persisted_after_save=page.evaluate("""async d=>(await (await fetch(`/game/sounds/${d.campaign}/scenes/${d.scene}`)).json())""",{"campaign":s["campaign_id"],"scene":s["scene_id"]})
            assert persisted_after_save[0]["id"]==persisted_before_save[0]["id"] and persisted_after_save[0]["version"]==created_version+1,(persisted_before_save,persisted_after_save)
            page.locator('[data-artistic-domain="sounds"]:visible').click();page.locator('[data-open-sound-modal="effect"]:visible').click();effect_modal=page.locator('[data-sound-product-modal="effect"]:not([hidden])');active=effect_modal.locator("[data-spatial-enabled]");expect(active).to_be_checked();active.uncheck();expect(effect_modal.locator("[data-spatial-enabled]")).not_to_be_checked();effect_modal.locator("[data-spatial-enabled]").check();expect(effect_modal.locator("[data-spatial-enabled]")).to_be_checked();effect_modal.locator("[data-modal-close]").click()
            fixed_before=page.evaluate("GravewrightSpatialSounds.debugSnapshot().emitters[0]");page.mouse.click(target_x-220,target_y-160);page.wait_for_timeout(150);fixed_after=page.evaluate("GravewrightSpatialSounds.debugSnapshot().emitters[0]");assert (fixed_after["x"],fixed_after["y"])==(fixed_before["x"],fixed_before["y"]),(fixed_before,fixed_after)
            page.locator('[data-tool-dock]:not([hidden]) [data-tool="select"]:visible').click();page.wait_for_function("()=>window.__gravewrightSpatialSoundPixi?.count===1");page.locator('[data-tool-dock]:not([hidden]) [data-artistic-domain="images"]:visible').click();page.wait_for_function("()=>window.__gravewrightSpatialSoundPixi?.count===1");artistic_reference=page.evaluate("GravewrightSpatialSounds.snapshotFor(GravewrightMap.activeCanvas())");assert artistic_reference["artisticReference"] and not artistic_reference["authoring"] and artistic_reference["selectedId"] is None,artistic_reference;expect(page.locator(f'[data-modal-id="scene-image-picker-{s["campaign_id"]}"]')).to_be_visible();page.locator(f'[data-modal-id="scene-image-picker-{s["campaign_id"]}"] [data-modal-close]').click();page.locator('[data-tool-dock]:not([hidden]) [data-artistic-domain="sounds"]:visible').click();page.wait_for_function("()=>window.__gravewrightSpatialSoundPixi?.count===1")
            projection=page.evaluate("GravewrightSpatialSounds.debugSnapshot()")
            assert projection["renderer"]=="pixi",projection
            assert len(projection["projected"])==1,projection
            center=projection["projected"][0];assert abs(center["x"]-target_x)<3,projection;assert abs(center["y"]-target_y)<3,projection
            page.mouse.move(center["x"],center["y"]);page.mouse.down();page.mouse.move(center["x"]+50,center["y"]+30);page.mouse.up();page.wait_for_timeout(150)
            moved=page.evaluate("GravewrightSpatialSounds.debugSnapshot().projected[0]");page.mouse.move(moved["x"]+moved["radius"],moved["y"]);page.mouse.down();page.mouse.move(moved["x"]+moved["radius"]+40,moved["y"]);page.mouse.up()
            sound_id=page.evaluate("GravewrightSpatialSounds.debugSnapshot().emitters[0].id");page.locator('.room-workspace.is-active [data-active-layer="walls"]').click();page.wait_for_timeout(200);wall_reference=page.evaluate("({layer:GravewrightTools.activeLayer,state:GravewrightSpatialSounds.snapshotFor(GravewrightMap.activeCanvas()),pixi:window.__gravewrightSpatialSoundPixi})");assert wall_reference["layer"]=="walls" and len(wall_reference["state"]["emitters"])==1,wall_reference;assert wall_reference["state"]["wallReference"] and not wall_reference["state"]["authoring"] and wall_reference["state"]["selectedId"] is None,wall_reference;page.wait_for_function("()=>window.__gravewrightSpatialSoundPixi?.count===1");page.locator('.room-workspace.is-active [data-active-layer="effects"]').click();page.wait_for_function("()=>window.__gravewrightSpatialSoundPixi?.count===0");page.evaluate("GravewrightTools.setActiveTool('shader')");page.keyboard.press("Delete");page.wait_for_timeout(150);assert page.evaluate("""async d=>(await (await fetch(`/game/sounds/${d.campaign}/scenes/${d.scene}`)).json()).some(sound=>sound.id===d.id)""",{"campaign":s["campaign_id"],"scene":s["scene_id"],"id":sound_id})
            page.locator('.room-workspace.is-active [data-active-layer="composition"]').click();page.locator('[data-tool-dock]:not([hidden]) [data-artistic-domain="sounds"]:visible').click();page.wait_for_function("()=>window.__gravewrightSpatialSoundPixi?.count===1")
            page.locator('.room-workspace.is-active [data-active-layer="game"]').click();page.wait_for_function("()=>window.__gravewrightSpatialSoundPixi?.count===0");assert page.evaluate("GravewrightSpatialSounds.debugSnapshot().emitters.length")==0
            page.locator('.room-workspace.is-active [data-active-layer="composition"]').click();page.locator('[data-tool-dock]:not([hidden]) [data-artistic-domain="sounds"]:visible').click();page.wait_for_function("()=>window.__gravewrightSpatialSoundPixi?.count===1")
            page.reload();close=page.locator("[data-onboarding-close]"); close.first.click() if close.count() else None
            page.locator('.room-workspace.is-active [data-active-layer="composition"]').click();page.locator('[data-artistic-domain="sounds"]:visible').click();page.locator('[data-open-sound-modal="effect"]').click();effect_modal=page.locator('[data-sound-product-modal="effect"]:not([hidden])');expect(effect_modal.locator('[data-spatial-id]')).to_have_count(1);effect_modal.locator('[data-spatial-id]').dblclick();inspector=page.locator('.spatial-sound-inspector:not([hidden])');expect(inspector).to_be_visible();inspector.locator('[data-modal-close]').click();effect_modal.locator('[data-spatial-delete]').click();expect(effect_modal.locator('[data-spatial-id]')).to_have_count(0)
            expect(page.get_by_text("Composition",exact=True)).to_have_count(0)
            assert not [error for error in page_errors if "setPointerCapture" in error],page_errors
        finally:_close(ctx);browser.close()

def test_artistic_images_opens_asset_picker_places_and_restores(sound_server):
    s=sound_server
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);ctx=browser.new_context();page=ctx.new_page()
        page_errors=[];page.on("pageerror",lambda error:page_errors.append(str(error)))
        try:
            _login(page,s["base_url"],GM_EMAIL,GM_PASSWORD);page.goto(f"{s['base_url']}/game?room={s['campaign_id']}");close=page.locator("[data-onboarding-close]");close.first.click() if close.count() else None
            page.locator('.room-workspace.is-active [data-active-layer="composition"]').click();page.locator('[data-artistic-domain="images"]:visible').click()
            modal=page.locator(f'[data-modal-id="scene-image-picker-{s["campaign_id"]}"]');expect(modal).to_be_visible()
            card=modal.locator(f'[data-library-asset-id="{s["image_id"]}"]');expect(card).to_be_visible()
            search=modal.locator("[data-scene-image-search]");search.fill("nao-existe-esta-imagem");expect(card).to_have_count(0);search.fill("");expect(card).to_be_visible()
            card.drag_to(page.locator('.room-workspace.is-active [data-map-canvas]'))
            image=page.locator('[data-scene-image-id]');expect(image).to_have_count(1);image.click();page.keyboard.press("ArrowRight")
            page.reload();close=page.locator("[data-onboarding-close]");close.first.click() if close.count() else None;expect(page.locator('[data-scene-image-id]')).to_have_count(1)
            page.locator('.room-workspace.is-active [data-active-layer="composition"]').click();page.locator('[data-artistic-domain="images"]:visible').click();expect(page.locator(f'[data-modal-id="scene-image-picker-{s["campaign_id"]}"]')).to_be_visible()
            assert not [error for error in page_errors if "sceneId" in error or "sceneDataFor" in error],page_errors
        finally:_close(ctx);browser.close()


def test_core_area_markers_and_game_only_hand_icon(sound_server):
    s=sound_server
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);ctx=browser.new_context();page=ctx.new_page()
        try:
            _login(page,s["base_url"],GM_EMAIL,GM_PASSWORD);page.goto(f"{s['base_url']}/game?room={s['campaign_id']}");close=page.locator("[data-onboarding-close]");close.first.click() if close.count() else None
            dock=page.locator('[data-tool-dock]:not([hidden])');expect(dock.locator("[data-layers-toggle]")).to_have_count(0);expect(page.locator('[data-tool-sub-panel="layers"]')).to_have_count(0);expect(dock.locator('[data-tool="hp"]')).to_have_count(0);expect(page.locator('[data-tool-sub-panel="hp"]')).to_have_count(0);expect(dock.locator(".tool-dock-btn--hand")).to_be_visible()
            dock.locator('[data-tool="shape"]').click();shape_panel=page.locator('[data-tool-sub-panel="shape"]:not([hidden])');buttons=shape_panel.locator("[data-area-marker-preset]");expect(buttons).to_have_count(4);assert buttons.evaluate_all("nodes => nodes.map(node => node.dataset.areaMarkerPreset)")==["core.line","core.circle","core.square","core.cone"]
            page.locator('.room-workspace.is-active [data-active-layer="composition"]').click();expect(dock.locator(".tool-dock-btn--hand")).to_be_hidden()
            page.locator('.room-workspace.is-active [data-active-layer="game"]').click();expect(dock.locator(".tool-dock-btn--hand")).to_be_visible()
        finally:_close(ctx);browser.close()


def test_area_marker_can_move_rotate_delete_and_clear(sound_server):
    s=sound_server
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);ctx=browser.new_context();page=ctx.new_page()
        try:
            _login(page,s["base_url"],GM_EMAIL,GM_PASSWORD);page.goto(f"{s['base_url']}/game?room={s['campaign_id']}");close=page.locator("[data-onboarding-close]");close.first.click() if close.count() else None
            dock=page.locator('[data-tool-dock]:not([hidden])');canvas=page.locator('.room-workspace.is-active [data-map-canvas]');box=canvas.bounding_box();assert box
            start=(box["x"]+box["width"]*.35,box["y"]+box["height"]*.35);end=(start[0]+140,start[1]+105)

            dock.locator('[data-tool="shape"]').click();panel=page.locator('[data-tool-sub-panel="shape"]:not([hidden])');panel.locator('[data-area-marker-preset="core.square"]').click()
            page.mouse.move(*start);page.mouse.down();page.mouse.move(*end);page.mouse.up();expect(page.locator('.board-area-marker-input')).to_be_visible();page.keyboard.press("Escape")
            page.wait_for_function("GravewrightMap.measurementSnapshot().items.some(item=>item.shape==='square')")
            marker=lambda shape:page.evaluate("shape=>GravewrightMap.measurementSnapshot().items.find(item=>item.shape===shape)||null",shape)
            screen=lambda point:page.evaluate("p=>{const c=document.querySelector('.room-workspace.is-active [data-map-canvas]'),s=GravewrightMap.stateFor(c);return[p.worldX*s.zoom+s.offsetX,p.worldY*s.zoom+s.offsetY]}",point)
            square=marker("square");before=square["start"]["worldX"];grid=float(canvas.get_attribute("data-scene-grid-size"));assert abs(square["start"]["worldX"]%grid-grid/2)<.01 and abs(square["start"]["worldY"]%grid-grid/2)<.01,square

            dock.locator('[data-tool="shape"]').click();panel=page.locator('[data-tool-sub-panel="shape"]:not([hidden])');panel.locator('[data-subtool="select"]').click();center=screen({"worldX":(square["start"]["worldX"]+square["end"]["worldX"])/2,"worldY":(square["start"]["worldY"]+square["end"]["worldY"])/2});page.mouse.move(*center);page.mouse.down();page.mouse.move(center[0]+90,center[1]+70);page.mouse.up();page.wait_for_timeout(150);square=marker("square");after_shape=square["start"]["worldX"];assert after_shape!=before

            dock.locator('[data-tool="select"]').click();center=screen({"worldX":(square["start"]["worldX"]+square["end"]["worldX"])/2,"worldY":(square["start"]["worldY"]+square["end"]["worldY"])/2});page.mouse.move(*center);page.mouse.down();page.mouse.move(center[0]+70,center[1]+70);page.mouse.up();page.wait_for_timeout(150);square=marker("square");after_universal=square["start"]["worldX"];assert after_universal!=after_shape

            center=screen({"worldX":(square["start"]["worldX"]+square["end"]["worldX"])/2,"worldY":(square["start"]["worldY"]+square["end"]["worldY"])/2});page.mouse.move(*center);page.mouse.click(*center);page.keyboard.down("Shift");page.mouse.wheel(0,100);page.keyboard.up("Shift");page.wait_for_timeout(250);square=marker("square");assert square.get("rotation")==5,square
            page.reload();close=page.locator("[data-onboarding-close]");close.first.click() if close.count() else None;page.wait_for_function("GravewrightMap.measurementSnapshot().items.some(item=>item.shape==='square')");square=marker("square");assert square.get("rotation")==5;square_center=screen({"worldX":(square["start"]["worldX"]+square["end"]["worldX"])/2,"worldY":(square["start"]["worldY"]+square["end"]["worldY"])/2})
            dock=page.locator('[data-tool-dock]:not([hidden])');dock.locator('[data-tool="select"]').click();page.mouse.click(*square_center);page.keyboard.press("Delete");page.wait_for_function("!GravewrightMap.measurementSnapshot().items.some(item=>item.shape==='square')")

            dock.locator('[data-tool="shape"]').click();panel=page.locator('[data-tool-sub-panel="shape"]:not([hidden])');panel.locator('[data-area-marker-preset="core.circle"]').click();page.mouse.move(*start);page.mouse.down();page.mouse.move(*end);page.mouse.up();page.keyboard.press("Escape");page.wait_for_function("GravewrightMap.measurementSnapshot().items.some(item=>item.shape==='circle')")
            dock.locator('[data-tool="shape"]').click();panel=page.locator('[data-tool-sub-panel="shape"]:not([hidden])');panel.locator('[data-tool-clear]').click();page.wait_for_function("!GravewrightMap.measurementSnapshot().items.some(item=>item.shape==='circle')")
            panel.locator('[data-area-marker-preset="core.line"]').click();screen_step=page.evaluate("""p=>{const canvas=document.querySelector('.room-workspace.is-active [data-map-canvas]');const a=GravewrightMap.worldFromScreen(canvas,p.x,p.y);const b=GravewrightMap.worldFromScreen(canvas,p.x+100,p.y);return Number(canvas.dataset.sceneGridSize)*100/(b.worldX-a.worldX)}""",{"x":start[0],"y":start[1]});page.mouse.move(*start);page.mouse.down();page.mouse.move(start[0]+4*screen_step,start[1]);page.mouse.up();page.keyboard.press("Escape");page.wait_for_function("GravewrightMap.measurementSnapshot().items.some(item=>item.shape==='line')");line=marker("line");assert str(line["label"]).startswith("5 ") and len(line["cells"])==5,line
        finally:_close(ctx);browser.close()

def test_upload_once_asset_becomes_reusable_native_sound(sound_server):
    s=sound_server
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);ctx=browser.new_context();page=ctx.new_page()
        try:
            _login(page,s["base_url"],GM_EMAIL,GM_PASSWORD);page.goto(f"{s['base_url']}/game?room={s['campaign_id']}");close=page.locator("[data-onboarding-close]");close.first.click() if close.count() else None
            # Assets parou na dock da camada de jogo, logo abaixo do olho: um
            # clique, sem modal empilhado no caminho.
            page.locator(f'[data-tool-dock]:not([hidden]) [data-modal-open="library-images-{s["campaign_id"]}"]').click()
            modal=page.locator(f'[data-modal-id="library-images-{s["campaign_id"]}"]');expect(modal).to_be_visible()
            expect(modal.locator('[data-scene-asset-upload="pdf"]')).to_have_count(0);expect(modal.locator('[data-asset-package-open]')).to_be_hidden();expect(modal.locator('[data-asset-kind="image"]')).to_be_visible();expect(modal.locator('[data-asset-kind="ambient-audio"]')).to_be_visible();effect_filter=modal.locator('[data-asset-kind="effect-audio"]');expect(effect_filter).to_be_visible();expect(effect_filter.locator("small")).to_have_text("1");modal.locator('[data-scene-asset-upload-input="effect-audio"]').set_input_files(s["upload_audio"]);expect(modal.get_by_text("storm.ogg",exact=False)).to_be_visible();expect(effect_filter.locator("small")).to_have_text("2")
            before=page.evaluate("async id=>(await (await fetch('/game/assets/state/'+id)).json()).assets.length",s["campaign_id"]);window_close=modal.locator("[data-modal-close]");window_close.click()
            page.locator('.room-workspace.is-active [data-active-layer="composition"]').click();page.locator('[data-artistic-domain="sounds"]:visible').click();initial_emitters=page.evaluate("GravewrightSpatialSounds.debugSnapshot().emitters.length");page.locator('[data-open-sound-modal="effect"]').click();effect_modal=page.locator('[data-sound-product-modal="effect"]:not([hidden])');effect_modal.locator("[data-place-spatial-sound]").click();canvas=page.locator(".room-workspace.is-active [data-map-canvas]");box=canvas.bounding_box();page.mouse.click(box["x"]+box["width"]*.6,box["y"]+box["height"]*.6);inspector=page.locator(".spatial-sound-inspector:not([hidden])");expect(inspector).to_be_visible();page.wait_for_function("expected=>GravewrightSpatialSounds.debugSnapshot().emitters.length===expected",arg=initial_emitters+1);inspector.locator("[data-spatial-inspector-save]").click()
            after=page.evaluate("async id=>(await (await fetch('/game/assets/state/'+id)).json()).assets.length",s["campaign_id"]);assert after==before
            page.reload();close=page.locator("[data-onboarding-close]");close.first.click() if close.count() else None;page.locator('.room-workspace.is-active [data-active-layer="composition"]').click();page.locator('[data-artistic-domain="sounds"]:visible').click();page.locator('[data-open-sound-modal="effect"]').click();expect(page.locator('[data-sound-product-modal="effect"]:not([hidden]) [data-spatial-id]')).to_have_count(initial_emitters+1)
        finally:_close(ctx);browser.close()


def test_player_hears_spatial_effect_only_through_controlled_token(sound_server):
    s=sound_server
    audio_double="""window.Audio=class{constructor(src){this.src=src;this.paused=true;this.volume=1;this.loop=false;this.duration=60;this.currentTime=0;}addEventListener(name,callback){if(name==='loadedmetadata')queueMicrotask(callback);}play(){this.paused=false;return Promise.resolve();}pause(){this.paused=true;}}"""
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);gm_ctx=browser.new_context();player_ctx=browser.new_context();gm_ctx.add_init_script(audio_double);player_ctx.add_init_script(audio_double);gm=gm_ctx.new_page();player=player_ctx.new_page()
        try:
            _login(gm,s["base_url"],GM_EMAIL,GM_PASSWORD);_login(player,s["base_url"],PLAYER_EMAIL,PLAYER_PASSWORD)
            gm.goto(f"{s['base_url']}/game?room={s['campaign_id']}");player.goto(f"{s['base_url']}/game?room={s['campaign_id']}")
            for page in (gm,player):
                close=page.locator("[data-onboarding-close]");close.first.click() if close.count() else None
                expect(page.locator("[data-personal-audio-toggle]")).to_be_visible()
            gm.locator("[data-personal-audio-toggle]").click();gm.locator('[data-personal-audio-popover] [data-mixer-channel="master"]').evaluate("el=>{el.value='.25';el.dispatchEvent(new Event('input',{bubbles:true}));}");player.locator("[data-personal-audio-toggle]").click();expect(player.locator('[data-personal-audio-popover] [data-mixer-channel="master"]')).to_have_value("1");assert gm.evaluate("GravewrightAudioRuntime.preference('master')")==.25 and player.evaluate("GravewrightAudioRuntime.preference('master')")==1
            player.mouse.click(5,5)
            emitter=gm.evaluate("""async d=>{const r=await fetch('/game/sounds/spatial',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});if(!r.ok)throw new Error(await r.text());return r.json();}""",{"campaignId":s["campaign_id"],"sceneId":s["scene_id"],"soundId":s["sound_id"],"x":105,"y":105,"radius":140,"gain":1,"falloff":"smooth","loop":True,"constrainedByWalls":True,"audience":{"kind":"campaign"}})
            projection=player.evaluate("""async d=>(await (await fetch(`/game/sounds/${d.campaign}/scenes/${d.scene}/acoustics`)).json()).find(v=>v.spatialSoundId===d.emitter)""",{"campaign":s["campaign_id"],"scene":s["scene_id"],"emitter":emitter["id"]})
            assert projection["listenerTokenId"]==s["listener_token_id"] and projection["projection"]==1
            gm_projection=gm.evaluate("""async d=>(await (await fetch(`/game/sounds/${d.campaign}/scenes/${d.scene}/acoustics`)).json()).find(v=>v.spatialSoundId===d.emitter)""",{"campaign":s["campaign_id"],"scene":s["scene_id"],"emitter":emitter["id"]})
            assert gm_projection["listenerTokenId"] is None and gm_projection["projection"]==0
            player.wait_for_function("id=>{const s=GravewrightAudioRuntime.inspect(id);return s&&!s.playing?false:!!s}",arg=projection["playbackId"])
            gm.wait_for_function("id=>{const s=GravewrightAudioRuntime.inspect(id);return s&&s.playing===false}",arg=projection["playbackId"])
            gm.evaluate("tokenId=>document.dispatchEvent(new CustomEvent('vtt:token-selection-changed',{detail:{tokenId}}))",s["gm_listener_token_id"])
            gm.evaluate("document.dispatchEvent(new CustomEvent('tool:vision-toggle'))")
            gm.wait_for_function("id=>{const s=GravewrightAudioRuntime.inspect(id);return s&&s.playing===true}",arg=projection["playbackId"])
            gm.evaluate("document.dispatchEvent(new CustomEvent('tool:vision-toggle'))")
            gm.wait_for_function("id=>{const s=GravewrightAudioRuntime.inspect(id);return s&&s.playing===false}",arg=projection["playbackId"])
            gm.evaluate("d=>GravewrightRealtime.sendCommand('token.move',{scene_id:d.scene,token_id:d.token,grid_x:5,grid_y:5},{sceneId:d.scene,roomId:d.room})",{"scene":s["scene_id"],"token":s["listener_token_id"],"room":s["campaign_id"]})
            player.wait_for_function("id=>{const s=GravewrightAudioRuntime.inspect(id);return s&&s.playing===false}",arg=projection["playbackId"])
            gm.evaluate("d=>GravewrightRealtime.sendCommand('token.move',{scene_id:d.scene,token_id:d.token,grid_x:2,grid_y:1},{sceneId:d.scene,roomId:d.room})",{"scene":s["scene_id"],"token":s["listener_token_id"],"room":s["campaign_id"]})
            player.wait_for_function("id=>{const s=GravewrightAudioRuntime.inspect(id);return s&&s.playing&&Math.abs(s.volume-.5)<.02}",arg=projection["playbackId"])
            gm.wait_for_function("id=>{const s=GravewrightAudioRuntime.inspect(id);return s&&s.playing===false}",arg=projection["playbackId"])
        finally:_close(gm_ctx);_close(player_ctx);browser.close()


LAYER_TRIM={"game":"192, 154, 90","gm":"208, 111, 111","composition":"96, 165, 250",
            "effects":"109, 179, 134","walls":"167, 139, 250","lighting":"250, 204, 21"}

def test_active_layer_paints_the_ui_trim(sound_server):
    """A borda de detalhe diz em que camada o mestre esta editando."""
    s=sound_server
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);ctx=browser.new_context();page=ctx.new_page()
        try:
            _login(page,s["base_url"],GM_EMAIL,GM_PASSWORD);page.goto(f"{s['base_url']}/game?room={s['campaign_id']}")
            close=page.locator("[data-onboarding-close]");close.first.click() if close.count() else None
            expect(page.locator("[data-tool-dock]:not([hidden])")).to_be_visible()
            checked=[]
            for layer,rgb in LAYER_TRIM.items():
                button=page.locator(f'.room-workspace.is-active [data-active-layer="{layer}"]')
                if not button.count():continue
                button.click();expect(page.locator("body")).to_have_attribute("data-table-layer",layer)
                assert page.evaluate("getComputedStyle(document.body).getPropertyValue('--layer-accent-rgb').trim()")==rgb,layer
                # o token derivado e a borda concreta do dock acompanham a camada
                accent=page.evaluate("getComputedStyle(document.body).getPropertyValue('--border-accent-strong').trim()")
                assert [int(v) for v in re.findall(r"\d+",accent)[:3]]==[int(v) for v in rgb.split(", ")],(layer,accent)
                border=page.evaluate("getComputedStyle(document.querySelector('[data-tool-dock]:not([hidden])')).borderTopColor")
                assert [int(v) for v in re.findall(r"\d+",border)[:3]]==[int(v) for v in rgb.split(", ")],(layer,border)
                checked.append(layer)
            assert set(checked)==set(LAYER_TRIM),checked
        finally:_close(ctx);browser.close()
