from __future__ import annotations
import time, uuid
from sqlalchemy import delete, insert, select, update
from app.persistence.database import all_dicts, engine_begin, engine_connect, one_or_none
from app.persistence.tables import scene_lights

class SceneLightRepository:
    def list_for_scene(self, scene_id: str) -> list[dict]:
        with engine_connect() as c:
            return all_dicts(c.execute(select(scene_lights).where(scene_lights.c.scene_id == scene_id).order_by(scene_lights.c.created_at, scene_lights.c.id)))
    def get(self, light_id: str) -> dict | None:
        with engine_connect() as c:
            return one_or_none(c.execute(select(scene_lights).where(scene_lights.c.id == light_id).limit(1)))
    def create(self, **values) -> dict:
        now = int(time.time()); light_id = uuid.uuid4().hex
        with engine_begin() as c:
            c.execute(insert(scene_lights).values(id=light_id, created_at=now, updated_at=now, **values))
        return self.get(light_id) or {}
    def update(self, light_id: str, **values) -> dict | None:
        values["updated_at"] = int(time.time())
        with engine_begin() as c:
            c.execute(update(scene_lights).where(scene_lights.c.id == light_id).values(**values))
        return self.get(light_id)
    def delete(self, light_id: str) -> bool:
        with engine_begin() as c:
            return bool(c.execute(delete(scene_lights).where(scene_lights.c.id == light_id)).rowcount)
    def delete_many(self, light_ids: list[str]) -> int:
        if not light_ids: return 0
        with engine_begin() as c:
            return int(c.execute(delete(scene_lights).where(scene_lights.c.id.in_(light_ids))).rowcount)
