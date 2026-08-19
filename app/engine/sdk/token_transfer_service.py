"""Token transfer: moving tokens between scenes without losing identity.

A transfer preserves the token's identity and ownership, recalculates zone
membership at both ends, and is atomic across a batch so a party cannot be
split by a partial failure. Moving a token is deliberately not the same as
moving anyone's view; navigation stays a separate, explicitly addressed act.
"""

from __future__ import annotations

import math

from app.engine.scenes.scene_service import SceneService
from app.engine.scenes.scene_zone_service import SceneZoneService
from app.engine.sdk.scene_navigation_service import SceneNavigationService
from app.engine.tokens.token_service import TokenService
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.scene_zone_repository import SceneZoneRepository
from app.persistence.repositories.token_repository import TokenRepository

from app.engine.sdk.semantic_authority import (
    SemanticResult,
    is_gm,
)

class TokenTransferService:
    MAX_BATCH=100
    def __init__(self):self.tokens=TokenRepository();self.scenes=SceneRepository()
    def transfer(self,*,campaign_id,user_id,values):return self.transfer_many(campaign_id=campaign_id,user_id=user_id,values={"transfers":[values],"navigateAudience":values.get("navigateAudience")})
    def transfer_many(self,*,campaign_id,user_id,values):
        specs=values.get("transfers")
        try:
            if not isinstance(values,dict) or set(values)-{"transfers","navigateAudience"} or not isinstance(specs,list) or not 1<=len(specs)<=self.MAX_BATCH:raise ValueError
            prepared=[];originals=[]
            for spec in specs:
                if not isinstance(spec,dict) or set(spec)-{"tokenId","sceneId","x","y","elevation","expectedVersion","navigateAudience"}:raise ValueError
                token=self.tokens.get_by_id(str(spec.get("tokenId") or ""));scene=self.scenes.get_by_id(str(spec.get("sceneId") or ""))
                if not token or not scene or scene["campaign_id"]!=campaign_id:return SemanticResult(False,error_key="sdk.tokens.transfer.not_found")
                source=self.scenes.get_by_id(token["scene_id"])
                if not source or source["campaign_id"]!=campaign_id:return SemanticResult(False,error_key="sdk.tokens.transfer.not_found")
                if source["id"]==scene["id"]:raise ValueError
                if not TokenService()._can_control_token(token=token,user_id=user_id,campaign_id=campaign_id):return SemanticResult(False,error_key="sdk.tokens.transfer.not_found")
                if not is_gm(campaign_id,user_id) and not SceneService().assert_user_can_view_scene(scene=scene,user_id=user_id):return SemanticResult(False,error_key="sdk.tokens.transfer.not_found")
                x=spec.get("x");y=spec.get("y");elevation=spec.get("elevation",token["elevation"])
                if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(float(v)) or abs(float(v))>1_000_000 for v in (x,y,elevation)):raise ValueError
                prepared.append({"token_id":token["id"],"scene_id":scene["id"],"grid_x":int(x),"grid_y":int(y),"elevation":float(elevation),"expected_version":spec.get("expectedVersion")})
                originals.append(token)
            moved=self.tokens.transfer_many(prepared)
            if moved is None:return SemanticResult(False,error_key="sdk.tokens.transfer.stale_version")
            navigation=None
            if isinstance(values.get("navigateAudience"),dict):
                navigation=SceneNavigationService().go(campaign_id=campaign_id,user_id=user_id,values={"sceneId":prepared[0]["scene_id"],"recipients":values["navigateAudience"],"reason":"token-transfer"})
            zone_events=[];zones=SceneZoneRepository();zone_service=SceneZoneService();members=CampaignRepository().list_members(campaign_id=campaign_id)
            for before,after in zip(originals,moved):
                source_scene=self.scenes.get_by_id(before["scene_id"]);destination_scene=self.scenes.get_by_id(after["scene_id"])
                source_size=float(source_scene.get("grid_size") or source_scene.get("tile_size") or 70);destination_size=float(destination_scene.get("grid_size") or destination_scene.get("tile_size") or 70)
                before_point=zone_service._token_point(before,source_size);after_point=zone_service._token_point(after,destination_size)
                for event_name,scene_id,rows,point in (("zone.left",before["scene_id"],zones.list_for_scene(before["scene_id"]),before_point),("zone.entered",after["scene_id"],zones.list_for_scene(after["scene_id"]),after_point)):
                    for zone in rows:
                        if not zone["enabled"] or not zone_service.contains(zone,*point):continue
                        audience=[m["user_id"] for m in members if zone_service._visible(zone,m["user_id"]) and (is_gm(campaign_id,m["user_id"]) or TokenService()._can_control_token(token=after,user_id=m["user_id"],campaign_id=campaign_id))]
                        if audience:zone_events.append({"event":event_name,"sceneId":scene_id,"zoneId":zone["id"],"tokenId":after["id"],"audienceIds":audience})
            deliveries=[]
            for token in moved:
                visible=[]
                for member in members:
                    snapshot=TokenService().get_snapshot(campaign_id=campaign_id,scene_id=token["scene_id"],user_id=member["user_id"])
                    if any(str(item.get("id") or item.get("token_id"))==token["id"] for item in (snapshot.tokens or [])):visible.append(member["user_id"])
                if visible:deliveries.append({"token":self._public(token),"audienceIds":visible})
            return SemanticResult(True,{"tokens":[self._public(t) for t in moved],"atomic":True,"navigation":navigation.value if navigation and navigation.success else None,"_zoneEvents":zone_events,"_deliveries":deliveries})
        except (TypeError,ValueError):return SemanticResult(False,error_key="sdk.tokens.transfer.invalid")
    @staticmethod
    def _public(t):return {"id":t["id"],"sceneId":t["scene_id"],"actorId":t["actor_id"],"x":t["grid_x"],"y":t["grid_y"],"elevation":t["elevation"],"version":t["version"]}
