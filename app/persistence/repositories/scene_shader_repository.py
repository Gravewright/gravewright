from __future__ import annotations
import time, uuid
from sqlalchemy import delete, insert, select, update
from app.persistence.database import all_dicts, engine_begin, engine_connect, one_or_none
from app.persistence.tables import scene_shaders

class SceneShaderRepository:
    def list_for_scene(self, scene_id: str) -> list[dict]:
        with engine_connect() as c:
            return all_dicts(c.execute(select(scene_shaders).where(scene_shaders.c.scene_id == scene_id).order_by(scene_shaders.c.created_at, scene_shaders.c.id)))
    def get(self, shader_id: str) -> dict | None:
        with engine_connect() as c:
            return one_or_none(c.execute(select(scene_shaders).where(scene_shaders.c.id == shader_id).limit(1)))
    def create(self, **values) -> dict:
        now = int(time.time()); shader_id = uuid.uuid4().hex
        with engine_begin() as c:
            c.execute(insert(scene_shaders).values(id=shader_id, created_at=now, updated_at=now, **values))
        return self.get(shader_id) or {}
    def update(self, shader_id: str, **values) -> dict | None:
        values["updated_at"] = int(time.time())
        with engine_begin() as c:
            c.execute(update(scene_shaders).where(scene_shaders.c.id == shader_id).values(**values))
        return self.get(shader_id)
    def delete(self, shader_id: str) -> bool:
        with engine_begin() as c:
            return bool(c.execute(delete(scene_shaders).where(scene_shaders.c.id == shader_id)).rowcount)
    def delete_many(self, shader_ids: list[str]) -> int:
        if not shader_ids: return 0
        with engine_begin() as c:
            return int(c.execute(delete(scene_shaders).where(scene_shaders.c.id.in_(shader_ids))).rowcount)
