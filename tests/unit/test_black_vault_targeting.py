"""Black Vault Phase 1 and Phase 4→5, driven by real participants.

No fixture-injected participant ids and no hard-coded users: the mission reads the
roster, and the alarm follows whichever token actually tripped the zone.
"""

import time

from litestar.testing import TestClient

from app.engine.sdk.durable_workflow_service import DurableWorkflowService
from tests.conftest import TEST_SESSION_CONFIG, login, seed_scene
from tests.unit.test_black_vault_mission import (
    alarm_workflow, answer, command, install, read, sheet, systems_actor, world,
)
from tests.unit.test_black_vault_world import RESTRICTED


FLOW_DEFINITION = {
    "id": "infiltration", "schemaVersion": 1, "turnModel": "SIMULTANEOUS",
    "phases": [{"id": p, "label": p.replace("_", " "), "submissionPolicy": "all"} for p in
               ["BRIEFING", "PLANNING", "REVEAL", "RESOLUTION", "SECURITY_RESPONSE", "EXTRACTION", "COMPLETE"]],
}


def operatives(client, campaign):
    """Exactly what black-vault.js does: roster in, player user ids out."""
    roster = read(client, campaign, "campaign.members").json()["members"]
    return [member["userId"] for member in roster if member["role"] == "player"]


def owned_token(campaign, scene, gm, owner, x=1, y=1):
    from app.persistence.repositories.actor_repository import ActorRepository
    from app.persistence.repositories.token_repository import TokenRepository

    actor = ActorRepository().create(campaign_id=campaign, system_id="core", actor_type="character",
                                     name=f"Operative {x}", created_by_user_id=gm)
    ActorRepository().add_owner(actor_id=actor, user_id=owner)
    return TokenRepository().create(scene_id=scene["id"], actor_id=actor, grid_x=x, grid_y=y)


def test_phase1_starts_the_flow_from_the_real_campaign_roster(db, tmp_path, monkeypatch):
    from main import app

    gm, a, b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        participants = operatives(client, campaign)
        assert set(participants) == {a, b}
        # The GM runs the op; they are not an infiltrator.
        assert gm not in participants

        command(client, campaign, "gameplay.flows.register", {"definition": FLOW_DEFINITION})
        started = command(client, campaign, "gameplay.flows.start", {"input": {
            "definitionId": "infiltration", "participants": participants,
            "sceneId": scene["id"], "idempotencyKey": f"black-vault:{scene['id']}"}})
        assert started.status_code == 201, started.text
        flow = started.json()["flow"]
        assert set(flow["participants"]) == {a, b}

        # Both discovered operatives can really submit; the roster was authoritative.
        flow = command(client, campaign, "gameplay.flows.advance", {
            "id": flow["id"], "expectedVersion": flow["version"]}).json()["flow"]
        login(client, a)
        after_a = command(client, campaign, "gameplay.flows.submit", {
            "id": flow["id"], "value": {"action": "HACK"}, "expectedVersion": flow["version"]})
        assert after_a.status_code in {200, 201}, after_a.text
        login(client, b)
        revealed = command(client, campaign, "gameplay.flows.submit", {
            "id": flow["id"], "value": {"action": "SCAN"},
            "expectedVersion": after_a.json()["flow"]["version"]}).json()["flow"]

    assert revealed["revealed"] is True
    assert set(revealed["submissions"]) == {a, b}


def test_phase4_to_5_targets_the_operative_whose_token_tripped_the_zone(db, tmp_path, monkeypatch):
    from main import app

    gm, a, b, campaign = world()
    entrance = seed_scene(campaign, name="Vault Entrance")
    install(tmp_path, monkeypatch, gm, campaign)
    actor = systems_actor(campaign, gm)
    token_a = owned_token(campaign, entrance, gm, a, x=1, y=1)
    owned_token(campaign, entrance, gm, b, x=2, y=2)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        participants = operatives(client, campaign)
        command(client, campaign, "zones.create", {"sceneId": entrance["id"], "values": {
            "type": RESTRICTED, "geometry": {"shape": "rect", "x": 0, "y": 0, "width": 4000, "height": 4000},
            "audience": {"kind": "campaign"}, "enabled": True}})

        # zone.entered hands the package a token id and nothing else.
        token = read(client, campaign, "tokens", entity_id=token_a["id"],
                     scene_id=entrance["id"]).json()["token"]
        controllers = token["controllers"]
        assert set(controllers) == {gm, a}
        recipient = next(user for user in controllers if user in participants)
        assert recipient == a

        # The EMP decision is addressed at the operative the token resolved to.
        definition = alarm_workflow(actor, recipient, int(time.time()) + 900)
        command(client, campaign, "workflows.register", {"definition": definition})
        workflow = command(client, campaign, "workflows.start", {"input": {
            "definitionId": "alarm-response", "sceneId": entrance["id"],
            "idempotencyKey": "alarm:targeted"}}).json()["workflow"]
        assert workflow["status"] == "WAITING_INTERACTION"

        # Player B, the other operative, was not asked.
        login(client, b)
        assert read(client, campaign, "interactions", status="open", recipient="me").json()["interactions"] == []

        login(client, a)
        pending = read(client, campaign, "interactions", status="open", recipient="me").json()["interactions"]
        assert [value["id"] for value in pending] == [workflow["waitingOn"]]
        assert answer(client, campaign, workflow["waitingOn"], "USE_JAMMER").status_code in {200, 201}

        login(client, gm)
        DurableWorkflowService().recover_campaign(campaign, int(time.time()) + 10)
        final = read(client, campaign, "workflows", entity_id=workflow["id"]).json()["workflow"]

    assert final["context"]["jammerDecision"] == "USE_JAMMER"
    assert final["status"] == "COMPLETED"
    assert sheet(campaign, actor, gm)["alarm"] == "SUPPRESSED"


def test_the_module_never_gains_authority_over_the_operative_it_targeted(db, tmp_path, monkeypatch):
    from main import app

    gm, a, b, campaign = world()
    entrance = seed_scene(campaign, name="Vault Entrance")
    install(tmp_path, monkeypatch, gm, campaign)
    actor = systems_actor(campaign, gm)
    token_a = owned_token(campaign, entrance, gm, a)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        definition = alarm_workflow(actor, a, int(time.time()) + 900)
        command(client, campaign, "workflows.register", {"definition": definition})
        workflow = command(client, campaign, "workflows.start", {"input": {
            "definitionId": "alarm-response", "sceneId": entrance["id"],
            "idempotencyKey": "alarm:no-impersonation"}}).json()["workflow"]

        # The GM knows A is the controller and the recipient, and still cannot answer for A.
        forged = command(client, campaign, "interactions.respond", {
            "id": workflow["waitingOn"], "response": "USE_JAMMER", "idempotencyKey": "gm-forges"})
        assert forged.status_code not in {200, 201}

        # Player B knows A's id from nothing here, and answering is refused regardless.
        login(client, b)
        assert command(client, campaign, "interactions.respond", {
            "id": workflow["waitingOn"], "response": "DECLINE",
            "idempotencyKey": "b-forges"}).status_code not in {200, 201}

        login(client, gm)
        still = read(client, campaign, "workflows", entity_id=workflow["id"]).json()["workflow"]
        assert still["status"] == "WAITING_INTERACTION" and "jammerDecision" not in still["context"]
        assert token_a["id"]
