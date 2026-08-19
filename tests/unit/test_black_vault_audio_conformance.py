"""Black Vault SDK 1 conformance: the shipped addon must reach persistent
spatial audio through the public contract only.

The package is the LTS stress module, so these tests read the *real* package
directory instead of a fixture: a regression in the public chain must fail here
before it reaches an author.
"""

import re
import shutil
from pathlib import Path

from litestar.testing import TestClient

from app.engine.audio.sound_domain_service import SoundDomainService
from app.engine.scenes.geometry_semantics import sound_attenuation
from app.persistence.repositories.scene_wall_repository import SceneWallRepository
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_scene, seed_user


PACKAGE_ID = "black-vault"
PACKAGE_DIR = Path(__file__).resolve().parents[2] / "examples" / "packages" / PACKAGE_ID
SCRIPT = PACKAGE_DIR / "assets" / "black-vault.js"

# A package that reaches any of these has left the public contract.
PRIVATE_API_PATTERNS = {
    "internal route": r"[\"'`]/(?:game|api|sdk/internal)/",
    "raw websocket": r"\bnew\s+WebSocket\b",
    "renderer": r"\bPIXI\b|\bGravewrightMap\b|\bGravewrightRenderer\b",
    "dom host": r"\bdocument\s*\.\s*(?:querySelector|getElementById|createElement)\b",
    "raw fetch": r"\bfetch\s*\(|\bXMLHttpRequest\b",
    "storage escape": r"\blocalStorage\b|\bindexedDB\b|\brequire\s*\(|\bimport\s*\(",
    "filesystem": r"\bfs\s*\.\s*read|[A-Za-z]:[\\/]{1,2}|\bprocess\s*\.\s*env\b",
}


def _install_black_vault(tmp_path, monkeypatch, user_id, campaign_id):
    from app.engine.sdk import package_registry
    from app.engine.sdk.package_activation_service import PackageActivationService
    from app.engine.sdk.package_install_service import PackageInstallService

    root = tmp_path / "packages"
    (root / "addons").mkdir(parents=True)
    shutil.copytree(PACKAGE_DIR, root / "addons" / PACKAGE_ID)
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", root)
    installed = PackageInstallService().install(package_id=PACKAGE_ID, user_id=user_id)
    assert installed.success, installed.error_key
    assert PackageInstallService().enable(package_id=PACKAGE_ID).success
    assert PackageActivationService().activate_package(campaign_id, PACKAGE_ID, user_id).success


def _command(client, campaign_id, name, payload):
    return client.post(
        f"/sdk/runtime/command/{name}",
        json={"campaign_id": campaign_id, "package_id": PACKAGE_ID, "payload": payload},
    )


def _read(client, campaign_id, resource, **params):
    return client.get(
        f"/sdk/runtime/read/{resource}",
        params={"campaign_id": campaign_id, "package_id": PACKAGE_ID, **params},
    )


def test_black_vault_source_uses_public_sdk_only():
    source = SCRIPT.read_text(encoding="utf-8")
    offenders = {label: re.findall(pattern, source) for label, pattern in PRIVATE_API_PATTERNS.items()}
    assert not {label: hits for label, hits in offenders.items() if hits}
    assert "window.GravewrightSDK.register" in source


def test_black_vault_declares_exactly_the_capabilities_it_uses(db, tmp_path, monkeypatch):
    from app.engine.sdk.package_doctor_service import PackageDoctorService

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    _install_black_vault(tmp_path, monkeypatch, gm, campaign)

    findings = [f for f in PackageDoctorService().audit() if f.package_id == PACKAGE_ID]
    unknown = [f for f in findings if f.code == "capability_unknown"]
    undeclared = [f for f in findings if f.code == "capability_used_undeclared"]
    forbidden = [f for f in findings if f.code == "capability_forbidden"]
    internal = [f for f in findings if f.code == "package_internal_route_access"]
    assert unknown == [] and undeclared == [] and forbidden == [] and internal == []
    assert [f for f in findings if f.severity == "error"] == []


def test_black_vault_reaches_persistent_spatial_audio_through_public_chain(db, tmp_path, monkeypatch):
    """Package audio -> canonical Asset -> Native Sound -> Spatial Sound."""
    from main import app

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)
    _install_black_vault(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        sounds = {}
        for name, shipped in (("Generator Hum", "audio/generator-hum.ogg"), ("Security Alarm", "audio/security-alarm.ogg")):
            created = _command(client, campaign, "sounds.create", {"input": {
                "name": name, "asset": {"kind": "package-asset", "id": shipped},
                "kind": "sound-effect", "defaultGain": 0.7, "defaultLoop": True,
                "tags": ["black-vault", "environment"],
            }})
            assert created.status_code == 201, created.text
            sounds[name] = created.json()["sound"]

        # Package-shipped bytes became campaign-owned canonical audio Assets with
        # no storage path or package path leaking into the public identity.
        assert {sound["asset"]["kind"] for sound in sounds.values()} == {"library-asset"}
        assert len({sound["asset"]["id"] for sound in sounds.values()}) == 2
        for sound in sounds.values():
            assert "audio/" not in str(sound["asset"]["id"])

        # sdk.assets.list surfaces them as public `audio` kind, with no raw
        # storage or package path in the payload the package can observe.
        state = client.get(f"/game/assets/state/{campaign}")
        assert state.status_code == 200, state.text
        library = {asset["id"]: asset for asset in state.json()["assets"]}
        audio_assets = [asset for asset in library.values() if asset["kind"] == "audio"]
        assert {asset["id"] for asset in audio_assets} == {sound["asset"]["id"] for sound in sounds.values()}
        assert "storage_path" not in str(state.json()) and str(PACKAGE_DIR) not in str(state.json())

        # Re-resolving the same shipped file must reuse the physical Asset while
        # still minting a distinct semantic Sound.
        again = _command(client, campaign, "sounds.create", {"input": {
            "name": "Generator Hum (Sub Level)", "asset": {"kind": "package-asset", "id": "audio/generator-hum.ogg"},
            "kind": "sound-effect",
        }})
        assert again.status_code == 201, again.text
        reused = again.json()["sound"]
        assert reused["asset"]["id"] == sounds["Generator Hum"]["asset"]["id"]
        assert reused["id"] != sounds["Generator Hum"]["id"]

        emitters = {}
        for name, position, radius, enabled in (
            ("Generator Hum", {"x": 280, "y": 280}, 560, True),
            ("Security Alarm", {"x": 700, "y": 350}, 700, False),
        ):
            created = _command(client, campaign, "spatialSounds.create", {"sceneId": scene["id"], "input": {
                "soundId": sounds[name]["id"], "position": position, "radius": radius,
                "gain": sounds[name]["defaultGain"], "falloff": "smooth", "loop": True,
                "enabled": enabled, "audience": {"kind": "campaign"}, "constrainedByWalls": True,
            }})
            assert created.status_code == 201, created.text
            emitters[name] = created.json()["spatialSound"]

        # Reload: a fresh public read sees the same persistent emitters.
        listed = _read(client, campaign, "scene.spatialSounds", scene_id=scene["id"]).json()["spatialSounds"]
        assert {value["id"] for value in listed} == {value["id"] for value in emitters.values()}
        assert {value["soundId"] for value in listed} == {sounds[name]["id"] for name in sounds}

        door = _command(client, campaign, "geometry.createWall", {
            "sceneId": scene["id"], "kind": "door", "x1": 480, "y1": 120, "x2": 480, "y2": 620,
        })
        assert door.status_code in {200, 201}, door.text
        wall_id = door.json()["wall"]["id"]

        # A listener inside the generator's radius but on the far side of the door.
        origin = (280.0, 280.0, 0.0)
        listener = (700.0, 300.0, 0.0)
        closed = _command(client, campaign, "geometry.setDoorState", {"id": wall_id, "state": "closed"})
        assert closed.status_code in {200, 201}, closed.text
        closed_gain = sound_attenuation(walls=SceneWallRepository().list_for_scene(scene["id"]), origin=origin, target=listener)

        opened = _command(client, campaign, "geometry.setDoorState", {"id": wall_id, "state": "open"})
        assert opened.status_code in {200, 201}, opened.text
        open_gain = sound_attenuation(walls=SceneWallRepository().list_for_scene(scene["id"]), origin=origin, target=listener)

        assert closed_gain < open_gain and open_gain == 1.0

        # The acoustic change is a projection, not a restart: the emitter row and
        # its runtime playback identity survive the door toggle untouched.
        after = _read(client, campaign, "scene.spatialSounds", entity_id=emitters["Generator Hum"]["id"]).json()["spatialSound"]
        assert after == emitters["Generator Hum"]

        projection = SoundDomainService().acoustic_projection(
            campaign_id=campaign, scene_id=scene["id"], user_id=gm,
            listener_x=listener[0], listener_y=listener[1],
        )
        assert projection.success
        generator = next(value for value in projection.value if value["spatialSoundId"] == emitters["Generator Hum"]["id"])
        assert generator["audible"] is True and generator["projection"] > 0
        assert generator["wallAttenuation"] == 1.0

        _command(client, campaign, "geometry.setDoorState", {"id": wall_id, "state": "closed"})
        blocked = SoundDomainService().acoustic_projection(
            campaign_id=campaign, scene_id=scene["id"], user_id=gm,
            listener_x=listener[0], listener_y=listener[1],
        )
        blocked_generator = next(value for value in blocked.value if value["spatialSoundId"] == emitters["Generator Hum"]["id"])
        assert blocked_generator["audible"] is False and blocked_generator["projection"] == 0.0
        assert blocked_generator["playbackId"] == generator["playbackId"]


def test_black_vault_cannot_reach_foreign_or_non_audio_resources(db, tmp_path, monkeypatch):
    from main import app
    from app.persistence.repositories.asset_repository import AssetRepository

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    other_gm = seed_user(name="Other GM")
    other_campaign = seed_campaign(other_gm)
    _install_black_vault(tmp_path, monkeypatch, gm, campaign)

    payload = tmp_path / "foreign.ogg"
    payload.write_bytes(b"OggS" + b"foreign" * 4)
    foreign = AssetRepository().create(
        campaign_id=other_campaign, owner_user_id=other_gm, filename="foreign.ogg",
        content_type="audio/ogg", byte_size=payload.stat().st_size,
        storage_path=str(payload), hash="black-vault-foreign",
    )

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        for asset in (
            {"kind": "package-asset", "id": "../../../etc/passwd"},
            {"kind": "package-asset", "id": "assets/black-vault.js"},
            {"kind": "package-asset", "id": "manifest.json"},
            {"kind": "library-asset", "id": foreign["id"]},
            {"kind": "filesystem", "id": str(PACKAGE_DIR / "audio" / "generator-hum.ogg")},
        ):
            response = _command(client, campaign, "sounds.create", {"input": {
                "name": "Forged", "asset": asset, "kind": "sound-effect",
            }})
            assert response.status_code not in {200, 201} and response.status_code < 500, asset
        assert SoundDomainService().list_sounds(campaign_id=campaign, user_id=gm).value == []
