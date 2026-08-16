from __future__ import annotations
import json,time,uuid
from sqlalchemy import and_,insert,or_,select,update
from app.persistence.database import all_dicts,engine_begin,engine_connect,one_or_none
from app.persistence.tables import automation_jobs as table
class AutomationJobRepository:
    def create(self, *, audit=None, **values):
        now=int(time.time()); job={"id":uuid.uuid4().hex,"status":"pending","attempts":0,"lease_owner":None,"lease_expires_at":None,"error_code":None,"created_at":now,"updated_at":now,**values}
        job["input_json"]=json.dumps(job.pop("input"),ensure_ascii=False,separators=(",",":"))
        with engine_begin() as conn:
            conn.execute(insert(table).values(**job))
            if audit:audit(conn,dict(job),"created",False)
        return self.get(job["id"])
    def get(self,job_id):
        with engine_connect() as conn: row=one_or_none(conn.execute(select(table).where(table.c.id==job_id)))
        return self._hydrate(row)
    def list(self,campaign_id,package_id):
        with engine_connect() as conn: rows=all_dicts(conn.execute(select(table).where(table.c.campaign_id==campaign_id,table.c.package_id==package_id).order_by(table.c.created_at.desc()).limit(100)))
        return [self._hydrate(r) for r in rows]
    def claim_due(self,worker_id,now=None,lease_seconds=30,audit=None):
        now=int(now or time.time())
        with engine_begin() as conn:
            row=one_or_none(conn.execute(select(table).where(or_(and_(table.c.status=="pending",table.c.run_at_utc<=now),and_(table.c.status=="running",table.c.lease_expires_at<now))).order_by(table.c.run_at_utc).limit(1)))
            if not row:return None
            recovered=row["status"]=="running"
            result=conn.execute(update(table).where(table.c.id==row["id"],or_(table.c.status=="pending",and_(table.c.status=="running",table.c.lease_expires_at<now))).values(status="running",lease_owner=worker_id,lease_expires_at=now+lease_seconds,attempts=table.c.attempts+1,updated_at=now))
            if result.rowcount!=1:return None
            claimed=one_or_none(conn.execute(select(table).where(table.c.id==row["id"])))
            if audit:audit(conn,dict(claimed),"claimed",recovered)
        return self._hydrate(claimed)
    def finish(self,job_id,worker_id,status,error_code=None,audit=None):
        with engine_begin() as conn:
            result=conn.execute(update(table).where(table.c.id==job_id,table.c.status=="running",table.c.lease_owner==worker_id).values(status=status,error_code=error_code,lease_owner=None,lease_expires_at=None,updated_at=int(time.time())))
            if result.rowcount==1 and audit:
                row=one_or_none(conn.execute(select(table).where(table.c.id==job_id)));audit(conn,row,status,False)
            return result.rowcount==1
    def retry(self,job_id,worker_id,run_at,error_code,audit=None):
        with engine_begin() as conn:
            result=conn.execute(update(table).where(table.c.id==job_id,table.c.status=="running",table.c.lease_owner==worker_id).values(status="pending",run_at_utc=run_at,error_code=error_code,lease_owner=None,lease_expires_at=None,updated_at=int(time.time())))
            if result.rowcount==1 and audit:
                row=one_or_none(conn.execute(select(table).where(table.c.id==job_id)));audit(conn,row,"retry_scheduled",False)
            return result.rowcount==1
    def cancel(self,job_id,campaign_id,package_id,audit=None):
        with engine_begin() as conn:
            result=conn.execute(update(table).where(table.c.id==job_id,table.c.campaign_id==campaign_id,table.c.package_id==package_id,table.c.status=="pending").values(status="cancelled",updated_at=int(time.time())))
            if result.rowcount==1 and audit:
                row=one_or_none(conn.execute(select(table).where(table.c.id==job_id)));audit(conn,row,"cancelled",False)
            return result.rowcount==1
    @staticmethod
    def _hydrate(row):
        if not row:return None
        row["input"]=json.loads(row.pop("input_json"));return row
