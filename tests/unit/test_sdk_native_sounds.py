import base64
import json

from litestar.testing import TestClient

from app.engine.audio.sound_domain_service import SoundDomainService
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user
from tests.unit.test_sdk_runtime_expansion import _install_runtime_addon
from tests.unit.test_sdk_runtime_expansion import _manifest


CAPS = ["assets.library", "assets.import", "sounds.read", "sounds.write", "scene.spatialSounds.write"]


def _command(client, campaign_id, name, payload):
    return client.post(
        f"/sdk/runtime/command/{name}",
        json={"campaign_id": campaign_id, "package_id": "runtime-addon", "payload": payload},
    )


def test_public_audio_asset_to_native_sound_to_spatial_sound_chain(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, CAPS)
    source = {"kind": "browser-file", "name": "alarm.ogg", "mime": "audio/ogg", "base64": base64.b64encode(b"OggS" + b"x" * 64).decode()}

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        first = _command(client, campaign, "assets.ingest", {"source": source})
        second = _command(client, campaign, "assets.ingest", {"source": source})
        assert first.status_code == 201 and first.json()["asset"]["kind"] == "audio"
        assert second.json()["asset"]["id"] == first.json()["asset"]["id"]
        assert second.json()["deduplicated"] is True
        asset = first.json()["asset"]
        assert "storage_path" not in asset

        created = _command(client, campaign, "sounds.create", {"input": {
            "name": "Security Alarm", "asset": {"kind": "library-asset", "id": asset["id"]},
            "kind": "sound-effect", "defaultGain": 0.8, "defaultLoop": True,
            "tags": ["alarm", "vault"], "metadata": {"role": "security"},
        }})
        assert created.status_code == 201, created.text
        sound = created.json()["sound"]
        assert sound["asset"] == {"kind": "library-asset", "id": asset["id"]}
        assert SoundDomainService()._sound(campaign, sound["id"])["id"] == sound["id"]

        params = {"campaign_id": campaign, "package_id": "runtime-addon"}
        listed = client.get("/sdk/runtime/read/sounds", params={**params, "kinds": "sound-effect", "q": "Alarm"})
        fetched = client.get("/sdk/runtime/read/sounds", params={**params, "entity_id": sound["id"]})
        assert listed.json()["sounds"] == [sound]
        assert fetched.json()["sound"] == sound

        stale = _command(client, campaign, "sounds.update", {"id": sound["id"], "patch": {"name": "Stale"}, "expectedVersion": 999})
        assert stale.status_code != 200
        updated = _command(client, campaign, "sounds.update", {"id": sound["id"], "patch": {"name": "Vault Alarm", "defaultGain": 0.6}, "expectedVersion": sound["version"]}).json()["sound"]
        assert updated["name"] == "Vault Alarm" and updated["defaultGain"] == 0.6

        spatial = _command(client, campaign, "spatialSounds.create", {"sceneId": scene["id"], "input": {
            "soundId": sound["id"], "position": {"x": 10, "y": 20}, "radius": 300,
        }}).json()["spatialSound"]
        # Dependency policy: the SDK denies with the same information the native
        # UI shows, and never leaves a dangling emitter behind.
        blocked = _command(client, campaign, "sounds.delete", {"id": sound["id"], "expectedVersion": updated["version"]})
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "RESOURCE_IN_USE"
        assert blocked.json()["error"]["details"]["dependencyCount"] == 1
        assert SoundDomainService().get_spatial(campaign, spatial["id"])["sound_id"] == sound["id"]

        # Once the emitter is gone the same delete succeeds under CAS.
        _command(client, campaign, "spatialSounds.delete", {"id": spatial["id"], "expectedVersion": spatial["version"]})
        removed = _command(client, campaign, "sounds.delete", {"id": sound["id"], "expectedVersion": updated["version"]})
        assert removed.status_code in {200, 201}, removed.text
        assert SoundDomainService()._sound(campaign, sound["id"]) is None


def test_native_sound_sdk_rejects_wrong_assets_authority_and_invalid_values(db, tmp_path, monkeypatch):
    from main import app
    from app.persistence.repositories.asset_repository import AssetRepository

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    other_gm = seed_user(name="Other GM")
    other_campaign = seed_campaign(other_gm)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, CAPS)
    image = tmp_path / "image.png"
    image.write_bytes(b"not-used")
    image_asset = AssetRepository().create(campaign_id=campaign, owner_user_id=gm, filename="x.png", content_type="image/png", byte_size=8, storage_path=str(image), hash="image")
    other_asset = AssetRepository().create(campaign_id=other_campaign, owner_user_id=other_gm, filename="x.ogg", content_type="audio/ogg", byte_size=8, storage_path=str(image), hash="other-audio")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        for asset_id, kind, gain in (("missing", "sound-effect", 1), (image_asset["id"], "sound-effect", 1), (other_asset["id"], "sound-effect", 1), (image_asset["id"], "invalid", 1), (image_asset["id"], "sound-effect", "NaN")):
            response = _command(client, campaign, "sounds.create", {"input": {"name": "Bad", "asset": {"kind": "library-asset", "id": asset_id}, "kind": kind, "defaultGain": gain}})
            assert response.status_code != 200 and response.status_code < 500

        login(client, other_gm)
        denied = _command(client, campaign, "sounds.create", {"input": {"name": "Denied", "asset": {"kind": "library-asset", "id": image_asset["id"]}, "kind": "sound-effect"}})
        assert denied.status_code != 200


def test_declared_package_audio_is_canonicalized_before_native_sound_creation(db, tmp_path, monkeypatch):
    from main import app
    from app.engine.sdk import package_registry
    from app.engine.sdk.package_activation_service import PackageActivationService
    from app.engine.sdk.package_install_service import PackageInstallService

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    root = tmp_path / "packages"
    package = root / "addons" / "runtime-addon"
    (package / "audio").mkdir(parents=True)
    (package / "audio" / "hum.ogg").write_bytes(b"OggS" + b"package-hum" * 4)
    manifest = _manifest(CAPS + ["assets.audio"])
    manifest["provides"] = {"assets": {"audio": [{"id": "hum", "label": "Hum", "path": "audio/hum.ogg"}]}}
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", root)
    assert PackageInstallService().install(package_id="runtime-addon", user_id=gm).success
    assert PackageInstallService().enable(package_id="runtime-addon").success
    assert PackageActivationService().activate_package(campaign, "runtime-addon", gm).success

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        created = _command(client, campaign, "sounds.create", {"input": {
            "name": "Generator Hum", "asset": {"kind": "package-asset", "id": "audio/hum.ogg"},
            "kind": "sound-effect", "defaultLoop": True,
        }})
        assert created.status_code == 201, created.text
        sound = created.json()["sound"]
        assert sound["asset"]["kind"] == "library-asset"
        native = SoundDomainService()._sound(campaign, sound["id"])
        assert native["asset_id"] == sound["asset"]["id"]


def test_native_sound_library_and_sdk_share_one_canonical_domain(db, tmp_path, monkeypatch):
    """Native Artistic Layer routes and the SDK must be two doors to one Sound."""
    from main import app

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, CAPS)
    source = {"kind": "browser-file", "name": "hum.ogg", "mime": "audio/ogg", "base64": base64.b64encode(b"OggS" + b"h" * 64).decode()}
    params = {"campaign_id": campaign, "package_id": "runtime-addon"}

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        asset = _command(client, campaign, "assets.ingest", {"source": source}).json()["asset"]

        # Native Artistic Layer creates it; the SDK must read the same resource.
        native = client.post("/game/sounds", json={
            "campaignId": campaign, "name": "Native Hum", "assetId": asset["id"],
            "kind": "ambience", "defaultGain": 0.5, "defaultLoop": True,
        })
        assert native.status_code == 201, native.text
        native_sound = native.json()
        seen = client.get("/sdk/runtime/read/sounds", params={**params, "entity_id": native_sound["id"]}).json()["sound"]
        assert seen["id"] == native_sound["id"] and seen["name"] == "Native Hum"
        assert seen["asset"] == {"kind": "library-asset", "id": asset["id"]}

        # The SDK creates it; the native Sound library must list the same resource.
        sdk_sound = _command(client, campaign, "sounds.create", {"input": {
            "name": "Package Hum", "asset": {"kind": "library-asset", "id": asset["id"]},
            "kind": "ambience", "defaultGain": 0.4,
        }}).json()["sound"]
        library = client.get(f"/game/sounds/{campaign}").json()
        assert {row["id"] for row in library} == {native_sound["id"], sdk_sound["id"]}

        # Updates flow both ways against the same version counter.
        renamed = client.post("/game/sounds/update", json={
            "campaignId": campaign, "soundId": sdk_sound["id"],
            "patch": {"name": "Renamed Natively"}, "expectedVersion": sdk_sound["version"],
        })
        assert renamed.status_code == 200, renamed.text
        reread = client.get("/sdk/runtime/read/sounds", params={**params, "entity_id": sdk_sound["id"]}).json()["sound"]
        assert reread["name"] == "Renamed Natively" and reread["version"] == sdk_sound["version"] + 1

        via_sdk = _command(client, campaign, "sounds.update", {
            "id": native_sound["id"], "patch": {"defaultGain": 0.9}, "expectedVersion": native_sound["version"],
        })
        assert via_sdk.status_code in {200, 201}, via_sdk.text
        native_reread = next(row for row in client.get(f"/game/sounds/{campaign}").json() if row["id"] == native_sound["id"])
        assert native_reread["default_gain"] == 0.9


def test_native_sound_sdk_rejects_forged_ids_bad_bounds_and_inactive_packages(db, tmp_path, monkeypatch):
    """The semantic failure matrix: every rejection is typed, bounded and stateless."""
    from main import app
    from app.engine.sdk.package_activation_service import PackageActivationService
    from app.persistence.repositories.asset_repository import AssetRepository

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    player = seed_user(name="Player")
    seed_member(campaign, player, "player")
    other_gm = seed_user(name="Other GM")
    other_campaign = seed_campaign(other_gm)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, CAPS)

    pdf = tmp_path / "handout.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%%EOF")
    pdf_asset = AssetRepository().create(campaign_id=campaign, owner_user_id=gm, filename="handout.pdf",
        content_type="application/pdf", byte_size=pdf.stat().st_size, storage_path=str(pdf), hash="sound-pdf")
    audio = tmp_path / "hum.ogg"
    audio.write_bytes(b"OggS" + b"h" * 32)
    audio_asset = AssetRepository().create(campaign_id=campaign, owner_user_id=gm, filename="hum.ogg",
        content_type="audio/ogg", byte_size=audio.stat().st_size, storage_path=str(audio), hash="sound-audio")
    foreign = SoundDomainService().create_sound(campaign_id=other_campaign, user_id=other_gm,
        values={"name": "Foreign", "assetId": AssetRepository().create(campaign_id=other_campaign,
            owner_user_id=other_gm, filename="f.ogg", content_type="audio/ogg", byte_size=8,
            storage_path=str(audio), hash="sound-foreign")["id"], "kind": "sound-effect"})
    assert foreign.success

    base = {"name": "Bad", "asset": {"kind": "library-asset", "id": audio_asset["id"]}, "kind": "sound-effect"}
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        for bad in (
            {**base, "asset": {"kind": "library-asset", "id": pdf_asset["id"]}},
            {**base, "defaultGain": "Infinity"},
            {**base, "defaultGain": "NaN"},
            {**base, "defaultGain": -0.1},
            {**base, "defaultGain": 1.5},
            {**base, "tags": [f"tag-{index}" for index in range(33)]},
            {**base, "tags": ["x" * 65]},
            {**base, "tags": "not-a-list"},
            {**base, "metadata": {"blob": "x" * 9000}},
            {**base, "metadata": []},
            {**base, "name": ""},
            {**base, "name": "n" * 192},
        ):
            response = _command(client, campaign, "sounds.create", {"input": bad})
            assert response.status_code not in {200, 201} and response.status_code < 500, bad.get("name")
        # A hand-rolled body with the raw JSON `Infinity` token never reaches the domain.
        raw = client.post("/sdk/runtime/command/sounds.create", headers={"content-type": "application/json"},
            content=json.dumps({"campaign_id": campaign, "package_id": "runtime-addon",
                "payload": {"input": {**base, "defaultGain": 1}}}).replace('"defaultGain": 1', '"defaultGain": Infinity'))
        assert raw.status_code not in {200, 201} and raw.status_code < 500
        assert SoundDomainService().list_sounds(campaign_id=campaign, user_id=gm).value == []

        # Forged and cross-campaign Sound IDs are indistinguishable from absent ones.
        for sound_id in ("forged", foreign.value["id"]):
            for command, payload in (
                ("sounds.update", {"id": sound_id, "patch": {"name": "Taken"}, "expectedVersion": 1}),
                ("sounds.delete", {"id": sound_id, "expectedVersion": 1}),
            ):
                response = _command(client, campaign, command, payload)
                assert response.status_code not in {200, 201} and response.status_code < 500
        assert SoundDomainService()._sound(other_campaign, foreign.value["id"])["name"] == "Foreign"

        owned = _command(client, campaign, "sounds.create", {"input": {**base, "name": "Owned"}}).json()["sound"]

        # A player has no authority to mutate the Sound library.
        login(client, player)
        for command, payload in (
            ("sounds.create", {"input": {**base, "name": "Player"}}),
            ("sounds.update", {"id": owned["id"], "patch": {"name": "Player"}, "expectedVersion": owned["version"]}),
            ("sounds.delete", {"id": owned["id"], "expectedVersion": owned["version"]}),
        ):
            assert _command(client, campaign, command, payload).status_code == 403
        assert SoundDomainService()._sound(campaign, owned["id"])["name"] == "Owned"

        # Deactivating the package closes the surface without touching campaign content.
        login(client, gm)
        assert PackageActivationService().deactivate_package(campaign, "runtime-addon", gm).success
        denied = _command(client, campaign, "sounds.create", {"input": {**base, "name": "Inactive"}})
        assert denied.status_code == 403 and denied.json()["error"]["code"] in {"PACKAGE_INACTIVE", "CAPABILITY_REQUIRED", "PERMISSION_DENIED"}
        assert SoundDomainService()._sound(campaign, owned["id"])["name"] == "Owned"
