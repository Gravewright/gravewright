from __future__ import annotations

import json
import pytest
from types import SimpleNamespace

from litestar.testing import TestClient

from app.engine.sdk.package_manifest_validator import validate_manifest
from app.engine.sdk.runtime_dto import actor_snapshot, scene_snapshot
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user


P0_CAPABILITIES = {
    "events.subscribe", "permissions.inspect", "actors.read", "actors.write", "actors.data.write",
    "items.read", "items.write", "tokens.read", "tokens.move", "tokens.manage",
    "scene.read", "scene.geometry.read", "scene.geometry.write", "scene.effects.read",
    "scene.effects.write", "ui.slots", "chat.read", "combat.read", "combat.manage",
    "rules.actions",
    "pdf.read", "pdf.viewer", "pdf.annotations.read", "pdf.annotations.write",
    "cards.read", "cards.manage",
}


def _manifest(capabilities: list[str]) -> dict:
    return {
        "schemaVersion": 1, "sdkVersion": "1", "kind": "addon", "id": "runtime-addon",
        "name": "Runtime Addon", "version": "1.0.0", "authors": ["Test"], "license": "MIT",
        "compatibility": {"minimum": "1", "verified": "1", "maximum": "1.x"},
        "capabilities": capabilities, "activation": {"scope": "campaign", "mode": "multiple"},
        "entrypoints": {}, "provides": {},
    }


def _install_runtime_addon(tmp_path, monkeypatch, user_id: str, campaign_id: str, capabilities: list[str]):
    from app.engine.sdk import package_registry
    from app.engine.sdk.package_activation_service import PackageActivationService
    from app.engine.sdk.package_install_service import PackageInstallService

    root = tmp_path / "packages"
    package = root / "addons" / "runtime-addon"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(json.dumps(_manifest(capabilities)), encoding="utf-8")
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", root)
    installed = PackageInstallService().install(package_id="runtime-addon", user_id=user_id)
    assert installed.success, installed.error_key
    assert PackageInstallService().enable(package_id="runtime-addon").success
    assert PackageActivationService().activate_package(campaign_id, "runtime-addon", user_id).success


def test_all_p0_capabilities_are_sdk1_manifest_capabilities():
    result = validate_manifest(_manifest(sorted(P0_CAPABILITIES)))
    assert result.ok, result.errors


def test_public_dtos_drop_private_fields_and_separate_scene_granularity():
    actor = actor_snapshot({"id": "a", "name": "Hero", "version": 3, "permissions_json": "secret"})
    scene = scene_snapshot({"id": "s", "tile_size": 256, "grid_size": 70, "chunk_size": 16, "private": True})
    assert actor == {"id": "a", "name": "Hero", "version": 3}
    assert scene["raster_tile_size"] == 256
    assert scene["grid_size"] == 70
    assert scene["chunk_span"] == 16
    assert "private" not in scene


def test_runtime_read_requires_active_declared_package_and_user_authority(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    outsider = seed_user(name="Outsider")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ["scene.read"])

    params = {"campaign_id": campaign, "package_id": "runtime-addon"}
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        visible = client.get("/sdk/runtime/read/scenes", params=params)
        missing_capability = client.get("/sdk/runtime/read/actors", params=params)
        login(client, outsider)
        denied = client.get("/sdk/runtime/read/scenes", params=params)

    assert visible.status_code == 200
    public_scene = visible.json()["scenes"][0]
    assert public_scene["id"] == scene["id"]
    assert {"grid_size", "raster_tile_size", "chunk_span"} <= public_scene.keys()
    assert missing_capability.status_code == 403
    assert missing_capability.json()["error"]["code"] == "CAPABILITY_REQUIRED"
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "PERMISSION_DENIED"


def test_raw_action_graph_endpoint_is_not_exposed(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ["rules.actions"])
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        response = client.post("/sdk/runtime/command/rules.validate", json={
            "campaign_id": campaign, "package_id": "runtime-addon",
            "payload": {"actions": [{"type": "combat.advance"}] * 33},
        })
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_geometry_write_has_independent_package_and_user_gates(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    player = seed_user(name="Player")
    campaign = seed_campaign(gm)
    seed_member(campaign, player, "player")
    scene = seed_scene(campaign)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ["scene.geometry.read", "scene.geometry.write"])
    body = {"campaign_id": campaign, "package_id": "runtime-addon", "payload": {
        "sceneId": scene["id"], "kind": "wall", "x1": 0, "y1": 0, "x2": 70, "y2": 0,
    }}
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        created = client.post("/sdk/runtime/command/geometry.createWall", json=body)
        listed = client.get("/sdk/runtime/read/geometry", params={
            "campaign_id": campaign, "package_id": "runtime-addon", "scene_id": scene["id"],
        })
        login(client, player)
        denied = client.post("/sdk/runtime/command/geometry.createWall", json=body)
    assert created.status_code == 201
    assert len(listed.json()["walls"]) == 1
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_hidden_actor_event_is_delivered_only_to_its_authorized_audience(db, monkeypatch):
    from app.actions.game import manage_actors
    from app.engine.actors.actor_service import ActorResult
    from app.persistence.repositories.actor_repository import ActorRepository
    from app.realtime.events import TransportEvent

    gm = seed_user(name="GM")
    owner = seed_user(name="Owner")
    stranger = seed_user(name="Stranger")
    campaign = seed_campaign(gm)
    seed_member(campaign, owner, "player")
    seed_member(campaign, stranger, "player")
    actor_id = ActorRepository().create(campaign_id=campaign, system_id="system", actor_type="npc", name="Secret", created_by_user_id=gm, owner_user_ids=[owner])
    delivered: list[str] = []

    class Transport:
        async def to_players(self, *, player_ids, event, payload):
            delivered.extend(player_ids)

    monkeypatch.setattr(manage_actors, "RealtimeTransport", Transport)
    await manage_actors._emit_actor(TransportEvent.ACTOR_UPDATED, ActorResult(success=True, actor_id=actor_id, campaign_id=campaign, system_id="system", version=2), user_id=gm)
    assert set(delivered) == {gm, owner}
    assert stranger not in delivered


def test_doctor_detects_used_undeclared_and_declared_unused_capabilities(tmp_path):
    from app.engine.sdk.package_doctor_service import PackageDoctorService

    (tmp_path / "main.js").write_text("sdk.items.get('item-id');", encoding="utf-8")
    loaded = SimpleNamespace(
        package_dir=tmp_path,
        manifest=SimpleNamespace(
            capabilities=["actors.read"],
            entrypoints={"game": SimpleNamespace(scripts=["main.js"])},
        ),
    )
    findings = PackageDoctorService()._audit_capabilities("addon", loaded)
    assert any(f.code == "capability_used_undeclared" and f.details["capability"] == "items.read" for f in findings)
    assert any(f.code == "capability_declared_unused" and f.details["capability"] == "actors.read" for f in findings)


def test_doctor_rejects_package_access_to_internal_game_routes(tmp_path):
    from app.engine.sdk.package_doctor_service import PackageDoctorService

    (tmp_path / "main.js").write_text('fetch("/game/cards/state/campaign");', encoding="utf-8")
    loaded = SimpleNamespace(
        package_dir=tmp_path,
        manifest=SimpleNamespace(
            capabilities=[],
            entrypoints={"game": SimpleNamespace(scripts=["main.js"])},
        ),
    )
    findings = PackageDoctorService()._audit_capabilities("addon", loaded)
    assert any(
        finding.code == "package_internal_route_access"
        and finding.details["route"] == "/game/cards/state/campaign"
        for finding in findings
    )


def test_bundled_rulesets_do_not_call_internal_game_routes():
    from app.helpers.env import PROJECT_ROOT

    roots = PROJECT_ROOT / "data" / "packages" / "rulesets"
    offenders = []
    for script in roots.rglob("*.js"):
        if '"/game/' in script.read_text(encoding="utf-8") or "'/game/" in script.read_text(encoding="utf-8"):
            offenders.append(str(script.relative_to(PROJECT_ROOT)))
    assert offenders == []


def test_actor_write_rejects_a_stale_expected_version(db):
    from app.persistence.repositories.actor_repository import ActorRepository

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    repository = ActorRepository()
    actor_id = repository.create(campaign_id=campaign, system_id="system", actor_type="npc", name="Before", created_by_user_id=gm)
    current = repository.update_core(actor_id=actor_id, name="Current", folder_id=None, portrait_asset_id=None, token_asset_id=None, expected_version=1)
    stale = repository.update_core(actor_id=actor_id, name="Stale", folder_id=None, portrait_asset_id=None, token_asset_id=None, expected_version=1)
    assert current == 2
    assert stale is None
    assert repository.get(actor_id)["name"] == "Current"


def test_pdf_service_validates_document_visibility_and_annotation_shape():
    from app.engine.sdk.pdf_service import SdkPdfService
    from app.engine.assets.asset_read_service import AssetReadResult

    class Assets:
        def get_by_id(self, document_id):
            return {"id": document_id, "campaign_id": "campaign", "filename": "rules.pdf", "content_type": "application/pdf", "byte_size": 42, "created_at": 10}

    class Reader:
        def get_asset(self, **kwargs):
            return AssetReadResult(success=True)

    class Annotations:
        row = None

        def create(self, **values):
            self.row = {"id": "note", "created_at": 11, "updated_at": 11, "region_json": json.dumps(values.pop("region")), **values}
            return self.row

        def list_for_document(self, **kwargs):
            return []

        def get(self, annotation_id):
            return self.row if self.row and self.row["id"] == annotation_id else None

        def update(self, **values):
            self.row = {**self.row, **values, "region_json": json.dumps(values.pop("region")), "updated_at": 12}
            return self.row

        def delete(self, annotation_id):
            return bool(self.row and self.row["id"] == annotation_id)

    service = SdkPdfService(assets=Assets(), reader=Reader(), annotations=Annotations())
    document = service.document(campaign_id="campaign", document_id="book", user_id="user")
    created = service.create_annotation(campaign_id="campaign", document_id="book", user_id="user", page=12, region={"x": 1, "y": 2, "width": 3, "height": 4}, text="grapple")
    invalid = service.create_annotation(campaign_id="campaign", document_id="book", user_id="user", page=0, region={}, text="")
    updated = service.update_annotation(campaign_id="campaign", document_id="book", annotation_id="note", user_id="user", page=13, region={"x": 2, "y": 3, "width": 4, "height": 5}, text="updated")
    deleted = service.delete_annotation(campaign_id="campaign", document_id="book", annotation_id="note", user_id="user")

    assert document.success and document.value["url"] == "/game/assets/file/book"
    assert created.success and created.value["page"] == 12 and created.value["text"] == "grapple"
    assert not invalid.success and invalid.error_key == "sdk.pdf.annotation_page_invalid"
    assert updated.success and updated.value["page"] == 13
    assert deleted.success and deleted.value["annotation_id"] == "note"


def test_sdk1_expansion_methods_are_gated_and_bridged():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    registry = json.loads((root / "app/engine/sdk/capabilities.json").read_text(encoding="utf-8"))
    runtime = (root / "static/js/sdk/gravewright-sdk.js").read_text(encoding="utf-8")
    bridge = (root / "app/actions/sdk/runtime.py").read_text(encoding="utf-8")
    expected = {
        "cards.manage": {"cards.reveal", "cards.discard", "cards.play", "cards.updatePlacement", "cards.discardPlacement"},
        "items.data.write": {"items.patchData"},
        "combat.manage": {"combat.advanceRound", "combat.setFlags", "combat.rollInitiative"},
        "journals.read": {"journals.get", "journals.list"},
        "journals.write": {"journals.create", "journals.update", "journals.delete"},
        "handouts.present": {"handouts.present"},
        "scene.fog.write": {"scene.fog.enable", "scene.fog.disable", "scene.fog.reset", "scene.fog.paint"},
        "scene.images.write": {"scene.images.place", "scene.images.update", "scene.images.delete"},
        "pdf.annotations.write": {"pdf.annotations.create", "pdf.annotations.update", "pdf.annotations.delete"},
    }
    for capability, methods in expected.items():
        registered = set(registry["capabilities"][capability]["methods"])
        assert methods <= registered
        for method in methods:
            assert f'requireCap("{method}")' in runtime
            assert method.split(".")[-1] in bridge


def test_id_mutations_cannot_cross_the_authorized_campaign(db, tmp_path, monkeypatch):
    from main import app
    from app.engine.journals.journal_service import JournalService
    from app.persistence.repositories.journal_repository import JournalRepository
    from app.persistence.repositories.scene_repository import SceneRepository

    gm = seed_user(name="GM")
    authorized_campaign = seed_campaign(gm, title="Authorized")
    other_campaign = seed_campaign(gm, title="Other")
    other_scene = seed_scene(other_campaign)
    journal = JournalService().create_journal(
        campaign_id=other_campaign,
        user_id=gm,
        journal_type="diary",
        title="Other journal",
        content_markdown="secret",
        data={"content": "secret", "gm": ""},
    )
    _install_runtime_addon(
        tmp_path,
        monkeypatch,
        gm,
        authorized_campaign,
        ["journals.write", "scene.fog.write"],
    )
    common = {"campaign_id": authorized_campaign, "package_id": "runtime-addon"}
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        journal_response = client.post(
            "/sdk/runtime/command/journals.update",
            json={**common, "payload": {"journalId": journal.journal_id, "title": "Changed"}},
        )
        fog_response = client.post(
            "/sdk/runtime/command/fog.enable",
            json={**common, "payload": {"sceneId": other_scene["id"], "initial": "hide_all"}},
        )

    assert journal_response.status_code == 404
    assert fog_response.status_code == 404
    assert JournalRepository().get_by_id(journal.journal_id)["title"] == "Other journal"
    assert not bool(SceneRepository().get_by_id(other_scene["id"])["fog_enabled"])


def test_journal_update_is_a_non_destructive_patch(db, tmp_path, monkeypatch):
    from main import app
    from app.engine.journals.journal_service import JournalService
    from app.persistence.repositories.journal_repository import JournalRepository

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    created = JournalService().create_journal(
        campaign_id=campaign,
        user_id=gm,
        journal_type="diary",
        title="Before",
        visibility="shared",
        content_markdown="preserve markdown",
        data={"content": "preserve data", "gm": "gm data"},
    )
    data_before = JournalRepository().get_by_id(created.journal_id)["data_json"]
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ["journals.write"])
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        response = client.post(
            "/sdk/runtime/command/journals.update",
            json={
                "campaign_id": campaign,
                "package_id": "runtime-addon",
                "payload": {"journalId": created.journal_id, "title": "After"},
            },
        )

    row = JournalRepository().get_by_id(created.journal_id)
    assert response.status_code == 200
    assert row["title"] == "After"
    assert row["visibility"] == "shared"
    assert row["content_markdown"] == "preserve markdown"
    assert row["data_json"] == data_before


def test_pdf_runtime_has_independent_read_and_annotation_capability_gates(db, tmp_path, monkeypatch):
    from main import app
    from app.actions.sdk import runtime
    from app.engine.sdk.pdf_service import PdfResult

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ["pdf.read", "pdf.annotations.write"])

    class PdfService:
        def document(self, **kwargs):
            return PdfResult(True, {"id": kwargs["document_id"], "url": "/game/assets/file/book"})

        def create_annotation(self, **kwargs):
            return PdfResult(True, {"id": "note", "document_id": kwargs["document_id"], "page": kwargs["page"], "region": kwargs["region"], "text": kwargs["text"]})

    monkeypatch.setattr(runtime, "SdkPdfService", PdfService)
    params = {"campaign_id": campaign, "package_id": "runtime-addon", "document_id": "book"}
    body = {"campaign_id": campaign, "package_id": "runtime-addon", "payload": {"documentId": "book", "page": 12, "region": {"x": 1, "y": 2, "width": 3, "height": 4}, "text": "note"}}
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        read = client.get("/sdk/runtime/read/pdf", params=params)
        annotation = client.post("/sdk/runtime/command/pdf.annotations.create", json=body)
        missing_list_capability = client.get("/sdk/runtime/read/pdf.annotations", params=params)

    assert read.status_code == 200 and read.json()["document"]["id"] == "book"
    assert annotation.status_code == 201 and annotation.json()["annotation"]["page"] == 12
    assert missing_list_capability.status_code == 403
    assert missing_list_capability.json()["error"]["code"] == "CAPABILITY_REQUIRED"
