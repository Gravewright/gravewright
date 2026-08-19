from __future__ import annotations

import contextlib,json,os,subprocess,sys,time
import pytest
from playwright.sync_api import sync_playwright

from tests.e2e.test_app_server_e2e import GM_EMAIL,GM_PASSWORD,PLAYER_EMAIL,PLAYER_PASSWORD,REPO_ROOT,_free_port,_seed_database,_wait_http_ready
from tests.e2e.test_multiplayer_playwright import _close,_csrf,_login

PACKAGE_ID="semantic-runtime-runtime-e2e";PLAYER_B_EMAIL="semantic-runtime-player-b@test.com"
CAPS=["workflows.read","workflows.start","workflows.control","gameplay.flows.read","gameplay.flows.manage","gameplay.flows.participate","tokens.read","tokens.transfer","timelines.read","timelines.start","timelines.control","interactions.respond","audio.playback","ui.presentations","navigation.scene","scene.geometry.write","scene.shaders.write","scene.effects.write"]


@pytest.fixture(scope="module")
def semantic_runtime_server(tmp_path_factory):
    tmp=tmp_path_factory.mktemp("semantic-runtime-runtime");db_path=tmp/"e2e.sqlite3";seeded=_seed_database(db_path);data=tmp/"data";package=data/"packages/addons"/PACKAGE_ID;package.mkdir(parents=True)
    manifest={"schemaVersion":1,"sdkVersion":"1","kind":"addon","id":PACKAGE_ID,"name":"Wave 4 E2E","version":"1.0.0","authors":["Test"],"license":"MIT","compatibility":{"minimum":"1","verified":"1","maximum":"1.x"},"capabilities":CAPS,"activation":{"scope":"campaign","mode":"multiple"},"entrypoints":{},"provides":{"assets":{"audio":[{"id":"thunder","label":"Thunder","path":"thunder.ogg"}]}}}
    text=json.dumps(manifest);(package/"manifest.json").write_text(text,encoding="utf-8");(package/"thunder.ogg").write_bytes(b"OggS")
    import app.persistence.database as db_module
    from app.persistence import engine as engine_module
    from app.persistence.repositories.actor_repository import ActorRepository
    from app.persistence.repositories.campaign_package_repository import CampaignPackageRepository
    from app.persistence.repositories.installed_package_repository import InstalledPackageRepository
    from app.persistence.repositories.scene_repository import SceneRepository
    from app.persistence.repositories.token_repository import TokenRepository
    from tests.conftest import seed_member,seed_scene,seed_user
    db_module.DATABASE_PATH=db_path.resolve();db_module._initialized=False;engine_module.reset_engine()
    player_b=seed_user(name="SemanticRuntime Player B",email=PLAYER_B_EMAIL);seed_member(seeded["campaign_id"],player_b,"player")
    a=seed_scene(seeded["campaign_id"],name="Portal A");b=seed_scene(seeded["campaign_id"],name="Portal B");SceneRepository().set_active_scene(campaign_id=seeded["campaign_id"],scene_id=a["id"])
    actor=ActorRepository().create(campaign_id=seeded["campaign_id"],system_id="system",actor_type="hero",name="Portal Hero",created_by_user_id=seeded["gm_id"],owner_user_ids=[seeded["player_id"]])
    token=TokenRepository().create(scene_id=a["id"],actor_id=actor,grid_x=1,grid_y=1)
    seeded.update(player_b_id=player_b,scene_a=a["id"],scene_b=b["id"],portal_token=token["id"],portal_token_version=token["version"])
    InstalledPackageRepository().upsert(package_id=PACKAGE_ID,kind="addon",name=manifest["name"],version=manifest["version"],status="enabled",package_dir=f"addons/{PACKAGE_ID}",manifest_json=text,compatibility_status="compatible",validation_errors_json="[]",installed_by_user_id=seeded["gm_id"],last_validation_status="valid")
    CampaignPackageRepository().activate(campaign_id=seeded["campaign_id"],package_id=PACKAGE_ID,activation_role="addon",enabled_by_user_id=seeded["gm_id"]);engine_module.reset_engine()
    port=_free_port();base=f"http://127.0.0.1:{port}";env=os.environ.copy();env.update({"APP_ENV":"test","DATABASE_URL":f"sqlite:///{db_path.resolve().as_posix()}","ALLOWED_HOSTS":"*","WS_ALLOWED_ORIGINS":base,"SESSION_COOKIE_SECURE":"false","ALLOW_METADATA_BOOTSTRAP":"true","GRAVEWRIGHT_TEST_TEMP_ROOT":str(tmp.resolve()),"GRAVEWRIGHT_DATA_DIR":str(data.resolve())})
    proc=subprocess.Popen([sys.executable,"-m","uvicorn","main:app","--host","127.0.0.1","--port",str(port),"--log-level","warning"],cwd=str(REPO_ROOT),env=env)
    try:_wait_http_ready(f"{base}/login",proc=proc);yield {"base_url":base,**seeded}
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):proc.wait(timeout=10)
        if proc.poll() is None:proc.kill()


def _cmd(page,s,name,payload):
    return page.evaluate("""async x=>{const r=await fetch('/sdk/runtime/command/'+x.name,{method:'POST',credentials:'same-origin',headers:{'content-type':'application/json','x-csrftoken':x.csrf},body:JSON.stringify({campaign_id:x.campaign,package_id:x.package,payload:x.payload})});return {status:r.status,body:await r.json()};}""",{"name":name,"campaign":s["campaign_id"],"package":PACKAGE_ID,"payload":payload,"csrf":_csrf(page)})


def _read(page,s,resource,extra=None):
    return page.evaluate("""async x=>{const q=new URLSearchParams({campaign_id:x.campaign,package_id:x.package,...x.extra});const r=await fetch('/sdk/runtime/read/'+x.resource+'?'+q,{credentials:'same-origin'});return {status:r.status,body:await r.json()};}""",{"resource":resource,"campaign":s["campaign_id"],"package":PACKAGE_ID,"extra":extra or {}})


def test_reaction_workflow_survives_player_reload(semantic_runtime_server):
    s=semantic_runtime_server;base=s["base_url"]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);gm_c=browser.new_context();pl_c=browser.new_context()
        try:
            gm=gm_c.new_page();player=pl_c.new_page();_login(gm,base,GM_EMAIL,GM_PASSWORD);_login(player,base,PLAYER_EMAIL,PLAYER_PASSWORD);gm.goto(base+"/inside");player.goto(base+"/inside")
            definition={"id":"reaction","schemaVersion":1,"steps":[{"type":"INTERACTION","request":{"recipients":[s["player_id"]],"title":"Reaction","text":"React?","responseSchema":{"type":"boolean"},"deadline":int(time.time())+300}},{"type":"COMPLETE"}]}
            assert _cmd(gm,s,"workflows.register",{"definition":definition})["status"]==201
            workflow=_cmd(gm,s,"workflows.start",{"input":{"definitionId":"reaction","idempotencyKey":"reaction-e2e"}})["body"]["workflow"]
            assert workflow["status"]=="WAITING_INTERACTION";player.reload()
            interaction=_read(player,s,"interactions",{"entity_id":workflow["waitingOn"]})["body"]["interaction"]
            assert interaction["status"]=="open"
            assert _cmd(player,s,"interactions.respond",{"id":interaction["id"],"response":True,"expectedVersion":interaction["version"],"idempotencyKey":"answer"})["status"] in {200,201}
            assert _read(gm,s,"workflows",{"entity_id":workflow["id"]})["body"]["workflow"]["status"]=="COMPLETED"
        finally:_close(pl_c);_close(gm_c);browser.close()


def test_simultaneous_secret_reveal_and_phased_flow(semantic_runtime_server):
    s=semantic_runtime_server;base=s["base_url"]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);gm_c=browser.new_context();a_c=browser.new_context();b_c=browser.new_context()
        try:
            gm=gm_c.new_page();a=a_c.new_page();b=b_c.new_page();_login(gm,base,GM_EMAIL,GM_PASSWORD);_login(a,base,PLAYER_EMAIL,PLAYER_PASSWORD);_login(b,base,PLAYER_B_EMAIL,"Password1!");gm.goto(base+"/inside");a.goto(base+"/inside");b.goto(base+"/inside")
            definition={"id":"secret","schemaVersion":1,"turnModel":"SIMULTANEOUS","phases":[{"id":"plan"},{"id":"reveal"}]};_cmd(gm,s,"gameplay.flows.register",{"definition":definition})
            flow=_cmd(gm,s,"gameplay.flows.start",{"input":{"definitionId":"secret","participants":[s["player_id"],s["player_b_id"]],"idempotencyKey":"secret-e2e"}})["body"]["flow"]
            one=_cmd(a,s,"gameplay.flows.submit",{"id":flow["id"],"value":{"order":"north"},"expectedVersion":flow["version"]})["body"]["flow"]
            assert _read(b,s,"gameplay.flows",{"entity_id":flow["id"]})["body"]["flow"]["submissions"]=={}
            two=_cmd(b,s,"gameplay.flows.submit",{"id":flow["id"],"value":{"order":"south"},"expectedVersion":one["version"]})["body"]["flow"]
            assert two["revealed"] and len(two["submissions"])==2
            phased={"id":"wargame","schemaVersion":1,"turnModel":"PHASED","phases":[{"id":"movement"},{"id":"shooting"},{"id":"combat"},{"id":"end"}]};_cmd(gm,s,"gameplay.flows.register",{"definition":phased})
            state=_cmd(gm,s,"gameplay.flows.start",{"input":{"definitionId":"wargame","participants":[s["player_id"]],"idempotencyKey":"war-e2e"}})["body"]["flow"]
            for phase in ("shooting","combat","end"):
                state=_cmd(gm,s,"gameplay.flows.advance",{"id":state["id"],"expectedVersion":state["version"]})["body"]["flow"];assert state["phaseId"]==phase
        finally:_close(b_c);_close(a_c);_close(gm_c);browser.close()


def test_portal_transfer_preserves_identity_navigation_and_reload(semantic_runtime_server):
    s=semantic_runtime_server;base=s["base_url"]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);gm_c=browser.new_context();pl_c=browser.new_context()
        try:
            gm=gm_c.new_page();player=pl_c.new_page();_login(gm,base,GM_EMAIL,GM_PASSWORD);_login(player,base,PLAYER_EMAIL,PLAYER_PASSWORD);gm.goto(base+"/inside");player.goto(base+"/inside")
            moved=_cmd(gm,s,"tokens.transfer",{"input":{"tokenId":s["portal_token"],"sceneId":s["scene_b"],"x":7,"y":8,"expectedVersion":s["portal_token_version"],"navigateAudience":{"kind":"users","ids":[s["player_id"]]}}})["body"]["transfer"]["tokens"][0]
            assert moved["id"]==s["portal_token"] and (moved["x"],moved["y"])==(7,8);player.reload()
            token=_read(player,s,"tokens",{"entity_id":s["portal_token"],"scene_id":s["scene_b"]})["body"]["token"]
            assert token["id"]==s["portal_token"] and token["scene_id"]==s["scene_b"]
        finally:_close(pl_c);_close(gm_c);browser.close()


def test_artistic_and_scene_transition_timelines(semantic_runtime_server):
    s=semantic_runtime_server;base=s["base_url"]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);gm_c=browser.new_context()
        try:
            gm=gm_c.new_page();_login(gm,base,GM_EMAIL,GM_PASSWORD);gm.goto(base+"/inside")
            cues=[{"cueId":"sound","offsetMs":0,"type":"AUDIO_PLAY","parameters":{"asset":{"kind":"package-asset","id":"thunder.ogg"},"channel":"sfx","audience":{"kind":"self"}}},{"cueId":"title","offsetMs":0,"type":"PRESENTATION_SHOW","parameters":{"mode":"title-card","content":{"title":"Thunder"},"audience":{"kind":"self"},"duration":2}},{"cueId":"light","offsetMs":0,"type":"LIGHT_CREATE","parameters":{"sceneId":s["scene_b"],"x":10,"y":10,"bright_radius":2,"dim_radius":4,"color":"#ffffff","intensity":1}},{"cueId":"shader","offsetMs":0,"type":"SHADER_PRESET","parameters":{"sceneId":s["scene_b"],"presetId":"weather-1","schemaVersion":1,"parameters":{}}},{"cueId":"particles","offsetMs":0,"type":"PARTICLE_CREATE","parameters":{"sceneId":s["scene_b"],"x":10,"y":10,"kind":"rain","scale":2,"density":0.5}},{"cueId":"navigation","offsetMs":0,"type":"NAVIGATION","parameters":{"sceneId":s["scene_b"],"recipients":{"kind":"self"}}}]
            assert _cmd(gm,s,"timelines.register",{"definition":{"id":"thunder","schemaVersion":1,"cues":cues}})["status"]==201
            timeline=_cmd(gm,s,"timelines.start",{"input":{"definitionId":"thunder","sceneId":s["scene_b"],"idempotencyKey":"thunder-e2e"}})["body"]["timeline"]
            assert timeline["status"]=="COMPLETED" and len(timeline["executedCueIds"])==6, (timeline.get("completionReason"),timeline.get("executedCueIds"))
            gm.reload();assert _read(gm,s,"timelines",{"entity_id":timeline["id"]})["body"]["timeline"]["status"]=="COMPLETED"
        finally:_close(gm_c);browser.close()
