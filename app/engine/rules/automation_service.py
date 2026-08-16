from __future__ import annotations
import json,time
from dataclasses import dataclass
from sqlalchemy.exc import IntegrityError
from app.engine.rules.declarative_action_registry import ActionContractError,DeclarativeActionRegistry
from app.engine.rules.declarative_action_service import DeclarativeActionService
from app.engine.sdk.runtime_authority import SdkRuntimeAuthority
from app.persistence.repositories.automation_job_repository import AutomationJobRepository
from app.business.audit import AuditService
from app.business.audit.catalog import EVENT_METADATA_KEYS
from app.persistence.repositories.campaign_repository import CampaignRepository
@dataclass(frozen=True)
class AutomationResult:
    success:bool; value:object=None; error_key:str|None=None
class AutomationService:
    MAX_PENDING=100; MAX_PAYLOAD=16_384; MAX_DEPTH=8; MAX_ATTEMPTS=3
    AUDIT_TYPES=tuple(name for name in EVENT_METADATA_KEYS if name.startswith("automation.job."))
    def __init__(self):self.jobs=AutomationJobRepository();self.audit=AuditService()
    def _audit_transition(self,conn,row,transition,recovered=False):
        event=f"automation.job.{transition}"
        if event not in self.AUDIT_TYPES:return
        reason=row.get("error_code")
        metadata={"package_id":row["package_id"],"action_ref":f'{row["package_id"]}:{row["action_id"]}@{row["action_version"]}',"attempt":int(row.get("attempts") or 0),"lease_recovered":bool(recovered),"semantic_reason":str(reason)[:191] if reason else None}
        self.audit.record(campaign_id=row["campaign_id"],actor_user_id=row.get("principal_user_id"),event_type=event,subject_type="automation_job",subject_id=row.get("id"),action=transition,result="success" if transition in {"created","claimed","succeeded","cancelled"} else transition,metadata=metadata,connection=conn,required=True)
    def _reject_schedule(self,*,campaign_id,user_id,package_id,action_ref,reason):
        self.audit.record(campaign_id=campaign_id,actor_user_id=user_id,event_type="automation.job.rejected",subject_type="automation_package",subject_id=None,action="schedule",result="rejected",metadata={"package_id":package_id,"action_ref":action_ref,"attempt":0,"semantic_reason":reason},required=True)
        return AutomationResult(False,error_key=reason)
    def schedule(self,*,campaign_id,user_id,package_id,action_id,version,inputs,run_at_utc,idempotency_key,origin_execution_id=None,origin_job_id=None,causal_depth=0):
        auth=SdkRuntimeAuthority().authorize(campaign_id=campaign_id,user_id=user_id,package_id=package_id,capability="automation.schedule")
        if not auth.allowed:return self._reject_schedule(campaign_id=campaign_id,user_id=user_id,package_id=package_id,action_ref=f"{package_id}:{action_id}@{version}",reason=auth.error_key or "sdk.runtime.denied")
        try:action=DeclarativeActionRegistry().get(package_id,action_id,version)
        except ActionContractError as exc:return self._reject_schedule(campaign_id=campaign_id,user_id=user_id,package_id=package_id,action_ref=f"{package_id}:{action_id}@{version}",reason=exc.code)
        action_ref=action.reference
        if action.durability!="supported" or action.idempotency!="REQUIRES_IDEMPOTENCY_KEY":return self._reject_schedule(campaign_id=campaign_id,user_id=user_id,package_id=package_id,action_ref=action_ref,reason="sdk.automation.not_durable")
        if not isinstance(inputs,dict) or len(json.dumps(inputs).encode())>self.MAX_PAYLOAD or not isinstance(idempotency_key,str) or not idempotency_key or causal_depth>self.MAX_DEPTH:return self._reject_schedule(campaign_id=campaign_id,user_id=user_id,package_id=package_id,action_ref=action_ref,reason="sdk.automation.invalid")
        if len([j for j in self.jobs.list(campaign_id,package_id) if j["status"] in {"pending","running"}])>=self.MAX_PENDING:return self._reject_schedule(campaign_id=campaign_id,user_id=user_id,package_id=package_id,action_ref=action_ref,reason="sdk.automation.quota")
        try: row=self.jobs.create(campaign_id=campaign_id,package_id=package_id,action_id=action.action_id,action_version=action.version,input=inputs,principal_user_id=user_id,run_at_utc=int(run_at_utc),idempotency_key=idempotency_key,origin_execution_id=origin_execution_id,origin_job_id=origin_job_id,causal_depth=causal_depth,audit=self._audit_transition)
        except (IntegrityError,ValueError):return self._reject_schedule(campaign_id=campaign_id,user_id=user_id,package_id=package_id,action_ref=action_ref,reason="sdk.automation.idempotency_conflict")
        return AutomationResult(True,self._public(row))
    def get(self,*,campaign_id,package_id,job_id):
        row=self.jobs.get(job_id);return AutomationResult(bool(row and row["campaign_id"]==campaign_id and row["package_id"]==package_id),self._public(row) if row and row["campaign_id"]==campaign_id and row["package_id"]==package_id else None,"sdk.automation.not_found")
    def list(self,*,campaign_id,package_id):return AutomationResult(True,[self._public(r) for r in self.jobs.list(campaign_id,package_id)])
    def cancel(self,*,campaign_id,package_id,job_id):return AutomationResult(self.jobs.cancel(job_id,campaign_id,package_id,audit=self._audit_transition),{"id":job_id,"status":"cancelled"},"sdk.automation.not_found")
    def list_audit(self,*,campaign_id,package_id,user_id):
        role=CampaignRepository().get_member_role(campaign_id=campaign_id,user_id=user_id)
        if role is None:return AutomationResult(False,error_key="sdk.automation.audit_not_found")
        events=[]
        for event_type in self.AUDIT_TYPES:
            rows,_=self.audit.repository.page(campaign_id=campaign_id,event_type=event_type,offset=0,limit=10_000)
            for row in rows:
                metadata=json.loads(row["metadata_json"])
                if metadata.get("package_id")!=package_id or role!="gm" and row.get("actor_user_id")!=user_id:continue
                item={"schemaVersion":1,"transition":event_type.removeprefix("automation.job."),"jobId":row.get("subject_id"),"campaignId":campaign_id,"packageId":package_id,"actionRef":metadata.get("action_ref"),"attempt":metadata.get("attempt"),"timestamp":row["created_at"]}
                if metadata.get("semantic_reason"):item["semanticReason"]=metadata["semantic_reason"]
                events.append(item)
        events.sort(key=lambda item:(item["timestamp"],item["jobId"] or ""),reverse=True)
        return AutomationResult(True,events[:500])
    def run_one(self,*,worker_id,now=None,fault=None):
        job=self.jobs.claim_due(worker_id,now,audit=self._audit_transition)
        if not job:return AutomationResult(True,None)
        if fault:fault("after_worker_claim")
        result=DeclarativeActionService().execute(campaign_id=job["campaign_id"],user_id=str(job.get("principal_user_id") or ""),package_id=job["package_id"],action_id=job["action_id"],version=job["action_version"],inputs=job["input"],idempotency_key=job["idempotency_key"],fault=fault)
        if result.success:self.jobs.finish(job["id"],worker_id,"succeeded",audit=self._audit_transition);return AutomationResult(True,self._public(self.jobs.get(job["id"])))
        permanent=not any(key in str(result.error_key) for key in ("busy","retryable","contention"))
        if permanent or job["attempts"]>=self.MAX_ATTEMPTS:self.jobs.finish(job["id"],worker_id,"rejected" if permanent else "failed",result.error_key,audit=self._audit_transition)
        else:self.jobs.retry(job["id"],worker_id,int(time.time())+min(60,2**job["attempts"]),result.error_key,audit=self._audit_transition)
        return AutomationResult(False,self._public(self.jobs.get(job["id"])),result.error_key)
    @staticmethod
    def _public(row):
        if not row:return None
        return {k:row.get(k) for k in ("id","package_id","action_id","action_version","run_at_utc","status","attempts","error_code","causal_depth","created_at","updated_at")}
