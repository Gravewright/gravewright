"""Persistence for runtime audio playback state."""

from __future__ import annotations

import json
import time
import uuid
from sqlalchemy import insert, select, update

from app.persistence.database import all_dicts, engine_begin
from app.persistence.tables import audio_playbacks


class AudioPlaybackRepository:
    def create(self, values: dict) -> dict:
        now = int(time.time()); values = dict(values, id=uuid.uuid4().hex, version=1, created_at=now, updated_at=now)
        with engine_begin() as conn: conn.execute(insert(audio_playbacks).values(**values))
        return self.get(values["id"])
    def get(self, playback_id: str) -> dict | None:
        with engine_begin() as conn: row = conn.execute(select(audio_playbacks).where(audio_playbacks.c.id == playback_id)).mappings().first()
        return self._row(row)
    def by_key(self, campaign_id: str, package_id: str, key: str) -> dict | None:
        with engine_begin() as conn: row = conn.execute(select(audio_playbacks).where(audio_playbacks.c.campaign_id == campaign_id, audio_playbacks.c.package_id == package_id, audio_playbacks.c.idempotency_key == key)).mappings().first()
        return self._row(row)
    def list(self, campaign_id: str) -> list[dict]:
        with engine_begin() as conn: rows = all_dicts(conn.execute(select(audio_playbacks).where(audio_playbacks.c.campaign_id == campaign_id).order_by(audio_playbacks.c.created_at)))
        return [self._row(row) for row in rows]
    def patch(self, playback_id: str, expected: int | None, values: dict) -> dict | None:
        stmt = update(audio_playbacks).where(audio_playbacks.c.id == playback_id)
        if expected is not None: stmt = stmt.where(audio_playbacks.c.version == expected)
        with engine_begin() as conn:
            changed = conn.execute(stmt.values(**values, version=audio_playbacks.c.version + 1, updated_at=int(time.time()))).rowcount
        return self.get(playback_id) if changed else None
    def stop_package(self, campaign_id: str, package_id: str) -> None:
        with engine_begin() as conn: conn.execute(update(audio_playbacks).where(audio_playbacks.c.campaign_id == campaign_id, audio_playbacks.c.package_id == package_id, audio_playbacks.c.state != "stopped").values(state="stopped", version=audio_playbacks.c.version + 1, updated_at=int(time.time())))
    @staticmethod
    def _row(row):
        if not row: return None
        value = dict(row)
        for source, target in (("asset_json","asset"),("audience_json","audience"),("anchor_json","worldAnchor"),("fade_json","fade")):
            raw=value.pop(source); value[target]=json.loads(raw) if raw else None
        return value
