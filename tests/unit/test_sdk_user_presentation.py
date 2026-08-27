from __future__ import annotations

import json

import pytest
from litestar.testing import TestClient

from app.business.users import UserPreferenceService
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_user


def _manifest(package_id: str, capabilities: list[str]) -> dict:
    return {
        "schemaVersion": 1,
        "sdkVersion": "1",
        "kind": "addon",
        "id": package_id,
        "name": "Presentation Test",
        "version": "1.0.0",
        "authors": ["Test"],
        "license": "MIT",
        "compatibility": {"minimum": "1", "verified": "1", "maximum": "1.x"},
        "capabilities": capabilities,
        "activation": {"scope": "campaign", "mode": "multiple"},
        "entrypoints": {},
        "provides": {},
    }


def _install(tmp_path, monkeypatch, *, package_id: str, user_id: str, campaign_id: str, capabilities: list[str]):
    from app.engine.sdk import package_registry
    from app.engine.sdk.package_activation_service import PackageActivationService
    from app.engine.sdk.package_install_service import PackageInstallService

    root = tmp_path / package_id / "packages"
    package = root / "addons" / package_id
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(json.dumps(_manifest(package_id, capabilities)), encoding="utf-8")
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", root)
    assert PackageInstallService().install(package_id=package_id, user_id=user_id).success
    assert PackageInstallService().enable(package_id=package_id).success
    assert PackageActivationService().activate_package(campaign_id, package_id, user_id).success


def test_get_and_list_project_only_visible_member_colors(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    player = seed_user(name="Player")
    outsider = seed_user(name="Outsider")
    campaign = seed_campaign(gm)
    seed_member(campaign, player, "player")
    UserPreferenceService().set_ping_color(user_id=gm, ping_color="#FF0000")
    UserPreferenceService().set_ping_color(user_id=player, ping_color="#0000FF")
    _install(tmp_path, monkeypatch, package_id="presentation-test", user_id=gm, campaign_id=campaign, capabilities=["users.presentation.read"])
    params = {"campaign_id": campaign, "package_id": "presentation-test"}

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        current = client.get("/sdk/runtime/read/user.presentations", params={**params, "entity_id": gm})
        other = client.get("/sdk/runtime/read/user.presentations", params={**params, "entity_id": player})
        unknown = client.get("/sdk/runtime/read/user.presentations", params={**params, "entity_id": outsider})
        listed = client.get("/sdk/runtime/read/user.presentations", params=params)

    assert current.json()["presentation"] == {"userId": gm, "color": "#ff0000"}
    assert other.json()["presentation"] == {"userId": player, "color": "#0000ff"}
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "NOT_FOUND"
    assert listed.json()["presentations"] == [
        {"userId": gm, "color": "#ff0000"},
        {"userId": player, "color": "#0000ff"},
    ]
    assert set(listed.json()["presentations"][0]) == {"userId", "color"}


def test_authority_capability_and_cross_campaign_do_not_leak(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    outsider = seed_user(name="Outsider")
    foreign_gm = seed_user(name="Foreign GM")
    campaign = seed_campaign(gm)
    foreign_campaign = seed_campaign(foreign_gm)
    _install(tmp_path, monkeypatch, package_id="presentation-test", user_id=gm, campaign_id=campaign, capabilities=["users.presentation.read"])
    params = {"campaign_id": campaign, "package_id": "presentation-test"}

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, outsider)
        outsider_list = client.get("/sdk/runtime/read/user.presentations", params=params)
        outsider_get = client.get("/sdk/runtime/read/user.presentations", params={**params, "entity_id": gm})
        login(client, gm)
        foreign_target = client.get("/sdk/runtime/read/user.presentations", params={**params, "entity_id": foreign_gm})
        foreign_context = client.get("/sdk/runtime/read/user.presentations", params={**params, "campaign_id": foreign_campaign})

    assert outsider_list.status_code == outsider_get.status_code == 403
    assert outsider_list.json()["error"]["code"] == "PERMISSION_DENIED"
    assert outsider_get.json()["error"]["code"] == "PERMISSION_DENIED"
    assert foreign_target.status_code == 404
    assert foreign_context.status_code == 403
    assert "presentation" not in outsider_get.json()


def test_missing_package_capability_is_rejected(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    _install(tmp_path, monkeypatch, package_id="presentation-no-cap", user_id=gm, campaign_id=campaign, capabilities=[])
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        response = client.get("/sdk/runtime/read/user.presentations", params={"campaign_id": campaign, "package_id": "presentation-no-cap"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CAPABILITY_REQUIRED"


@pytest.mark.asyncio
async def test_canonical_color_update_emits_once_per_authorized_campaign(db, monkeypatch):
    import importlib

    action = importlib.import_module("app.actions.game.update_ping_preference")
    from app.actions.game.update_ping_preference import UpdatePingPreferenceForm
    from app.realtime.events import TransportEvent

    user = seed_user(name="User")
    first = seed_campaign(user)
    second = seed_campaign(user)
    delivered = []

    class Transport:
        async def to_room(self, *, room_id, event, payload):
            delivered.append((room_id, event, payload))

    monkeypatch.setattr(action, "RealtimeTransport", Transport)
    response = await action.update_ping_preference.fn(
        current_user={"id": user},
        user_preference_service=UserPreferenceService(),
        data=UpdatePingPreferenceForm(ping_color="#8B5CF6"),
    )

    assert response.content == {"ok": True, "ping_color": "#8b5cf6"}
    assert {room for room, _, _ in delivered} == {first, second}
    assert len(delivered) == 2
    assert all(event is TransportEvent.USER_PRESENTATION_CHANGED for _, event, _ in delivered)
    assert all(payload == {"user_id": user, "color": "#8b5cf6"} for _, _, payload in delivered)
    assert UserPreferenceService().get_ping_color(user) == "#8b5cf6"


def test_frontend_contract_uses_capability_filtered_event_and_public_shape():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[2] / "static/js/sdk/gravewright-sdk.js").read_text(encoding="utf-8")
    assert 'requireCap("users.presentation.get")' in source
    assert 'requireCap("users.presentation.list")' in source
    assert 'runtimeRead("user.presentations", { entity_id: payload.user_id }, "sdk.events.on")' in source
    assert 'event.resourceId = String(id)' in source
    assert "resource: { id:" not in source


def test_fixture_passes_package_doctor_capability_audit():
    from pathlib import Path

    from app.engine.sdk.package_doctor_service import PackageDoctorService
    from app.engine.sdk.package_loader import load_package

    package = Path(__file__).resolve().parents[1] / "fixtures/sdk_packages/valid/addons/user-presentation-reader"
    loaded = load_package(package, expected_id="user-presentation-reader", expected_kind_root="addons")
    assert PackageDoctorService()._audit_capabilities("user-presentation-reader", loaded) == []
