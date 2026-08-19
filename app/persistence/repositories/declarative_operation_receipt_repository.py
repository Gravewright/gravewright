from __future__ import annotations
import json,time
from sqlalchemy import insert,select
from sqlalchemy.exc import IntegrityError
from app.persistence.database import engine_begin
from app.persistence.tables import declarative_operation_receipts as table

class DeclarativeOperationReceiptRepository:
    def get(self,identity:str)->dict|None:
        with engine_begin() as conn:row=conn.execute(select(table).where(table.c.identity==identity)).mappings().first()
        if not row:return None
        value=dict(row);value["result"]=json.loads(value.pop("result_json"));return value
    def put(self,*,identity:str,campaign_id:str,package_id:str,payload_hash:str,result:dict)->dict:
        try:
            with engine_begin() as conn:conn.execute(insert(table).values(identity=identity,campaign_id=campaign_id,package_id=package_id,payload_hash=payload_hash,result_json=json.dumps(result,separators=(",",":")),created_at=int(time.time())))
        except IntegrityError:pass
        return self.get(identity)
