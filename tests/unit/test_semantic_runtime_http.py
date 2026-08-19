from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_scene, seed_user
from tests.unit.test_sdk_runtime_expansion import _install_runtime_addon


CAPS=["workflows.read","workflows.start","workflows.control","gameplay.flows.read","gameplay.flows.manage","gameplay.flows.participate","tokens.transfer","timelines.read","timelines.start","timelines.control"]


def _command(client,campaign,name,payload):
    return client.post(f"/sdk/runtime/command/{name}",json={"campaign_id":campaign,"package_id":"runtime-addon","payload":payload})


def test_semantic_runtime_http_contract_routes_all_domains(db,tmp_path,monkeypatch):
    from main import app
    from app.persistence.repositories.token_repository import TokenRepository
    gm=seed_user();campaign=seed_campaign(gm);a=seed_scene(campaign,name="A");b=seed_scene(campaign,name="B")
    token=TokenRepository().create(scene_id=a["id"],actor_id=None,grid_x=0,grid_y=0)
    _install_runtime_addon(tmp_path,monkeypatch,gm,campaign,CAPS)
    with TestClient(app=app,session_config=TEST_SESSION_CONFIG) as client:
        login(client,gm)
        registered=_command(client,campaign,"workflows.register",{"definition":{"id":"simple","schemaVersion":1,"steps":[{"type":"COMPLETE"}]}})
        assert registered.status_code==201
        workflow=_command(client,campaign,"workflows.start",{"input":{"definitionId":"simple","idempotencyKey":"wf"}}).json()["workflow"]
        assert workflow["status"]=="COMPLETED"
        assert client.get("/sdk/runtime/read/workflows",params={"campaign_id":campaign,"package_id":"runtime-addon","entity_id":workflow["id"]}).json()["workflow"]["id"]==workflow["id"]

        flow_definition={"id":"phases","schemaVersion":1,"turnModel":"PHASED","phases":[{"id":"move"},{"id":"end"}]}
        assert _command(client,campaign,"gameplay.flows.register",{"definition":flow_definition}).status_code==201
        flow=_command(client,campaign,"gameplay.flows.start",{"input":{"definitionId":"phases","participants":[gm],"idempotencyKey":"flow"}}).json()["flow"]
        advanced=_command(client,campaign,"gameplay.flows.advance",{"id":flow["id"],"expectedVersion":flow["version"]}).json()["flow"]
        assert advanced["phaseId"]=="end"

        transfer=_command(client,campaign,"tokens.transfer",{"input":{"tokenId":token["id"],"sceneId":b["id"],"x":2,"y":3,"expectedVersion":token["version"]}})
        assert transfer.status_code in {200,201} and transfer.json()["transfer"]["tokens"][0]["id"]==token["id"]

        timeline_definition={"id":"nav","schemaVersion":1,"cues":[{"cueId":"navigate","offsetMs":0,"type":"NAVIGATION","parameters":{"sceneId":b["id"],"recipients":{"kind":"self"}}}]}
        assert _command(client,campaign,"timelines.register",{"definition":timeline_definition}).status_code==201
        timeline=_command(client,campaign,"timelines.start",{"input":{"definitionId":"nav","idempotencyKey":"timeline"}}).json()["timeline"]
        assert timeline["status"]=="COMPLETED"


def test_semantic_runtime_http_rejects_missing_capability_and_raw_callback(db,tmp_path,monkeypatch):
    from main import app
    gm=seed_user();campaign=seed_campaign(gm);_install_runtime_addon(tmp_path,monkeypatch,gm,campaign,["workflows.start"])
    with TestClient(app=app,session_config=TEST_SESSION_CONFIG) as client:
        login(client,gm)
        raw=_command(client,campaign,"workflows.register",{"definition":{"id":"bad","schemaVersion":1,"steps":[{"type":"ACTION","callback":"alert(1)"}]}})
        read=client.get("/sdk/runtime/read/workflows",params={"campaign_id":campaign,"package_id":"runtime-addon"})
    assert raw.status_code==400 and read.status_code==403 and read.json()["error"]["code"]=="CAPABILITY_REQUIRED"
