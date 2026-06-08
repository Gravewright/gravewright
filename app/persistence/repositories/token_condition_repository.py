from __future__ import annotations

import time
import uuid

from sqlalchemy import delete
from sqlalchemy import select

from app.domain.tokens import TokenConditionKind
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import token_conditions


class TokenConditionRepository:
    def add(
        self,
        *,
        token_id: str,
        condition_id: str,
        label: str,
        icon: str | None = None,
        duration: int | None = None,
        source: str | None = None,
        kind: str = TokenConditionKind.NEUTRAL,
        visible_to: str = "everyone",
    ) -> dict:
        now = int(time.time())
        values = {
            "id": uuid.uuid4().hex,
            "token_id": token_id,
            "condition_id": condition_id,
            "label": label,
            "icon": icon,
            "duration": duration,
            "source": source,
            "kind": kind,
            "visible_to": visible_to,
            "created_at": now,
        }

        with engine_begin() as conn:
            conn.execute(
                upsert_statement(
                    dialect_name=conn.dialect.name,
                    table=token_conditions,
                    values=values,
                    index_elements=[token_conditions.c.token_id, token_conditions.c.condition_id],
                    set_={
                        "label": label,
                        "icon": icon,
                        "duration": duration,
                        "source": source,
                        "kind": kind,
                        "visible_to": visible_to,
                    },
                )
            )
            row = (
                conn.execute(
                    select(token_conditions)
                    .where(token_conditions.c.token_id == token_id)
                    .where(token_conditions.c.condition_id == condition_id)
                    .limit(1)
                )
                .mappings()
                .first()
            )

        return dict(row)

    def remove(self, *, token_id: str, condition_id: str) -> bool:
        with engine_begin() as conn:
            cursor = conn.execute(
                delete(token_conditions)
                .where(token_conditions.c.token_id == token_id)
                .where(token_conditions.c.condition_id == condition_id)
            )

        return cursor.rowcount > 0

    def list_by_token(self, token_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = (
                conn.execute(
                    select(token_conditions)
                    .where(token_conditions.c.token_id == token_id)
                    .order_by(token_conditions.c.created_at.asc())
                )
                .mappings()
                .all()
            )

        return [dict(r) for r in rows]

    def list_by_tokens(self, token_ids: list[str]) -> dict[str, list[dict]]:
        """Return {token_id: [conditions]} for all given token_ids in one query."""
        if not token_ids:
            return {}

        with engine_connect() as conn:
            rows = (
                conn.execute(
                    select(token_conditions)
                    .where(token_conditions.c.token_id.in_(token_ids))
                    .order_by(token_conditions.c.created_at.asc())
                )
                .mappings()
                .all()
            )

        result: dict[str, list[dict]] = {tid: [] for tid in token_ids}
        for row in rows:
            r = dict(row)
            result[r["token_id"]].append(r)

        return result
