"""Black Vault: the alarm cascade, the access card, and the clue.

Phases 6, 7, 9 and 10 — the parts where the mission composes existing semantic
runtimes instead of reaching for the renderer, a timer, or its own inventory.
"""

import base64

from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user
from tests.unit.test_black_vault_mission import PACKAGE_ID, command, install, read, world


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


def alarm_timeline(scene_id, asset_id):
    """Exactly the cue set shipped in black-vault.js."""
    return {"id": "alarm-cascade", "schemaVersion": 1, "cues": [
        {"cueId": "siren", "offsetMs": 0, "type": "AUDIO_PLAY", "parameters": {
            "asset": {"kind": "library-asset", "id": asset_id}, "channel": "sfx",
            "gain": 0.9, "loop": False, "audience": {"kind": "campaign"}, "sceneId": scene_id}},
        {"cueId": "warning", "offsetMs": 0, "type": "PRESENTATION_SHOW", "parameters": {
            "mode": "title-card", "content": {"title": "ALARME", "text": "Resposta de seguranca acionada."},
            "audience": {"kind": "campaign"}}},
        {"cueId": "redlight", "offsetMs": 400, "type": "LIGHT_CREATE", "parameters": {
            "x": 700, "y": 350, "bright_radius": 120, "dim_radius": 320,
            "color": "#ff2f3a", "intensity": 0.9}},
        {"cueId": "bloom", "offsetMs": 600, "type": "SHADER_PRESET", "parameters": {
            "presetId": "vortex-1"}},
        {"cueId": "sparks", "offsetMs": 900, "type": "PARTICLE_CREATE", "parameters": {
            "x": 700, "y": 350, "kind": "ember", "density": 0.6, "scale": 4}},
    ]}


def audio_asset(campaign, gm):
    from app.engine.assets.asset_library_service import AssetLibraryService

    created = AssetLibraryService().upload_asset(campaign_id=campaign, user_id=gm, filename="alarm.ogg",
                                                 content_type="audio/ogg", data=b"OggS" + b"a" * 48)
    assert created.success, created.error_key
    return created.payload["asset"]["id"]


def image_asset(campaign, gm, name="card.png"):
    from app.engine.assets.asset_library_service import AssetLibraryService

    created = AssetLibraryService().upload_asset(campaign_id=campaign, user_id=gm, filename=name,
                                                 content_type="image/png", data=PNG)
    assert created.success, created.error_key
    return created.payload["asset"]["id"]


# --- PHASE 6: alarm timeline ---------------------------------------------------

def test_alarm_cascade_composes_five_semantic_domains_without_a_renderer(db, tmp_path, monkeypatch):
    from main import app

    gm, _a, _b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)
    asset = audio_asset(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        definition = alarm_timeline(scene["id"], asset)
        registered = command(client, campaign, "timelines.register", {"definition": definition})
        assert registered.status_code == 201, registered.text
        # The core derives the duration; a package cannot assert timing authority.
        assert registered.json()["definition"]["durationMs"] == 900

        started = command(client, campaign, "timelines.start", {"input": {
            "definitionId": "alarm-cascade", "sceneId": scene["id"],
            "audience": {"kind": "campaign"}, "idempotencyKey": f"alarm-cascade:{scene['id']}"}})
        assert started.status_code == 201, started.text
        timeline = started.json()["timeline"]
        assert timeline["status"] in {"RUNNING", "COMPLETED"}
        assert timeline["providerPackageId"] == PACKAGE_ID

        # Replaying the same cascade is idempotent, not a second alarm.
        again = command(client, campaign, "timelines.start", {"input": {
            "definitionId": "alarm-cascade", "sceneId": scene["id"],
            "audience": {"kind": "campaign"}, "idempotencyKey": f"alarm-cascade:{scene['id']}"}})
        assert again.json()["timeline"]["id"] == timeline["id"]

        fetched = read(client, campaign, "timelines", entity_id=timeline["id"]).json()["timeline"]
        assert set(fetched["executedCueIds"]) <= {c["cueId"] for c in definition["cues"]}


def test_timeline_rejects_raw_renderer_and_foreign_provider_cues(db, tmp_path, monkeypatch):
    from main import app

    gm, _a, _b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        for cue in (
            {"cueId": "glsl", "offsetMs": 0, "type": "SHADER_SOURCE", "parameters": {"source": "void main(){}"}},
            {"cueId": "raw", "offsetMs": 0, "type": "ACTION", "action": "some-other-package:evil@1"},
            {"cueId": "late", "offsetMs": 999_999_999, "type": "SHADER_PRESET", "parameters": {}},
        ):
            denied = command(client, campaign, "timelines.register", {
                "definition": {"id": "bad", "schemaVersion": 1, "cues": [cue]}})
            assert denied.status_code not in {200, 201}, cue["cueId"]
        assert scene["id"]


# --- PHASE 7 + 9: cards --------------------------------------------------------

def test_access_card_and_artifact_stay_private_to_the_holder(db, tmp_path, monkeypatch):
    from main import app

    gm, a, b, campaign = world()
    seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)
    art = image_asset(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        instantiated = command(client, campaign, "cards.instantiateDefinition", {
            "definitionId": "infiltration-kit", "version": 1, "name": "Infiltration Kit",
            "artwork": {"access-card": art, "artifact": art}, "metadata": {"missionId": "black-vault"}})
        assert instantiated.status_code in {200, 201}, instantiated.text
        deck = instantiated.json()["deck"]

        drawn = command(client, campaign, "cards.draw", {
            "deckId": deck["id"], "count": 1, "destination": "hand"})
        assert drawn.status_code in {200, 201}, drawn.text

        gm_state = read(client, campaign, "cards").json()
        held = [c for c in gm_state["cards"] if c.get("owner_user_id") == gm]
        assert held and held[0]["visibility"] == "owner_only" and held[0]["face_state"] == "face_down"
        secret_name = held[0]["name"]
        assert secret_name in {"Access Card", "The Artifact"}

        # Player B never learns the private face of a card they do not hold.
        login(client, b)
        for card in read(client, campaign, "cards").json()["cards"]:
            if card.get("owner_user_id") == gm:
                assert card.get("name") != secret_name
                assert not card.get("metadata")
        assert a != b


def test_a_forged_card_definition_or_foreign_artwork_is_refused(db, tmp_path, monkeypatch):
    from main import app

    gm, _a, _b, campaign = world()
    other_gm = seed_user(name="Other GM")
    other_campaign = seed_campaign(other_gm)
    install(tmp_path, monkeypatch, gm, campaign)
    foreign = image_asset(other_campaign, other_gm, name="foreign.png")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        unknown = command(client, campaign, "cards.instantiateDefinition", {
            "definitionId": "does-not-exist", "artwork": {}})
        assert unknown.status_code not in {200, 201}
        stolen = command(client, campaign, "cards.instantiateDefinition", {
            "definitionId": "infiltration-kit", "version": 1,
            "artwork": {"access-card": foreign, "artifact": foreign}})
        assert stolen.status_code not in {200, 201}


# --- PHASE 10: the clue --------------------------------------------------------

def test_clue_pin_opens_native_content_without_granting_hidden_access(db, tmp_path, monkeypatch):
    from main import app

    gm, a, _b, campaign = world()
    scene = seed_scene(campaign)
    install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        journal = command(client, campaign, "journals.create", {
            "title": "Black Vault - Recovered Log", "type": "lore", "visibility": "private",
            "data": {"sections": [{"id": "intro", "kind": "text", "title": "Recovered Log",
                                   "body": "The night shift never clocked out."}]}})
        assert journal.status_code in {200, 201}, journal.text
        journal_id = journal.json()["journal_id"]
        reference = f"grave://campaign/{campaign}/journal/{journal_id}"

        resolved = read(client, campaign, "content.references", reference=reference)
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["value"]["id"] == journal_id

        # The reference is a pointer, not a grant: a player without access resolves nothing.
        login(client, a)
        hidden = read(client, campaign, "content.references", reference=reference)
        assert hidden.status_code != 200 or not hidden.json().get("value")
        assert scene["id"]


def test_a_content_reference_cannot_address_another_campaign(db, tmp_path, monkeypatch):
    from main import app

    gm, _a, _b, campaign = world()
    other_gm = seed_user(name="Other GM")
    other_campaign = seed_campaign(other_gm)
    seed_member(other_campaign, gm, "player")
    install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, other_gm)
        pass
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        forged = read(client, campaign, "content.references",
                      reference=f"grave://campaign/{other_campaign}/journal/anything")
        assert forged.status_code != 200 or not forged.json().get("value")
