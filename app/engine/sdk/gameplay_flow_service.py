"""Gameplay flow: phases, participants and commitment.

A flow orders who acts and when, without assuming any ruleset. It carries no
dice, initiative or hit points; a simultaneous phase keeps each submission
private until every participant has committed, and only then reveals.
"""

from __future__ import annotations

import time

from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.semantic_instance_repository import SemanticInstanceRepository
from app.persistence.repositories.semantic_registration_repository import SemanticRegistrationRepository

from app.engine.sdk.semantic_authority import (
    IDENTIFIER, SemanticResult,
    is_gm, is_json_safe,
)

class GameplayFlowService:
    DOMAIN = "gameplay-flow"; REGISTRY = "gameplay-flow-definition"; MODES = {"SEQUENTIAL", "SIMULTANEOUS", "PHASED"}
    def __init__(self): self.definitions=SemanticRegistrationRepository(); self.instances=SemanticInstanceRepository()
    def register(self,*,campaign_id,package_id,definition):
        try:
            if not isinstance(definition,dict) or set(definition)-{"id","schemaVersion","turnModel","phases"}:raise ValueError
            ident=str(definition.get("id") or ""); phases=definition.get("phases"); mode=definition.get("turnModel")
            if not IDENTIFIER.fullmatch(ident) or definition.get("schemaVersion")!=1 or mode not in self.MODES or not isinstance(phases,list) or not 1<=len(phases)<=32:raise ValueError
            normalized=[];ids=set()
            for phase in phases:
                if not isinstance(phase,dict) or set(phase)-{"id","label","submissionPolicy","deadlineSeconds"} or not IDENTIFIER.fullmatch(str(phase.get("id") or "")) or phase["id"] in ids:raise ValueError
                deadline=phase.get("deadlineSeconds")
                if deadline is not None and (not isinstance(deadline,int) or not 1<=deadline<=86_400):raise ValueError
                if phase.get("submissionPolicy","all")!="all":raise ValueError
                ids.add(phase["id"]);normalized.append({"id":phase["id"],"label":str(phase.get("label") or phase["id"])[:256],"submissionPolicy":phase.get("submissionPolicy","all"),**({"deadlineSeconds":deadline} if deadline else {})})
            value={"id":ident,"schemaVersion":1,"turnModel":mode,"phases":normalized}
            self.definitions.put(campaign_id,package_id,self.REGISTRY,ident,value);return SemanticResult(True,{"packageId":package_id,**value})
        except (TypeError,ValueError):return SemanticResult(False,error_key="sdk.gameplay.flows.invalid_definition")
    def start(self,*,campaign_id,user_id,package_id,values):
        row=self.definitions.get(campaign_id,package_id,self.REGISTRY,str(values.get("definitionId") or ""))
        try:
            if not is_gm(campaign_id,user_id):return SemanticResult(False,error_key="sdk.gameplay.flows.not_found")
            participants=list(dict.fromkeys(map(str,values.get("participants",[])))); members={m["user_id"] for m in CampaignRepository().list_members(campaign_id=campaign_id)}
            if not row or not participants or len(participants)>64 or any(p not in members for p in participants):raise ValueError
            key=str(values.get("idempotencyKey") or "");
            if not key or len(key)>191 or set(values)-{"definitionId","participants","sceneId","idempotencyKey"}:raise ValueError
            scene_id=values.get("sceneId")
            if scene_id:
                scene=SceneRepository().get_by_id(str(scene_id))
                if not scene or scene["campaign_id"]!=campaign_id:raise ValueError
            prior=self.instances.by_idempotency(campaign_id,package_id,self.DOMAIN,key)
            if prior:return SemanticResult(True,self._public(prior,user_id))
            definition=row["definition"];now=int(time.time())
            deadline=definition["phases"][0].get("deadlineSeconds")
            instance=self.instances.create({"campaign_id":campaign_id,"package_id":package_id,"domain":self.DOMAIN,"definition_id":definition["id"],"schema_version":1,"owner_user_id":user_id,"scene_id":scene_id,"status":"ACTIVE","waiting_on":None,"wake_at":now+deadline if deadline else None,"idempotency_key":key,"payload":{"phaseIndex":0,"activeIndex":0,"round":1,"cycle":1,"participants":participants,"submissions":{},"revealed":False,"startedAt":now,"phaseStartedAt":now,"definitionSnapshot":definition}})
            return SemanticResult(True,self._public(instance,user_id))
        except (TypeError,ValueError):return SemanticResult(False,error_key="sdk.gameplay.flows.invalid_input")
    def get(self,*,campaign_id,user_id,package_id,instance_id):
        row=self.instances.get(instance_id)
        if not self._visible(row,campaign_id,user_id,package_id):return SemanticResult(False,error_key="sdk.gameplay.flows.not_found")
        return SemanticResult(True,self._public(row,user_id))
    def list(self,*,campaign_id,user_id,package_id):return SemanticResult(True,[self._public(r,user_id) for r in self.instances.list(campaign_id,self.DOMAIN,package_id) if self._visible(r,campaign_id,user_id,package_id)])
    def submit(self,*,campaign_id,user_id,package_id,instance_id,value,expected_version=None):
        row=self.instances.get(instance_id)
        if not self._visible(row,campaign_id,user_id,package_id) or user_id not in row["payload"]["participants"]:return SemanticResult(False,error_key="sdk.gameplay.flows.not_found")
        if row["status"]!="ACTIVE" or not is_json_safe(value):return SemanticResult(False,error_key="sdk.gameplay.flows.invalid_submission")
        registered=self.definitions.get(campaign_id,package_id,self.REGISTRY,row["definition_id"])
        if not registered:return SemanticResult(False,error_key="sdk.gameplay.flows.provider_unavailable")
        definition=row["payload"].get("definitionSnapshot") or registered["definition"]
        payload=dict(row["payload"])
        if definition["turnModel"]=="SEQUENTIAL" and payload["participants"][payload.get("activeIndex",0)]!=user_id:return SemanticResult(False,error_key="sdk.gameplay.flows.not_active_participant")
        if user_id in payload["submissions"]:return SemanticResult(False,error_key="sdk.gameplay.flows.already_submitted")
        sub=dict(payload["submissions"]);sub[user_id]={"value":value,"submittedAt":int(time.time())};payload["submissions"]=sub
        if definition["turnModel"]=="SEQUENTIAL":payload["activeIndex"]=(payload.get("activeIndex",0)+1)%len(payload["participants"])
        if definition["turnModel"]=="SIMULTANEOUS" and len(sub)==len(payload["participants"]):payload["revealed"]=True
        changed=self.instances.patch(instance_id,expected_version if expected_version is not None else row["version"],payload=payload)
        return SemanticResult(bool(changed),self._public(changed,user_id) if changed else None,None if changed else "sdk.gameplay.flows.stale_version")
    def advance(self,*,campaign_id,user_id,package_id,instance_id,expected_version=None):
        row=self.instances.get(instance_id)
        if not self._visible(row,campaign_id,user_id,package_id) or not is_gm(campaign_id,user_id):return SemanticResult(False,error_key="sdk.gameplay.flows.not_found")
        definition=self.definitions.get(campaign_id,package_id,self.REGISTRY,row["definition_id"])
        if not definition or definition["definition"]["schemaVersion"]!=row["schema_version"]:return SemanticResult(False,error_key="sdk.gameplay.flows.provider_unavailable")
        snapshot=row["payload"].get("definitionSnapshot") or definition["definition"]
        return self._advance(row,snapshot,expected_version,viewer=user_id)
    def _advance(self,row,definition,expected_version=None,viewer=None):
        payload=dict(row["payload"]);payload["phaseIndex"]=(payload["phaseIndex"]+1)%len(definition["phases"])
        if payload["phaseIndex"]==0:payload["round"]+=1;payload["cycle"]+=1
        now=int(time.time());payload["submissions"]={};payload["revealed"]=False;payload["activeIndex"]=0;payload["phaseStartedAt"]=now
        deadline=definition["phases"][payload["phaseIndex"]].get("deadlineSeconds")
        changed=self.instances.patch(row["id"],expected_version if expected_version is not None else row["version"],payload=payload,wake_at=now+deadline if deadline else None)
        return SemanticResult(bool(changed),self._public(changed,viewer or row["owner_user_id"]) if changed else None,None if changed else "sdk.gameplay.flows.stale_version")
    def recover_campaign(self,campaign_id,now=None):
        now=int(now or time.time());output=[]
        for row in self.instances.list(campaign_id,self.DOMAIN):
            if row["status"]!="ACTIVE" or row["wake_at"] is None or row["wake_at"]>now:continue
            definition=self.definitions.get(campaign_id,row["package_id"],self.REGISTRY,row["definition_id"])
            if not definition or definition["definition"]["schemaVersion"]!=row["schema_version"]:
                failed=self.instances.patch(row["id"],row["version"],status="CANCELLED",wake_at=None,payload={**row["payload"],"completionReason":"provider-unavailable"})
                if failed:output.append(self._public(failed,row["owner_user_id"]))
            else:
                result=self._advance(row,row["payload"].get("definitionSnapshot") or definition["definition"])
                if result.success:output.append(result.value)
        return output
    @staticmethod
    def _visible(row,campaign_id,user_id,package_id):return bool(row and row["campaign_id"]==campaign_id and row["package_id"]==package_id and (user_id in row["payload"].get("participants",[]) or is_gm(campaign_id,user_id)))
    def _public(self,row,viewer):
        p=row["payload"];definition=self.definitions.get(row["campaign_id"],row["package_id"],self.REGISTRY,row["definition_id"]);frozen=p.get("definitionSnapshot") or (definition["definition"] if definition else None);phases=frozen["phases"] if frozen else []
        submissions=p["submissions"] if p["revealed"] or is_gm(row["campaign_id"],viewer) else ({viewer:p["submissions"][viewer]} if viewer in p["submissions"] else {})
        mode=frozen["turnModel"] if frozen else "PHASED";active=[p["participants"][p.get("activeIndex",0)]] if mode=="SEQUENTIAL" else list(p["participants"])
        return {"id":row["id"],"campaignId":row["campaign_id"],"sceneId":row["scene_id"],"definitionId":row["definition_id"],"providerPackageId":row["package_id"],"status":row["status"],"phaseId":phases[p["phaseIndex"]]["id"] if phases else None,"round":p["round"],"cycle":p["cycle"],"participants":p["participants"],"activeParticipants":active,"submissions":submissions,"revealed":p["revealed"],"version":row["version"]}
