from __future__ import annotations

from app.domain.roles import PlayerRole
from app.engine.actors.actor_service import ActorService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.engine.systems.system_install_service import SystemInstallService
from tests.conftest import seed_campaign, seed_member, seed_user


def _enable_test_system(owner_id: str) -> None:
    service = SystemInstallService()
    assert service.install(package_id="dnd5e", user_id=owner_id).success
    assert service.enable(package_id="dnd5e").success


def test_gm_creates_actor_and_initializes_sheet_data(db):
    gm_id = seed_user(name="GM", email="gm-actor@test.com")
    campaign_id = seed_campaign(gm_id)
    _enable_test_system(gm_id)

    result = ActorService().create_actor(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        actor_type="character",
        name="Aria",
    )

    assert result.success
    assert result.actor_id is not None
    assert result.version == 1

    data = SheetDataService().get_data(actor_id=result.actor_id, user_id=gm_id)
    assert data.success
    assert data.version == 1
    assert data.data["hp"]["value"] == 10
    assert data.data["hp"]["max"] == 10
    assert data.data["abilities"]["dex"]["score"] == 10


def test_player_cannot_create_actor(db):
    gm_id = seed_user(name="GM", email="gm-actor-2@test.com")
    player_id = seed_user(name="Player", email="player-actor-2@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    _enable_test_system(gm_id)

    result = ActorService().create_actor(
        campaign_id=campaign_id,
        user_id=player_id,
        system_id="dnd5e",
        actor_type="character",
        name="Sneaky",
    )
    assert not result.success
    assert result.error_key == "game.actors.errors.gm_required"


def test_create_rejects_unknown_actor_type(db):
    gm_id = seed_user(name="GM", email="gm-actor-3@test.com")
    campaign_id = seed_campaign(gm_id)
    _enable_test_system(gm_id)

    result = ActorService().create_actor(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        actor_type="dragon",
        name="Smaug",
    )
    assert not result.success
    assert result.error_key == "game.actors.errors.invalid_type"


def test_create_requires_enabled_system(db):
    gm_id = seed_user(name="GM", email="gm-actor-4@test.com")
    campaign_id = seed_campaign(gm_id)
                                
    assert SystemInstallService().install(package_id="dnd5e", user_id=gm_id).success

    result = ActorService().create_actor(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        actor_type="character",
        name="Aria",
    )
    assert not result.success
    assert result.error_key == "game.actors.errors.system_not_enabled"


def test_update_core_bumps_version(db):
    gm_id = seed_user(name="GM", email="gm-actor-5@test.com")
    campaign_id = seed_campaign(gm_id)
    _enable_test_system(gm_id)
    created = ActorService().create_actor(
        campaign_id=campaign_id, user_id=gm_id, system_id="dnd5e",
        actor_type="character", name="Aria",
    )

    updated = ActorService().update_core(
        actor_id=created.actor_id, user_id=gm_id, name="Aria the Bold"
    )
    assert updated.success
    assert updated.version == 2

    fetched = ActorService().get_actor(actor_id=created.actor_id, user_id=gm_id)
    assert fetched["name"] == "Aria the Bold"


def test_player_cannot_view_private_actor(db):
    gm_id = seed_user(name="GM", email="gm-actor-6@test.com")
    player_id = seed_user(name="Player", email="player-actor-6@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    _enable_test_system(gm_id)
    created = ActorService().create_actor(
        campaign_id=campaign_id, user_id=gm_id, system_id="dnd5e",
        actor_type="character", name="Aria",
    )

    assert ActorService().get_actor(actor_id=created.actor_id, user_id=player_id) is None
    assert ActorService().list_for_campaign(campaign_id=campaign_id, user_id=player_id) == []
