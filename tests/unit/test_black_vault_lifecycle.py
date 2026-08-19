"""Black Vault: credential drop, module settings, mission log, and unload.

Phase 7's card-to-terminal drop plus the package lifecycle the mission depends on
between sessions.
"""

from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_scene
from tests.unit.test_black_vault_composition import image_asset
from tests.unit.test_black_vault_mission import PACKAGE_ID, command, install, read, world
from tests.unit.test_black_vault_world import TERMINAL_TYPE, object_type


TERMINAL_POINT = {"x": 640, "y": 300}


def provision_terminal(client, campaign, scene):
    command(client, campaign, "objectTypes.register", {
        "definition": object_type(TERMINAL_TYPE, "Vault Terminal", ["hack"])})
    created = command(client, campaign, "objects.create", {"sceneId": scene["id"], "input": {
        "typeId": TERMINAL_TYPE, "geometry": {"kind": "point", **TERMINAL_POINT},
        "data": {"state": "locked"}, "audience": {"kind": "campaign"}}})
    assert created.status_code in {200, 201}, created.text
    return created.json()["object"]


def register_drag(client, campaign):
    source = command(client, campaign, "dragDrop.register", {"kind": "source", "definition": {
        "id": "card", "referenceKinds": ["card"], "operations": ["place"],
        "label": "Access credential", "schemaVersion": 1}})
    target = command(client, campaign, "dragDrop.register", {"kind": "target", "definition": {
        "id": f"{PACKAGE_ID}.terminal-slot", "operations": ["place"], "surface": "scene-world-object",
        "targetKinds": ["scene-object"], "worldObjectTypeId": TERMINAL_TYPE,
        "actionReference": f"{PACKAGE_ID}:terminal.slot-card@1", "schemaVersion": 1}})
    assert source.status_code in {200, 201}, source.text
    assert target.status_code in {200, 201}, target.text


def kit_and_card(client, campaign, gm):
    art = image_asset(campaign, gm)
    deck = command(client, campaign, "cards.instantiateDefinition", {
        "definitionId": "infiltration-kit", "version": 1,
        "artwork": {"access-card": art, "artifact": art}}).json()["deck"]
    assert command(client, campaign, "cards.draw", {
        "deckId": deck["id"], "count": 1, "destination": "hand"}).status_code in {200, 201}
    cards = read(client, campaign, "cards").json()["cards"]
    held = next(card for card in cards if card.get("owner_user_id") == gm)
    return deck, held


def test_access_card_reaches_the_terminal_through_a_semantic_drop(db, tmp_path, monkeypatch):
    from main import app

    gm, _a, _b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        terminal = provision_terminal(client, campaign, scene)
        register_drag(client, campaign)
        _deck, card = kit_and_card(client, campaign, gm)

        dropped = command(client, campaign, "dragDrop.drop", {"input": {
            "operation": "place",
            "payload": {"kind": "card", "reference": f"grave://campaign/{campaign}/card/{card['id']}",
                        "schemaVersion": 1},
            "destination": {"targetDefinitionId": f"{PACKAGE_ID}.terminal-slot", "kind": "scene-object",
                            "resource": {"id": terminal["id"]}, "worldPosition": TERMINAL_POINT},
            "idempotencyKey": f"slot:{card['id']}"}})
        assert dropped.status_code in {200, 201}, dropped.text
        result = dropped.json()["result"]
        assert result["operation"] == "place"
        assert result["destination"]["resource"]["typeId"] == TERMINAL_TYPE
        # The registered action, not the package, produced the canonical placement.
        assert result["actionResult"]["reference"] == f"{PACKAGE_ID}:terminal.slot-card@1"

        placements = read(client, campaign, "cards").json()["scene_placements"]
        assert len(placements) == 1 and placements[0]["scene_id"] == scene["id"]


def test_a_forged_drop_destination_or_reference_is_refused(db, tmp_path, monkeypatch):
    from main import app

    gm, _a, _b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        terminal = provision_terminal(client, campaign, scene)
        register_drag(client, campaign)
        _deck, card = kit_and_card(client, campaign, gm)
        reference = f"grave://campaign/{campaign}/card/{card['id']}"

        forgeries = [
            # A destination the pointer never actually touched.
            {"targetDefinitionId": f"{PACKAGE_ID}.terminal-slot", "kind": "scene-object",
             "resource": {"id": terminal["id"]}, "worldPosition": {"x": 5, "y": 5}},
            # An unregistered target definition.
            {"targetDefinitionId": f"{PACKAGE_ID}.ghost-slot", "kind": "scene-object",
             "resource": {"id": terminal["id"]}, "worldPosition": TERMINAL_POINT},
            # A stale world object version.
            {"targetDefinitionId": f"{PACKAGE_ID}.terminal-slot", "kind": "scene-object",
             "resource": {"id": terminal["id"]}, "worldPosition": TERMINAL_POINT, "expectedVersion": 999},
        ]
        for destination in forgeries:
            denied = command(client, campaign, "dragDrop.drop", {"input": {
                "operation": "place",
                "payload": {"kind": "card", "reference": reference, "schemaVersion": 1},
                "destination": destination}})
            assert denied.status_code not in {200, 201}, destination["targetDefinitionId"]

        forged_reference = command(client, campaign, "dragDrop.drop", {"input": {
            "operation": "place",
            "payload": {"kind": "card", "reference": f"grave://campaign/{campaign}/card/forged",
                        "schemaVersion": 1},
            "destination": {"targetDefinitionId": f"{PACKAGE_ID}.terminal-slot", "kind": "scene-object",
                            "resource": {"id": terminal["id"]}, "worldPosition": TERMINAL_POINT}}})
        assert forged_reference.status_code not in {200, 201}


def test_module_settings_and_mission_log_are_package_owned_and_bounded(db, tmp_path, monkeypatch):
    from main import app

    gm, _a, _b, campaign = world()
    install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        difficulty = client.post("/sdk/packages/settings", json={
            "campaign_id": campaign, "package_id": PACKAGE_ID, "key": "difficulty", "value": "hardened"})
        assert difficulty.status_code in {200, 201}, difficulty.text
        assert difficulty.json()["success"] is True

        # An undeclared key is not a Black Vault setting.
        rogue = client.post("/sdk/packages/settings", json={
            "campaign_id": campaign, "package_id": PACKAGE_ID, "key": "godmode", "value": True})
        assert rogue.status_code not in {200, 201} or rogue.json()["success"] is False

        # The objective log is the one thing no core domain already owns.
        wrote = client.post(f"/sdk/packages/{PACKAGE_ID}/storage/sqlite/execute", json={
            "campaign_id": campaign, "scope": "campaign", "query": "recordBeat",
            "params": {"missionId": "m1", "beat": "ALARM_TRIGGERED",
                       "detail": "restricted", "at": 1700000000}})
        assert wrote.status_code in {200, 201}, wrote.text
        rows = client.post(f"/sdk/packages/{PACKAGE_ID}/storage/sqlite/query", json={
            "campaign_id": campaign, "scope": "campaign", "query": "missionLog",
            "params": {"missionId": "m1"}})
        assert rows.status_code in {200, 201}, rows.text
        assert [row["beat"] for row in rows.json()["rows"]] == ["ALARM_TRIGGERED"]

        # Ad-hoc SQL is not a public surface: only named queries exist.
        raw = client.post(f"/sdk/packages/{PACKAGE_ID}/storage/sqlite/query", json={
            "campaign_id": campaign, "scope": "campaign",
            "query": "DROP TABLE objective_log", "params": {}})
        assert raw.status_code not in {200, 201}


def test_unloading_black_vault_closes_runtime_primitives_without_zombies(db, tmp_path, monkeypatch):
    from main import app
    from app.engine.sdk.package_activation_service import PackageActivationService
    from app.engine.sdk.durable_workflow_service import DurableWorkflowService
    from tests.unit.test_black_vault_mission import alarm_workflow, systems_actor

    gm, a, _b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)
    actor = systems_actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        import time

        command(client, campaign, "workflows.register", {
            "definition": alarm_workflow(actor, a, int(time.time()) + 900)})
        workflow = command(client, campaign, "workflows.start", {"input": {
            "definitionId": "alarm-response", "sceneId": scene["id"],
            "idempotencyKey": "alarm:unload"}}).json()["workflow"]
        assert workflow["status"] == "WAITING_INTERACTION"
        interaction_id = workflow["waitingOn"]

        assert PackageActivationService().deactivate_package(campaign, PACKAGE_ID, gm).success

        # The waiting primitive is closed, not orphaned.
        row = DurableWorkflowService().instances.get(workflow["id"])
        assert row["status"] == "CANCELLED"
        assert row["payload"]["completionReason"] == "package-unload"

        # And the surface is gone for the package.
        assert command(client, campaign, "workflows.start", {"input": {
            "definitionId": "alarm-response", "sceneId": scene["id"],
            "idempotencyKey": "alarm:after-unload"}}).status_code == 403

        # Campaign-owned content the mission created is not destroyed by unloading.
        login(client, gm)
        assert interaction_id
        from app.engine.sheets.sheet_data_service import SheetDataService
        data = (SheetDataService().get_data(actor_id=actor, user_id=gm).data or {}).get("blackVault", {})
        assert data.get("alarm") == "RAISED"
