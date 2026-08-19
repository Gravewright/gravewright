"""Authoritative package-defined objects rendered and hit-tested by the core."""
from __future__ import annotations
import json, math, re
from dataclasses import dataclass
from typing import Any
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.scene_object_repository import SceneObjectRepository

@dataclass(frozen=True)
class ObjectResult:
    success: bool; value: Any=None; error_key: str|None=None

class SceneObjectService:
    MAX_VERTICES=256; MAX_DATA_BYTES=16_384; MAX_PRIMITIVES=8
    def __init__(self):self.repo=SceneObjectRepository()
    def _role(self,c,u):return CampaignRepository().get_member_role(campaign_id=c,user_id=u)
    def _scene(self,c,s):
        row=SceneRepository().get_by_id(s); return row if row and row.get("campaign_id")==c else None
    def _write(self,c,u):return self._role(c,u) in {"gm","assistant_gm"}
    def _visible(self,c,row,u):
        role=self._role(c,u); audience=row["audience"]; return role in {"gm","assistant_gm"} or audience.get("kind")=="campaign" or audience.get("kind")=="users" and u in audience.get("ids",[])
    @staticmethod
    def _num(v):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>1_000_000:raise ValueError
        return float(v)
    @classmethod
    def geometry(cls,g):
        if not isinstance(g,dict) or g.get("kind") not in {"point","rect","circle","polygon","polyline"}:raise ValueError
        k=g["kind"]
        if k=="point":
            x,y=cls._num(g.get("x")),cls._num(g.get("y")); return {"kind":k,"x":x,"y":y},(x-12,y-12,x+12,y+12)
        if k=="rect":
            x,y,w,h=map(cls._num,(g.get("x"),g.get("y"),g.get("width"),g.get("height")))
            if w<=0 or h<=0:raise ValueError
            return {"kind":k,"x":x,"y":y,"width":w,"height":h},(x,y,x+w,y+h)
        if k=="circle":
            x,y,r=map(cls._num,(g.get("x"),g.get("y"),g.get("radius")))
            if r<=0:raise ValueError
            return {"kind":k,"x":x,"y":y,"radius":r},(x-r,y-r,x+r,y+r)
        points=g.get("points")
        if not isinstance(points,list) or not (3 if k=="polygon" else 2)<=len(points)<=cls.MAX_VERTICES:raise ValueError
        pts=[{"x":cls._num(p.get("x")),"y":cls._num(p.get("y"))} for p in points if isinstance(p,dict)]
        if len(pts)!=len(points):raise ValueError
        xs=[p["x"] for p in pts];ys=[p["y"] for p in pts];return {"kind":k,"points":pts},(min(xs),min(ys),max(xs),max(ys))
    @staticmethod
    def _safe_json(value,limit):
        encoded=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":"));
        if len(encoded.encode())>limit:raise ValueError
        return encoded
    def register_type(self,*,campaign_id,user_id,package_id,definition):
        try:
            type_id=str(definition.get("typeId") or ""); version=int(definition.get("schemaVersion")); kinds=definition.get("geometryKinds")
            if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{2,190}",type_id) or not type_id.startswith(package_id+".") or version<1:raise ValueError
            if not isinstance(kinds,list) or not kinds or not set(kinds)<={"point","rect","circle","polygon","polyline"}:raise ValueError
            visuals=definition.get("visualDefinition",[]); interactions=definition.get("interactionDefinitions",[])
            if not isinstance(visuals,list) or len(visuals)>self.MAX_PRIMITIVES or any(not isinstance(v,dict) or v.get("kind") not in {"icon","label","shape","line","badge","asset"} for v in visuals):raise ValueError
            if not isinstance(interactions,list) or len(interactions)>16 or any(not isinstance(i,dict) or not re.fullmatch(r"[a-z][a-z0-9.-]{0,63}",str(i.get("id") or "")) for i in interactions):raise ValueError
            self._safe_json(definition,self.MAX_DATA_BYTES)
        except (TypeError,ValueError):return ObjectResult(False,error_key="sdk.scene.objects.invalid_type")
        old=self.repo.get_type(campaign_id,type_id)
        if old and old["package_id"]!=package_id:return ObjectResult(False,error_key="sdk.scene.objects.duplicate_type")
        return ObjectResult(True,self.repo.register_type(campaign_id=campaign_id,package_id=package_id,type_id=type_id,definition=definition,schema_version=version)["definition"])
    def unregister_type(self,*,campaign_id,package_id,type_id):
        found=self.repo.get_type(campaign_id,type_id)
        if found and found["package_id"]==package_id:self.repo.deactivate_type(campaign_id,package_id,type_id)
        return ObjectResult(True,{"typeId":type_id,"active":False})
    def list(self,*,campaign_id,scene_id,user_id,q=None):
        if not self._scene(campaign_id,scene_id):return ObjectResult(False,error_key="sdk.scene.objects.not_found")
        return ObjectResult(True,[self._public(campaign_id,o) for o in self.repo.list_scene(scene_id,q) if self._visible(campaign_id,o,user_id)])
    def get(self,*,campaign_id,object_id,user_id):
        o=self.repo.get(object_id)
        if not o or not self._scene(campaign_id,o["scene_id"]) or not self._visible(campaign_id,o,user_id):return ObjectResult(False,error_key="sdk.scene.objects.not_found")
        return ObjectResult(True,self._public(campaign_id,o))
    def create(self,*,campaign_id,scene_id,user_id,package_id,values):
        if not self._scene(campaign_id,scene_id):return ObjectResult(False,error_key="sdk.scene.objects.not_found")
        if not self._write(campaign_id,user_id):return ObjectResult(False,error_key="sdk.scene.objects.not_authorized")
        definition=self.repo.get_type(campaign_id,str(values.get("typeId") or ""))
        if not definition:return ObjectResult(False,error_key="sdk.scene.objects.unknown_object_type")
        if definition["package_id"]!=package_id:return ObjectResult(False,error_key="sdk.scene.objects.provider_spoof")
        try:
            geometry,bounds=self.geometry(values.get("geometry"));
            if geometry["kind"] not in definition["definition"]["geometryKinds"]:raise ValueError
            data=values.get("data",{}); self._safe_json(data,self.MAX_DATA_BYTES);self._validate_data(definition["definition"].get("dataSchema",{}),data)
            audience=values.get("audience",{"kind":"campaign"}); self._audience(campaign_id,audience)
            presentation=self._presentation(values.get("presentation",{})); transform=self._transform(values.get("transform",{}))
            search=" ".join(str(data.get(k,""))[:256] for k in definition["definition"].get("searchableFields",[]) if isinstance(data,dict))[:2048]
        except (TypeError,ValueError):return ObjectResult(False,error_key="sdk.scene.objects.invalid_object_data")
        o=self.repo.create(scene_id=scene_id,type_id=definition["type_id"],provider_package_id=package_id,schema_version=definition["schema_version"],geometry_json=json.dumps(geometry),transform_json=json.dumps(transform),presentation_json=json.dumps(presentation),data_json=json.dumps(data),audience_json=json.dumps(audience),enabled=1 if values.get("enabled",True) else 0,min_x=bounds[0],min_y=bounds[1],max_x=bounds[2],max_y=bounds[3],search_text=search)
        return ObjectResult(True,self._public(campaign_id,o))
    def update(self,*,campaign_id,object_id,user_id,patch,expected_version):
        old=self.repo.get(object_id)
        if not old or not self._scene(campaign_id,old["scene_id"]):return ObjectResult(False,error_key="sdk.scene.objects.not_found")
        if not self._write(campaign_id,user_id):return ObjectResult(False,error_key="sdk.scene.objects.not_authorized")
        if not isinstance(expected_version,int):return ObjectResult(False,error_key="sdk.scene.objects.stale_version")
        values={}
        try:
            if "geometry" in patch:
                g,b=self.geometry(patch["geometry"]);values.update(geometry_json=json.dumps(g),min_x=b[0],min_y=b[1],max_x=b[2],max_y=b[3])
            if "data" in patch:
                self._safe_json(patch["data"],self.MAX_DATA_BYTES);definition=self.repo.get_type(campaign_id,old["type_id"])
                if not definition:raise ValueError
                self._validate_data(definition["definition"].get("dataSchema",{}),patch["data"]);values["data_json"]=json.dumps(patch["data"])
            if "presentation" in patch:values["presentation_json"]=json.dumps(self._presentation(patch["presentation"]))
            if "transform" in patch:values["transform_json"]=json.dumps(self._transform(patch["transform"]))
            if "enabled" in patch:values["enabled"]=1 if patch["enabled"] else 0
        except (TypeError,ValueError):return ObjectResult(False,error_key="sdk.scene.objects.invalid_object_data")
        o=self.repo.update(object_id,values,expected_version);return ObjectResult(bool(o),self._public(campaign_id,o) if o else None,None if o else "sdk.scene.objects.stale_version")
    def delete(self,*,campaign_id,object_id,user_id,expected_version=None):
        old=self.repo.get(object_id)
        if not old or not self._scene(campaign_id,old["scene_id"]):return ObjectResult(False,error_key="sdk.scene.objects.not_found")
        if not self._write(campaign_id,user_id):return ObjectResult(False,error_key="sdk.scene.objects.not_authorized")
        ok=self.repo.delete(object_id,expected_version);return ObjectResult(ok,{"id":object_id,"deleted":True} if ok else None,None if ok else "sdk.scene.objects.stale_version")
    def interact(self,*,campaign_id,object_id,user_id,interaction_id,expected_version):
        found=self.get(campaign_id=campaign_id,object_id=object_id,user_id=user_id)
        if not found.success:return found
        o=self.repo.get(object_id); t=self.repo.get_type(campaign_id,o["type_id"])
        if not t:return ObjectResult(False,error_key="sdk.scene.objects.provider_unavailable")
        if t["schema_version"]!=o["schema_version"]:return ObjectResult(False,error_key="sdk.scene.objects.provider_unavailable")
        definition=next((i for i in t["definition"].get("interactionDefinitions",[]) if i.get("id")==interaction_id),None)
        if not definition:return ObjectResult(False,error_key="sdk.scene.objects.unknown_interaction")
        if expected_version is not None and expected_version!=o["version"]:return ObjectResult(False,error_key="sdk.scene.objects.stale_version")
        reference=definition.get("actionReference")
        if reference and (not isinstance(reference,dict) or reference.get("provider")!=o["provider_package_id"] or not isinstance(reference.get("id"),str)):return ObjectResult(False,error_key="sdk.scene.objects.unknown_interaction")
        return ObjectResult(True,{"object":self._public(campaign_id,o),"interactionId":interaction_id,"actionReference":reference,"principal":{"userId":user_id}})
    def hit_test(self,*,campaign_id,scene_id,user_id,x,y,tolerance=8):
        try:x=self._num(x);y=self._num(y);t=max(0,min(32,self._num(tolerance)))
        except ValueError:return ObjectResult(False,error_key="sdk.scene.objects.invalid_geometry")
        hits=[]
        for o in self.repo.candidates(scene_id,x,y,t):
            if self._visible(campaign_id,o,user_id) and self._contains(o["geometry"],x,y,t):hits.append(self._public(campaign_id,o))
        return ObjectResult(True,hits)
    @staticmethod
    def _contains(g,x,y,t):
        if g["kind"]=="point":return (x-g["x"])**2+(y-g["y"])**2<=(12+t)**2
        if g["kind"]=="rect":return g["x"]-t<=x<=g["x"]+g["width"]+t and g["y"]-t<=y<=g["y"]+g["height"]+t
        if g["kind"]=="circle":return (x-g["x"])**2+(y-g["y"])**2<=(g["radius"]+t)**2
        pts=g["points"]
        if g["kind"]=="polyline":return any(SceneObjectService._segment(p,q,x,y)<=t for p,q in zip(pts,pts[1:]))
        inside=False;j=len(pts)-1
        for i,p in enumerate(pts):
            q=pts[j]
            if (p["y"]>y)!=(q["y"]>y) and x<(q["x"]-p["x"])*(y-p["y"])/(q["y"]-p["y"])+p["x"]:inside=not inside
            j=i
        return inside
    @staticmethod
    def _segment(a,b,x,y):
        dx=b["x"]-a["x"];dy=b["y"]-a["y"];d=dx*dx+dy*dy
        u=max(0,min(1,((x-a["x"])*dx+(y-a["y"])*dy)/d)) if d else 0
        return math.hypot(x-(a["x"]+u*dx),y-(a["y"]+u*dy))
    def _audience(self,c,a):
        if not isinstance(a,dict) or a.get("kind") not in {"campaign","gm","users"}:raise ValueError
        members={m["user_id"] for m in CampaignRepository().list_members(campaign_id=c)}
        if a.get("kind")=="users" and (not isinstance(a.get("ids"),list) or len(a["ids"])>64 or any(i not in members for i in a["ids"])):raise ValueError
    @staticmethod
    def _validate_data(schema,value):
        if not isinstance(schema,dict) or schema.get("type","object")!="object" or not isinstance(value,dict):raise ValueError
        properties=schema.get("properties",{});required=schema.get("required",[])
        if not isinstance(properties,dict) or not isinstance(required,list) or any(k not in value for k in required) or schema.get("additionalProperties") is False and any(k not in properties for k in value):raise ValueError
        kinds={"string":str,"number":(int,float),"integer":int,"boolean":bool,"object":dict,"array":list}
        for key,item in value.items():
            rule=properties.get(key,{})
            if not isinstance(rule,dict):raise ValueError
            expected=rule.get("type")
            if expected in kinds and (not isinstance(item,kinds[expected]) or expected in {"number","integer"} and isinstance(item,bool)):raise ValueError
            if rule.get("format")=="content-reference" and (not isinstance(item,dict) or item.get("kind") not in {"actor","item","journal","card","pdf"} or not isinstance(item.get("id"),str)):raise ValueError
    def _presentation(self,p):
        allowed={"icon","label","fill","stroke","opacity","lineWidth","fontScale","rotation","iconScale","asset"}
        if not isinstance(p,dict) or len(p)>9 or set(p)-allowed:raise ValueError
        for key in {"opacity","lineWidth","fontScale","rotation","iconScale"}&set(p):
            value=self._num(p[key]);bounds={"opacity":(0,1),"lineWidth":(0,32),"fontScale":(.25,4),"rotation":(-360,360),"iconScale":(.25,4)}[key]
            if not bounds[0]<=value<=bounds[1]:raise ValueError
        if "asset" in p and (not isinstance(p["asset"],dict) or set(p["asset"])!={"kind","id"} or p["asset"].get("kind") not in {"library-asset","package-asset"} or not isinstance(p["asset"].get("id"),str)):raise ValueError
        for key in {"icon","label","fill","stroke"}&set(p):
            if not isinstance(p[key],str) or len(p[key])>256 or "<" in p[key]:raise ValueError
        self._safe_json(p,4096);return p
    def _transform(self,t):
        if not isinstance(t,dict):raise ValueError
        return {"rotation":max(-360,min(360,self._num(t.get("rotation",0)))),"scale":max(.1,min(10,self._num(t.get("scale",1))))}
    def _public(self,c,o):
        registered=self.repo.get_type(c,o["type_id"]);provider=registered if registered and registered["schema_version"]==o["schema_version"] else None;status="available" if provider else "outdated" if registered else "unavailable"
        return {"id":o["id"],"sceneId":o["scene_id"],"typeId":o["type_id"],"providerPackageId":o["provider_package_id"],"schemaVersion":o["schema_version"],"geometry":o["geometry"],"transform":o["transform"],"presentation":o["presentation"] if provider else {"kind":"unavailable","label":o["type_id"]},"interactions":provider["definition"].get("interactionDefinitions",[]) if provider else [],"editor":provider["definition"].get("editorDefinition",{}) if provider else {},"dataSchema":provider["definition"].get("dataSchema",{}) if provider else {},"data":o["data"] if provider else {},"audience":o["audience"],"enabled":bool(o["enabled"]),"providerAvailable":bool(provider),"providerStatus":status,"version":o["version"],"createdAt":o["created_at"],"updatedAt":o["updated_at"]}
