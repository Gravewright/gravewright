"""Semantic adapters over the core's internal TTL coordination store."""
from __future__ import annotations
import math
import uuid
from dataclasses import dataclass
from typing import Any
from app.engine.tokens.token_service import TokenService
from app.engine.scenes.scene_service import SceneService
from app.engine.sdk.pdf_service import SdkPdfService
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.core_ephemeral_state_repository import CoreEphemeralStateRepository

@dataclass(frozen=True)
class EphemeralResult:
    success: bool
    value: Any = None
    error_key: str | None = None

class TokenTargetService:
    NS = "token-targets-v1"; KEY = "current"; MAX = 64
    def __init__(self): self.store = CoreEphemeralStateRepository()
    def list(self, *, campaign_id: str, scene_id: str, user_id: str) -> EphemeralResult:
        visible = TokenService().get_snapshot(campaign_id=campaign_id, scene_id=scene_id, user_id=user_id)
        if not visible.success: return EphemeralResult(False, error_key="sdk.tokens.targets.not_found")
        allowed = {str(t.get("id") or t.get("token_id")) for t in visible.tokens or []}
        row = next((r for r in self.store.list_scope(namespace=self.NS, campaign_id=campaign_id, scope_id=scene_id) if r["owner_user_id"] == user_id), None)
        return EphemeralResult(True, [token_id for token_id in (row or {}).get("payload", {}).get("ids", []) if token_id in allowed])
    def set(self, *, campaign_id: str, scene_id: str, user_id: str, ids: object) -> EphemeralResult:
        if not isinstance(ids, list) or len(ids) > self.MAX or len(set(map(str, ids))) != len(ids): return EphemeralResult(False, error_key="sdk.tokens.targets.invalid")
        visible = TokenService().get_snapshot(campaign_id=campaign_id, scene_id=scene_id, user_id=user_id)
        if not visible.success: return EphemeralResult(False, error_key="sdk.tokens.targets.not_found")
        allowed = {str(t.get("id") or t.get("token_id")) for t in visible.tokens or []}; normalized = [str(i) for i in ids]
        if any(i not in allowed for i in normalized): return EphemeralResult(False, error_key="sdk.tokens.targets.not_found")
        current = next((r for r in self.store.list_scope(namespace=self.NS,campaign_id=campaign_id,scope_id=scene_id) if r["owner_user_id"]==user_id),None)
        if current and current["updated_at"] >= __import__('time').time().__int__(): return EphemeralResult(False,error_key="sdk.tokens.targets.rate_limited")
        self.store.delete_owner_except_scope(namespace=self.NS, campaign_id=campaign_id, owner_user_id=user_id, scope_id=scene_id)
        self.store.put(namespace=self.NS, campaign_id=campaign_id, scope_id=scene_id, owner_user_id=user_id, entry_key=self.KEY, audience={"kind":"owner"}, payload={"ids":normalized}, ttl_seconds=86_400)
        return EphemeralResult(True, normalized)
    def clear(self, *, campaign_id: str, scene_id: str, user_id: str) -> EphemeralResult:
        self.store.delete(namespace=self.NS, campaign_id=campaign_id, scope_id=scene_id,
                          owner_user_id=user_id, entry_key=self.KEY)
        return EphemeralResult(True, [])

class SharedMeasurementService:
    NS = "shared-measurements-v1"; MAX_ACTIVE = 16
    def __init__(self): self.store = CoreEphemeralStateRepository()
    def _scene(self, campaign_id, scene_id, user_id):
        return any(s.get("id") == scene_id for s in (SceneService().list_scenes_for_campaign(campaign_id=campaign_id, user_id=user_id).scenes or []))
    def create(self, *, campaign_id: str, scene_id: str, user_id: str, geometry: object, audience: str, ttl_seconds: int = 30) -> EphemeralResult:
        if not self._scene(campaign_id, scene_id, user_id): return EphemeralResult(False, error_key="sdk.scene.measurements.not_found")
        if audience not in {"self","campaign","gm"} or not isinstance(geometry, dict): return EphemeralResult(False, error_key="sdk.scene.measurements.invalid")
        points = geometry.get("points")
        if not isinstance(points, list) or not 2 <= len(points) <= 32 or any(not isinstance(p, dict) or any(not isinstance(p.get(k),(int,float)) or isinstance(p.get(k),bool) or not math.isfinite(p[k]) for k in ("x","y")) for p in points): return EphemeralResult(False, error_key="sdk.scene.measurements.invalid")
        active = [r for r in self.store.list_scope(namespace=self.NS, campaign_id=campaign_id, scope_id=scene_id) if r["owner_user_id"] == user_id]
        if len(active) >= self.MAX_ACTIVE: return EphemeralResult(False, error_key="sdk.scene.measurements.quota")
        if sum(r["created_at"] >= __import__('time').time().__int__() for r in active) >= 8: return EphemeralResult(False,error_key="sdk.scene.measurements.rate_limited")
        entry = uuid.uuid4().hex; row = self.store.put(namespace=self.NS, campaign_id=campaign_id, scope_id=scene_id, owner_user_id=user_id, entry_key=entry, audience={"kind":audience}, payload={"geometry":geometry}, ttl_seconds=max(1,min(int(ttl_seconds),300)))
        return EphemeralResult(True, self._public(row))
    def list(self, *, campaign_id: str, scene_id: str, user_id: str) -> EphemeralResult:
        if not self._scene(campaign_id, scene_id, user_id): return EphemeralResult(False, error_key="sdk.scene.measurements.not_found")
        role = CampaignRepository().get_member_role(campaign_id=campaign_id,user_id=user_id)
        rows = [r for r in self.store.list_scope(namespace=self.NS,campaign_id=campaign_id,scope_id=scene_id) if r["owner_user_id"] == user_id or r["audience"].get("kind") == "campaign" or r["audience"].get("kind") == "gm" and role in {"gm","assistant_gm"}]
        return EphemeralResult(True,[self._public(r) for r in rows])
    def cancel(self, *, campaign_id: str, scene_id: str, user_id: str, measurement_id: str) -> EphemeralResult:
        rows=self.store.list_scope(namespace=self.NS,campaign_id=campaign_id,scope_id=scene_id); row=next((r for r in rows if r["entry_key"]==measurement_id),None); role=CampaignRepository().get_member_role(campaign_id=campaign_id,user_id=user_id)
        if not row or row["owner_user_id"] != user_id and role not in {"gm","assistant_gm"}: return EphemeralResult(False,error_key="sdk.scene.measurements.not_found")
        self.store.delete(namespace=self.NS,campaign_id=campaign_id,scope_id=scene_id,owner_user_id=row["owner_user_id"],entry_key=measurement_id); return EphemeralResult(True,self._public(row))
    @staticmethod
    def _public(row): return {"id":row["entry_key"],"creator":row["owner_user_id"],"sceneId":row["scope_id"],"geometry":row["payload"]["geometry"],"audience":row["audience"]["kind"],"expiresAt":row["expires_at"],"version":row["version"]}

class PdfPresentationService:
    NS="pdf-presentations-v1"; KEY="current"
    def __init__(self): self.store=CoreEphemeralStateRepository(); self.pdf=SdkPdfService()
    def start(self, *, campaign_id, document_id, user_id, audience, page, ttl_seconds=300):
        role=CampaignRepository().get_member_role(campaign_id=campaign_id,user_id=user_id)
        if role not in {"gm","assistant_gm"} or not self.pdf.document(campaign_id=campaign_id,document_id=document_id,user_id=user_id).success: return EphemeralResult(False,error_key="sdk.pdf.presentation.not_found")
        if not isinstance(audience,list) or not audience: return EphemeralResult(False,error_key="sdk.pdf.presentation.audience_invalid")
        members={m["user_id"] for m in CampaignRepository().list_members(campaign_id=campaign_id)}
        audience_ids=list(dict.fromkeys(map(str,audience)))
        if any(uid not in members or not self.pdf.document(campaign_id=campaign_id,document_id=document_id,user_id=uid).success for uid in audience_ids): return EphemeralResult(False,error_key="sdk.pdf.presentation.audience_invalid")
        try: page=int(page)
        except (TypeError,ValueError): return EphemeralResult(False,error_key="sdk.pdf.presentation.page_invalid")
        if page < 1: return EphemeralResult(False,error_key="sdk.pdf.presentation.page_invalid")
        session_id=uuid.uuid4().hex; row=self.store.put(namespace=self.NS,campaign_id=campaign_id,scope_id=document_id,owner_user_id=user_id,entry_key=self.KEY,audience={"kind":"users","ids":audience_ids},payload={"id":session_id,"page":page,"status":"active"},ttl_seconds=max(1,min(int(ttl_seconds),3600)))
        return EphemeralResult(True,self._public(row))
    def current(self, *, campaign_id, document_id, user_id):
        if not self.pdf.document(campaign_id=campaign_id,document_id=document_id,user_id=user_id).success: return EphemeralResult(False,error_key="sdk.pdf.presentation.not_found")
        row=next((r for r in self.store.list_scope(namespace=self.NS,campaign_id=campaign_id,scope_id=document_id) if r["entry_key"]==self.KEY and (r["owner_user_id"]==user_id or user_id in r["audience"].get("ids",[]))),None)
        return EphemeralResult(True,self._public(row) if row else None)
    def update(self, *, campaign_id, document_id, user_id, page, expected_version):
        row=next((r for r in self.store.list_scope(namespace=self.NS,campaign_id=campaign_id,scope_id=document_id) if r["entry_key"]==self.KEY and r["owner_user_id"]==user_id),None)
        if not row: return EphemeralResult(False,error_key="sdk.pdf.presentation.not_found")
        try: page=int(page); expected_version=int(expected_version)
        except (TypeError,ValueError): return EphemeralResult(False,error_key="sdk.pdf.presentation.page_invalid")
        updated=self.store.put(namespace=self.NS,campaign_id=campaign_id,scope_id=document_id,owner_user_id=user_id,entry_key=self.KEY,audience=row["audience"],payload={**row["payload"],"page":page},ttl_seconds=max(1,row["expires_at"]-__import__('time').time().__int__()),expected_version=expected_version)
        return EphemeralResult(bool(updated),self._public(updated) if updated else None,"sdk.pdf.presentation.stale_version" if not updated else None)
    def end(self, *, campaign_id, document_id, user_id):
        row=next((r for r in self.store.list_scope(namespace=self.NS,campaign_id=campaign_id,scope_id=document_id) if r["entry_key"]==self.KEY and r["owner_user_id"]==user_id),None)
        if not row:return EphemeralResult(False,error_key="sdk.pdf.presentation.not_found")
        value=self._public(row);value["status"]="ended";ok=self.store.delete(namespace=self.NS,campaign_id=campaign_id,scope_id=document_id,owner_user_id=user_id,entry_key=self.KEY);return EphemeralResult(ok,value,"sdk.pdf.presentation.not_found" if not ok else None)
    @staticmethod
    def _public(row): return None if not row else {"id":row["payload"]["id"],"presenter":row["owner_user_id"],"documentId":row["scope_id"],"audience":row["audience"]["ids"],"page":row["payload"]["page"],"version":row["version"],"status":row["payload"]["status"],"expiresAt":row["expires_at"]}
