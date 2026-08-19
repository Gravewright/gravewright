from __future__ import annotations
import json, time, uuid
from sqlalchemy import delete, insert, select, update
from app.persistence.database import all_dicts, engine_begin, engine_connect, one_or_none
from app.persistence.engine import upsert_statement
from app.persistence.tables import scene_object_types as types, scene_objects as objects

class SceneObjectRepository:
    def register_type(self, *, campaign_id: str, package_id: str, type_id: str, definition: dict, schema_version: int) -> dict:
        now=int(time.time()); values={"campaign_id":campaign_id,"package_id":package_id,"type_id":type_id,"definition_json":json.dumps(definition),"schema_version":schema_version,"active":1,"created_at":now,"updated_at":now}
        with engine_begin() as conn:
            conn.execute(upsert_statement(dialect_name=conn.dialect.name,table=types,values=values,index_elements=[types.c.campaign_id,types.c.package_id,types.c.type_id],set_={"definition_json":values["definition_json"],"schema_version":schema_version,"active":1,"updated_at":now}))
        return self.get_type(campaign_id,type_id) or {}
    def get_type(self,campaign_id,type_id):
        with engine_connect() as conn: row=one_or_none(conn.execute(select(types).where(types.c.campaign_id==campaign_id,types.c.type_id==type_id,types.c.active==1).limit(1)))
        return self._type(row) if row else None
    def deactivate_type(self,campaign_id,package_id,type_id):
        with engine_begin() as conn: conn.execute(update(types).where(types.c.campaign_id==campaign_id,types.c.package_id==package_id,types.c.type_id==type_id).values(active=0,updated_at=int(time.time())))
    def deactivate_package(self,campaign_id,package_id):
        with engine_begin() as conn:conn.execute(update(types).where(types.c.campaign_id==campaign_id,types.c.package_id==package_id).values(active=0,updated_at=int(time.time())))
    def create(self,**values):
        now=int(time.time()); object_id=uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(insert(objects).values(id=object_id,version=1,created_at=now,updated_at=now,**values)); row=conn.execute(select(objects).where(objects.c.id==object_id)).mappings().one()
        return self._object(dict(row))
    def get(self,object_id):
        with engine_connect() as conn: row=one_or_none(conn.execute(select(objects).where(objects.c.id==object_id).limit(1)))
        return self._object(row) if row else None
    def list_scene(self,scene_id,q=None):
        stmt=select(objects).where(objects.c.scene_id==scene_id)
        if q: stmt=stmt.where(objects.c.search_text.ilike(f"%{q[:128]}%"))
        with engine_connect() as conn: rows=all_dicts(conn.execute(stmt.order_by(objects.c.created_at)))
        return [self._object(r) for r in rows]
    def candidates(self,scene_id,x,y,tolerance=0):
        with engine_connect() as conn: rows=all_dicts(conn.execute(select(objects).where(objects.c.scene_id==scene_id,objects.c.enabled==1,objects.c.min_x<=x+tolerance,objects.c.max_x>=x-tolerance,objects.c.min_y<=y+tolerance,objects.c.max_y>=y-tolerance)))
        return [self._object(r) for r in rows]
    def update(self,object_id,values,expected_version):
        stmt=update(objects).where(objects.c.id==object_id,objects.c.version==expected_version)
        with engine_begin() as conn:
            result=conn.execute(stmt.values(**values,version=objects.c.version+1,updated_at=int(time.time())))
            if result.rowcount!=1:return None
            row=conn.execute(select(objects).where(objects.c.id==object_id)).mappings().one()
        return self._object(dict(row))
    def delete(self,object_id,expected_version=None):
        stmt=delete(objects).where(objects.c.id==object_id)
        if expected_version is not None:stmt=stmt.where(objects.c.version==expected_version)
        with engine_begin() as conn:return conn.execute(stmt).rowcount==1
    @staticmethod
    def _type(row):
        row=dict(row); row["definition"]=json.loads(row.pop("definition_json")); return row
    @staticmethod
    def _object(row):
        row=dict(row)
        for key in ("geometry","transform","presentation","data","audience"):row[key]=json.loads(row.pop(f"{key}_json"))
        return row
