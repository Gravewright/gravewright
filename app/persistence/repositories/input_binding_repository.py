"""Persistence for user-owned input command bindings."""

from __future__ import annotations

import time
from sqlalchemy import insert, select, update

from app.persistence.database import all_dicts, engine_begin
from app.persistence.tables import input_bindings


class InputBindingRepository:
    def list(self, user_id: str) -> list[dict]:
        with engine_begin() as conn: return all_dicts(conn.execute(select(input_bindings).where(input_bindings.c.user_id==user_id).order_by(input_bindings.c.binding)))
    def set(self,user_id:str,package_id:str,command_id:str,binding:str,expected:int|None=None)->dict|None:
        now=int(time.time())
        with engine_begin() as conn:
            current=conn.execute(select(input_bindings).where(input_bindings.c.user_id==user_id,input_bindings.c.package_id==package_id,input_bindings.c.command_id==command_id)).mappings().first()
            conflict=conn.execute(select(input_bindings).where(input_bindings.c.user_id==user_id,input_bindings.c.binding==binding)).mappings().first()
            if conflict and (conflict["package_id"],conflict["command_id"])!=(package_id,command_id):return None
            if current:
                if expected is not None and current["version"]!=expected:return None
                conn.execute(update(input_bindings).where(input_bindings.c.user_id==user_id,input_bindings.c.package_id==package_id,input_bindings.c.command_id==command_id).values(binding=binding,version=input_bindings.c.version+1,updated_at=now))
            else: conn.execute(insert(input_bindings).values(user_id=user_id,package_id=package_id,command_id=command_id,binding=binding,version=1,created_at=now,updated_at=now))
        return next(row for row in self.list(user_id) if row["package_id"]==package_id and row["command_id"]==command_id)
