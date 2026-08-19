"""Semantic timelines: scheduled composition of existing semantic effects.

A timeline states what should happen at which offset from an authoritative
start time. Core owns the clock, so a late joiner sees the cues already due
and no package can claim timing authority of its own.
"""

from __future__ import annotations

import time

from app.engine.audio.audio_runtime_service import AudioRuntimeService
from app.engine.rules.declarative_action_service import DeclarativeActionService
from app.engine.scenes.scene_light_service import SceneLightService
from app.engine.scenes.scene_particle_service import SceneParticleService
from app.engine.scenes.scene_shader_service import SceneShaderService
from app.engine.sdk.scene_navigation_service import SceneNavigationService
from app.engine.sdk.semantic_presentation_service import SemanticPresentationService
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.semantic_instance_repository import SemanticInstanceRepository
from app.persistence.repositories.semantic_registration_repository import SemanticRegistrationRepository

from app.engine.sdk.semantic_authority import (
    ACTION_REFERENCE, IDENTIFIER, SemanticResult,
    is_gm, is_json_safe, resolve_audience,
)

class SemanticTimelineService:
    DOMAIN="timeline";REGISTRY="semantic-timeline-definition";KINDS={"ACTION","AUDIO_PLAY","PRESENTATION_SHOW","LIGHT_CREATE","SHADER_PRESET","PARTICLE_CREATE","NAVIGATION"};MAX_CUES=256;MAX_DURATION_MS=600_000
    def __init__(self):self.definitions=SemanticRegistrationRepository();self.instances=SemanticInstanceRepository()
    def register(self,*,campaign_id,package_id,definition):
        try:
            if not isinstance(definition,dict) or set(definition)-{"id","schemaVersion","cues"}:raise ValueError
            ident=str(definition.get("id") or "");cues=definition.get("cues")
            if not IDENTIFIER.fullmatch(ident) or definition.get("schemaVersion")!=1 or not isinstance(cues,list) or not 1<=len(cues)<=self.MAX_CUES:raise ValueError
            normalized=[];cue_ids=set()
            for cue in cues:
                if not isinstance(cue,dict) or set(cue)-{"cueId","offsetMs","type","action","parameters","cleanupAction","cleanupInput"} or cue.get("type") not in self.KINDS or not isinstance(cue.get("offsetMs"),int) or not 0<=cue["offsetMs"]<=self.MAX_DURATION_MS or not isinstance(cue.get("parameters",{}),dict):raise ValueError
                cue_id=str(cue.get("cueId") or "")
                if not IDENTIFIER.fullmatch(cue_id) or cue_id in cue_ids:raise ValueError
                cue_ids.add(cue_id)
                if cue["type"]=="ACTION":
                    action=ACTION_REFERENCE.fullmatch(str(cue.get("action") or ""))
                    if not action or action.group(1)!=package_id:raise ValueError
                if cue.get("cleanupAction"):
                    cleanup=ACTION_REFERENCE.fullmatch(str(cue["cleanupAction"]));
                    if not cleanup or cleanup.group(1)!=package_id or not isinstance(cue.get("cleanupInput",{}),dict):raise ValueError
                normalized.append({**cue,"cueId":cue_id})
            normalized.sort(key=lambda c:c["offsetMs"])
            value={"id":ident,"schemaVersion":1,"cues":normalized,"durationMs":max(c["offsetMs"] for c in normalized)}
            self.definitions.put(campaign_id,package_id,self.REGISTRY,ident,value);return SemanticResult(True,{"packageId":package_id,**value})
        except (TypeError,ValueError):return SemanticResult(False,error_key="sdk.timelines.invalid_definition")
    def start(self,*,campaign_id,user_id,package_id,values):
        definition=self.definitions.get(campaign_id,package_id,self.REGISTRY,str(values.get("definitionId") or ""));key=str(values.get("idempotencyKey") or "")
        if not isinstance(values,dict) or set(values)-{"definitionId","idempotencyKey","sceneId","startedAt","audience","origin"} or not definition or not key or len(key)>191:return SemanticResult(False,error_key="sdk.timelines.invalid_input")
        prior=self.instances.by_idempotency(campaign_id,package_id,self.DOMAIN,key)
        if prior:return SemanticResult(True,self._public(prior))
        scene_id=values.get("sceneId")
        if scene_id:
            scene=SceneRepository().get_by_id(str(scene_id))
            if not scene or scene["campaign_id"]!=campaign_id:return SemanticResult(False,error_key="sdk.timelines.invalid_input")
        origin=values.get("origin",{})
        try:audience=resolve_audience(campaign_id,user_id,values.get("audience",{"kind":"campaign"}))
        except (TypeError,ValueError,PermissionError):return SemanticResult(False,error_key="sdk.timelines.invalid_input")
        if not isinstance(origin,dict) or not is_json_safe(origin):return SemanticResult(False,error_key="sdk.timelines.invalid_input")
        now_ms=int(time.time()*1000)
        try:started=int(values.get("startedAt") or now_ms)
        except (TypeError,ValueError):return SemanticResult(False,error_key="sdk.timelines.invalid_input")
        if started>now_ms+5_000 or started<now_ms-self.MAX_DURATION_MS:return SemanticResult(False,error_key="sdk.timelines.invalid_input")
        now=int(time.time())
        row=self.instances.create({"campaign_id":campaign_id,"package_id":package_id,"domain":self.DOMAIN,"definition_id":definition["entry_id"],"schema_version":1,"owner_user_id":user_id,"scene_id":scene_id,"status":"RUNNING","waiting_on":None,"wake_at":now,"idempotency_key":key,"payload":{"startedAt":started,"audience":audience,"origin":origin,"receipts":{},"definitionSnapshot":definition["definition"]}})
        return self._drive(row,int(time.time()*1000))
    def get(self,*,campaign_id,user_id,package_id,instance_id):
        row=self.instances.get(instance_id)
        if not self._visible(row,campaign_id,user_id,package_id):return SemanticResult(False,error_key="sdk.timelines.not_found")
        return SemanticResult(True,self._public(row))
    def list(self,*,campaign_id,user_id,package_id):return SemanticResult(True,[self._public(r) for r in self.instances.list(campaign_id,self.DOMAIN,package_id) if self._visible(r,campaign_id,user_id,package_id)])
    def cancel(self,*,campaign_id,user_id,package_id,instance_id,expected_version=None):
        row=self.instances.get(instance_id)
        if not self._visible(row,campaign_id,user_id,package_id) or user_id!=row["owner_user_id"] and not is_gm(campaign_id,user_id):return SemanticResult(False,error_key="sdk.timelines.not_found")
        payload=dict(row["payload"]);cleanup=[];definition=self.definitions.get(campaign_id,package_id,self.REGISTRY,row["definition_id"]);frozen=payload.get("definitionSnapshot") or (definition["definition"] if definition else None)
        if frozen:
            for cue in frozen["cues"]:
                if cue["cueId"] not in payload.get("receipts",{}) or not cue.get("cleanupAction"):continue
                match=ACTION_REFERENCE.fullmatch(cue["cleanupAction"]);result=DeclarativeActionService().execute(campaign_id=campaign_id,user_id=user_id,package_id=match.group(1),action_id=match.group(2),version=int(match.group(3)),inputs=cue.get("cleanupInput",{}),idempotency_key=f"timeline:{row['id']}:cleanup:{cue['cueId']}")
                cleanup.append({"cueId":cue["cueId"],"success":result.success,"error":result.error_key})
        payload.update(completionReason="cancelled",cleanup=cleanup)
        changed=self.instances.patch(instance_id,expected_version,status="CANCELLED",wake_at=None,payload=payload)
        return SemanticResult(bool(changed),self._public(changed) if changed else None,None if changed else "sdk.timelines.stale_version")
    def recover_campaign(self,campaign_id,now_ms=None):
        out=[]
        for row in self.instances.list(campaign_id,self.DOMAIN):
            if row["status"]=="RUNNING":
                result=self._drive(row,int(now_ms or time.time()*1000));
                if result.success:out.append(result.value)
        return out
    def _drive(self,row,now_ms):
        definition=self.definitions.get(row["campaign_id"],row["package_id"],self.REGISTRY,row["definition_id"])
        if not definition or definition["definition"]["schemaVersion"]!=row["schema_version"]:
            row=self.instances.patch(row["id"],row["version"],status="FAILED",wake_at=None,payload={**row["payload"],"completionReason":"provider-unavailable"});return SemanticResult(True,self._public(row))
        payload=dict(row["payload"]);frozen=payload.get("definitionSnapshot") or definition["definition"];receipts=dict(payload["receipts"]);elapsed=max(0,now_ms-payload["startedAt"]);cue_events=[]
        for cue in frozen["cues"]:
            if cue["offsetMs"]>elapsed or cue["cueId"] in receipts:continue
            result=self._execute(row,cue)
            if not result.success:
                row=self.instances.patch(row["id"],row["version"],status="FAILED",wake_at=None,payload={**payload,"receipts":receipts,"completionReason":result.error_key})
                public=self._public(row);public["_cueEvents"]=cue_events
                return SemanticResult(True,public)
            receipts[cue["cueId"]]=result.value;cue_events.append({"cueId":cue["cueId"],"type":cue["type"],"value":result.value})
        payload["receipts"]=receipts
        pending=[c for c in frozen["cues"] if c["cueId"] not in receipts]
        status="RUNNING" if pending else "COMPLETED";wake_at=int((payload["startedAt"]+pending[0]["offsetMs"])/1000) if pending else None
        row=self.instances.patch(row["id"],row["version"],status=status,wake_at=wake_at,payload={**payload,**({"completionReason":"complete"} if not pending else {})})
        public=self._public(row);public["_cueEvents"]=cue_events
        return SemanticResult(True,public)
    def _execute(self,row,cue):
        p=cue.get("parameters",{});kind=cue["type"]
        if kind=="ACTION":
            m=ACTION_REFERENCE.fullmatch(cue["action"]);r=DeclarativeActionService().execute(campaign_id=row["campaign_id"],user_id=row["owner_user_id"],package_id=m.group(1),action_id=m.group(2),version=int(m.group(3)),inputs=p,idempotency_key=f"timeline:{row['id']}:{cue['cueId']}")
        elif kind=="AUDIO_PLAY":r=AudioRuntimeService().play(campaign_id=row["campaign_id"],user_id=row["owner_user_id"],package_id=row["package_id"],values={**p,"idempotencyKey":f"timeline:{row['id']}:{cue['cueId']}"})
        elif kind=="PRESENTATION_SHOW":r=SemanticPresentationService().show(campaign_id=row["campaign_id"],user_id=row["owner_user_id"],package_id=row["package_id"],values=p)
        elif kind=="NAVIGATION":r=SceneNavigationService().go(campaign_id=row["campaign_id"],user_id=row["owner_user_id"],values=p)
        elif kind=="LIGHT_CREATE":r=SceneLightService().create(campaign_id=row["campaign_id"],scene_id=str(p.get("sceneId") or row["scene_id"] or ""),user_id=row["owner_user_id"],**{k:v for k,v in p.items() if k!="sceneId"})
        elif kind=="SHADER_PRESET":r=SceneShaderService().apply_preset(campaign_id=row["campaign_id"],scene_id=str(p.get("sceneId") or row["scene_id"] or ""),user_id=row["owner_user_id"],preset_id=str(p.get("presetId") or ""),schema_version=int(p.get("schemaVersion",1)),parameters=p.get("parameters",{}))
        else:r=SceneParticleService().create(campaign_id=row["campaign_id"],scene_id=str(p.get("sceneId") or row["scene_id"] or ""),user_id=row["owner_user_id"],**{k:v for k,v in p.items() if k!="sceneId"})
        return SemanticResult(bool(r.success),getattr(r,"value",None) or getattr(r,"payload",None),getattr(r,"error_key",None))
    @staticmethod
    def _visible(row,campaign_id,user_id,package_id):return bool(row and row["campaign_id"]==campaign_id and row["package_id"]==package_id and (row["owner_user_id"]==user_id or is_gm(campaign_id,user_id)))
    @staticmethod
    def _public(row):
        p=row["payload"];return {"id":row["id"],"definitionId":row["definition_id"],"providerPackageId":row["package_id"],"campaignId":row["campaign_id"],"sceneId":row["scene_id"],"status":row["status"],"startedAt":p["startedAt"],"audience":p.get("audience"),"origin":p.get("origin",{}),"executedCueIds":list(p.get("receipts",{})),"completionReason":p.get("completionReason"),"version":row["version"]}
