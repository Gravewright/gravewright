from __future__ import annotations
import contextlib,json,os,shutil,subprocess,sys
import pytest
from playwright.sync_api import expect,sync_playwright
from tests.e2e.test_app_server_e2e import GM_EMAIL,GM_PASSWORD,PLAYER_EMAIL,PLAYER_PASSWORD,REPO_ROOT,_free_port,_seed_database,_wait_http_ready
from tests.e2e.test_multiplayer_playwright import _close,_csrf,_login

PACKAGE_ID="scene-runtime-e2e";PLAYER_B_EMAIL="runtime-player-b@test.com"

@pytest.fixture(scope="module")
def runtime_server(tmp_path_factory):
    tmp=tmp_path_factory.mktemp("scene-runtime");db_path=tmp/"e2e.sqlite3";seeded=_seed_database(db_path);data=tmp/"data";target=data/"packages/addons"/PACKAGE_ID;target.parent.mkdir(parents=True);shutil.copytree(REPO_ROOT/"tests/fixtures/sdk_packages/valid/addons"/PACKAGE_ID,target);text=(target/"manifest.json").read_text(encoding="utf-8");manifest=json.loads(text)
    import app.persistence.database as db_module
    from app.persistence import engine as engine_module
    from app.persistence.repositories.installed_package_repository import InstalledPackageRepository
    from app.persistence.repositories.campaign_package_repository import CampaignPackageRepository
    from app.persistence.repositories.scene_repository import SceneRepository
    from tests.conftest import seed_member,seed_scene,seed_user
    db_module.DATABASE_PATH=db_path.resolve();db_module._initialized=False;engine_module.reset_engine();player_b=seed_user(name="Runtime Player B",email=PLAYER_B_EMAIL);seed_member(seeded["campaign_id"],player_b,"player");a=seed_scene(seeded["campaign_id"],name="Runtime A");b=seed_scene(seeded["campaign_id"],name="Runtime B");SceneRepository().set_active_scene(campaign_id=seeded["campaign_id"],scene_id=a["id"]);seeded.update(player_b_id=player_b,scene_a=a["id"],scene_b=b["id"])
    InstalledPackageRepository().upsert(package_id=PACKAGE_ID,kind="addon",name=manifest["name"],version=manifest["version"],status="enabled",package_dir=f"addons/{PACKAGE_ID}",manifest_json=text,compatibility_status="compatible",validation_errors_json="[]",installed_by_user_id=seeded["gm_id"],last_validation_status="valid");CampaignPackageRepository().activate(campaign_id=seeded["campaign_id"],package_id=PACKAGE_ID,activation_role="addon",enabled_by_user_id=seeded["gm_id"]);engine_module.reset_engine()
    port=_free_port();base=f"http://127.0.0.1:{port}";env=os.environ.copy();env.update({"APP_ENV":"test","DATABASE_URL":f"sqlite:///{db_path.resolve().as_posix()}","ALLOWED_HOSTS":"*","WS_ALLOWED_ORIGINS":base,"SESSION_COOKIE_SECURE":"false","ALLOW_METADATA_BOOTSTRAP":"true","GRAVEWRIGHT_TEST_TEMP_ROOT":str(tmp.resolve()),"GRAVEWRIGHT_DATA_DIR":str(data.resolve())});proc=subprocess.Popen([sys.executable,"-m","uvicorn","main:app","--host","127.0.0.1","--port",str(port),"--log-level","warning"],cwd=str(REPO_ROOT),env=env)
    try:_wait_http_ready(f"{base}/login",proc=proc);yield {"base_url":base,**seeded}
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):proc.wait(timeout=10)
        if proc.poll() is None:proc.kill()

def test_audio_navigation_and_input_representative_multiplayer(runtime_server):
    s=runtime_server;base=s["base_url"];url=f"{base}/game?room={s['campaign_id']}"
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);gm_c=browser.new_context();a_c=browser.new_context();b_c=browser.new_context()
        try:
            gm=gm_c.new_page();a=a_c.new_page();b=b_c.new_page();_login(gm,base,GM_EMAIL,GM_PASSWORD);_login(a,base,PLAYER_EMAIL,PLAYER_PASSWORD);_login(b,base,PLAYER_B_EMAIL,PLAYER_PASSWORD);gm.goto(url);a.goto(url);b.goto(url);gm.locator("[data-onboarding-close]").first.click();a.reload();b.reload();controls=gm.get_by_test_id("scene-runtime-controls");expect(controls).to_be_attached()
            gm.get_by_test_id("scene-runtime-users").fill(s["player_id"]);gm.get_by_test_id("scene-runtime-audio").click();gm.wait_for_function("document.body.dataset.sceneRuntimePlaybackId");playback=gm.locator("body").get_attribute("data-scene-runtime-playback-id");assert playback
            a.wait_for_function("id => window.GravewrightAudioRuntime?.inspect(id)!==null",arg=playback);assert b.evaluate("id => window.GravewrightAudioRuntime?.inspect(id)===null",playback)
            a.reload();a.wait_for_function("id => window.GravewrightAudioRuntime?.inspect(id)!==null",arg=playback);a.wait_for_timeout(350);projection=a.evaluate("id => window.GravewrightAudioRuntime.inspect(id)",playback);assert projection["fading"] and 0<=projection["volume"]<=.8
            gm.get_by_test_id("scene-runtime-scene").fill(s["scene_b"]);gm.get_by_test_id("scene-runtime-nav").click();expect(a.locator(f'[data-map-canvas][data-scene-id="{s["scene_b"]}"]')).to_be_attached(timeout=10000);expect(b.locator(f'[data-map-canvas][data-scene-id="{s["scene_a"]}"]')).to_be_attached();a.reload();expect(a.locator(f'[data-map-canvas][data-scene-id="{s["scene_b"]}"]')).to_be_attached();assert a.locator("[data-token-id]").count()==0
            executions=[];gm.on("request",lambda request:executions.append(request.post_data or "") if "/sdk/runtime/command/input.execute" in request.url else None);settle=lambda:gm.evaluate("() => new Promise(done => requestAnimationFrame(() => done(true)))")
            # A local semantic command opens a package application. The handler sees
            # resolved metadata only, and never reaches the server.
            gm.keyboard.press("Alt+u");expect(gm.get_by_test_id("scene-runtime-console-body")).to_be_visible()
            assert gm.locator("body").get_attribute("data-scene-runtime-invocation")=="binding,commandId,context,packageId,source"
            assert gm.locator("body").get_attribute("data-scene-runtime-invocation-command")=="open-console/binding/Alt+U"
            assert executions==[],"a local-only command must not reach the server"
            # A server-bound command runs its registered action from pre-bound input.
            gm.keyboard.press("Shift+H");gm.wait_for_function("() => document.body.dataset.sceneRuntimeCompletions==='1'")
            assert len(executions)==1 and "inputs" not in json.loads(executions[0])["payload"]
            gm.get_by_test_id("scene-runtime-read").click();gm.wait_for_function("() => document.body.dataset.sceneRuntimeCommandHit==='true'")
            # Hot rebind: the declared binding event arrives and the old key goes inert.
            gm.get_by_test_id("scene-runtime-rebind").click();gm.wait_for_function("() => document.body.dataset.sceneRuntimeBinding==='Ctrl+J'");gm.wait_for_function("() => document.body.dataset.sceneRuntimeBindingEvent==='1'")
            gm.keyboard.press("Shift+H");gm.keyboard.press("Control+J");gm.wait_for_function("() => document.body.dataset.sceneRuntimeCompletions==='2'")
            assert len(executions)==2,"the retired binding is inert and the new one fires once"
            # Typing suppresses a text-input-excluded command; the next free press proves
            # the command itself still works, so the gap can only be the suppression.
            gm.get_by_test_id("scene-runtime-users").focus();gm.keyboard.press("Control+J");gm.keyboard.press("Alt+u");settle()
            gm.evaluate("() => document.activeElement?.blur()");gm.keyboard.press("Control+J");gm.wait_for_function("() => document.body.dataset.sceneRuntimeCompletions==='3'")
            assert len(executions)==3,"the suppressed press contributed nothing"
            status=gm.evaluate("""async ({campaignId,csrf})=>{const body=new URLSearchParams({campaign_id:campaignId,package_id:'scene-runtime-e2e'});const response=await fetch('/sdk/campaigns/packages/deactivate',{method:'POST',credentials:'same-origin',headers:{Accept:'application/json','Content-Type':'application/x-www-form-urlencoded','x-csrftoken':csrf},body});return response.status;}""",{"campaignId":s["campaign_id"],"csrf":_csrf(gm)});assert status in {200,201};expect(gm.get_by_test_id("scene-runtime-controls")).to_have_count(0,timeout=10000);gm.keyboard.press("Control+J");settle();assert len(executions)==3,"a deactivated package leaves no live binding"
        finally:_close(b_c);_close(a_c);_close(gm_c);browser.close()
