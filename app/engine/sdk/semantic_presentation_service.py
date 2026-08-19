"""Bounded, server-owned semantic presentations; never accepts HTML or CSS."""
from __future__ import annotations
import math, re, time, uuid
from dataclasses import dataclass
from typing import Any
from app.engine.scenes.scene_object_service import SceneObjectService
from app.engine.tokens.token_service import TokenService
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.realtime.presence import PresenceService
from app.persistence.repositories.core_ephemeral_state_repository import CoreEphemeralStateRepository
from app.persistence.repositories.asset_repository import AssetRepository
from app.engine.sdk.package_asset_service import PackageAssetService

@dataclass(frozen=True)
class PresentationResult:
    success: bool; value: Any=None; error_key: str|None=None

class SemanticPresentationService:
    NAMESPACE="sdk.presentations"; MODES={"world-anchor","screen-overlay","title-card","countdown","fade"}; MAX_TEXT=2048
    def __init__(self):self.repo=CoreEphemeralStateRepository()
    def _role(self,c,u):return CampaignRepository().get_member_role(campaign_id=c,user_id=u)
    def _audience(self,c,u,value):
        role=self._role(c,u); members={m["user_id"] for m in CampaignRepository().list_members(campaign_id=c)}
        if not isinstance(value,dict) or value.get("kind") not in {"self","campaign","gm","users"}:raise ValueError
        kind=value["kind"];ids=list(dict.fromkeys(value.get("ids",[]))) if kind=="users" else []
        if kind=="self":ids=[u]
        elif kind=="gm":ids=[m["user_id"] for m in CampaignRepository().list_members(campaign_id=c) if m.get("role") in {"gm","assistant_gm"}]
        elif kind=="campaign":ids=list(members)
        if any(i not in members for i in ids) or len(ids)>64 or (set(ids)!={u} and role not in {"gm","assistant_gm"}):raise PermissionError
        return {"kind":kind,"ids":ids}
    def _content(self,value,campaign_id=None,package_id=None):
        if not isinstance(value,dict):raise ValueError
        allowed={"title","text","subtitle","label","progress","value","icon","asset","buttons","preset"}
        if set(value)-allowed:raise ValueError
        out={}
        for k,v in value.items():
            if k in {"title","text","subtitle","label","icon","preset"}:
                if not isinstance(v,str) or len(v)>self.MAX_TEXT or "<" in v or "javascript:" in v.lower():raise ValueError
                if k=="preset" and v not in {"letterbox","damage-flash","darken"}:raise ValueError
            elif k in {"progress","value"}:
                if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError
            elif k=="asset":
                if not isinstance(v,dict) or set(v)!={"kind","id"} or v.get("kind") not in {"library-asset","package-asset"} or not re.fullmatch(r"[A-Za-z0-9._:-]{1,191}",str(v.get("id") or "")):raise ValueError
                if campaign_id and (v["kind"]=="library-asset" and ((asset:=AssetRepository().get_by_id(v["id"])) is None or asset["campaign_id"]!=campaign_id) or v["kind"]=="package-asset" and PackageAssetService().resolve(str(package_id or ""),v["id"]) is None):raise ValueError
            elif k=="buttons":
                if not isinstance(v,list) or len(v)>8:raise ValueError
                for b in v:
                    if not isinstance(b,dict) or set(b)-{"id","label","actionReference"} or not re.fullmatch(rf"{re.escape(str(package_id or ''))}:[a-zA-Z0-9._-]+@[1-9][0-9]*",str(b.get("actionReference") or "")):raise ValueError
            out[k]=v
        return out
    def _anchor(self,c,u,anchor):
        if not isinstance(anchor,dict) or anchor.get("kind") not in {"token","scene-object"} or not isinstance(anchor.get("id"),str):raise ValueError
        if anchor["kind"]=="scene-object":
            found=SceneObjectService().get(campaign_id=c,object_id=anchor["id"],user_id=u)
            if not found.success:raise PermissionError
            return {"kind":"scene-object","id":anchor["id"],"sceneId":found.value["sceneId"]}
        for scene in []:pass
        # Token snapshots are permission-filtered; require an explicit scene id to avoid cross-scene probing.
        scene_id=str(anchor.get("sceneId") or "")
        snapshot=TokenService().get_snapshot(campaign_id=c,scene_id=scene_id,user_id=u)
        if not any(str(t.get("id") or t.get("token_id"))==anchor["id"] for t in (snapshot.tokens or [])):raise PermissionError
        return {"kind":"token","id":anchor["id"],"sceneId":scene_id}
    def show(self,*,campaign_id,user_id,package_id,values):
        try:
            mode=values.get("mode")
            if mode not in self.MODES:raise ValueError
            audience=self._audience(campaign_id,user_id,values.get("audience",{"kind":"self"}));content=self._content(values.get("content",{}),campaign_id,package_id)
            anchor=self._anchor(campaign_id,user_id,values.get("anchor")) if mode=="world-anchor" else None
            duration=int(values.get("duration",30));
            if not 1<=duration<=3600:raise ValueError
            deadline=int(values.get("deadline",int(time.time())+duration))
            if mode=="countdown" and not int(time.time())<deadline<=int(time.time())+86400:raise ValueError
            completion=values.get("completion",{"policy":"server-time"})
            if not isinstance(completion,dict) or set(completion)-{"policy","timeoutMs"} or completion.get("policy","server-time") not in {"server-time","all-connected-recipients"}:raise ValueError
            timeout_ms=int(completion.get("timeoutMs",5000))
            if not 100<=timeout_ms<=60000:raise ValueError
        except PermissionError:return PresentationResult(False,error_key="sdk.ui.presentations.not_authorized")
        except (TypeError,ValueError):return PresentationResult(False,error_key="sdk.ui.presentations.invalid_presentation")
        pid=uuid.uuid4().hex;scope=anchor["sceneId"] if anchor else str(values.get("sceneId") or campaign_id);now_ms=int(time.time()*1000);ends_at=(deadline*1000 if mode=="countdown" else now_ms+duration*1000)
        payload={"id":pid,"campaignId":campaign_id,"packageId":package_id,"ownerUserId":user_id,"sceneId":scope if scope!=campaign_id else None,"mode":mode,"content":content,"audience":audience,"anchor":anchor,"deadline":deadline if mode=="countdown" else None,"status":"active","startedAt":now_ms,"endsAt":ends_at,"completedAt":None,"completionReason":None,"completionPolicy":{"policy":completion.get("policy","server-time"),"timeoutMs":timeout_ms},"recipientSnapshot":audience["ids"],"acknowledgedRecipients":[]}
        row=self.repo.put(namespace=self.NAMESPACE,campaign_id=campaign_id,scope_id=scope,owner_user_id=user_id,entry_key=pid,audience=audience,payload=payload,ttl_seconds=min(86400,duration+(timeout_ms+999)//1000+3600))
        return PresentationResult(True,self._public(row))
    def _reconcile(self,row):
        payload=dict(row["payload"]);now_ms=int(time.time()*1000)
        if payload.get("status")!="active" or now_ms<int(payload.get("endsAt") or 0):return row
        policy=payload.get("completionPolicy",{});reason=None
        if policy.get("policy")=="server-time":reason="server-time"
        else:
            online=PresenceService().list_online_user_ids(list(payload.get("recipientSnapshot",[])))
            acknowledged=set(payload.get("acknowledgedRecipients",[]));relevant=online&set(payload.get("recipientSnapshot",[]))
            if relevant<=acknowledged:reason="recipients"
            elif now_ms>=int(payload["endsAt"])+int(policy.get("timeoutMs",5000)):reason="timeout"
        if reason:
            payload.update(status="completed",completedAt=now_ms,completionReason=reason)
            ttl=max(60,min(3600,row["expires_at"]-int(time.time())))
            return self.repo.put(namespace=self.NAMESPACE,campaign_id=row["campaign_id"],scope_id=row["scope_id"],owner_user_id=row["owner_user_id"],entry_key=row["entry_key"],audience=row["audience"],payload=payload,ttl_seconds=ttl,expected_version=row["version"]) or row
        return row
    def acknowledge(self,*,campaign_id,user_id,package_id,presentation_id):
        row=next((r for r in self.repo.list_namespace(namespace=self.NAMESPACE) if r["campaign_id"]==campaign_id and r["entry_key"]==presentation_id and r["payload"].get("packageId")==package_id),None)
        if not row or user_id not in row["payload"].get("recipientSnapshot",[]):return PresentationResult(False,error_key="sdk.ui.presentations.not_found")
        if row["payload"].get("status")!="active":return PresentationResult(True,self._public(row))
        if int(time.time()*1000)<int(row["payload"].get("endsAt") or 0):return PresentationResult(False,error_key="sdk.ui.presentations.not_complete")
        payload=dict(row["payload"]);payload["acknowledgedRecipients"]=list(dict.fromkeys([*payload.get("acknowledgedRecipients",[]),user_id]))
        ttl=max(60,min(86400,row["expires_at"]-int(time.time())));updated=self.repo.put(namespace=self.NAMESPACE,campaign_id=campaign_id,scope_id=row["scope_id"],owner_user_id=row["owner_user_id"],entry_key=presentation_id,audience=row["audience"],payload=payload,ttl_seconds=ttl,expected_version=row["version"])
        return PresentationResult(True,self._public(self._reconcile(updated or row)))
    def list(self,*,campaign_id,user_id,package_id,scene_id=None):
        rows=self.repo.list_namespace(namespace=self.NAMESPACE); now=int(time.time()); result=[]
        for row in rows:
            row=self._reconcile(row);p=row["payload"]
            if row["campaign_id"]!=campaign_id or p.get("packageId")!=package_id or row["expires_at"]<=now or (user_id!=p.get("ownerUserId") and user_id not in p["audience"]["ids"]):continue
            if p.get("anchor") and scene_id and p["anchor"].get("sceneId")!=scene_id:continue
            if p.get("sceneId") and scene_id and p["sceneId"]!=scene_id:continue
            if p.get("anchor"):
                try:self._anchor(campaign_id,user_id,p["anchor"])
                except (ValueError,PermissionError):continue
            result.append(self._public(row))
        return PresentationResult(True,result)
    def get(self,*,campaign_id,user_id,package_id,presentation_id):
        rows=self.list(campaign_id=campaign_id,user_id=user_id,package_id=package_id)
        found=next((p for p in rows.value if p["id"]==presentation_id),None)
        return PresentationResult(bool(found),found,None if found else "sdk.ui.presentations.not_found")
    def update(self,*,campaign_id,user_id,package_id,presentation_id,patch,expected_version):
        rows=self.repo.list_namespace(namespace=self.NAMESPACE);row=next((r for r in rows if r["campaign_id"]==campaign_id and r["entry_key"]==presentation_id and r["payload"].get("packageId")==package_id),None)
        if not row:return PresentationResult(False,error_key="sdk.ui.presentations.not_found")
        if row["owner_user_id"]!=user_id:return PresentationResult(False,error_key="sdk.ui.presentations.not_authorized")
        if row["version"]!=expected_version:return PresentationResult(False,error_key="sdk.ui.presentations.stale_version")
        payload=dict(row["payload"])
        try:
            if "content" in patch:payload["content"]=self._content(patch["content"],campaign_id,package_id)
            if "anchor" in patch:payload["anchor"]=self._anchor(campaign_id,user_id,patch["anchor"])
            if set(patch)-{"content","anchor"}:raise ValueError
        except PermissionError:return PresentationResult(False,error_key="sdk.ui.presentations.anchor_not_visible")
        except (TypeError,ValueError):return PresentationResult(False,error_key="sdk.ui.presentations.invalid_presentation")
        ttl=max(1,row["expires_at"]-int(time.time()));updated=self.repo.put(namespace=self.NAMESPACE,campaign_id=campaign_id,scope_id=row["scope_id"],owner_user_id=user_id,entry_key=presentation_id,audience=row["audience"],payload=payload,ttl_seconds=ttl,expected_version=expected_version)
        return PresentationResult(bool(updated),self._public(updated) if updated else None,None if updated else "sdk.ui.presentations.stale_version")
    def close(self,*,campaign_id,user_id,package_id,presentation_id,expected_version=None):
        rows=self.repo.list_namespace(namespace=self.NAMESPACE);row=next((r for r in rows if r["campaign_id"]==campaign_id and r["entry_key"]==presentation_id and r["payload"].get("packageId")==package_id),None)
        if not row:return PresentationResult(True,{"id":presentation_id,"status":"closed"})
        if row["owner_user_id"]!=user_id:return PresentationResult(False,error_key="sdk.ui.presentations.not_authorized")
        if row["payload"].get("status")!="active":return PresentationResult(True,self._public(row))
        if expected_version is not None and row["version"]!=expected_version:return PresentationResult(False,error_key="sdk.ui.presentations.stale_version")
        payload=dict(row["payload"]);payload.update(status="closed",completedAt=int(time.time()*1000),completionReason="closed")
        updated=self.repo.put(namespace=self.NAMESPACE,campaign_id=campaign_id,scope_id=row["scope_id"],owner_user_id=user_id,entry_key=presentation_id,audience=row["audience"],payload=payload,ttl_seconds=3600,expected_version=row["version"])
        return PresentationResult(bool(updated),self._public(updated) if updated else None,None if updated else "sdk.ui.presentations.stale_version")
    def close_package(self,*,campaign_id,package_id):
        cancelled=[]
        for row in self.repo.list_namespace(namespace=self.NAMESPACE):
            if row["campaign_id"]==campaign_id and row["payload"].get("packageId")==package_id:
                payload=dict(row["payload"]);payload.update(status="cancelled",completedAt=int(time.time()*1000),completionReason="package-unload")
                updated=self.repo.put(namespace=self.NAMESPACE,campaign_id=campaign_id,scope_id=row["scope_id"],owner_user_id=row["owner_user_id"],entry_key=row["entry_key"],audience=row["audience"],payload=payload,ttl_seconds=3600,expected_version=row["version"])
                if updated:cancelled.append(self._public(updated))
        return cancelled
    @staticmethod
    def _public(row):
        p=dict(row["payload"]);snapshot=p.pop("recipientSnapshot",[]);acked=p.pop("acknowledgedRecipients",[]);p["recipientSummary"]={"expected":len(snapshot),"completed":len(acked)};p.update(version=row["version"],createdAt=row["created_at"],updatedAt=row["updated_at"],expiresAt=row["expires_at"]);return p
