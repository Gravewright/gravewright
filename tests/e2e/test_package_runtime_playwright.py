from __future__ import annotations
import contextlib, json, os, shutil, subprocess, sys
import pytest
from playwright.sync_api import expect, sync_playwright
from tests.e2e.test_app_server_e2e import GM_EMAIL,GM_PASSWORD,PLAYER_EMAIL,PLAYER_PASSWORD,REPO_ROOT,_free_port,_seed_database,_wait_http_ready
from tests.e2e.test_multiplayer_playwright import _close,_login

PACKAGE_ID="world-objects-e2e"

@pytest.fixture(scope="module")
def world_objects_server(tmp_path_factory):
    tmp=tmp_path_factory.mktemp("world-objects-e2e");db_path=tmp/"e2e.sqlite3";seeded=_seed_database(db_path);data=tmp/"data";target=data/"packages/addons"/PACKAGE_ID;target.parent.mkdir(parents=True);shutil.copytree(REPO_ROOT/"tests/fixtures/sdk_packages/valid/addons"/PACKAGE_ID,target)
    text=(target/"manifest.json").read_text(encoding="utf-8");manifest=json.loads(text)
    import app.persistence.database as db_module
    from app.persistence import engine as engine_module
    from app.persistence.repositories.installed_package_repository import InstalledPackageRepository
    from app.persistence.repositories.campaign_package_repository import CampaignPackageRepository
    from app.persistence.repositories.scene_repository import SceneRepository
    from tests.conftest import seed_scene
    db_module.DATABASE_PATH=db_path.resolve();db_module._initialized=False;engine_module.reset_engine()
    scene=seed_scene(seeded["campaign_id"]);SceneRepository().set_active_scene(campaign_id=seeded["campaign_id"],scene_id=scene["id"]);seeded["scene_id"]=scene["id"]
    InstalledPackageRepository().upsert(package_id=PACKAGE_ID,kind="addon",name=manifest["name"],version=manifest["version"],status="enabled",package_dir=f"addons/{PACKAGE_ID}",manifest_json=text,compatibility_status="compatible",validation_errors_json="[]",installed_by_user_id=seeded["gm_id"],last_validation_status="valid")
    CampaignPackageRepository().activate(campaign_id=seeded["campaign_id"],package_id=PACKAGE_ID,activation_role="addon",enabled_by_user_id=seeded["gm_id"]);engine_module.reset_engine()
    port=_free_port();base=f"http://127.0.0.1:{port}";env=os.environ.copy();env.update({"APP_ENV":"test","DATABASE_URL":f"sqlite:///{db_path.resolve().as_posix()}","ALLOWED_HOSTS":"*","WS_ALLOWED_ORIGINS":base,"SESSION_COOKIE_SECURE":"false","ALLOW_METADATA_BOOTSTRAP":"true","GRAVEWRIGHT_TEST_TEMP_ROOT":str(tmp.resolve()),"GRAVEWRIGHT_DATA_DIR":str(data.resolve())})
    proc=subprocess.Popen([sys.executable,"-m","uvicorn","main:app","--host","127.0.0.1","--port",str(port),"--log-level","warning"],cwd=str(REPO_ROOT),env=env)
    try:_wait_http_ready(f"{base}/login",proc=proc);yield {"base_url":base,**seeded}
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):proc.wait(timeout=10)
        if proc.poll() is None:proc.kill()

def test_world_object_interaction_and_remote_presentation_reload_expiry(world_objects_server):
    server=world_objects_server;base=server["base_url"];url=f"{base}/game?room={server['campaign_id']}"
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);gm_context=browser.new_context();player_context=browser.new_context()
        try:
            gm=gm_context.new_page();player=player_context.new_page();_login(gm,base,GM_EMAIL,GM_PASSWORD);_login(player,base,PLAYER_EMAIL,PLAYER_PASSWORD);gm.goto(url);player.goto(url);gm.locator("[data-onboarding-close]").first.click();player.reload()
            expect(gm.get_by_test_id("world-objects-controls")).to_be_attached();expect(player.get_by_test_id("world-objects-controls")).to_be_attached()
            gm.get_by_test_id("world-objects-create-object").click();expect(gm.get_by_test_id("world-objects-status")).to_contain_text("created:");expect(gm.locator('[data-scene-object-id]')).to_have_count(1);expect(player.locator('[data-scene-object-id]')).to_have_count(1)
            assert player.locator('[data-scene-object-id]').get_attribute("data-interaction-count")=="1";player.locator('[data-scene-object-id]').press("Enter");expect(player.get_by_test_id("world-objects-status")).to_contain_text("interacted:");expect(gm.get_by_test_id("world-objects-status")).to_contain_text("interacted:")
            gm.get_by_test_id("world-objects-recipient").fill(server["player_id"]);gm.get_by_test_id("world-objects-show-title").click()
            title=player.locator('[data-presentation-mode="title-card"]');expect(title).to_contain_text("THE CRYPT");expect(gm.locator('[data-presentation-mode="title-card"]')).to_have_count(0)
            response=player.reload();assert response is not None and response.ok;expect(player.locator('[data-presentation-mode="title-card"]')).to_contain_text("THE CRYPT")
            expect(player.locator('[data-presentation-mode="title-card"]')).to_have_count(0,timeout=8000)
        finally:_close(player_context);_close(gm_context);browser.close()
