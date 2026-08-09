from __future__ import annotations

from sqlalchemy import delete, func, insert, select

from app.persistence.database import engine_begin, engine_connect
from app.persistence.tables import audit_events


class AuditEventRepository:
    def append(self, values: dict, *, connection=None) -> dict:
        if connection is not None:
            connection.execute(insert(audit_events).values(**values))
        else:
            with engine_begin() as own_connection:
                own_connection.execute(insert(audit_events).values(**values))
        return dict(values)

    def page(self, *, campaign_id: str, event_type: str | None, offset: int, limit: int) -> tuple[list[dict], int]:
        filters = [audit_events.c.campaign_id == campaign_id]
        if event_type:
            filters.append(audit_events.c.event_type == event_type)
        with engine_connect() as connection:
            total = int(connection.execute(select(func.count()).select_from(audit_events).where(*filters)).scalar_one())
            rows = [dict(row) for row in connection.execute(
                select(audit_events).where(*filters)
                .order_by(audit_events.c.created_at.desc(), audit_events.c.id.desc())
                .offset(offset).limit(limit)
            ).mappings()]
        return rows, total

    def prune_before(self, cutoff: int) -> int:
        with engine_begin() as connection:
            result = connection.execute(delete(audit_events).where(audit_events.c.created_at < cutoff))
        return int(result.rowcount or 0)
