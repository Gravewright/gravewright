from __future__ import annotations
import json, time, uuid
from sqlalchemy import delete, insert, select, update
from app.persistence.database import all_dicts, engine_begin, engine_connect, one_or_none
from app.persistence.tables import scene_zones as table

class SceneZoneRepository:
    def create(self, **values):
        now=int(time.time()); zone_id=uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(insert(table).values(id=zone_id, version=1, created_at=now, updated_at=now, **values))
            row=conn.execute(select(table).where(table.c.id==zone_id)).mappings().one()
        return self._hydrate(dict(row))
    def get(self, zone_id):
        with engine_connect() as conn: row=one_or_none(conn.execute(select(table).where(table.c.id==zone_id).limit(1)))
        return self._hydrate(row) if row else None
    def list_for_scene(self, scene_id):
        with engine_connect() as conn: rows=all_dicts(conn.execute(select(table).where(table.c.scene_id==scene_id).order_by(table.c.created_at)))
        return [self._hydrate(r) for r in rows]
    def candidates(self, scene_id, min_x, min_y, max_x, max_y):
        with engine_connect() as conn: rows=all_dicts(conn.execute(select(table).where(table.c.scene_id==scene_id,table.c.enabled==1,table.c.max_x>=min_x,table.c.min_x<=max_x,table.c.max_y>=min_y,table.c.min_y<=max_y)))
        return [self._hydrate(r) for r in rows]
    def update(self, zone_id, values, expected_version):
        now=int(time.time()); stmt=update(table).where(table.c.id==zone_id)
        if expected_version is not None: stmt=stmt.where(table.c.version==expected_version)
        with engine_begin() as conn:
            result=conn.execute(stmt.values(**values,version=table.c.version+1,updated_at=now))
            if result.rowcount != 1: return None
            row=conn.execute(select(table).where(table.c.id==zone_id)).mappings().one()
        return self._hydrate(dict(row))
    def delete(self, zone_id, expected_version=None):
        stmt=delete(table).where(table.c.id==zone_id)
        if expected_version is not None: stmt=stmt.where(table.c.version==expected_version)
        with engine_begin() as conn: return conn.execute(stmt).rowcount==1
    @staticmethod
    def _hydrate(row):
        row=dict(row); row["geometry"]=json.loads(row.pop("geometry_json")); row["audience"]=json.loads(row.pop("audience_json")); row["tags"]=json.loads(row.pop("tags_json")); return row
