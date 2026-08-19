import math
from app.engine.scenes.scene_object_service import SceneObjectService
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_user

def world():
    gm=seed_user(); player=seed_user(); hidden=seed_user(); campaign=seed_campaign(gm);seed_member(campaign,player,"player");seed_member(campaign,hidden,"player");scene=seed_scene(campaign)
    return gm,player,hidden,campaign,scene["id"]

def definition():
    return {"typeId":"pins.scene-pin","schemaVersion":1,"displayName":"Scene pin","geometryKinds":["point","rect","circle","polygon","polyline"],"dataSchema":{"type":"object"},"visualDefinition":[{"kind":"icon"},{"kind":"label"}],"interactionDefinitions":[{"id":"inspect","label":"Inspect","actionReference":{"provider":"pins","id":"inspect","version":1}}],"searchableFields":["label"]}

def test_type_instance_crud_cas_audience_search_and_orphan(db):
    gm,player,_,campaign,scene=world();service=SceneObjectService()
    assert service.register_type(campaign_id=campaign,user_id=gm,package_id="pins",definition=definition()).success
    made=service.create(campaign_id=campaign,scene_id=scene,user_id=gm,package_id="pins",values={"typeId":"pins.scene-pin","geometry":{"kind":"point","x":40,"y":50},"presentation":{"icon":"pin","label":"Crypt"},"data":{"label":"Crypt"},"audience":{"kind":"gm"}})
    assert made.success and made.value["providerPackageId"]=="pins"
    assert not service.get(campaign_id=campaign,object_id=made.value["id"],user_id=player).success
    assert service.list(campaign_id=campaign,scene_id=scene,user_id=gm,q="crypt").value[0]["id"]==made.value["id"]
    changed=service.update(campaign_id=campaign,object_id=made.value["id"],user_id=gm,patch={"geometry":{"kind":"circle","x":40,"y":50,"radius":10}},expected_version=1)
    assert changed.success and changed.value["version"]==2
    assert service.update(campaign_id=campaign,object_id=made.value["id"],user_id=gm,patch={"enabled":False},expected_version=1).error_key.endswith("stale_version")
    service.repo.deactivate_type(campaign,"pins","pins.scene-pin")
    orphan=service.get(campaign_id=campaign,object_id=made.value["id"],user_id=gm).value
    assert not orphan["providerAvailable"] and orphan["data"]=={}
    assert service.register_type(campaign_id=campaign,user_id=gm,package_id="pins",definition=definition()).success
    assert service.get(campaign_id=campaign,object_id=made.value["id"],user_id=gm).value["providerAvailable"]

def test_geometry_hit_test_interaction_and_torture(db):
    gm,player,_,campaign,scene=world();service=SceneObjectService();service.register_type(campaign_id=campaign,user_id=gm,package_id="pins",definition=definition())
    made=service.create(campaign_id=campaign,scene_id=scene,user_id=gm,package_id="pins",values={"typeId":"pins.scene-pin","geometry":{"kind":"polygon","points":[{"x":0,"y":0},{"x":100,"y":0},{"x":50,"y":100}]},"data":{},"audience":{"kind":"campaign"}}).value
    assert service.hit_test(campaign_id=campaign,scene_id=scene,user_id=player,x=50,y=25).value[0]["id"]==made["id"]
    intent=service.interact(campaign_id=campaign,object_id=made["id"],user_id=player,interaction_id="inspect",expected_version=1)
    assert intent.success and intent.value["principal"]["userId"]==player and intent.value["actionReference"]["id"]=="inspect"
    assert service.interact(campaign_id=campaign,object_id=made["id"],user_id=player,interaction_id="forged",expected_version=1).error_key.endswith("unknown_interaction")
    for bad in ({"kind":"point","x":math.nan,"y":0},{"kind":"polygon","points":[]},{"kind":"mesh"}):
        try:service.geometry(bad)
        except ValueError:pass
        else:raise AssertionError("invalid geometry accepted")

def test_provider_spoof_and_player_mutation_rejected(db):
    gm,player,_,campaign,scene=world();service=SceneObjectService();service.register_type(campaign_id=campaign,user_id=gm,package_id="pins",definition=definition())
    assert service.create(campaign_id=campaign,scene_id=scene,user_id=gm,package_id="evil",values={"typeId":"pins.scene-pin","geometry":{"kind":"point","x":0,"y":0}}).error_key.endswith("provider_spoof")
    assert service.create(campaign_id=campaign,scene_id=scene,user_id=player,package_id="pins",values={"typeId":"pins.scene-pin","geometry":{"kind":"point","x":0,"y":0}}).error_key.endswith("not_authorized")
