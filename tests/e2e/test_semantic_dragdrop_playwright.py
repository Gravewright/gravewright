from __future__ import annotations
import contextlib,json,os,shutil,subprocess,sys
import pytest
from playwright.sync_api import expect,sync_playwright
from tests.e2e.test_app_server_e2e import GM_EMAIL,GM_PASSWORD,PLAYER_EMAIL,PLAYER_PASSWORD,REPO_ROOT,_free_port,_seed_database,_wait_http_ready
from tests.e2e.test_multiplayer_playwright import _close,_login

PACKAGE_ID="semantic-dragdrop-e2e";RULESET_ID="item-insertion-e2e"
@pytest.fixture(scope="module")
def scene_runtime_server(tmp_path_factory):
    tmp=tmp_path_factory.mktemp("semantic-dragdrop-e2e");db_path=tmp/"e2e.sqlite3";seeded=_seed_database(db_path);data=tmp/"data";target=data/"packages/addons"/PACKAGE_ID;target.parent.mkdir(parents=True);shutil.copytree(REPO_ROOT/"tests/fixtures/sdk_packages/valid/addons"/PACKAGE_ID,target);text=(target/"manifest.json").read_text(encoding="utf-8");manifest=json.loads(text);ruleset=data/"packages/rulesets"/RULESET_ID;ruleset.parent.mkdir(parents=True);shutil.copytree(REPO_ROOT/"tests/fixtures/sdk_packages/valid/rulesets"/RULESET_ID,ruleset);rules_text=(ruleset/"manifest.json").read_text(encoding="utf-8");rules_manifest=json.loads(rules_text)
    import app.persistence.database as db_module
    from app.persistence import engine as engine_module
    from app.persistence.repositories.installed_package_repository import InstalledPackageRepository
    from app.persistence.repositories.campaign_package_repository import CampaignPackageRepository
    from app.persistence.repositories.scene_repository import SceneRepository
    from app.engine.decks.card_service import CardService
    from app.engine.decks.cards import DrawDestination
    from app.persistence.repositories.actor_repository import ActorRepository
    from app.persistence.repositories.item_repository import ItemRepository
    from app.persistence.repositories.campaign_repository import CampaignRepository
    from tests.conftest import seed_scene
    db_module.DATABASE_PATH=db_path.resolve();db_module._initialized=False;engine_module.reset_engine();scene=seed_scene(seeded["campaign_id"]);SceneRepository().set_active_scene(campaign_id=seeded["campaign_id"],scene_id=scene["id"]);seeded["scene_id"]=scene["id"];seeded["actor_id"]=ActorRepository().create(campaign_id=seeded["campaign_id"],system_id=RULESET_ID,actor_type="character",name="Drop Actor",created_by_user_id=seeded["gm_id"]);seeded["item_id"]=ItemRepository().create(campaign_id=seeded["campaign_id"],system_id=RULESET_ID,item_type="equipment",name="Drop Rope",created_by_user_id=seeded["gm_id"])
    InstalledPackageRepository().upsert(package_id=RULESET_ID,kind="ruleset",name=rules_manifest["name"],version=rules_manifest["version"],status="enabled",package_dir=f"rulesets/{RULESET_ID}",manifest_json=rules_text,compatibility_status="compatible",validation_errors_json="[]",installed_by_user_id=seeded["gm_id"],last_validation_status="valid");CampaignRepository().update_system(campaign_id=seeded["campaign_id"],changed_by_user_id=seeded["gm_id"],next_system_id=RULESET_ID)
    InstalledPackageRepository().upsert(package_id=PACKAGE_ID,kind="addon",name=manifest["name"],version=manifest["version"],status="enabled",package_dir=f"addons/{PACKAGE_ID}",manifest_json=text,compatibility_status="compatible",validation_errors_json="[]",installed_by_user_id=seeded["gm_id"],last_validation_status="valid");CampaignPackageRepository().activate(campaign_id=seeded["campaign_id"],package_id=PACKAGE_ID,activation_role="addon",enabled_by_user_id=seeded["gm_id"])
    cards=CardService();definition=cards.create_deck_definition(campaign_id=seeded["campaign_id"],user_id=seeded["gm_id"],name="Private Hand",description=None,cards=[{"name":"Secret Card","front_asset_id":"front-secret","quantity":1}]).payload["deck"];deck=cards.instantiate_deck(campaign_id=seeded["campaign_id"],user_id=seeded["gm_id"],deck_definition_id=definition["id"]).payload["deck"];drawn=cards.draw(campaign_id=seeded["campaign_id"],user_id=seeded["player_id"],deck_instance_id=deck["id"],count=1,destination=DrawDestination.HAND);seeded["card_id"]=drawn.payload["cards"][0]["id"];engine_module.reset_engine()
    port=_free_port();base=f"http://127.0.0.1:{port}";env=os.environ.copy();env.update({"APP_ENV":"test","DATABASE_URL":f"sqlite:///{db_path.resolve().as_posix()}","ALLOWED_HOSTS":"*","WS_ALLOWED_ORIGINS":base,"SESSION_COOKIE_SECURE":"false","ALLOW_METADATA_BOOTSTRAP":"true","GRAVEWRIGHT_TEST_TEMP_ROOT":str(tmp.resolve()),"GRAVEWRIGHT_DATA_DIR":str(data.resolve())});proc=subprocess.Popen([sys.executable,"-m","uvicorn","main:app","--host","127.0.0.1","--port",str(port),"--log-level","warning"],cwd=str(REPO_ROOT),env=env)
    try:_wait_http_ready(f"{base}/login",proc=proc);yield {"base_url":base,**seeded}
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):proc.wait(timeout=10)
        if proc.poll() is None:proc.kill()

def test_private_card_pointer_drop_creates_authoritative_persistent_placement(scene_runtime_server):
    server=scene_runtime_server;base=server["base_url"];url=f"{base}/game?room={server['campaign_id']}"
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);gm_ctx=browser.new_context();player_ctx=browser.new_context()
        try:
            gm=gm_ctx.new_page();player=player_ctx.new_page();_login(gm,base,GM_EMAIL,GM_PASSWORD);_login(player,base,PLAYER_EMAIL,PLAYER_PASSWORD);gm.goto(url);player.goto(url);gm.locator("[data-onboarding-close]").first.click();player.reload()
            expect(gm.get_by_test_id("scene-runtime-create-zone")).to_be_attached();gm.get_by_test_id("scene-runtime-create-zone").click();zone=player.locator('[data-scene-object-type="semantic-dragdrop-e2e.board-zone"]');expect(zone).to_be_attached()
            player.locator(f'[data-modal-open="panel-hand-{server["campaign_id"]}"]').click();source=player.locator(f'[data-card-drag-id="{server["card_id"]}"]');expect(source).to_be_visible();a=source.bounding_box();b=zone.bounding_box();assert a and b
            player.mouse.move(a["x"]+a["width"]/2,a["y"]+a["height"]/2);player.mouse.down();player.mouse.move(b["x"]+b["width"]/2,b["y"]+b["height"]/2,steps=8);player.mouse.up()
            expect(player.locator("[data-table-card-id]")).to_have_count(1);player.reload();expect(player.locator("[data-table-card-id]")).to_have_count(1)
        finally:_close(player_ctx);_close(gm_ctx);browser.close()

def _drag(page,source,target):
    a=source.bounding_box();b=target.bounding_box();assert a and b
    page.mouse.move(a["x"]+a["width"]/2,a["y"]+a["height"]/2);page.mouse.down();page.mouse.move(b["x"]+b["width"]/2,b["y"]+b["height"]/2,steps=10);page.mouse.up()

def test_item_to_actor_sheet_uses_ruleset_insertion_and_survives_reload(scene_runtime_server):
    s=scene_runtime_server;url=f"{s['base_url']}/game?room={s['campaign_id']}"
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);ctx=browser.new_context()
        try:
            page=ctx.new_page();_login(page,s["base_url"],GM_EMAIL,GM_PASSWORD);page.goto(url);page.locator("[data-onboarding-close]").first.click();page.locator(f'[data-panel-toggle="panel-actors-{s["campaign_id"]}"]').click();page.locator(f'[data-actor-open="{s["actor_id"]}"]').click();sheet=page.locator(f'[data-actor-sheet-root][data-actor-id="{s["actor_id"]}"]');expect(sheet).to_be_visible();page.locator(f'[data-modal-id="actor-{s["actor_id"]}"]').evaluate("node=>Object.assign(node.style,{left:'2vw',top:'2vh',width:'42vw',height:'90vh'})");page.locator(f'[data-panel-toggle="panel-items-{s["campaign_id"]}"]').evaluate("node=>node.click()");source=page.locator(f'[data-item-card="{s["item_id"]}"]');expect(source).to_be_visible();_drag(page,source,sheet);page.wait_for_timeout(700);page.reload();close=page.locator("[data-onboarding-close]");close.first.click() if close.count() else None;stored=page.evaluate("""async actor=>{const response=await fetch(`/game/actor/${actor}/sheet-data`);return response.json()}""",s["actor_id"]);assert [item["name"] for item in stored["data"]["inventory"]]==["Drop Rope"]
        finally:_close(ctx);browser.close()

PIN_SELECTOR='[data-scene-object-type="semantic-dragdrop-e2e.scene-pin"][data-interaction-count="1"]'
def _semantic_runtime_ready(page):
    """Block until the package runtime can actually serve a semantic interaction.

    The dock slot is registered last in the fixture package's ready(), so its button
    proves every dragDrop source/target registration already committed; the open
    socket proves scene.object.interacted can still reach this client."""
    expect(page.get_by_test_id("scene-runtime-create-zone")).to_be_attached();page.wait_for_function("()=>Boolean(window.GravewrightRealtime?.isOpen())")

def test_journal_to_pin_reload_interaction_opens_native_journal(scene_runtime_server):
    s=scene_runtime_server;url=f"{s['base_url']}/game?room={s['campaign_id']}"
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);ctx=browser.new_context()
        try:
            page=ctx.new_page();_login(page,s["base_url"],GM_EMAIL,GM_PASSWORD);page.goto(url);page.locator("[data-onboarding-close]").first.click();_semantic_runtime_ready(page);page.locator(f'[data-panel-toggle="panel-journal-{s["campaign_id"]}"]').click();source=page.locator(f'.journal-card[data-journal-id="{s["journal_id"]}"]');canvas=page.locator(f'[data-map-canvas][data-scene-id="{s["scene_id"]}"]');expect(source).to_be_visible();_drag(page,source,canvas)
            expect(page.locator(PIN_SELECTOR)).to_have_count(1);page.reload();page.locator("[data-onboarding-close]").first.click();_semantic_runtime_ready(page)
            pin=page.locator(PIN_SELECTOR);expect(pin).to_be_visible();pin.click();expect(page.locator("body")).to_have_attribute("data-scene-runtime-pin-interaction","opened");expect(page.locator(f'[data-modal-id="journal-{s["journal_id"]}"]')).to_be_visible()
        finally:_close(ctx);browser.close()
