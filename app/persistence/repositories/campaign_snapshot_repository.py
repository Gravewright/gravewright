from __future__ import annotations

from sqlalchemy import delete, insert, select

from app.persistence.database import engine_begin, engine_connect, one_or_none
from app.persistence.tables import campaign_snapshots


class CampaignSnapshotRepository:
    def create(self, values: dict, *, connection=None) -> dict:
        if connection is not None:
            connection.execute(insert(campaign_snapshots).values(**values))
            return dict(values)
        with engine_begin() as own_connection:
            own_connection.execute(insert(campaign_snapshots).values(**values))
        return dict(values)

    def get(self, snapshot_id: str, *, connection=None) -> dict | None:
        statement = select(campaign_snapshots).where(campaign_snapshots.c.id == snapshot_id)
        if connection is not None:
            return one_or_none(connection.execute(statement))
        with engine_connect() as own_connection:
            return one_or_none(own_connection.execute(statement))

    def list_for_campaign(self, campaign_id: str) -> list[dict]:
        with engine_connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(campaign_snapshots)
                    .where(campaign_snapshots.c.campaign_id == campaign_id)
                    .order_by(campaign_snapshots.c.created_at.desc())
                ).mappings()
            ]

    def delete(self, snapshot_id: str, campaign_id: str) -> bool:
        with engine_begin() as connection:
            result = connection.execute(
                delete(campaign_snapshots)
                .where(campaign_snapshots.c.id == snapshot_id)
                .where(campaign_snapshots.c.campaign_id == campaign_id)
            )
        return bool(result.rowcount)

    def prune(self, campaign_id: str, keep: int, *, connection) -> int:
        stale_ids = list(
            connection.execute(
                select(campaign_snapshots.c.id)
                .where(campaign_snapshots.c.campaign_id == campaign_id)
                .order_by(campaign_snapshots.c.created_at.desc())
                .offset(keep)
            ).scalars()
        )
        if not stale_ids:
            return 0
        return int(
            connection.execute(
                delete(campaign_snapshots).where(campaign_snapshots.c.id.in_(stale_ids))
            ).rowcount
            or 0
        )
