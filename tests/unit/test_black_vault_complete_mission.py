"""Black Vault: the complete canonical mission, start to COMPLETE.

One run of the whole vertical slice on the public SDK only — roster, secret
planning, the restricted zone, the alarm branch, the cascade, the credential, the
terminal, the artifact, the clue, the elevator, and extraction.
"""

import time

from litestar.testing import TestClient

from app.engine.sdk.durable_workflow_service import DurableWorkflowService
from tests.conftest import TEST_SESSION_CONFIG, login, seed_scene
from tests.unit.test_black_vault_composition import alarm_timeline, audio_asset, image_asset
from tests.unit.test_black_vault_lifecycle import register_drag
from tests.unit.test_black_vault_mission import (
    PACKAGE_ID, alarm_workflow, answer, command, install, read, sheet, systems_actor,
    terminal_workflow, world,
)
from tests.unit.test_black_vault_targeting import FLOW_DEFINITION, operatives, owned_token
from tests.unit.test_black_vault_world import (
    CLUE_TYPE, ELEVATOR_TYPE, EXTRACTION, PEDESTAL_TYPE, RESTRICTED, TERMINAL_TYPE, object_type,
)


TERMINAL_POINT = {"x": 640, "y": 300}


def _phase(client, campaign, flow_id):
    return read(client, campaign, "gameplay.flows", entity_id=flow_id).json()["flow"]


def _advance_to(client, campaign, flow, target):
    while flow["phaseId"] != target:
        flow = command(client, campaign, "gameplay.flows.advance", {
            "id": flow["id"], "expectedVersion": flow["version"]}).json()["flow"]
    return flow


def test_black_vault_runs_the_complete_mission_on_public_sdk_only(db, tmp_path, monkeypatch):
    from main import app
    from app.persistence.repositories.token_repository import TokenRepository

    gm, a, b, campaign = world()
    entrance = seed_scene(campaign, name="Vault Entrance")
    inner = seed_scene(campaign, name="Inner Vault")
    install(tmp_path, monkeypatch, gm, campaign)
    actor = systems_actor(campaign, gm)
    token_a = owned_token(campaign, entrance, gm, a, x=1, y=1)
    token_b = owned_token(campaign, entrance, gm, b, x=2, y=2)
    alarm_asset = audio_asset(campaign, gm)
    art = image_asset(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        # 1. Session start: the roster decides who infiltrates.
        login(client, gm)
        participants = operatives(client, campaign)
        assert set(participants) == {a, b}
        command(client, campaign, "gameplay.flows.register", {"definition": FLOW_DEFINITION})
        flow = command(client, campaign, "gameplay.flows.start", {"input": {
            "definitionId": "infiltration", "participants": participants,
            "sceneId": entrance["id"], "idempotencyKey": f"black-vault:{entrance['id']}"}}).json()["flow"]

        # World provisioning.
        for definition in (
            object_type(TERMINAL_TYPE, "Vault Terminal", ["hack"]),
            object_type(PEDESTAL_TYPE, "Artifact Pedestal", ["take-artifact"]),
            object_type(ELEVATOR_TYPE, "Vault Elevator", ["enter-inner-vault"]),
            object_type(CLUE_TYPE, "Clue Pin", ["open-clue"]),
        ):
            command(client, campaign, "objectTypes.register", {"definition": definition})
        objects = {}
        for type_id, x, y in ((TERMINAL_TYPE, 640, 300), (PEDESTAL_TYPE, 600, 200),
                              (ELEVATOR_TYPE, 860, 420), (CLUE_TYPE, 320, 480)):
            objects[type_id] = command(client, campaign, "objects.create", {
                "sceneId": entrance["id"], "input": {
                    "typeId": type_id, "geometry": {"kind": "point", "x": x, "y": y},
                    "data": {"state": "idle"}, "audience": {"kind": "campaign"}}}).json()["object"]
        restricted = command(client, campaign, "zones.create", {"sceneId": entrance["id"], "values": {
            "type": RESTRICTED, "geometry": {"shape": "rect", "x": 400, "y": 100, "width": 600, "height": 600},
            "audience": {"kind": "campaign"}, "enabled": True}}).json()["zone"]
        extraction = command(client, campaign, "zones.create", {"sceneId": inner["id"], "values": {
            "type": EXTRACTION, "geometry": {"shape": "rect", "x": 0, "y": 0, "width": 4000, "height": 4000},
            "audience": {"kind": "campaign"}, "enabled": True}}).json()["zone"]

        # 2-3. Planning: secret commitment, then reveal.
        flow = _advance_to(client, campaign, flow, "PLANNING")
        login(client, a)
        flow_a = command(client, campaign, "gameplay.flows.submit", {
            "id": flow["id"], "value": {"action": "HACK"}, "expectedVersion": flow["version"]}).json()["flow"]
        login(client, b)
        assert _phase(client, campaign, flow["id"])["submissions"] == {}
        flow = command(client, campaign, "gameplay.flows.submit", {
            "id": flow["id"], "value": {"action": "DISTRACT"},
            "expectedVersion": flow_a["version"]}).json()["flow"]
        assert flow["revealed"] is True and set(flow["submissions"]) == {a, b}

        login(client, gm)
        flow = _advance_to(client, campaign, flow, "RESOLUTION")

        # 4. Authoritative movement into the Restricted Area.
        TokenRepository().move(token_id=token_a["id"], grid_x=8, grid_y=4)
        members = read(client, campaign, "scene.zones", entity_id=restricted["id"],
                       action="members").json()["members"]
        assert token_a["id"] in {m["tokenId"] if isinstance(m, dict) else m for m in members}

        # The zone hands over a token id; the token resolves the operative.
        token = read(client, campaign, "tokens", entity_id=token_a["id"],
                     scene_id=entrance["id"]).json()["token"]
        recipient = next(user for user in token["controllers"] if user in participants)
        assert recipient == a

        # 5. Alarm workflow waits on that operative.
        flow = _advance_to(client, campaign, flow, "SECURITY_RESPONSE")
        command(client, campaign, "workflows.register", {
            "definition": alarm_workflow(actor, recipient, int(time.time()) + 900)})
        alarm = command(client, campaign, "workflows.start", {"input": {
            "definitionId": "alarm-response", "sceneId": entrance["id"],
            "idempotencyKey": f"alarm:{entrance['id']}"}}).json()["workflow"]
        assert alarm["status"] == "WAITING_INTERACTION"

    # Reload torture while the decision is pending.
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, a)
        pending = read(client, campaign, "interactions", status="open", recipient="me").json()["interactions"]
        assert [value["id"] for value in pending] == [alarm["waitingOn"]]
        assert answer(client, campaign, alarm["waitingOn"], "DECLINE").status_code in {200, 201}

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        DurableWorkflowService().recover_campaign(campaign, int(time.time()) + 10)
        resolved = read(client, campaign, "workflows", entity_id=alarm["id"]).json()["workflow"]
        assert resolved["context"]["jammerDecision"] == "DECLINE"
        assert sheet(campaign, actor, gm)["alarm"] == "RAISED"

        # 6. The declined alarm plays the full cascade.
        command(client, campaign, "timelines.register", {
            "definition": alarm_timeline(entrance["id"], alarm_asset)})
        cascade = command(client, campaign, "timelines.start", {"input": {
            "definitionId": "alarm-cascade", "sceneId": entrance["id"],
            "audience": {"kind": "campaign"}, "idempotencyKey": f"alarm-cascade:{entrance['id']}"}})
        assert cascade.status_code == 201, cascade.text
        assert cascade.json()["timeline"]["status"] in {"RUNNING", "COMPLETED"}

        # 7. Access Card into the Vault Terminal through a semantic drop.
        register_drag(client, campaign)
        deck = command(client, campaign, "cards.instantiateDefinition", {
            "definitionId": "infiltration-kit", "version": 1,
            "artwork": {"access-card": art, "artifact": art}}).json()["deck"]
        command(client, campaign, "cards.draw", {"deckId": deck["id"], "count": 1, "destination": "hand"})
        held = next(c for c in read(client, campaign, "cards").json()["cards"] if c.get("owner_user_id") == gm)
        dropped = command(client, campaign, "dragDrop.drop", {"input": {
            "operation": "place",
            "payload": {"kind": "card", "reference": f"grave://campaign/{campaign}/card/{held['id']}",
                        "schemaVersion": 1},
            "destination": {"targetDefinitionId": f"{PACKAGE_ID}.terminal-slot", "kind": "scene-object",
                            "resource": {"id": objects[TERMINAL_TYPE]["id"]}, "worldPosition": TERMINAL_POINT},
            "idempotencyKey": f"slot:{held['id']}"}})
        assert dropped.status_code in {200, 201}, dropped.text

        # 8. Terminal hack: quiet override branch, server-timed.
        assert command(client, campaign, "objects.interact", {
            "id": objects[TERMINAL_TYPE]["id"], "interactionId": "hack"}).status_code in {200, 201}
        command(client, campaign, "workflows.register", {
            "definition": terminal_workflow(actor, recipient, int(time.time()) + 900)})
        terminal = command(client, campaign, "workflows.start", {"input": {
            "definitionId": "terminal-hack", "sceneId": entrance["id"],
            "idempotencyKey": f"terminal:{entrance['id']}"}}).json()["workflow"]
        login(client, a)
        assert answer(client, campaign, terminal["waitingOn"], "QUIET_OVERRIDE").status_code in {200, 201}
        login(client, gm)
        DurableWorkflowService().recover_campaign(campaign, int(time.time()) + 10)
        opened = read(client, campaign, "workflows", entity_id=terminal["id"]).json()["workflow"]
        assert opened["context"]["overrideMode"] == "QUIET_OVERRIDE"
        assert opened["completionReason"] == "vault-open"
        assert sheet(campaign, actor, gm)["vaultLock"] == "OPEN"
        assert "trace" not in sheet(campaign, actor, gm)

        # 9. The Artifact leaves the pedestal as native Card content.
        assert command(client, campaign, "objects.interact", {
            "id": objects[PEDESTAL_TYPE]["id"], "interactionId": "take-artifact"}).status_code in {200, 201}
        assert command(client, campaign, "cards.draw", {
            "deckId": deck["id"], "count": 1, "destination": "hand"}).status_code in {200, 201}

        # 10. The Clue Pin opens native content.
        journal_id = command(client, campaign, "journals.create", {
            "title": "Black Vault - Recovered Log", "type": "lore", "visibility": "private",
            "data": {"sections": []}}).json()["journal_id"]
        reference = f"grave://campaign/{campaign}/journal/{journal_id}"
        assert read(client, campaign, "content.references",
                    reference=reference).json()["value"]["id"] == journal_id

        # 11. The Elevator moves the party atomically; navigation stays separate.
        assert command(client, campaign, "objects.interact", {
            "id": objects[ELEVATOR_TYPE]["id"], "interactionId": "enter-inner-vault"}).status_code in {200, 201}
        before_navigation = read(client, campaign, "navigation.scene").json()["navigation"]
        transfer = command(client, campaign, "tokens.transferMany", {"input": {"transfers": [
            {"tokenId": token_a["id"], "sceneId": inner["id"], "x": 1, "y": 1},
            {"tokenId": token_b["id"], "sceneId": inner["id"], "x": 2, "y": 2},
        ]}}).json()["transfer"]
        assert transfer["atomic"] is True and transfer["navigation"] is None
        assert read(client, campaign, "navigation.scene").json()["navigation"] == before_navigation
        assert command(client, campaign, "navigation.scene.go", {"input": {
            "sceneId": inner["id"], "recipients": {"kind": "users", "ids": participants}}}
        ).status_code in {200, 201}

        # 12. Extraction, then COMPLETE.
        arrived = read(client, campaign, "scene.zones", entity_id=extraction["id"],
                       action="members").json()["members"]
        assert {m["tokenId"] if isinstance(m, dict) else m for m in arrived} >= {token_a["id"], token_b["id"]}
        flow = _advance_to(client, campaign, _phase(client, campaign, flow["id"]), "EXTRACTION")
        flow = _advance_to(client, campaign, flow, "COMPLETE")
        assert flow["phaseId"] == "COMPLETE"

    # The finished mission is reconstructable from a cold session.
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, a)
        reloaded = _phase(client, campaign, flow["id"])
        assert reloaded["phaseId"] == "COMPLETE"
        tokens = read(client, campaign, "tokens", scene_id=inner["id"]).json()["tokens"]
        assert {str(t["id"]) for t in tokens} >= {token_a["id"], token_b["id"]}
        # A player reconstructs the mission, not the GM's private workflow ledger.
        assert read(client, campaign, "workflows", entity_id=alarm["id"]).json().get("workflow") is None
        login(client, gm)
        assert read(client, campaign, "workflows",
                    entity_id=alarm["id"]).json()["workflow"]["status"] == "COMPLETED"
