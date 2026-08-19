import math
import pytest
from app.engine.scenes.scene_zone_service import SceneZoneService
from app.engine.tokens.token_service import TokenService
from app.persistence.repositories.token_repository import TokenRepository
from app.realtime.events import TransportEvent
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_user

def _world():
    gm=seed_user(name="GM"); player=seed_user(name="Player"); campaign=seed_campaign(gm); seed_member(campaign,player,"player"); scene=seed_scene(campaign)
    return gm,player,campaign,scene["id"]

def test_zone_crud_cas_audience_and_provenance(db):
    gm,player,campaign,scene=_world(); service=SceneZoneService()
    made=service.create(campaign_id=campaign,scene_id=scene,user_id=gm,package_id="weather-addon",values={"type":"altar","geometry":{"shape":"circle","x":100,"y":100,"radius":25},"vertical":{"bottom":5,"top":20},"audience":{"kind":"gm"},"tags":["holy"]})
    assert made.success and made.value["packageProvenance"]["packageId"]=="weather-addon"
    assert not service.get(campaign_id=campaign,zone_id=made.value["id"],user_id=player).success
    changed=service.update(campaign_id=campaign,zone_id=made.value["id"],user_id=gm,patch={"enabled":False},expected_version=1)
    assert changed.success and changed.value["version"]==2
    assert service.update(campaign_id=campaign,zone_id=made.value["id"],user_id=gm,patch={"enabled":True},expected_version=1).error_key.endswith("stale_version")
    assert service.delete(campaign_id=campaign,zone_id=made.value["id"],user_id=gm,expected_version=2).success

def test_geometry_membership_crossing_vertical_and_validation(db):
    circle={"geometry":{"shape":"circle","x":0,"y":0,"radius":5},"vertical_bottom":0,"vertical_top":10}
    rect={"geometry":{"shape":"rect","x":-2,"y":-2,"width":4,"height":4},"vertical_bottom":None,"vertical_top":None}
    polygon={"geometry":{"shape":"polygon","points":[{"x":0,"y":0},{"x":10,"y":0},{"x":5,"y":10}]},"vertical_bottom":None,"vertical_top":None}
    assert SceneZoneService.contains(circle,0,0,5) and not SceneZoneService.contains(circle,0,0,11)
    assert SceneZoneService.crosses(circle,(-10,0),(10,0),5)
    assert SceneZoneService.contains(rect,0,0,0) and SceneZoneService.contains(polygon,5,5,0)
    for bad in ({"shape":"circle","x":math.nan,"y":0,"radius":1},{"shape":"polygon","points":[{"x":0,"y":0},{"x":1,"y":1}]}):
        try: SceneZoneService._normalize_geometry(bad)
        except ValueError: pass
        else: raise AssertionError("malformed geometry accepted")

def test_enter_leave_cross_and_teleport_semantics(db):
    zone={"geometry":{"shape":"circle","x":0,"y":0,"radius":5},"vertical_bottom":None,"vertical_top":None}
    assert not SceneZoneService.contains(zone,-10,0,0) and SceneZoneService.contains(zone,0,0,0)
    assert SceneZoneService.crosses(zone,(-10,0),(10,0),0)
    # Teleport callers deliberately skip crosses; endpoints still define enter/leave.
    assert not SceneZoneService.contains(zone,10,0,0)

@pytest.mark.asyncio
async def test_authoritative_fast_movement_emits_deduplicated_transitions(db):
    gm,_,campaign,scene=_world(); zones=SceneZoneService()
    made=zones.create(campaign_id=campaign,scene_id=scene,user_id=gm,package_id="trap",values={"geometry":{"shape":"circle","x":105,"y":35,"radius":30},"audience":{"kind":"campaign"}})
    assert made.success
    token=TokenRepository().create(scene_id=scene,actor_id=None,grid_x=0,grid_y=0,controlled_by_role="gm")
    class Transport:
        def __init__(self): self.events=[]
        async def to_players(self,**kw): self.events.append(kw)
        async def to_room(self,**kw): self.events.append(kw)
        async def to_token_audience(self,**kw): self.events.append(kw)
    transport=Transport(); service=TokenService()
    entered=await service.move(campaign_id=campaign,scene_id=scene,token_id=token["id"],grid_x=1,grid_y=0,user_id=gm,transport=transport)
    assert entered.success and any(e["event"]==TransportEvent.ZONE_ENTERED for e in transport.events)
    transport.events.clear(); same=await service.move(campaign_id=campaign,scene_id=scene,token_id=token["id"],grid_x=1,grid_y=0,user_id=gm,transport=transport)
    assert same.success and not any(e["event"] in {TransportEvent.ZONE_ENTERED,TransportEvent.ZONE_LEFT,TransportEvent.ZONE_CROSSED} for e in transport.events)
    transport.events.clear(); left=await service.move(campaign_id=campaign,scene_id=scene,token_id=token["id"],grid_x=2,grid_y=0,user_id=gm,transport=transport)
    assert left.success and any(e["event"]==TransportEvent.ZONE_LEFT for e in transport.events)
    await service.move(campaign_id=campaign,scene_id=scene,token_id=token["id"],grid_x=0,grid_y=0,user_id=gm,transport=transport)
    transport.events.clear(); crossed=await service.move(campaign_id=campaign,scene_id=scene,token_id=token["id"],grid_x=2,grid_y=0,user_id=gm,transport=transport)
    assert crossed.success and any(e["event"]==TransportEvent.ZONE_CROSSED for e in transport.events)
