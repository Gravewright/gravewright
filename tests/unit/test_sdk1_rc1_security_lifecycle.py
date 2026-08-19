"""RC 1 security and lifecycle gate.

Representative certification of the invariants the SDK promises, asserted at the
public runtime boundary rather than inside the services that implement them.
"""

from __future__ import annotations

import time

from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user
from tests.unit.test_sdk_runtime_expansion import _install_runtime_addon


CAPS = [
    "scene.read", "scene.zones.read", "scene.zones.write", "workflows.start", "workflows.read",
    "timelines.start", "gameplay.flows.manage", "gameplay.flows.participate", "gameplay.flows.read",
    "interactions.request", "interactions.respond", "tokens.read", "campaign.members.read",
]


def _world():
    gm = seed_user(name="GM")
    a = seed_user(name="Player A")
    b = seed_user(name="Player B")
    campaign = seed_campaign(gm)
    seed_member(campaign, a, "player")
    seed_member(campaign, b, "player")
    return gm, a, b, campaign


def _command(client, campaign, name, payload):
    return client.post(f"/sdk/runtime/command/{name}",
                       json={"campaign_id": campaign, "package_id": "runtime-addon", "payload": payload})


def _read(client, campaign, resource, **params):
    return client.get(f"/sdk/runtime/read/{resource}",
                      params={"campaign_id": campaign, "package_id": "runtime-addon", **params})


# --- no arbitrary execution ----------------------------------------------------

def test_declarative_definitions_reject_everything_outside_the_closed_enums(db, tmp_path, monkeypatch):
    from main import app

    gm, a, _b, campaign = _world()
    scene = seed_scene(campaign)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, CAPS)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        for definition in (
            {"id": "escape", "schemaVersion": 1, "steps": [{"type": "CALLBACK", "url": "https://evil"}]},
            {"id": "escape", "schemaVersion": 1, "steps": [{"type": "EVAL", "code": "1"}]},
            {"id": "escape", "schemaVersion": 1,
             "steps": [{"type": "ACTION", "action": "some-other-package:evil@1"}]},
            {"id": "escape", "schemaVersion": 1,
             "steps": [{"type": "SET", "key": "x", "value": 1},
                       {"type": "BRANCH", "key": "x", "equals": 1, "then": 0, "else": 0}]},
        ):
            assert _command(client, campaign, "workflows.register",
                            {"definition": definition}).status_code not in {200, 201}

        for cue in (
            {"cueId": "sql", "offsetMs": 0, "type": "SQL", "parameters": {"q": "DROP TABLE tokens"}},
            {"cueId": "glsl", "offsetMs": 0, "type": "SHADER_SOURCE", "parameters": {"source": "void main(){}"}},
            {"cueId": "raw", "offsetMs": 0, "type": "ACTION", "action": "other:evil@1"},
        ):
            assert _command(client, campaign, "timelines.register",
                            {"definition": {"id": "bad", "schemaVersion": 1, "cues": [cue]}}
                            ).status_code not in {200, 201}

        # An unknown command is a closed-enum miss, never a route to something else.
        assert _command(client, campaign, "system.exec", {"cmd": "ls"}).status_code == 404
        assert _read(client, campaign, "database").status_code in {403, 404}
        assert scene["id"] and a


# --- authority, impersonation, audience ---------------------------------------

def test_no_permission_elevation_or_impersonation_through_the_runtime(db, tmp_path, monkeypatch):
    from main import app

    gm, a, b, campaign = _world()
    scene = seed_scene(campaign)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, CAPS)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        interaction = _command(client, campaign, "interactions.request", {"input": {
            "recipients": [a], "title": "Decide", "text": "Choose",
            "responseSchema": {"type": "boolean"}, "deadline": int(time.time()) + 300,
        }}).json()["interaction"]

        # The requester cannot answer for the recipient.
        assert _command(client, campaign, "interactions.respond", {
            "id": interaction["id"], "response": True, "idempotencyKey": "gm"}).status_code not in {200, 201}

        login(client, b)
        # Nor can an unrelated participant.
        assert _command(client, campaign, "interactions.respond", {
            "id": interaction["id"], "response": True, "idempotencyKey": "b"}).status_code not in {200, 201}
        # A player cannot claim GM-only authority.
        assert _command(client, campaign, "zones.create", {"sceneId": scene["id"], "values": {
            "type": "runtime-addon.zone",
            "geometry": {"shape": "rect", "x": 0, "y": 0, "width": 10, "height": 10}}}
        ).status_code not in {200, 201}
        # A player cannot address an audience wider than themselves.
        _command(client, campaign, "timelines.register", {"definition": {
            "id": "aud", "schemaVersion": 1,
            "cues": [{"cueId": "c", "offsetMs": 0, "type": "PRESENTATION_SHOW", "parameters": {
                "mode": "title-card", "content": {"title": "x"}, "audience": {"kind": "campaign"}}}]}})
        assert _command(client, campaign, "timelines.start", {"input": {
            "definitionId": "aud", "sceneId": scene["id"], "audience": {"kind": "campaign"},
            "idempotencyKey": "aud"}}).status_code not in {200, 201}

        login(client, a)
        answered = _command(client, campaign, "interactions.respond", {
            "id": interaction["id"], "response": True, "idempotencyKey": "a"})
        assert answered.status_code in {200, 201}, answered.text


def test_cross_campaign_reads_and_writes_are_closed(db, tmp_path, monkeypatch):
    from main import app

    gm, _a, _b, campaign = _world()
    other_gm = seed_user(name="Other GM")
    other_campaign = seed_campaign(other_gm)
    other_scene = seed_scene(other_campaign)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, CAPS)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        for resource in ("scenes", "campaign.members", "workflows", "gameplay.flows"):
            response = _read(client, other_campaign, resource)
            assert response.status_code == 403, resource
        assert _command(client, campaign, "zones.create", {"sceneId": other_scene["id"], "values": {
            "type": "runtime-addon.zone",
            "geometry": {"shape": "rect", "x": 0, "y": 0, "width": 10, "height": 10}}}
        ).status_code not in {200, 201}


def test_stale_version_is_enforced_on_public_mutations(db, tmp_path, monkeypatch):
    from main import app

    gm, a, b, campaign = _world()
    scene = seed_scene(campaign)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, CAPS)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        zone = _command(client, campaign, "zones.create", {"sceneId": scene["id"], "values": {
            "type": "runtime-addon.zone",
            "geometry": {"shape": "rect", "x": 0, "y": 0, "width": 10, "height": 10}}}).json()["zone"]
        stale = _command(client, campaign, "zones.update", {
            "id": zone["id"], "patch": {"enabled": False}, "expectedVersion": 999})
        assert stale.status_code == 409
        assert _read(client, campaign, "scene.zones", entity_id=zone["id"]).json()["zone"]["enabled"] is True
        assert a and b


# --- lifecycle -----------------------------------------------------------------

def test_durable_primitives_survive_reload_and_close_on_package_unload(db, tmp_path, monkeypatch):
    from main import app
    from app.engine.sdk.package_activation_service import PackageActivationService
    from app.engine.sdk.durable_workflow_service import DurableWorkflowService

    gm, a, _b, campaign = _world()
    scene = seed_scene(campaign)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, CAPS)
    definition = {"id": "wait", "schemaVersion": 1, "steps": [
        {"type": "INTERACTION", "request": {
            "recipients": [a], "title": "Hold", "text": "Hold",
            "responseSchema": {"type": "boolean"}, "deadline": int(time.time()) + 900}},
        {"type": "COMPLETE"}]}

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        _command(client, campaign, "workflows.register", {"definition": definition})
        workflow = _command(client, campaign, "workflows.start", {"input": {
            "definitionId": "wait", "sceneId": scene["id"], "idempotencyKey": "rc1"}}).json()["workflow"]
        assert workflow["status"] == "WAITING_INTERACTION"

    # Reload / reconnect: a cold session still sees the pending decision.
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, a)
        pending = _read(client, campaign, "interactions", status="open", recipient="me").json()["interactions"]
        assert [value["id"] for value in pending] == [workflow["waitingOn"]]

    # Server restart: recovery drives durable state, not an in-memory handle.
    assert DurableWorkflowService().recover_campaign(campaign, int(time.time())) is not None

    # Package unload closes the waiting primitive rather than orphaning it.
    assert PackageActivationService().deactivate_package(campaign, "runtime-addon", gm).success
    row = DurableWorkflowService().instances.get(workflow["id"])
    assert row["status"] == "CANCELLED"
    assert row["payload"]["completionReason"] == "package-unload"

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert _command(client, campaign, "workflows.start", {"input": {
            "definitionId": "wait", "sceneId": scene["id"],
            "idempotencyKey": "after-unload"}}).status_code == 403


def test_a_provider_that_disappears_fails_its_instances_closed(db, tmp_path, monkeypatch):
    from app.engine.sdk.durable_workflow_service import DurableWorkflowService
    from app.persistence.repositories.semantic_instance_repository import SemanticInstanceRepository

    gm, _a, _b, campaign = _world()
    service = DurableWorkflowService()
    service.register(campaign_id=campaign, package_id="runtime-addon", definition={
        "id": "gone", "schemaVersion": 1, "steps": [{"type": "WAIT_UNTIL", "delaySeconds": 0}]})
    started = service.start(campaign_id=campaign, user_id=gm, package_id="runtime-addon",
                            values={"definitionId": "gone", "idempotencyKey": "provider"}).value

    changed = SemanticInstanceRepository().fail_closed_package(campaign, "runtime-addon")
    assert changed and changed[0]["id"] == started["id"]
    assert changed[0]["status"] == "CANCELLED"
