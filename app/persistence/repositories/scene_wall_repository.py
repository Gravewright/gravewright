from __future__ import annotations
import time, uuid
from sqlalchemy import delete, insert, select, update
from app.persistence.database import all_dicts, engine_begin, engine_connect, one_or_none
from app.persistence.tables import scene_walls

class SceneWallRepository:
    def list_for_scene(self, scene_id: str) -> list[dict]:
        with engine_connect() as c:
            return all_dicts(c.execute(select(scene_walls).where(scene_walls.c.scene_id == scene_id).order_by(scene_walls.c.created_at, scene_walls.c.id)))
    def get(self, wall_id: str) -> dict | None:
        with engine_connect() as c:
            return one_or_none(c.execute(select(scene_walls).where(scene_walls.c.id == wall_id).limit(1)))
    def create(self, **values) -> dict:
        now = int(time.time()); wall_id = uuid.uuid4().hex



        values.setdefault("door_state", "closed")
        with engine_begin() as c:
            c.execute(insert(scene_walls).values(id=wall_id, created_at=now, updated_at=now, **values))
        return self.get(wall_id) or {}
    def update(self, wall_id: str, **values) -> dict | None:
        values["updated_at"] = int(time.time())
        with engine_begin() as c:
            c.execute(update(scene_walls).where(scene_walls.c.id == wall_id).values(**values))
        return self.get(wall_id)
    def delete(self, wall_id: str) -> bool:
        with engine_begin() as c:
            return bool(c.execute(delete(scene_walls).where(scene_walls.c.id == wall_id)).rowcount)
    def delete_many(self, wall_ids: list[str]) -> int:
        if not wall_ids: return 0
        with engine_begin() as c:
            return int(c.execute(delete(scene_walls).where(scene_walls.c.id.in_(wall_ids))).rowcount)
