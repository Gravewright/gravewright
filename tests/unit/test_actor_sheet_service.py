from __future__ import annotations

from app.domain.roles import PlayerRole
from app.engine.actors.actor_service import ActorService
from app.engine.sheets.actor_sheet_service import ActorSheetService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.engine.systems.system_install_service import SystemInstallService
from tests.conftest import seed_campaign, seed_member, seed_user


def _setup(prefix: str, *, package: str = "dnd5e") -> tuple[str, str, str]:
    gm_id = seed_user(name="GM", email=f"gm-{prefix}@test.com")
    campaign_id = seed_campaign(gm_id)
    svc = SystemInstallService()
    assert svc.install(package_id=package, user_id=gm_id).success
    assert svc.enable(package_id=package).success
    actor = ActorService().create_actor(
        campaign_id=campaign_id, user_id=gm_id, system_id=package,
        actor_type="character", name="Aria",
    )
    assert actor.success
    return gm_id, campaign_id, actor.actor_id


def test_bundle_includes_layout_and_derived_data(db):
    gm_id, _, actor_id = _setup("bundle")
    SheetDataService().patch_data(
        actor_id=actor_id, user_id=gm_id,
        patch={"hp.value": 20, "hp.max": 30, "ac": 15, "abilities.dex.score": 14},
    )

    bundle = ActorSheetService().build_bundle(actor_id=actor_id, user_id=gm_id)
    assert bundle is not None
    assert bundle.layout is not None
    assert bundle.layout["kind"] == "actorSheet"
    assert bundle.can_edit is True
                                                            
    assert bundle.data["abilities"]["dex"]["mod"] == 2
    assert bundle.data["init"] == 2


def test_bundle_to_dict_shape(db):
    gm_id, _, actor_id = _setup("bundle-dict")
    payload = ActorSheetService().to_dict(
        ActorSheetService().build_bundle(actor_id=actor_id, user_id=gm_id)
    )
    assert payload["actor"]["name"] == "Aria"
    assert set(payload.keys()) == {
        "actor", "version", "can_edit", "layout", "data",
        "portrait_url", "token_url", "summary",
    }


def test_player_without_access_gets_no_bundle(db):
    gm_id, campaign_id, actor_id = _setup("bundle-perm")
    player_id = seed_user(name="Player", email="player-bundle-perm@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    assert ActorSheetService().build_bundle(actor_id=actor_id, user_id=player_id) is None
