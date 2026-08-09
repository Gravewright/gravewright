from __future__ import annotations
import time, uuid
from sqlalchemy import delete, insert, select, update
from app.persistence.database import all_dicts, engine_begin, engine_connect, one_or_none
from app.persistence.tables import scene_particles

class SceneParticleRepository:
    def list_for_scene(self, scene_id: str) -> list[dict]:
        with engine_connect() as c:
            return all_dicts(c.execute(select(scene_particles).where(scene_particles.c.scene_id == scene_id).order_by(scene_particles.c.created_at, scene_particles.c.id)))
    def get(self, emitter_id: str) -> dict | None:
        with engine_connect() as c:
            return one_or_none(c.execute(select(scene_particles).where(scene_particles.c.id == emitter_id).limit(1)))
    def create(self, **values) -> dict:
        now = int(time.time()); emitter_id = uuid.uuid4().hex
        with engine_begin() as c:
            c.execute(insert(scene_particles).values(id=emitter_id, created_at=now, updated_at=now, **values))
        return self.get(emitter_id) or {}
    def update(self, emitter_id: str, **values) -> dict | None:
        values["updated_at"] = int(time.time())
        with engine_begin() as c:
            c.execute(update(scene_particles).where(scene_particles.c.id == emitter_id).values(**values))
        return self.get(emitter_id)
    def delete(self, emitter_id: str) -> bool:
        with engine_begin() as c:
            return bool(c.execute(delete(scene_particles).where(scene_particles.c.id == emitter_id)).rowcount)
    def delete_many(self, emitter_ids: list[str]) -> int:
        if not emitter_ids: return 0
        with engine_begin() as c:
            return int(c.execute(delete(scene_particles).where(scene_particles.c.id.in_(emitter_ids))).rowcount)
