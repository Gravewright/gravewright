from __future__ import annotations
import contextlib,json,os,shutil,subprocess,sys
import pytest
from playwright.sync_api import expect,sync_playwright
from tests.e2e.test_app_server_e2e import GM_EMAIL,GM_PASSWORD,PLAYER_EMAIL,PLAYER_PASSWORD,REPO_ROOT,_free_port,_seed_database,_wait_http_ready
from tests.e2e.test_multiplayer_playwright import _close,_login

PACKAGE_ID="scene-navigation-e2e";PLAYER_B_EMAIL="player-b-scene-runtime@test.com"

@pytest.fixture(scope="module")
def transition_server(tmp_path_factory):
    tmp=tmp_path_factory.mktemp("scene-navigation");db_path=tmp/"e2e.sqlite3";seeded=_seed_database(db_path);data=tmp/"data";target=data/"packages/addons"/PACKAGE_ID;target.parent.mkdir(parents=True);shutil.copytree(REPO_ROOT/"tests/fixtures/sdk_packages/valid/addons"/PACKAGE_ID,target);text=(target/"manifest.json").read_text(encoding="utf-8");manifest=json.loads(text)
    import app.persistence.database as db_module
    from app.persistence import engine as engine_module
    from app.persistence.repositories.installed_package_repository import InstalledPackageRepository
    from app.persistence.repositories.campaign_package_repository import CampaignPackageRepository
    from app.persistence.repositories.scene_repository import SceneRepository
    from tests.conftest import seed_member,seed_scene,seed_user
    db_module.DATABASE_PATH=db_path.resolve();db_module._initialized=False;engine_module.reset_engine();player_b=seed_user(name="Player B",email=PLAYER_B_EMAIL);seed_member(seeded["campaign_id"],player_b,"player");a=seed_scene(seeded["campaign_id"],name="Scene A");b=seed_scene(seeded["campaign_id"],name="Scene B");SceneRepository().set_active_scene(campaign_id=seeded["campaign_id"],scene_id=a["id"]);seeded.update(player_b_id=player_b,scene_a=a["id"],scene_b=b["id"])
    InstalledPackageRepository().upsert(package_id=PACKAGE_ID,kind="addon",name=manifest["name"],version=manifest["version"],status="enabled",package_dir=f"addons/{PACKAGE_ID}",manifest_json=text,compatibility_status="compatible",validation_errors_json="[]",installed_by_user_id=seeded["gm_id"],last_validation_status="valid");CampaignPackageRepository().activate(campaign_id=seeded["campaign_id"],package_id=PACKAGE_ID,activation_role="addon",enabled_by_user_id=seeded["gm_id"]);engine_module.reset_engine()
    port=_free_port();base=f"http://127.0.0.1:{port}";env=os.environ.copy();env.update({"APP_ENV":"test","DATABASE_URL":f"sqlite:///{db_path.resolve().as_posix()}","ALLOWED_HOSTS":"*","WS_ALLOWED_ORIGINS":base,"SESSION_COOKIE_SECURE":"false","ALLOW_METADATA_BOOTSTRAP":"true","GRAVEWRIGHT_TEST_TEMP_ROOT":str(tmp.resolve()),"GRAVEWRIGHT_DATA_DIR":str(data.resolve())});proc=subprocess.Popen([sys.executable,"-m","uvicorn","main:app","--host","127.0.0.1","--port",str(port),"--log-level","warning"],cwd=str(REPO_ROOT),env=env)
    try:_wait_http_ready(f"{base}/login",proc=proc);yield {"base_url":base,**seeded}
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):proc.wait(timeout=10)
        if proc.poll() is None:proc.kill()

def test_completion_barrier_drives_transition_and_disconnected_recipient_does_not_deadlock(transition_server):
    s=transition_server;base=s["base_url"];url=f"{base}/game?room={s['campaign_id']}"
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);gm_c=browser.new_context();a_c=browser.new_context();b_c=browser.new_context()
        try:
            gm=gm_c.new_page();a=a_c.new_page();b=b_c.new_page();errors=[]
            gm.on("pageerror",lambda error:errors.append(str(error)))
            _login(gm,base,GM_EMAIL,GM_PASSWORD);_login(a,base,PLAYER_EMAIL,PLAYER_PASSWORD);_login(b,base,PLAYER_B_EMAIL,PLAYER_PASSWORD)
            gm.goto(url);a.goto(url);b.goto(url);gm.locator("[data-onboarding-close]").first.click();a.reload();b.reload()
            controls=gm.get_by_test_id("scene-navigation-controls");expect(controls).to_be_attached()
            gm.get_by_test_id("scene-navigation-recipients").fill(f"{s['player_id']},{s['player_b_id']}")
            gm.get_by_test_id("scene-navigation-scene").fill(s["scene_b"]);gm.get_by_test_id("scene-navigation-run").click()
            expect(a.locator('[data-presentation-mode="fade"]')).to_be_attached();expect(b.locator('[data-presentation-mode="fade"]')).to_be_attached();b_c.close()
            expect(a.locator(f'[data-map-canvas][data-scene-id="{s["scene_b"]}"]')).to_be_attached(timeout=10000)
            expect(gm.locator("body")).to_have_attribute("data-scene-navigation-state","done",timeout=12000)
            history=gm.locator("body").get_attribute("data-scene-navigation-history")
            assert history==",fade-out,navigation,title,fade-in,done"
            assert not errors
            a.reload();expect(a.locator(f'[data-map-canvas][data-scene-id="{s["scene_b"]}"]')).to_be_attached()
        finally:_close(a_c);_close(gm_c);browser.close()
