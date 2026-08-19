"""Black Vault RC 1 mission conformance.

These tests drive the shipped package's own definitions through the public SDK
runtime exactly as `black-vault.js` does, so a regression in the public contract
fails here rather than in a hand-written fixture.
"""

import json
import shutil
import time
from pathlib import Path

from litestar.testing import TestClient

from app.engine.sdk.durable_workflow_service import DurableWorkflowService
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user


PACKAGE_ID = "black-vault"
PACKAGE_DIR = Path(__file__).resolve().parents[2] / "examples" / "packages" / PACKAGE_ID
MANIFEST = json.loads((PACKAGE_DIR / "manifest.json").read_text(encoding="utf-8"))


def install(tmp_path, monkeypatch, gm, campaign):
    from app.engine.sdk import package_registry
    from app.engine.sdk.package_activation_service import PackageActivationService
    from app.engine.sdk.package_install_service import PackageInstallService

    root = tmp_path / "packages"
    (root / "addons").mkdir(parents=True)
    shutil.copytree(PACKAGE_DIR, root / "addons" / PACKAGE_ID)
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", root)
    installed = PackageInstallService().install(package_id=PACKAGE_ID, user_id=gm)
    assert installed.success, installed.error_key
    assert PackageInstallService().enable(package_id=PACKAGE_ID).success
    assert PackageActivationService().activate_package(campaign, PACKAGE_ID, gm).success


def command(client, campaign, name, payload):
    return client.post(f"/sdk/runtime/command/{name}",
                       json={"campaign_id": campaign, "package_id": PACKAGE_ID, "payload": payload})


def read(client, campaign, resource, **params):
    return client.get(f"/sdk/runtime/read/{resource}",
                      params={"campaign_id": campaign, "package_id": PACKAGE_ID, **params})


def world():
    gm = seed_user(name="GM")
    a = seed_user(name="Player A")
    b = seed_user(name="Player B")
    campaign = seed_campaign(gm)
    seed_member(campaign, a, "player")
    seed_member(campaign, b, "player")
    return gm, a, b, campaign


def systems_actor(campaign, gm):
    from app.persistence.repositories.actor_repository import ActorRepository

    return ActorRepository().create(campaign_id=campaign, system_id="core", actor_type="character",
                                    name="Vault Systems", created_by_user_id=gm)


# --- the package's own definitions, read from the shipped source ---------------

def alarm_workflow(actor_id, eligible, deadline):
    return {"id": "alarm-response", "schemaVersion": 1, "maxDuration": 3600, "steps": [
        {"type": "ACTION", "action": f"{PACKAGE_ID}:alarm.raise@1", "input": {"actorId": actor_id}},
        {"type": "INTERACTION", "resultKey": "jammerDecision", "request": {
            "kind": "black-vault.jammer", "recipients": [eligible],
            "title": "Bloqueador EMP", "text": "Usar bloqueador EMP?",
            "responseSchema": {"type": "single-choice", "choices": [
                {"id": "USE_JAMMER", "label": "Usar bloqueador EMP"},
                {"id": "DECLINE", "label": "Deixar o alarme soar"}]},
            "visibility": "requester", "deadline": deadline, "responsePolicy": "immutable"}},
        {"type": "BRANCH", "key": "jammerDecision", "equals": "USE_JAMMER", "then": 3, "else": 4},
        {"type": "ACTION", "action": f"{PACKAGE_ID}:alarm.suppress@1", "input": {"actorId": actor_id}},
        {"type": "COMPLETE", "reason": "alarm-resolved"},
    ]}


def terminal_workflow(actor_id, eligible, deadline, quiet=0, fast=0):
    return {"id": "terminal-hack", "schemaVersion": 1, "maxDuration": 3600, "steps": [
        {"type": "INTERACTION", "resultKey": "overrideMode", "request": {
            "kind": "black-vault.override", "recipients": [eligible],
            "title": "Vault Terminal", "text": "Escolha o modo de override.",
            "responseSchema": {"type": "single-choice", "choices": [
                {"id": "QUIET_OVERRIDE", "label": "Quiet Override"},
                {"id": "FAST_OVERRIDE", "label": "Fast Override"}]},
            "visibility": "requester", "deadline": deadline, "responsePolicy": "immutable"}},
        {"type": "BRANCH", "key": "overrideMode", "equals": "QUIET_OVERRIDE", "then": 2, "else": 4},
        {"type": "WAIT_UNTIL", "delaySeconds": quiet},
        {"type": "BRANCH", "key": "overrideMode", "equals": "QUIET_OVERRIDE", "then": 6, "else": 6},
        {"type": "WAIT_UNTIL", "delaySeconds": fast},
        {"type": "ACTION", "action": f"{PACKAGE_ID}:vault.trace@1", "input": {"actorId": actor_id}},
        {"type": "ACTION", "action": f"{PACKAGE_ID}:vault.unlock@1", "input": {"actorId": actor_id}},
        {"type": "COMPLETE", "reason": "vault-open"},
    ]}


def answer(client, campaign, interaction_id, choice):
    fetched = read(client, campaign, "interactions", entity_id=interaction_id).json().get("interaction")
    return command(client, campaign, "interactions.respond", {
        "id": interaction_id, "response": choice,
        "expectedVersion": fetched["version"] if fetched else None,
        "idempotencyKey": f"answer:{choice}"})


def sheet(campaign, actor_id, gm):
    from app.engine.sheets.sheet_data_service import SheetDataService

    return (SheetDataService().get_data(actor_id=actor_id, user_id=gm).data or {}).get("blackVault", {})


def _run_branch(client, campaign, gm, player, scene, actor, definition, choice, key):
    assert command(client, campaign, "workflows.register", {"definition": definition}).status_code == 201
    started = command(client, campaign, "workflows.start", {"input": {
        "definitionId": definition["id"], "sceneId": scene["id"], "idempotencyKey": key}})
    assert started.status_code == 201, started.text
    workflow = started.json()["workflow"]
    assert workflow["status"] == "WAITING_INTERACTION"

    login(client, player)
    assert answer(client, campaign, workflow["waitingOn"], choice).status_code in {200, 201}
    login(client, gm)
    DurableWorkflowService().recover_campaign(campaign, int(time.time()) + 10)
    return read(client, campaign, "workflows", entity_id=workflow["id"]).json()["workflow"]


# --- PART L: Phase 5 -----------------------------------------------------------

def test_phase5_use_jammer_branches_to_the_suppression_action(db, tmp_path, monkeypatch):
    from main import app

    gm, a, _b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)
    actor = systems_actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        definition = alarm_workflow(actor, a, int(time.time()) + 900)
        final = _run_branch(client, campaign, gm, a, scene, actor, definition, "USE_JAMMER", "alarm:jam")

    assert final["context"]["jammerDecision"] == "USE_JAMMER"
    assert final["status"] == "COMPLETED" and final["completionReason"] == "alarm-resolved"
    assert sheet(campaign, actor, gm) == {"alarm": "SUPPRESSED", "securityResponse": "JAMMED"}


def test_phase5_decline_follows_the_full_alarm_path(db, tmp_path, monkeypatch):
    from main import app

    gm, a, _b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)
    actor = systems_actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        definition = alarm_workflow(actor, a, int(time.time()) + 900)
        final = _run_branch(client, campaign, gm, a, scene, actor, definition, "DECLINE", "alarm:decline")

    assert final["context"]["jammerDecision"] == "DECLINE"
    assert final["status"] == "COMPLETED"
    # The suppression action never ran: the alarm stays raised.
    assert sheet(campaign, actor, gm) == {"alarm": "RAISED", "securityResponse": "ACTIVE"}


# --- PART M: Phase 8 -----------------------------------------------------------

def test_phase8_quiet_override_waits_then_unlocks_without_a_trace(db, tmp_path, monkeypatch):
    from main import app

    gm, a, _b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)
    actor = systems_actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        definition = terminal_workflow(actor, a, int(time.time()) + 900)
        final = _run_branch(client, campaign, gm, a, scene, actor, definition, "QUIET_OVERRIDE", "terminal:quiet")

    assert final["context"]["overrideMode"] == "QUIET_OVERRIDE"
    assert final["status"] == "COMPLETED" and final["completionReason"] == "vault-open"
    assert sheet(campaign, actor, gm) == {"vaultLock": "OPEN"}


def test_phase8_fast_override_unlocks_but_leaves_a_security_trace(db, tmp_path, monkeypatch):
    from main import app

    gm, a, _b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)
    actor = systems_actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        definition = terminal_workflow(actor, a, int(time.time()) + 900)
        final = _run_branch(client, campaign, gm, a, scene, actor, definition, "FAST_OVERRIDE", "terminal:fast")

    assert final["context"]["overrideMode"] == "FAST_OVERRIDE"
    assert final["status"] == "COMPLETED" and final["completionReason"] == "vault-open"
    assert sheet(campaign, actor, gm) == {"trace": "DETECTED", "securityResponse": "ACTIVE", "vaultLock": "OPEN"}


def test_only_the_eligible_operative_can_decide_the_branch(db, tmp_path, monkeypatch):
    from main import app

    gm, a, b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)
    actor = systems_actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        definition = alarm_workflow(actor, a, int(time.time()) + 900)
        assert command(client, campaign, "workflows.register", {"definition": definition}).status_code == 201
        workflow = command(client, campaign, "workflows.start", {"input": {
            "definitionId": "alarm-response", "sceneId": scene["id"], "idempotencyKey": "alarm:authority"}}).json()["workflow"]

        # Player B is not the recipient and cannot answer for Player A.
        login(client, b)
        assert answer(client, campaign, workflow["waitingOn"], "USE_JAMMER").status_code not in {200, 201}
        login(client, gm)
        still = read(client, campaign, "workflows", entity_id=workflow["id"]).json()["workflow"]
        assert still["status"] == "WAITING_INTERACTION" and "jammerDecision" not in still["context"]
        assert sheet(campaign, actor, gm)["alarm"] == "RAISED"


# --- PHASES 1-3: systemless flow with secret commitment ------------------------

FLOW_DEFINITION = {
    "id": "infiltration", "schemaVersion": 1, "turnModel": "SIMULTANEOUS",
    "phases": [{"id": p, "label": p.replace("_", " "), "submissionPolicy": "all"} for p in
               ["BRIEFING", "PLANNING", "REVEAL", "RESOLUTION", "SECURITY_RESPONSE", "EXTRACTION", "COMPLETE"]],
}


def start_flow(client, campaign, scene, participants):
    assert command(client, campaign, "gameplay.flows.register", {"definition": FLOW_DEFINITION}).status_code == 201
    started = command(client, campaign, "gameplay.flows.start", {"input": {
        "definitionId": "infiltration", "participants": participants,
        "sceneId": scene["id"], "idempotencyKey": f"black-vault:{scene['id']}"}})
    assert started.status_code == 201, started.text
    return started.json()["flow"]


def flow_of(client, campaign, flow_id):
    return read(client, campaign, "gameplay.flows", entity_id=flow_id).json()["flow"]


def test_planning_commitments_stay_secret_until_the_flow_reveals_them(db, tmp_path, monkeypatch):
    """No RPG ruleset, no dice: the phase machine alone runs the mission."""
    from main import app

    gm, a, b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        flow = start_flow(client, campaign, scene, [a, b])
        assert flow["phaseId"] == "BRIEFING"
        flow = command(client, campaign, "gameplay.flows.advance", {
            "id": flow["id"], "expectedVersion": flow["version"]}).json()["flow"]
        assert flow["phaseId"] == "PLANNING"

        login(client, a)
        after_a = command(client, campaign, "gameplay.flows.submit", {
            "id": flow["id"], "value": {"action": "HACK"}, "expectedVersion": flow["version"]})
        assert after_a.status_code in {200, 201}, after_a.text
        # A sees only its own commitment and nothing is revealed yet.
        seen_by_a = flow_of(client, campaign, flow["id"])
        assert seen_by_a["revealed"] is False
        assert set(seen_by_a["submissions"]) == {a}

        login(client, b)
        # B cannot read A's plan before the reveal.
        seen_by_b = flow_of(client, campaign, flow["id"])
        assert seen_by_b["submissions"] == {} and seen_by_b["revealed"] is False
        # B cannot submit twice, and a stale version is refused.
        stale = command(client, campaign, "gameplay.flows.submit", {
            "id": flow["id"], "value": {"action": "SCAN"}, "expectedVersion": 1})
        assert stale.status_code == 409
        revealed = command(client, campaign, "gameplay.flows.submit", {
            "id": flow["id"], "value": {"action": "SCAN"},
            "expectedVersion": seen_by_b["version"]}).json()["flow"]
        duplicate = command(client, campaign, "gameplay.flows.submit", {
            "id": flow["id"], "value": {"action": "MOVE"}, "expectedVersion": revealed["version"]})
        assert duplicate.status_code not in {200, 201}

    # Both committed: the flow revealed itself, and the values are the committed ones.
    assert revealed["revealed"] is True
    assert {user: entry["value"]["action"] for user, entry in revealed["submissions"].items()} == {a: "HACK", b: "SCAN"}


def test_a_non_participant_cannot_read_or_submit_to_the_mission_flow(db, tmp_path, monkeypatch):
    from main import app

    gm, a, b, campaign = world()
    outsider = seed_user(name="Outsider")
    seed_member(campaign, outsider, "player")
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        flow = start_flow(client, campaign, scene, [a, b])
        login(client, outsider)
        assert read(client, campaign, "gameplay.flows", entity_id=flow["id"]).json().get("flow") is None
        denied = command(client, campaign, "gameplay.flows.submit", {
            "id": flow["id"], "value": {"action": "MOVE"}, "expectedVersion": flow["version"]})
        assert denied.status_code not in {200, 201}
        # A player may never drive the phase machine.
        login(client, a)
        assert command(client, campaign, "gameplay.flows.advance", {
            "id": flow["id"], "expectedVersion": flow["version"]}).status_code not in {200, 201}


def test_mission_flow_survives_reload_and_reconstructs_the_current_phase(db, tmp_path, monkeypatch):
    from main import app

    gm, a, b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        flow = start_flow(client, campaign, scene, [a, b])
        flow = command(client, campaign, "gameplay.flows.advance", {
            "id": flow["id"], "expectedVersion": flow["version"]}).json()["flow"]
        login(client, a)
        command(client, campaign, "gameplay.flows.submit", {
            "id": flow["id"], "value": {"action": "DISTRACT"}, "expectedVersion": flow["version"]})

    # A brand new client session — the reload the player actually performs.
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, a)
        reloaded = flow_of(client, campaign, flow["id"])
        assert reloaded["phaseId"] == "PLANNING"
        assert reloaded["submissions"][a]["value"] == {"action": "DISTRACT"}
        # The commitment is immutable across the reload.
        assert command(client, campaign, "gameplay.flows.submit", {
            "id": flow["id"], "value": {"action": "MOVE"},
            "expectedVersion": reloaded["version"]}).status_code not in {200, 201}


def test_reload_while_the_jammer_decision_is_pending_reconstructs_it(db, tmp_path, monkeypatch):
    """The reload torture: the pending decision is server state, not a promise."""
    from main import app

    gm, a, b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)
    actor = systems_actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        definition = alarm_workflow(actor, a, int(time.time()) + 900)
        command(client, campaign, "workflows.register", {"definition": definition})
        workflow = command(client, campaign, "workflows.start", {"input": {
            "definitionId": "alarm-response", "sceneId": scene["id"],
            "idempotencyKey": "alarm:reload"}}).json()["workflow"]
        assert workflow["status"] == "WAITING_INTERACTION"

    # Player A reloads the browser mid-decision: a brand new session.
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, a)
        pending = read(client, campaign, "interactions", status="open", recipient="me").json()["interactions"]
        assert [value["id"] for value in pending] == [workflow["waitingOn"]]
        assert pending[0]["prompt"]["text"] == "Usar bloqueador EMP?"

        # Player B's reload shows nothing: the decision is A's alone.
        login(client, b)
        assert read(client, campaign, "interactions", status="open", recipient="me").json()["interactions"] == []

        login(client, a)
        assert answer(client, campaign, workflow["waitingOn"], "USE_JAMMER").status_code in {200, 201}

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        DurableWorkflowService().recover_campaign(campaign, int(time.time()) + 10)
        final = read(client, campaign, "workflows", entity_id=workflow["id"]).json()["workflow"]

    assert final["context"]["jammerDecision"] == "USE_JAMMER"
    assert final["status"] == "COMPLETED"
    assert sheet(campaign, actor, gm)["alarm"] == "SUPPRESSED"
