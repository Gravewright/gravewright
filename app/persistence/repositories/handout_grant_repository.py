from __future__ import annotations

import time
import uuid

from sqlalchemy import and_, or_, select, update

from app.persistence.database import engine_begin, engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import handout_grants


class HandoutGrantRepository:
    def grant(self, *, campaign_id: str, resource_type: str, resource_id: str,
              subject_type: str, subject_id: str, created_by_user_id: str) -> dict:
        now = int(time.time())
        values = {
            "id": uuid.uuid4().hex,
            "campaign_id": campaign_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "created_by_user_id": created_by_user_id,
            "created_at": now,
            "revoked_at": None,
        }
        with engine_begin() as connection:
            statement = upsert_statement(
                dialect_name=connection.dialect.name,
                table=handout_grants,
                values=values,
                index_elements=[
                    handout_grants.c.campaign_id,
                    handout_grants.c.resource_type,
                    handout_grants.c.resource_id,
                    handout_grants.c.subject_type,
                    handout_grants.c.subject_id,
                ],
                set_={
                    "created_by_user_id": created_by_user_id,
                    "created_at": now,
                    "revoked_at": None,
                },
            )
            connection.execute(statement)
            row = connection.execute(
                select(handout_grants).where(
                    handout_grants.c.campaign_id == campaign_id,
                    handout_grants.c.resource_type == resource_type,
                    handout_grants.c.resource_id == resource_id,
                    handout_grants.c.subject_type == subject_type,
                    handout_grants.c.subject_id == subject_id,
                )
            ).mappings().one()
        return dict(row)

    def revoke(self, *, grant_id: str, campaign_id: str) -> dict | None:
        now = int(time.time())
        with engine_begin() as connection:
            row = connection.execute(
                select(handout_grants).where(
                    handout_grants.c.id == grant_id,
                    handout_grants.c.campaign_id == campaign_id,
                )
            ).mappings().first()
            if row is None:
                return None
            connection.execute(
                update(handout_grants)
                .where(handout_grants.c.id == grant_id)
                .values(revoked_at=now)
            )
        result = dict(row)
        result["revoked_at"] = now
        return result

    def list_active(self, *, campaign_id: str, resource_type: str, resource_id: str) -> list[dict]:
        with engine_connect() as connection:
            return [dict(row) for row in connection.execute(
                select(handout_grants).where(
                    handout_grants.c.campaign_id == campaign_id,
                    handout_grants.c.resource_type == resource_type,
                    handout_grants.c.resource_id == resource_id,
                    handout_grants.c.revoked_at.is_(None),
                ).order_by(handout_grants.c.created_at.asc())
            ).mappings()]

    def can_view(self, *, campaign_id: str, resource_type: str, resource_id: str,
                 user_id: str, role: str) -> bool:
        with engine_connect() as connection:
            row = connection.execute(
                select(handout_grants.c.id).where(
                    handout_grants.c.campaign_id == campaign_id,
                    handout_grants.c.resource_type == resource_type,
                    handout_grants.c.resource_id == resource_id,
                    handout_grants.c.revoked_at.is_(None),
                    or_(
                        handout_grants.c.subject_type == "everyone",
                        and_(handout_grants.c.subject_type == "user", handout_grants.c.subject_id == user_id),
                        and_(handout_grants.c.subject_type == "role", handout_grants.c.subject_id == role),
                    ),
                ).limit(1)
            ).first()
        return row is not None

    def list_accessible(self, *, campaign_id: str, user_id: str, role: str) -> list[dict]:
        with engine_connect() as connection:
            rows = connection.execute(
                select(handout_grants).where(
                    handout_grants.c.campaign_id == campaign_id,
                    handout_grants.c.revoked_at.is_(None),
                    or_(
                        handout_grants.c.subject_type == "everyone",
                        and_(
                            handout_grants.c.subject_type == "user",
                            handout_grants.c.subject_id == user_id,
                        ),
                        and_(
                            handout_grants.c.subject_type == "role",
                            handout_grants.c.subject_id == role,
                        ),
                    ),
                ).order_by(handout_grants.c.created_at.desc())
            ).mappings()
            return [dict(row) for row in rows]
