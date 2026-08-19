"""Persistence for package-declared semantic definitions.

A registration is the package side of a semantic contract: the definition a
package declares once and core replays authoritatively afterwards.
"""

from __future__ import annotations

import json
import time
from sqlalchemy import delete, insert, select, update

from app.persistence.database import all_dicts, engine_begin
from app.persistence.tables import sdk_semantic_registrations


class SemanticRegistrationRepository:
    def put(self, campaign_id: str, package_id: str, registry: str, entry_id: str, definition: dict) -> dict:
        now = int(time.time()); encoded = json.dumps(definition, separators=(",", ":"), ensure_ascii=False)
        with engine_begin() as conn:
            where = (sdk_semantic_registrations.c.campaign_id == campaign_id, sdk_semantic_registrations.c.package_id == package_id,
                     sdk_semantic_registrations.c.registry == registry, sdk_semantic_registrations.c.entry_id == entry_id)
            row = conn.execute(select(sdk_semantic_registrations).where(*where)).mappings().first()
            if row: conn.execute(update(sdk_semantic_registrations).where(*where).values(definition_json=encoded, active=1, updated_at=now))
            else: conn.execute(insert(sdk_semantic_registrations).values(campaign_id=campaign_id, package_id=package_id, registry=registry, entry_id=entry_id, definition_json=encoded, active=1, created_at=now, updated_at=now))
        return self.get(campaign_id, package_id, registry, entry_id)

    def get(self, campaign_id: str, package_id: str, registry: str, entry_id: str) -> dict | None:
        with engine_begin() as conn:
            row = conn.execute(select(sdk_semantic_registrations).where(sdk_semantic_registrations.c.campaign_id == campaign_id, sdk_semantic_registrations.c.package_id == package_id, sdk_semantic_registrations.c.registry == registry, sdk_semantic_registrations.c.entry_id == entry_id, sdk_semantic_registrations.c.active == 1)).mappings().first()
        return self._row(row)

    def list(self, campaign_id: str, registry: str, package_id: str | None = None) -> list[dict]:
        stmt = select(sdk_semantic_registrations).where(sdk_semantic_registrations.c.campaign_id == campaign_id, sdk_semantic_registrations.c.registry == registry, sdk_semantic_registrations.c.active == 1)
        if package_id: stmt = stmt.where(sdk_semantic_registrations.c.package_id == package_id)
        with engine_begin() as conn: rows = all_dicts(conn.execute(stmt.order_by(sdk_semantic_registrations.c.package_id, sdk_semantic_registrations.c.entry_id)))
        return [self._row(row) for row in rows]

    def remove(self, campaign_id: str, package_id: str, registry: str, entry_id: str) -> bool:
        with engine_begin() as conn: return conn.execute(delete(sdk_semantic_registrations).where(sdk_semantic_registrations.c.campaign_id == campaign_id, sdk_semantic_registrations.c.package_id == package_id, sdk_semantic_registrations.c.registry == registry, sdk_semantic_registrations.c.entry_id == entry_id)).rowcount == 1

    def remove_package(self, campaign_id: str, package_id: str) -> None:
        with engine_begin() as conn: conn.execute(delete(sdk_semantic_registrations).where(sdk_semantic_registrations.c.campaign_id == campaign_id, sdk_semantic_registrations.c.package_id == package_id))

    @staticmethod
    def _row(row):
        if not row: return None
        value = dict(row); value["definition"] = json.loads(value.pop("definition_json")); return value
