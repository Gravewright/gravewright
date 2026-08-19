"""Black Vault: authoritative Scene world, zones, and party movement.

Phases 4, 9, 11 and 12 of the mission — the parts where the package asks the core
to own geometry, membership and identity instead of tracking them itself.
"""

from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user
from tests.unit.test_black_vault_mission import PACKAGE_ID, command, install, read, world


RESTRICTED = "black-vault.restricted"
EXTRACTION = "black-vault.extraction"
TERMINAL_TYPE = "black-vault.vault-terminal"
ELEVATOR_TYPE = "black-vault.vault-elevator"
CLUE_TYPE = "black-vault.clue-pin"
BEACON_TYPE = "black-vault.alarm-beacon"
PEDESTAL_TYPE = "black-vault.artifact-pedestal"


def object_type(type_id, display, interactions):
    return {
        "typeId": type_id, "schemaVersion": 1, "displayName": display,
        "dataSchema": {"type": "object", "properties": {
            "state": {"type": "string"}, "contentReference": {"type": "string"}}},
        "geometryKinds": ["point"], "visualDefinition": [{"kind": "shape"}],
        "interactionDefinitions": [{"id": name, "label": name} for name in interactions],
    }


def seed_token(campaign, scene, gm, owner, x=1, y=1):
    from app.persistence.repositories.actor_repository import ActorRepository
    from app.persistence.repositories.token_repository import TokenRepository

    actor = ActorRepository().create(campaign_id=campaign, system_id="core", actor_type="character",
                                     name="Operative", created_by_user_id=gm)
    return TokenRepository().create(scene_id=scene["id"], actor_id=actor, grid_x=x, grid_y=y,
                                    controlled_by_user_ids=[owner])


def test_restricted_zone_and_world_objects_are_authoritative_and_package_owned(db, tmp_path, monkeypatch):
    from main import app

    gm, _a, _b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        for definition in (
            object_type(TERMINAL_TYPE, "Vault Terminal", ["hack"]),
            object_type(PEDESTAL_TYPE, "Artifact Pedestal", ["take-artifact"]),
            object_type(ELEVATOR_TYPE, "Vault Elevator", ["enter-inner-vault"]),
            object_type(BEACON_TYPE, "Alarm Beacon", ["inspect"]),
            object_type(CLUE_TYPE, "Clue Pin", ["open-clue"]),
        ):
            registered = command(client, campaign, "objectTypes.register", {"definition": definition})
            assert registered.status_code in {200, 201}, registered.text

        zone = command(client, campaign, "zones.create", {"sceneId": scene["id"], "values": {
            "type": RESTRICTED, "geometry": {"shape": "rect", "x": 520, "y": 160, "width": 360, "height": 360},
            "audience": {"kind": "campaign"}, "enabled": True, "tags": ["black-vault"]}})
        assert zone.status_code in {200, 201}, zone.text
        assert zone.json()["zone"]["packageProvenance"]["packageId"] == PACKAGE_ID

        objects = {}
        for type_id, x, y in ((TERMINAL_TYPE, 640, 300), (BEACON_TYPE, 700, 350), (ELEVATOR_TYPE, 860, 420),
                              (PEDESTAL_TYPE, 600, 200), (CLUE_TYPE, 320, 480)):
            created = command(client, campaign, "objects.create", {"sceneId": scene["id"], "input": {
                "typeId": type_id, "geometry": {"kind": "point", "x": x, "y": y},
                "data": {"state": "idle"}, "audience": {"kind": "campaign"}}})
            assert created.status_code in {200, 201}, created.text
            objects[type_id] = created.json()["object"]

        listed = read(client, campaign, "scene.objects", scene_id=scene["id"]).json()["objects"]
        assert {value["typeId"] for value in listed} == set(objects)

        intent = command(client, campaign, "objects.interact", {
            "id": objects[TERMINAL_TYPE]["id"], "interactionId": "hack"})
        assert intent.status_code in {200, 201}, intent.text
        assert intent.json()["interaction"]["principal"]["userId"] == gm

        forged = command(client, campaign, "objects.interact", {
            "id": objects[TERMINAL_TYPE]["id"], "interactionId": "self-destruct"})
        assert forged.status_code not in {200, 201}


def test_party_transfer_is_atomic_keeps_identity_and_stays_separate_from_navigation(db, tmp_path, monkeypatch):
    from main import app

    gm, a, b, campaign = world()
    entrance = seed_scene(campaign, name="Vault Entrance")
    inner = seed_scene(campaign, name="Inner Vault")
    install(tmp_path, monkeypatch, gm, campaign)
    token_a = seed_token(campaign, entrance, gm, a)
    token_b = seed_token(campaign, entrance, gm, b, x=2, y=2)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        extraction = command(client, campaign, "zones.create", {"sceneId": inner["id"], "values": {
            "type": EXTRACTION, "geometry": {"shape": "rect", "x": 0, "y": 0, "width": 4000, "height": 4000},
            "audience": {"kind": "campaign"}, "enabled": True}}).json()["zone"]
        before = read(client, campaign, "navigation.scene").json()["navigation"]

        # A stale member must not split the party.
        partial = command(client, campaign, "tokens.transferMany", {"input": {"transfers": [
            {"tokenId": token_a["id"], "sceneId": inner["id"], "x": 1, "y": 1},
            {"tokenId": token_b["id"], "sceneId": inner["id"], "x": 2, "y": 2, "expectedVersion": 999},
        ]}})
        assert partial.status_code not in {200, 201}
        remaining = read(client, campaign, "tokens", scene_id=entrance["id"]).json()["tokens"]
        assert {str(value.get("id") or value.get("token_id")) for value in remaining} == {token_a["id"], token_b["id"]}

        moved = command(client, campaign, "tokens.transferMany", {"input": {"transfers": [
            {"tokenId": token_a["id"], "sceneId": inner["id"], "x": 1, "y": 1},
            {"tokenId": token_b["id"], "sceneId": inner["id"], "x": 2, "y": 2},
        ]}})
        assert moved.status_code in {200, 201}, moved.text
        transfer = moved.json()["transfer"]
        assert transfer["atomic"] is True
        assert {value["id"] for value in transfer["tokens"]} == {token_a["id"], token_b["id"]}
        assert {value["sceneId"] for value in transfer["tokens"]} == {inner["id"]}

        # Transfer alone moved nobody's view.
        assert transfer["navigation"] is None
        assert read(client, campaign, "navigation.scene").json()["navigation"] == before

        members = read(client, campaign, "scene.zones", entity_id=extraction["id"], action="members").json()["members"]
        identities = {value["tokenId"] if isinstance(value, dict) else value for value in members}
        assert identities >= {token_a["id"], token_b["id"]}

        navigated = command(client, campaign, "navigation.scene.go", {"input": {
            "sceneId": inner["id"], "recipients": {"kind": "users", "ids": [a, b]}}})
        assert navigated.status_code in {200, 201}, navigated.text
        assert navigated.json()["navigation"]["sceneId"] == inner["id"]


def test_a_player_cannot_move_a_foreign_token_or_navigate_another_user(db, tmp_path, monkeypatch):
    from main import app

    gm, a, b, campaign = world()
    entrance = seed_scene(campaign, name="Vault Entrance")
    inner = seed_scene(campaign, name="Inner Vault")
    install(tmp_path, monkeypatch, gm, campaign)
    token_b = seed_token(campaign, entrance, gm, b)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, a)
        stolen = command(client, campaign, "tokens.transfer", {"input": {
            "tokenId": token_b["id"], "sceneId": inner["id"], "x": 1, "y": 1}})
        assert stolen.status_code not in {200, 201}
        remote = command(client, campaign, "navigation.scene.go", {"input": {
            "sceneId": inner["id"], "recipients": {"kind": "users", "ids": [b]}}})
        assert remote.status_code not in {200, 201}


def test_zones_and_objects_never_leak_across_campaigns(db, tmp_path, monkeypatch):
    from main import app

    gm, _a, _b, campaign = world()
    scene = seed_scene(campaign)
    other_gm = seed_user(name="Other GM")
    other_campaign = seed_campaign(other_gm)
    other_scene = seed_scene(other_campaign)
    seed_member(other_campaign, gm, "player")
    install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        command(client, campaign, "objectTypes.register", {
            "definition": object_type(BEACON_TYPE, "Alarm Beacon", ["inspect"])})
        # A scene from another campaign is not a legal destination.
        forged = command(client, campaign, "zones.create", {"sceneId": other_scene["id"], "values": {
            "type": RESTRICTED, "geometry": {"shape": "rect", "x": 0, "y": 0, "width": 10, "height": 10}}})
        assert forged.status_code not in {200, 201}
        forged_object = command(client, campaign, "objects.create", {"sceneId": other_scene["id"], "input": {
            "typeId": BEACON_TYPE, "geometry": {"kind": "point", "x": 1, "y": 1}}})
        assert forged_object.status_code not in {200, 201}
        assert read(client, campaign, "scene.objects", scene_id=other_scene["id"]).json().get("objects", []) == []
        assert read(client, campaign, "scene.zones", scene_id=other_scene["id"]).json().get("zones", []) == []
        assert scene["id"] != other_scene["id"]
