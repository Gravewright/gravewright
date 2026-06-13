from __future__ import annotations

from litestar.testing import TestClient

from app.business.campaigns.campaign_system_service import CampaignSystemService
from app.business.game_page_service import GamePageService
from app.engine.systems.system_install_service import SystemInstallService
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.realtime.events import TransportEvent
from tests.conftest import (
    TEST_SESSION_CONFIG,
    install_system,
    login,
    seed_campaign,
    seed_system,
    seed_user,
)


def _room(user_id: str, campaign_id: str) -> dict:
    return next(
        r for r in GamePageService().build_context(user_id=user_id).rooms if r["id"] == campaign_id
    )


def test_enabled_manifest_system_is_assignable_and_listed(db):
    gm_id = seed_user(name="GM", email="gm-assign@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id)
    svc = SystemInstallService()
    assert svc.install(package_id="dnd5e", user_id=gm_id).success
    assert svc.enable(package_id="dnd5e").success

    context = GamePageService().build_context(user_id=gm_id)
    assert any(s["id"] == "dnd5e" for s in context.available_systems)

    result = CampaignSystemService().assign_to_campaign(
        campaign_id=campaign_id, user_id=gm_id, system_id="dnd5e"
    )
    assert result.success

    assert CampaignRepository().get_for_user(
        campaign_id=campaign_id, user_id=gm_id
    )["active_system_id"] == "dnd5e"
    assert _room(gm_id, campaign_id)["active_system"]["name"] == "Dungeons & Dragons 5e"


def test_area_marker_presets_resolve_labels_for_enabled_system(db):
    gm_id = seed_user(name="GM", email="gm-presets@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id)

    presets = CampaignSystemService().area_marker_presets("dnd5e")

    assert presets, "enabled system should expose its area-marker presets"

    assert all(p.get("label") and not p["label"].startswith("dnd5e.") for p in presets)
    assert {p["id"] for p in presets} == {
        p["id"] for p in _room(gm_id, campaign_id)["active_system"]["area_markers"]
    }


def test_area_marker_presets_empty_when_detached():
    assert CampaignSystemService().area_marker_presets(None) == []


def test_set_system_broadcasts_presets_to_room(db, monkeypatch):
    """Attaching a system pushes the resolved presets to the live room so already
    connected sessions refresh the tool palette without a reload."""
    from main import app
    import app.realtime.transport as transport_mod

    calls: list[tuple] = []

    async def _capture(self, *, room_id, event, payload):
        calls.append((room_id, event, payload))

    monkeypatch.setattr(transport_mod.RealtimeTransport, "to_room", _capture)

    gm_id = seed_user(name="GM", email="gm-broadcast@test.com")
    campaign_id = seed_campaign(gm_id)
    install_system(gm_id)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        resp = client.post(
            "/campaigns/set-system",
            data={"campaign_id": campaign_id, "system_id": "dnd5e"},
            follow_redirects=False,
        )

    assert resp.status_code in {302, 303}
    assert len(calls) == 1
    room_id, event, payload = calls[0]
    assert room_id == campaign_id
    assert event == TransportEvent.CAMPAIGN_SYSTEM_CHANGED
    assert payload["system_id"] == "dnd5e"
    assert payload["area_markers"], "broadcast should carry the resolved presets"
    assert all(m.get("label") and not m["label"].startswith("dnd5e.") for m in payload["area_markers"])


def test_detaching_system_broadcasts_empty_presets(db, monkeypatch):
    from main import app
    import app.realtime.transport as transport_mod

    calls: list[tuple] = []

    async def _capture(self, *, room_id, event, payload):
        calls.append((room_id, event, payload))

    monkeypatch.setattr(transport_mod.RealtimeTransport, "to_room", _capture)

    gm_id = seed_user(name="GM", email="gm-detach@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        resp = client.post(
            "/campaigns/set-system",
            data={"campaign_id": campaign_id, "system_id": ""},
            follow_redirects=False,
        )

    assert resp.status_code in {302, 303}
    assert len(calls) == 1
    _room_id, event, payload = calls[0]
    assert event == TransportEvent.CAMPAIGN_SYSTEM_CHANGED
    assert payload["system_id"] is None
    assert payload["area_markers"] == []


def test_disabled_manifest_system_is_not_assignable(db):
    gm_id = seed_user(name="GM", email="gm-assign-2@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id)
                                
    assert SystemInstallService().install(package_id="dnd5e", user_id=gm_id).success

    result = CampaignSystemService().assign_to_campaign(
        campaign_id=campaign_id, user_id=gm_id, system_id="dnd5e"
    )
    assert not result.success
    assert result.error_key == "inside.systems.errors.not_found"
