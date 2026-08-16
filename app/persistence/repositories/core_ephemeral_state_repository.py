from __future__ import annotations
import json
import time
import uuid
from sqlalchemy import delete, insert, select, update
from app.persistence.database import all_dicts, engine_begin
from app.persistence.tables import core_ephemeral_states as table

class CoreEphemeralStateRepository:
    MAX_PAYLOAD_BYTES = 16_384
    def _cleanup(self, conn, now: int) -> None:
        conn.execute(delete(table).where(table.c.expires_at <= now))

    def put(self, *, namespace: str, campaign_id: str, scope_id: str, owner_user_id: str,
            entry_key: str, audience: dict, payload: dict, ttl_seconds: int,
            expected_version: int | None = None) -> dict | None:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > self.MAX_PAYLOAD_BYTES or not 1 <= ttl_seconds <= 86_400:
            raise ValueError("ephemeral payload or ttl invalid")
        now = int(time.time()); expires = now + ttl_seconds
        with engine_begin() as conn:
            self._cleanup(conn, now)
            where = [table.c.namespace == namespace, table.c.campaign_id == campaign_id,
                     table.c.scope_id == scope_id, table.c.owner_user_id == owner_user_id,
                     table.c.entry_key == entry_key]
            current = conn.execute(select(table).where(*where).limit(1)).mappings().first()
            if current:
                if expected_version is not None and int(current["version"]) != expected_version:
                    return None
                conn.execute(update(table).where(table.c.id == current["id"]).values(
                    audience_json=json.dumps(audience), payload_json=encoded,
                    version=table.c.version + 1, updated_at=now, expires_at=expires))
                row_id = current["id"]
            else:
                if expected_version not in {None, 0}:
                    return None
                row_id = uuid.uuid4().hex
                conn.execute(insert(table).values(id=row_id, namespace=namespace, campaign_id=campaign_id,
                    scope_id=scope_id, owner_user_id=owner_user_id, entry_key=entry_key,
                    audience_json=json.dumps(audience), payload_json=encoded, version=1,
                    created_at=now, updated_at=now, expires_at=expires))
            row = conn.execute(select(table).where(table.c.id == row_id)).mappings().one()
        return self._hydrate(dict(row))

    def list_scope(self, *, namespace: str, campaign_id: str, scope_id: str) -> list[dict]:
        now = int(time.time())
        with engine_begin() as conn:
            self._cleanup(conn, now)
            rows = all_dicts(conn.execute(select(table).where(table.c.namespace == namespace,
                table.c.campaign_id == campaign_id, table.c.scope_id == scope_id).order_by(table.c.created_at)))
        return [self._hydrate(row) for row in rows]

    def delete(self, *, namespace: str, campaign_id: str, scope_id: str, owner_user_id: str,
               entry_key: str, expected_version: int | None = None) -> bool:
        with engine_begin() as conn:
            stmt = delete(table).where(table.c.namespace == namespace, table.c.campaign_id == campaign_id,
                table.c.scope_id == scope_id, table.c.owner_user_id == owner_user_id, table.c.entry_key == entry_key)
            if expected_version is not None: stmt = stmt.where(table.c.version == expected_version)
            return conn.execute(stmt).rowcount == 1

    def delete_owner_except_scope(self, *, namespace: str, campaign_id: str, owner_user_id: str, scope_id: str) -> None:
        with engine_begin() as conn:
            conn.execute(delete(table).where(table.c.namespace == namespace, table.c.campaign_id == campaign_id,
                table.c.owner_user_id == owner_user_id, table.c.scope_id != scope_id))
    def delete_scope(self, *, namespace: str, campaign_id: str, scope_id: str) -> None:
        with engine_begin() as conn:
            conn.execute(delete(table).where(table.c.namespace == namespace,table.c.campaign_id == campaign_id,table.c.scope_id == scope_id))

    @staticmethod
    def _hydrate(row: dict) -> dict:
        row["audience"] = json.loads(row.pop("audience_json")); row["payload"] = json.loads(row.pop("payload_json"))
        return row
