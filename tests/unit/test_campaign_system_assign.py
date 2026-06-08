from __future__ import annotations

from app.business.campaigns.campaign_system_service import CampaignSystemService
from app.business.game_page_service import GamePageService
from app.engine.systems.system_install_service import SystemInstallService
from app.persistence.repositories.campaign_repository import CampaignRepository
from tests.conftest import seed_campaign, seed_system, seed_user


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
