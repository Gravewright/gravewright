from __future__ import annotations

from app.domain.roles import PlayerRole
from app.engine.actors.actor_service import ActorService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.engine.systems.system_install_service import SystemInstallService
from tests.conftest import seed_campaign, seed_member, seed_user


def _setup(db_email_prefix: str) -> tuple[str, str, str]:
    gm_id = seed_user(name="GM", email=f"gm-{db_email_prefix}@test.com")
    campaign_id = seed_campaign(gm_id)
    service = SystemInstallService()
    assert service.install(package_id="dnd5e", user_id=gm_id).success
    assert service.enable(package_id="dnd5e").success
    actor = ActorService().create_actor(
        campaign_id=campaign_id, user_id=gm_id, system_id="dnd5e",
        actor_type="character", name="Aria",
    )
    assert actor.success
    return gm_id, campaign_id, actor.actor_id


def test_patch_sets_nested_path_and_bumps_version(db):
    gm_id, _, actor_id = _setup("sd-1")

    result = SheetDataService().patch_data(
        actor_id=actor_id, user_id=gm_id,
        patch={"hp.value": 20, "hp.max": 30, "level": 3},
    )
    assert result.success
    assert result.version == 2
    assert result.changed_paths == ["hp.max", "hp.value", "level"]

    fetched = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id)
    assert fetched.data["hp"]["value"] == 20
    assert fetched.data["hp"]["max"] == 30
    assert fetched.data["level"] == 3
    assert fetched.version == 2


def test_patch_merges_without_dropping_siblings(db):
    gm_id, _, actor_id = _setup("sd-2")
    service = SheetDataService()
    service.patch_data(actor_id=actor_id, user_id=gm_id, patch={"hp.value": 10, "hp.max": 10})
    service.patch_data(actor_id=actor_id, user_id=gm_id, patch={"hp.value": 4})

    fetched = service.get_data(actor_id=actor_id, user_id=gm_id)
    assert fetched.data["hp"]["value"] == 4
    assert fetched.data["hp"]["max"] == 10
    assert fetched.version == 3


def test_empty_patch_is_rejected(db):
    gm_id, _, actor_id = _setup("sd-3")
    result = SheetDataService().patch_data(actor_id=actor_id, user_id=gm_id, patch={})
    assert not result.success
    assert result.error_key == "game.sheet_data.errors.empty_patch"


def test_player_cannot_read_or_patch_private_actor(db):
    gm_id, campaign_id, actor_id = _setup("sd-4")
    player_id = seed_user(name="Player", email="player-sd-4@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    read = SheetDataService().get_data(actor_id=actor_id, user_id=player_id)
    patch = SheetDataService().patch_data(actor_id=actor_id, user_id=player_id, patch={"hp.value": 1})

    assert not read.success
    assert read.error_key == "game.actors.errors.not_allowed"
    assert not patch.success
    assert patch.error_key == "game.actors.errors.not_allowed"


def test_set_data_replaces_whole_document(db):
    gm_id, _, actor_id = _setup("sd-5")
    service = SheetDataService()
    service.patch_data(actor_id=actor_id, user_id=gm_id, patch={"hp.value": 10, "old": "x"})

    result = service.set_data(actor_id=actor_id, user_id=gm_id, data={"fresh": True})
    assert result.success
    fetched = service.get_data(actor_id=actor_id, user_id=gm_id)
    assert fetched.data == {"fresh": True}
