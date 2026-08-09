import asyncio

from app.engine.tokens.token_service import TokenService
from app.engine.tokens.token_view_service import TokenViewService
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.token_repository import TokenRepository
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_system, seed_user

def test_snapshot_reports_the_owners_who_can_see_through_a_token(db):
    """A visao do jogador depende de controlled_by_user_ids. A coluna homonima na
    tabela nunca e escrita, entao a posse tem de vir de actor_owners — sem isso
    nenhum jogador tem token e ninguem enxerga nada."""
    gm=seed_user(name="GM"); player=seed_user(name="Player")
    campaign=seed_campaign(gm); seed_member(campaign,player,"player")
    system=seed_system(campaign,gm); scene=seed_scene(campaign)

    actors=ActorRepository()
    actor_id=actors.create(campaign_id=campaign,system_id=system,actor_type="character",
                           name="Rogue",created_by_user_id=gm,owner_user_ids=[player])
    token=TokenRepository().create(scene_id=scene["id"],actor_id=actor_id,grid_x=3,grid_y=4)
    assert token["controlled_by_user_ids"] == [], "a coluna continua vazia no banco"

    snapshot=TokenService().get_snapshot(campaign_id=campaign,scene_id=scene["id"],user_id=player)
    assert snapshot.success
    view=next(v for v in snapshot.tokens if v["token_id"] == token["id"])
    assert view["controlled_by_user_ids"] == [player], "a posse do ator chega ao TokenView"
    assert view["vision_enabled"] is True

def test_tokens_without_an_actor_report_no_owners(db):
    gm=seed_user(name="GM"); campaign=seed_campaign(gm); scene=seed_scene(campaign)
    token=TokenRepository().create(scene_id=scene["id"],actor_id=None,grid_x=1,grid_y=1)
    snapshot=TokenService().get_snapshot(campaign_id=campaign,scene_id=scene["id"],user_id=gm)
    view=next(v for v in snapshot.tokens if v["token_id"] == token["id"])
    assert view["controlled_by_user_ids"] == []

def _token(scene_id: str) -> dict:
    repo = TokenRepository()
    return repo.create(scene_id=scene_id, actor_id=None, grid_x=1, grid_y=1)

def test_new_tokens_see_as_far_as_the_walls_allow(db):
    gm=seed_user(name="GM"); campaign=seed_campaign(gm); scene=seed_scene(campaign)
    token=_token(scene["id"])
    # O default reproduz a linha de visao ilimitada que os tokens ja tinham.
    assert bool(token["vision_enabled"]) is True
    assert float(token["vision_range"]) == 0.0

    view=TokenViewService().build_view(token=token)
    assert view["vision_enabled"] is True and view["vision_range"] == 0.0

def test_gm_sets_vision_and_the_view_reflects_it(db):
    gm=seed_user(name="GM"); campaign=seed_campaign(gm); scene=seed_scene(campaign)
    token=_token(scene["id"])
    service=TokenService()

    result=asyncio.run(service.set_vision(
        campaign_id=campaign, scene_id=scene["id"], token_id=token["id"],
        vision_enabled=True, vision_range=6.5, user_id=gm,
    ))
    assert result.success
    assert float(result.token["vision_range"]) == 6.5
    assert result.token["version"] == token["version"] + 1, "mexer na visao versiona o token"

    blinded=asyncio.run(service.set_vision(
        campaign_id=campaign, scene_id=scene["id"], token_id=token["id"],
        vision_enabled=False, vision_range=6.5, user_id=gm,
    ))
    assert blinded.success and not bool(blinded.token["vision_enabled"])
    assert TokenViewService().build_view(token=blinded.token)["vision_enabled"] is False

def test_negative_range_is_floored_and_players_cannot_set_vision(db):
    gm=seed_user(name="GM"); player=seed_user(name="Player")
    campaign=seed_campaign(gm); seed_member(campaign,player,"player"); scene=seed_scene(campaign)
    token=_token(scene["id"]); service=TokenService()

    floored=asyncio.run(service.set_vision(
        campaign_id=campaign, scene_id=scene["id"], token_id=token["id"],
        vision_enabled=True, vision_range=-10, user_id=gm,
    ))
    assert float(floored.token["vision_range"]) == 0.0

    denied=asyncio.run(service.set_vision(
        campaign_id=campaign, scene_id=scene["id"], token_id=token["id"],
        vision_enabled=True, vision_range=9, user_id=player,
    ))
    assert denied.error_key == "tokens.errors.permission_denied"
    assert float(TokenRepository().get_by_id(token["id"])["vision_range"]) == 0.0

def test_stale_version_does_not_overwrite_vision(db):
    gm=seed_user(name="GM"); campaign=seed_campaign(gm); scene=seed_scene(campaign)
    token=_token(scene["id"]); service=TokenService()
    stale=token["version"]

    first=asyncio.run(service.set_vision(
        campaign_id=campaign, scene_id=scene["id"], token_id=token["id"],
        vision_enabled=True, vision_range=4, user_id=gm, expected_version=stale,
    ))
    assert first.success

    conflict=asyncio.run(service.set_vision(
        campaign_id=campaign, scene_id=scene["id"], token_id=token["id"],
        vision_enabled=True, vision_range=99, user_id=gm, expected_version=stale,
    ))
    assert conflict.error_key == "tokens.errors.version_conflict"
    assert float(TokenRepository().get_by_id(token["id"])["vision_range"]) == 4.0
