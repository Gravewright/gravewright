from litestar.testing import TestClient

from app.engine.audio.sound_domain_service import SoundDomainService
from app.persistence.repositories.asset_repository import AssetRepository
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user
from tests.unit.test_sdk_runtime_expansion import _install_runtime_addon


CAPS = ["scene.spatialSounds.read", "scene.spatialSounds.write"]


def _command(client, campaign_id, name, payload):
    return client.post(
        f"/sdk/runtime/command/{name}",
        json={"campaign_id": campaign_id, "package_id": "runtime-addon", "payload": payload},
    )


def _native_sound(tmp_path, campaign_id, gm_id):
    audio = tmp_path / "alarm.ogg"
    audio.write_bytes(b"OggS" + b"x" * 32)
    asset = AssetRepository().create(
        campaign_id=campaign_id, owner_user_id=gm_id, filename="alarm.ogg",
        content_type="audio/ogg", byte_size=audio.stat().st_size,
        storage_path=str(audio), hash="sdk-spatial-alarm",
    )
    result = SoundDomainService().create_sound(
        campaign_id=campaign_id, user_id=gm_id,
        values={"name": "Alarm", "assetId": asset["id"], "kind": "sound-effect"},
    )
    assert result.success
    return result.value


def test_sdk_spatial_sound_crud_cas_and_native_resource_parity(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)
    sound = _native_sound(tmp_path, campaign, gm)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, CAPS)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        created = _command(client, campaign, "spatialSounds.create", {
            "sceneId": scene["id"], "input": {
                "soundId": sound["id"], "position": {"x": 120, "y": 80},
                "radius": 350, "gain": 0.7, "falloff": "smooth", "loop": True,
                "enabled": True, "audience": {"kind": "campaign"},
                "constrainedByWalls": True,
            },
        })
        assert created.status_code == 201, created.text
        emitter = created.json()["spatialSound"]
        assert emitter["position"] == {"x": 120.0, "y": 80.0}
        assert SoundDomainService().get_spatial(campaign, emitter["id"])["id"] == emitter["id"]

        params = {"campaign_id": campaign, "package_id": "runtime-addon"}
        listed = client.get("/sdk/runtime/read/scene.spatialSounds", params={**params, "scene_id": scene["id"]})
        fetched = client.get("/sdk/runtime/read/scene.spatialSounds", params={**params, "entity_id": emitter["id"]})
        assert listed.json()["spatialSounds"][0]["id"] == emitter["id"]
        assert fetched.json()["spatialSound"] == emitter

        stale = _command(client, campaign, "spatialSounds.update", {
            "id": emitter["id"], "patch": {"radius": 500}, "expectedVersion": 999,
        })
        assert stale.status_code != 200
        assert SoundDomainService().get_spatial(campaign, emitter["id"])["radius"] == 350

        updated = _command(client, campaign, "spatialSounds.update", {
            "id": emitter["id"], "patch": {"position": {"x": 200, "y": 210}, "radius": 500, "enabled": False},
            "expectedVersion": emitter["version"],
        }).json()["spatialSound"]
        assert updated["position"] == {"x": 200.0, "y": 210.0}
        assert updated["radius"] == 500 and updated["enabled"] is False

        deleted = _command(client, campaign, "spatialSounds.delete", {
            "id": emitter["id"], "expectedVersion": updated["version"],
        })
        assert deleted.json() == {"id": emitter["id"], "deleted": True}
        assert SoundDomainService().get_spatial(campaign, emitter["id"]) is None


def test_sdk_spatial_sound_authority_isolation_audience_and_invalid_values(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    player = seed_user(name="Player")
    campaign = seed_campaign(gm)
    seed_member(campaign, player, "player")
    scene = seed_scene(campaign)
    other_gm = seed_user(name="Other GM")
    other_campaign = seed_campaign(other_gm)
    other_scene = seed_scene(other_campaign)
    sound = _native_sound(tmp_path, campaign, gm)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, CAPS)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        base = {"soundId": sound["id"], "position": {"x": 1, "y": 2}, "radius": 10}
        for bad in (
            {**base, "radius": -1}, {**base, "radius": 100001},
            {**base, "gain": 2}, {**base, "falloff": "inverse"},
            {**base, "position": {"x": "NaN", "y": 2}},
        ):
            response = _command(client, campaign, "spatialSounds.create", {"sceneId": scene["id"], "input": bad})
            assert response.status_code < 500 and response.status_code != 200
        forged_scene = _command(client, campaign, "spatialSounds.create", {"sceneId": other_scene["id"], "input": base})
        assert forged_scene.status_code != 200
        hidden = _command(client, campaign, "spatialSounds.create", {
            "sceneId": scene["id"], "input": {**base, "audience": {"kind": "gm"}},
        }).json()["spatialSound"]

        login(client, player)
        params = {"campaign_id": campaign, "package_id": "runtime-addon", "entity_id": hidden["id"]}
        assert client.get("/sdk/runtime/read/scene.spatialSounds", params=params).json()["spatialSound"] is None
        denied = _command(client, campaign, "spatialSounds.update", {
            "id": hidden["id"], "patch": {"gain": 0.2}, "expectedVersion": hidden["version"],
        })
        assert denied.status_code != 200
