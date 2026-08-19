"""First-class, server-authoritative semantic scene zones."""
from __future__ import annotations
import json, math
from dataclasses import dataclass
from typing import Any
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.scene_zone_repository import SceneZoneRepository
from app.engine.tokens.token_service import TokenService
from app.realtime.events import TransportEvent

@dataclass(frozen=True)
class ZoneResult:
    success: bool
    value: Any = None
    error_key: str | None = None

class SceneZoneService:
    MAX_VERTICES=256; MAX_TAGS=32; MAX_CAUSAL_DEPTH=16
    def __init__(self): self.zones=SceneZoneRepository()
    @staticmethod
    def _role(campaign_id,user_id): return CampaignRepository().get_member_role(campaign_id=campaign_id,user_id=user_id)
    def _scene(self,campaign_id,scene_id):
        row=SceneRepository().get_by_id(scene_id); return row if row and row.get("campaign_id")==campaign_id else None
    def _can_write(self,campaign_id,user_id): return self._role(campaign_id,user_id) in {"gm","assistant_gm"}
    def _visible(self,row,user_id):
        role=self._role(SceneRepository().get_by_id(row["scene_id"])["campaign_id"],user_id)
        audience=row["audience"]; kind=audience.get("kind")
        return role in {"gm","assistant_gm"} or kind=="campaign" or kind=="users" and user_id in audience.get("ids",[])
    @classmethod
    def _normalize_geometry(cls,g):
        if not isinstance(g,dict) or g.get("shape") not in {"circle","rect","polygon"}: raise ValueError
        shape=g["shape"]
        def number(v):
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>1_000_000: raise ValueError
            return float(v)
        if shape=="circle":
            x,y,r=number(g.get("x")),number(g.get("y")),number(g.get("radius"))
            if r<=0: raise ValueError
            return {"shape":shape,"x":x,"y":y,"radius":r},(x-r,y-r,x+r,y+r)
        if shape=="rect":
            x,y,w,h=number(g.get("x")),number(g.get("y")),number(g.get("width")),number(g.get("height"))
            if w<=0 or h<=0: raise ValueError
            return {"shape":shape,"x":x,"y":y,"width":w,"height":h},(x,y,x+w,y+h)
        pts=g.get("points")
        if not isinstance(pts,list) or not 3<=len(pts)<=cls.MAX_VERTICES: raise ValueError
        points=[{"x":number(p.get("x")),"y":number(p.get("y"))} for p in pts if isinstance(p,dict)]
        if len(points)!=len(pts): raise ValueError
        # Reject zero-area polygons; self-intersection is deliberately rejected.
        area=sum(points[i]["x"]*points[(i+1)%len(points)]["y"]-points[(i+1)%len(points)]["x"]*points[i]["y"] for i in range(len(points)))
        if abs(area)<1e-9 or cls._self_intersects(points): raise ValueError
        xs=[p["x"] for p in points]; ys=[p["y"] for p in points]
        return {"shape":shape,"points":points},(min(xs),min(ys),max(xs),max(ys))
    @staticmethod
    def _self_intersects(p):
        def orient(a,b,c): return (b["x"]-a["x"])*(c["y"]-a["y"])-(b["y"]-a["y"])*(c["x"]-a["x"])
        n=len(p)
        for i in range(n):
            for j in range(i+1,n):
                if i==j or (i+1)%n==j or i==(j+1)%n: continue
                a,b,c,d=p[i],p[(i+1)%n],p[j],p[(j+1)%n]
                if orient(a,b,c)*orient(a,b,d)<0 and orient(c,d,a)*orient(c,d,b)<0: return True
        return False
    @staticmethod
    def _audience(value,members):
        if not isinstance(value,dict) or value.get("kind") not in {"campaign","gm","users"}: raise ValueError
        ids=list(dict.fromkeys(map(str,value.get("ids",[])))) if value.get("kind")=="users" else []
        if len(ids)>64 or any(i not in members for i in ids): raise ValueError
        return {"kind":value["kind"],**({"ids":ids} if ids else {})}
    def list(self,*,campaign_id,scene_id,user_id):
        if not self._scene(campaign_id,scene_id): return ZoneResult(False,error_key="sdk.scene.zones.not_found")
        return ZoneResult(True,[self._public(z) for z in self.zones.list_for_scene(scene_id) if self._visible(z,user_id)])
    def get(self,*,campaign_id,zone_id,user_id):
        z=self.zones.get(zone_id)
        if not z or not self._scene(campaign_id,z["scene_id"]) or not self._visible(z,user_id): return ZoneResult(False,error_key="sdk.scene.zones.not_found")
        return ZoneResult(True,self._public(z))
    def create(self,*,campaign_id,scene_id,user_id,package_id,values):
        if not self._scene(campaign_id,scene_id): return ZoneResult(False,error_key="sdk.scene.zones.not_found")
        if not self._can_write(campaign_id,user_id): return ZoneResult(False,error_key="sdk.scene.zones.permission_denied")
        try:
            geometry,bounds=self._normalize_geometry(values.get("geometry")); members={m["user_id"] for m in CampaignRepository().list_members(campaign_id=campaign_id)}
            audience=self._audience(values.get("audience",{"kind":"campaign"}),members); vertical=values.get("vertical") or {}
            bottom=vertical.get("bottom"); top=vertical.get("top")
            for v in (bottom,top):
                if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)): raise ValueError
            if bottom is not None and top is not None and bottom>top: raise ValueError
            tags=list(dict.fromkeys(str(t)[:64] for t in values.get("tags",[])))
            if len(tags)>self.MAX_TAGS: raise ValueError
        except (TypeError,ValueError): return ZoneResult(False,error_key="sdk.scene.zones.invalid")
        z=self.zones.create(scene_id=scene_id,zone_type=str(values.get("type") or "standard")[:64],geometry_json=json.dumps(geometry),vertical_bottom=bottom,vertical_top=top,audience_json=json.dumps(audience),enabled=1 if values.get("enabled",True) else 0,tags_json=json.dumps(tags),package_id=package_id,provider_id=str(values.get("providerId"))[:128] if values.get("providerId") else None,min_x=bounds[0],min_y=bounds[1],max_x=bounds[2],max_y=bounds[3])
        return ZoneResult(True,self._public(z))
    def update(self,*,campaign_id,zone_id,user_id,patch,expected_version):
        old=self.zones.get(zone_id)
        if not old or not self._scene(campaign_id,old["scene_id"]): return ZoneResult(False,error_key="sdk.scene.zones.not_found")
        if not self._can_write(campaign_id,user_id): return ZoneResult(False,error_key="sdk.scene.zones.permission_denied")
        values={}
        try:
            if "geometry" in patch:
                g,b=self._normalize_geometry(patch["geometry"]); values.update(geometry_json=json.dumps(g),min_x=b[0],min_y=b[1],max_x=b[2],max_y=b[3])
            if "enabled" in patch: values["enabled"]=1 if patch["enabled"] else 0
            if "tags" in patch: values["tags_json"]=json.dumps(list(dict.fromkeys(map(str,patch["tags"]))))
        except (TypeError,ValueError): return ZoneResult(False,error_key="sdk.scene.zones.invalid")
        z=self.zones.update(zone_id,values,expected_version)
        return ZoneResult(bool(z),self._public(z) if z else None,None if z else "sdk.scene.zones.stale_version")
    def delete(self,*,campaign_id,zone_id,user_id,expected_version=None):
        z=self.zones.get(zone_id)
        if not z or not self._scene(campaign_id,z["scene_id"]): return ZoneResult(False,error_key="sdk.scene.zones.not_found")
        if not self._can_write(campaign_id,user_id): return ZoneResult(False,error_key="sdk.scene.zones.permission_denied")
        ok=self.zones.delete(zone_id,expected_version); return ZoneResult(ok,{"id":zone_id,"deleted":True} if ok else None,None if ok else "sdk.scene.zones.stale_version")
    def members(self,*,campaign_id,zone_id,user_id):
        found=self.get(campaign_id=campaign_id,zone_id=zone_id,user_id=user_id)
        if not found.success:return found
        z=self.zones.get(zone_id); visible=TokenService().get_snapshot(campaign_id=campaign_id,scene_id=z["scene_id"],user_id=user_id)
        scene=self._scene(campaign_id,z["scene_id"]); size=float(scene.get("grid_size") or scene.get("tile_size") or 70)
        ids=[str(t.get("id") or t.get("token_id")) for t in (visible.tokens or []) if self.contains(z,*self._token_point(t,size))]
        return ZoneResult(True,ids)
    @staticmethod
    def _token_point(token,size=1): return ((float(token["grid_x"])+float(token.get("width_cells") or 1)/2)*size,(float(token["grid_y"])+float(token.get("height_cells") or 1)/2)*size,float(token.get("elevation") or 0))
    @staticmethod
    def contains(z,x,y,elevation):
        if z["vertical_bottom"] is not None and elevation<z["vertical_bottom"] or z["vertical_top"] is not None and elevation>z["vertical_top"]: return False
        g=z["geometry"]
        if g["shape"]=="circle": return (x-g["x"])**2+(y-g["y"])**2<=g["radius"]**2
        if g["shape"]=="rect": return g["x"]<=x<=g["x"]+g["width"] and g["y"]<=y<=g["y"]+g["height"]
        inside=False; pts=g["points"]; j=len(pts)-1
        for i,p in enumerate(pts):
            q=pts[j]
            if (p["y"]>y)!=(q["y"]>y) and x < (q["x"]-p["x"])*(y-p["y"])/(q["y"]-p["y"])+p["x"]: inside=not inside
            j=i
        return inside
    @classmethod
    def crosses(cls,z,a,b,elevation):
        if cls.contains(z,a[0],a[1],elevation) or cls.contains(z,b[0],b[1],elevation): return False
        g=z["geometry"]
        if g["shape"]=="circle":
            dx=b[0]-a[0]; dy=b[1]-a[1]; length=dx*dx+dy*dy
            if length==0:return False
            t=max(0,min(1,((g["x"]-a[0])*dx+(g["y"]-a[1])*dy)/length)); x=a[0]+t*dx; y=a[1]+t*dy
            return (x-g["x"])**2+(y-g["y"])**2<=g["radius"]**2
        pts=([{"x":g["x"],"y":g["y"]},{"x":g["x"]+g["width"],"y":g["y"]},{"x":g["x"]+g["width"],"y":g["y"]+g["height"]},{"x":g["x"],"y":g["y"]+g["height"]}] if g["shape"]=="rect" else g["points"])
        def side(p,q,r): return (q["x"]-p["x"])*(r[1]-p["y"])-(q["y"]-p["y"])*(r[0]-p["x"])
        return any(side(pts[i],pts[(i+1)%len(pts)],a)*side(pts[i],pts[(i+1)%len(pts)],b)<=0 and side({"x":a[0],"y":a[1]},{"x":b[0],"y":b[1]},(pts[i]["x"],pts[i]["y"]))*side({"x":a[0],"y":a[1]},{"x":b[0],"y":b[1]},(pts[(i+1)%len(pts)]["x"],pts[(i+1)%len(pts)]["y"]))<=0 for i in range(len(pts)))
    async def process_move(self,*,campaign_id,scene_id,token_before,token_after,origin,target,transport,teleport=False,origin_execution_id=None,origin_job_id=None,causal_depth=0):
        if causal_depth>self.MAX_CAUSAL_DEPTH:return
        elevation=float(token_after.get("elevation") or 0); bounds=(min(origin[0],target[0]),min(origin[1],target[1]),max(origin[0],target[0]),max(origin[1],target[1]))
        for zone in self.zones.candidates(scene_id,*bounds):
            was=self.contains(zone,origin[0],origin[1],float(token_before.get("elevation") or 0)); now=self.contains(zone,target[0],target[1],elevation)
            event=TransportEvent.ZONE_ENTERED if not was and now else TransportEvent.ZONE_LEFT if was and not now else TransportEvent.ZONE_CROSSED if not teleport and not was and not now and self.crosses(zone,origin,target,elevation) else None
            if event is None:continue
            recipients=[]
            for member in CampaignRepository().list_members(campaign_id=campaign_id):
                uid=member["user_id"]
                if not self._visible(zone,uid):continue
                snapshot=TokenService().get_snapshot(campaign_id=campaign_id,scene_id=scene_id,user_id=uid)
                if any(str(t.get("id") or t.get("token_id"))==str(token_after["id"]) for t in (snapshot.tokens or [])):recipients.append(uid)
            if recipients:
                await transport.to_players(player_ids=recipients,event=event,payload={"room_id":campaign_id,"scene_id":scene_id,"zone_id":zone["id"],"token_id":token_after["id"],"schema_version":1,"origin_execution_id":origin_execution_id,"origin_job_id":origin_job_id,"causal_depth":causal_depth})
    @staticmethod
    def _public(z):
        return {"id":z["id"],"sceneId":z["scene_id"],"type":z["zone_type"],"geometry":z["geometry"],"vertical":{"bottom":z["vertical_bottom"],"top":z["vertical_top"]},"audience":z["audience"],"enabled":bool(z["enabled"]),"tags":z["tags"],"packageProvenance":{"packageId":z["package_id"],"providerId":z["provider_id"]},"version":z["version"]}
