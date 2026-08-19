from app.engine.sdk.token_transfer_service import TokenTransferService
from app.persistence.repositories.token_repository import TokenRepository
from app.engine.scenes.scene_zone_service import SceneZoneService
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_user


def test_single_transfer_preserves_identity_ownership_and_location(db):
    gm=seed_user();campaign=seed_campaign(gm);a=seed_scene(campaign,name="A");b=seed_scene(campaign,name="B")
    token=TokenRepository().create(scene_id=a["id"],actor_id=None,grid_x=1,grid_y=2,controlled_by_role="gm",controlled_by_user_ids=[gm])
    result=TokenTransferService().transfer(campaign_id=campaign,user_id=gm,values={"tokenId":token["id"],"sceneId":b["id"],"x":8,"y":9,"elevation":3,"expectedVersion":token["version"]})
    assert result.success and result.value["tokens"][0]["id"]==token["id"]
    stored=TokenRepository().get_by_id(token["id"])
    assert stored["scene_id"]==b["id"] and (stored["grid_x"],stored["grid_y"],stored["elevation"])==(8,9,3)
    assert stored["controlled_by_user_ids"]==[gm]


def test_party_transfer_is_atomic_on_stale_member(db):
    gm=seed_user();campaign=seed_campaign(gm);a=seed_scene(campaign,name="A");b=seed_scene(campaign,name="B");repo=TokenRepository()
    one=repo.create(scene_id=a["id"],actor_id=None,grid_x=0,grid_y=0);two=repo.create(scene_id=a["id"],actor_id=None,grid_x=1,grid_y=0)
    result=TokenTransferService().transfer_many(campaign_id=campaign,user_id=gm,values={"transfers":[{"tokenId":one["id"],"sceneId":b["id"],"x":3,"y":3,"expectedVersion":one["version"]},{"tokenId":two["id"],"sceneId":b["id"],"x":4,"y":3,"expectedVersion":999}]})
    assert not result.success and result.error_key.endswith("stale_version")
    assert repo.get_by_id(one["id"])["scene_id"]==a["id"] and repo.get_by_id(two["id"])["scene_id"]==a["id"]


def test_transfer_emits_endpoint_zone_lifecycle_without_crossed(db):
    gm=seed_user();campaign=seed_campaign(gm);a=seed_scene(campaign,name="A");b=seed_scene(campaign,name="B");zones=SceneZoneService()
    left=zones.create(campaign_id=campaign,scene_id=a["id"],user_id=gm,package_id="portal",values={"geometry":{"shape":"circle","x":35,"y":35,"radius":30},"audience":{"kind":"campaign"}}).value
    entered=zones.create(campaign_id=campaign,scene_id=b["id"],user_id=gm,package_id="portal",values={"geometry":{"shape":"circle","x":105,"y":105,"radius":30},"audience":{"kind":"campaign"}}).value
    token=TokenRepository().create(scene_id=a["id"],actor_id=None,grid_x=0,grid_y=0)
    result=TokenTransferService().transfer(campaign_id=campaign,user_id=gm,values={"tokenId":token["id"],"sceneId":b["id"],"x":1,"y":1})
    events=result.value["_zoneEvents"]
    assert {(e["event"],e["zoneId"]) for e in events}=={("zone.left",left["id"]),("zone.entered",entered["id"])}
    assert all(e["event"]!="zone.crossed" for e in events)


def test_player_may_transfer_only_controlled_token_and_foreign_destination_does_not_disclose(db):
    gm=seed_user();player=seed_user();campaign=seed_campaign(gm);seed_member(campaign,player,"player");a=seed_scene(campaign);b=seed_scene(campaign);other_gm=seed_user();other_campaign=seed_campaign(other_gm);secret=seed_scene(other_campaign)
    from app.persistence.repositories.actor_repository import ActorRepository
    actor=ActorRepository().create(campaign_id=campaign,system_id="system",actor_type="hero",name="Hero",created_by_user_id=gm,owner_user_ids=[player])
    controlled=TokenRepository().create(scene_id=a["id"],actor_id=actor,grid_x=0,grid_y=0,controlled_by_user_ids=[player],controlled_by_role="owner")
    forbidden=TokenRepository().create(scene_id=a["id"],actor_id=None,grid_x=1,grid_y=0,controlled_by_role="gm")
    service=TokenTransferService()
    assert service.transfer(campaign_id=campaign,user_id=player,values={"tokenId":controlled["id"],"sceneId":b["id"],"x":2,"y":2}).success
    denied=service.transfer(campaign_id=campaign,user_id=player,values={"tokenId":forbidden["id"],"sceneId":b["id"],"x":2,"y":2})
    hidden=service.transfer(campaign_id=campaign,user_id=gm,values={"tokenId":forbidden["id"],"sceneId":secret["id"],"x":2,"y":2})
    assert denied.error_key==hidden.error_key=="sdk.tokens.transfer.not_found"


def test_transfer_rejects_invalid_coordinates_without_implicit_navigation_or_duplication(db):
    import math
    gm=seed_user();campaign=seed_campaign(gm);a=seed_scene(campaign);b=seed_scene(campaign);repo=TokenRepository()
    token=repo.create(scene_id=a["id"],actor_id=None,grid_x=0,grid_y=0);service=TokenTransferService()
    assert not service.transfer(campaign_id=campaign,user_id=gm,values={"tokenId":token["id"],"sceneId":b["id"],"x":math.nan,"y":0}).success
    moved=service.transfer(campaign_id=campaign,user_id=gm,values={"tokenId":token["id"],"sceneId":b["id"],"x":2,"y":3})
    assert moved.success and moved.value["navigation"] is None
    assert repo.get_by_id(token["id"])["scene_id"]==b["id"]
    assert len(repo.list_by_scene(a["id"]))==0 and len(repo.list_by_scene(b["id"]))==1
