"""Semantic multiplayer decisions backed by the private ephemeral store."""
from __future__ import annotations
import math, time, uuid
from dataclasses import dataclass
from typing import Any
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.core_ephemeral_state_repository import CoreEphemeralStateRepository

@dataclass(frozen=True)
class InteractionResult:
    success: bool
    value: Any = None
    error_key: str | None = None

class DirectedInteractionService:
    NS="directed-interactions-v1"; SCOPE="campaign"; MAX_RECIPIENTS=64; MAX_CHOICES=32; MAX_TEXT=4000
    def __init__(self): self.store=CoreEphemeralStateRepository()
    def _members(self,campaign_id): return {str(m["user_id"]):str(m["role"]) for m in CampaignRepository().list_members(campaign_id=campaign_id)}
    def _rows(self,campaign_id): return self.store.list_scope(namespace=self.NS,campaign_id=campaign_id,scope_id=self.SCOPE)
    def _find(self,campaign_id,interaction_id): return next((r for r in self._rows(campaign_id) if r["entry_key"]==interaction_id),None)
    @classmethod
    def _schema(cls,s):
        if not isinstance(s,dict) or s.get("type") not in {"boolean","single-choice","multi-choice","number","string"}: raise ValueError
        out={"type":s["type"]}
        if s["type"] in {"single-choice","multi-choice"}:
            choices=s.get("choices")
            if not isinstance(choices,list) or not 1<=len(choices)<=cls.MAX_CHOICES: raise ValueError
            normalized=[]; ids=set()
            for c in choices:
                if not isinstance(c,dict) or not str(c.get("id") or "") or len(str(c.get("label") or ""))>256: raise ValueError
                ident=str(c["id"])
                if ident in ids: raise ValueError
                ids.add(ident); normalized.append({"id":ident,"label":str(c.get("label") or ident)})
            out["choices"]=normalized
            if s["type"]=="multi-choice": out["maxSelections"]=max(1,min(int(s.get("maxSelections",len(normalized))),len(normalized)))
        if s["type"]=="number":
            lo=float(s.get("minimum",-1_000_000)); hi=float(s.get("maximum",1_000_000))
            if not math.isfinite(lo) or not math.isfinite(hi) or lo>hi: raise ValueError
            out.update(minimum=lo,maximum=hi)
        if s["type"]=="string": out["maxLength"]=max(1,min(int(s.get("maxLength",1000)),4000))
        return out
    @staticmethod
    def _status(row):
        status=row["payload"]["status"]
        return "expired" if status=="open" and int(time.time())>=row["payload"]["deadline"] else status
    def request(self,*,campaign_id,user_id,package_id,values):
        members=self._members(campaign_id)
        if user_id not in members: return InteractionResult(False,error_key="sdk.interactions.not_found")
        try:
            recipients=list(dict.fromkeys(map(str,values.get("recipients",[]))))
            if not 1<=len(recipients)<=self.MAX_RECIPIENTS or any(r not in members for r in recipients): raise ValueError
            title=str(values.get("title") or "")[:256]; text=str(values.get("text") or "")
            if not title or not text or len(text)>self.MAX_TEXT: raise ValueError
            schema=self._schema(values.get("responseSchema")); deadline=int(values.get("deadline") or int(time.time())+300)
            if not int(time.time())<deadline<=int(time.time())+86_400: raise ValueError
            visibility=str(values.get("visibility") or "requester")
            if visibility not in {"requester","participants","public-after-close"}: raise ValueError
            policy=str(values.get("responsePolicy") or "immutable")
            if policy not in {"immutable","replace"}: raise ValueError
        except (TypeError,ValueError): return InteractionResult(False,error_key="sdk.interactions.invalid")
        interaction_id=uuid.uuid4().hex
        payload={"kind":str(values.get("kind") or "prompt")[:64],"schemaVersion":1,"packageId":package_id,"requester":user_id,"recipients":recipients,"title":title,"text":text,"responseSchema":schema,"visibility":visibility,"deadline":deadline,"status":"open","responsePolicy":policy,"responses":{},"origin":values.get("origin") if isinstance(values.get("origin"),dict) else {}}
        row=self.store.put(namespace=self.NS,campaign_id=campaign_id,scope_id=self.SCOPE,owner_user_id=user_id,entry_key=interaction_id,audience={"kind":"users","ids":list(dict.fromkeys([user_id,*recipients]))},payload=payload,ttl_seconds=min(86_400,max(60,deadline-int(time.time())+3600)))
        return InteractionResult(True,self._public(row,user_id))
    def get(self,*,campaign_id,interaction_id,user_id):
        row=self._find(campaign_id,interaction_id)
        if not row or user_id not in row["audience"].get("ids",[]): return InteractionResult(False,error_key="sdk.interactions.not_found")
        return InteractionResult(True,self._public(row,user_id))
    def list(self,*,campaign_id,user_id,status=None,recipient_me=False):
        rows=[r for r in self._rows(campaign_id) if user_id in r["audience"].get("ids",[])]
        if recipient_me: rows=[r for r in rows if user_id in r["payload"]["recipients"]]
        if status: rows=[r for r in rows if self._status(r)==status]
        return InteractionResult(True,[self._public(r,user_id) for r in rows])
    def respond(self,*,campaign_id,interaction_id,user_id,response,expected_version=None,idempotency_key=None):
        row=self._find(campaign_id,interaction_id)
        if not row or user_id not in row["payload"]["recipients"]: return InteractionResult(False,error_key="sdk.interactions.not_found")
        status=self._status(row)
        if status!="open": return InteractionResult(False,error_key=f"sdk.interactions.{status}")
        responses=row["payload"]["responses"]; prior=responses.get(user_id)
        if prior and idempotency_key and prior.get("idempotencyKey")==idempotency_key: return InteractionResult(True,self._public(row,user_id))
        if prior and row["payload"]["responsePolicy"]=="immutable": return InteractionResult(False,error_key="sdk.interactions.already_responded")
        try: normalized=self._validate_response(row["payload"]["responseSchema"],response)
        except (TypeError,ValueError): return InteractionResult(False,error_key="sdk.interactions.response_invalid")
        payload=dict(row["payload"]); payload["responses"]=dict(responses); payload["responses"][user_id]={"value":normalized,"respondedAt":int(time.time()),"idempotencyKey":str(idempotency_key or "")[:128]}
        if len(payload["responses"])==len(payload["recipients"]): payload["status"]="completed"
        updated=self.store.put(namespace=self.NS,campaign_id=campaign_id,scope_id=self.SCOPE,owner_user_id=row["owner_user_id"],entry_key=interaction_id,audience=row["audience"],payload=payload,ttl_seconds=max(60,row["expires_at"]-int(time.time())),expected_version=expected_version if expected_version is not None else row["version"])
        return InteractionResult(bool(updated),self._public(updated,user_id) if updated else None,None if updated else "sdk.interactions.stale_version")
    def cancel(self,*,campaign_id,interaction_id,user_id,expected_version=None):
        row=self._find(campaign_id,interaction_id); role=self._members(campaign_id).get(user_id)
        if not row or user_id!=row["payload"]["requester"] and role not in {"gm","assistant_gm"}: return InteractionResult(False,error_key="sdk.interactions.not_found")
        if self._status(row)!="open": return InteractionResult(False,error_key="sdk.interactions.closed")
        payload=dict(row["payload"]); payload["status"]="cancelled"
        updated=self.store.put(namespace=self.NS,campaign_id=campaign_id,scope_id=self.SCOPE,owner_user_id=row["owner_user_id"],entry_key=interaction_id,audience=row["audience"],payload=payload,ttl_seconds=max(60,row["expires_at"]-int(time.time())),expected_version=expected_version if expected_version is not None else row["version"])
        return InteractionResult(bool(updated),self._public(updated,user_id) if updated else None,None if updated else "sdk.interactions.stale_version")
    def cancel_package(self,*,campaign_id,package_id):
        cancelled=[]
        for row in self._rows(campaign_id):
            if row["payload"].get("packageId")!=package_id or self._status(row)!="open": continue
            payload=dict(row["payload"]); payload["status"]="cancelled"
            updated=self.store.put(namespace=self.NS,campaign_id=campaign_id,scope_id=self.SCOPE,owner_user_id=row["owner_user_id"],entry_key=row["entry_key"],audience=row["audience"],payload=payload,ttl_seconds=max(60,row["expires_at"]-int(time.time())),expected_version=row["version"])
            if updated: cancelled.append(updated["entry_key"])
        return cancelled
    def expire_due(self):
        expired=[]; now=int(time.time())
        for row in self.store.list_namespace(namespace=self.NS):
            if row["payload"].get("status")!="open" or row["payload"].get("deadline",now+1)>now: continue
            payload=dict(row["payload"]); payload["status"]="expired"
            updated=self.store.put(namespace=self.NS,campaign_id=row["campaign_id"],scope_id=self.SCOPE,owner_user_id=row["owner_user_id"],entry_key=row["entry_key"],audience=row["audience"],payload=payload,ttl_seconds=max(60,row["expires_at"]-now),expected_version=row["version"])
            if updated: expired.append({"campaignId":row["campaign_id"],"id":row["entry_key"],"recipients":row["audience"].get("ids",[])})
        return expired
    @classmethod
    def _validate_response(cls,schema,value):
        kind=schema["type"]
        if kind=="boolean":
            if not isinstance(value,bool): raise ValueError
            return value
        if kind=="single-choice":
            if not isinstance(value,str) or value not in {c["id"] for c in schema["choices"]}: raise ValueError
            return value
        if kind=="multi-choice":
            if not isinstance(value,list) or len(value)>schema["maxSelections"] or len(set(value))!=len(value) or any(v not in {c["id"] for c in schema["choices"]} for v in value): raise ValueError
            return value
        if kind=="number":
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not schema["minimum"]<=value<=schema["maximum"]: raise ValueError
            return value
        if not isinstance(value,str) or len(value)>schema["maxLength"]: raise ValueError
        return value
    def _public(self,row,viewer):
        p=row["payload"]; responses=p["responses"]
        if viewer!=p["requester"] and p["visibility"]!="participants": responses={viewer:responses[viewer]} if viewer in responses else {}
        return {"id":row["entry_key"],"kind":p["kind"],"schemaVersion":1,"requester":p["requester"],"recipients":p["recipients"],"prompt":{"title":p["title"],"text":p["text"]},"responseSchema":p["responseSchema"],"visibility":p["visibility"],"deadline":p["deadline"],"status":self._status(row),"responses":responses,"version":row["version"],"origin":p["origin"],"packageProvenance":{"packageId":p["packageId"]},"createdAt":row["created_at"],"expiresAt":row["expires_at"]}
