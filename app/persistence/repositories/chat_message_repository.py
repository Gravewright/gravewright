from __future__ import annotations

import json
import time
import uuid

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select

from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import chat_messages


class ChatMessageRepository:
    """Chat message persistence implemented with SQLAlchemy Core."""

    def _row_to_entry(self, row) -> dict:                
        entry = dict(row)
        entry["groups"] = json.loads(row["groups_json"]) if row["groups_json"] else []
        entry["metadata"] = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        return entry

    def create(
        self,
        *,
        message_id: str,
        campaign_id: str,
        author_user_id: str,
        author_name: str,
        author_role: str,
        kind: str,
        content: str | None,
        expression: str | None,
        groups: list[dict] | None,
        modifier: int | None,
        total: int | None,
        visibility: str,
        metadata: dict | None = None,
    ) -> None:
        now = int(time.time())
        groups_json = json.dumps(groups, ensure_ascii=False) if groups is not None else None
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else "{}"

        with engine_begin() as conn:
            conn.execute(
                insert(chat_messages).values(
                    id=message_id,
                    campaign_id=campaign_id,
                    author_user_id=author_user_id,
                    author_name=author_name,
                    author_role=author_role,
                    kind=kind,
                    content=content,
                    expression=expression,
                    groups_json=groups_json,
                    modifier=modifier,
                    total=total,
                    visibility=visibility,
                    metadata_json=metadata_json,
                    created_at=now,
                )
            )

    def list_for_campaign(self, *, campaign_id: str, limit: int = 50) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(chat_messages)
                    .where(chat_messages.c.campaign_id == campaign_id)
                    .order_by(chat_messages.c.created_at.desc())
                    .limit(limit)
                )
            )

        return [self._row_to_entry(row) for row in reversed(rows)]

    def get_for_campaign(self, *, campaign_id: str, message_id: str) -> dict | None:
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(chat_messages)
                    .where(chat_messages.c.campaign_id == campaign_id)
                    .where(chat_messages.c.id == message_id)
                    .limit(1)
                )
            )

        return self._row_to_entry(row) if row else None

    def delete_for_campaign(self, *, campaign_id: str, message_id: str) -> bool:
        with engine_begin() as conn:
            result = conn.execute(
                delete(chat_messages)
                .where(chat_messages.c.campaign_id == campaign_id)
                .where(chat_messages.c.id == message_id)
            )

        return result.rowcount > 0

    def delete_all_for_campaign(self, *, campaign_id: str) -> int:
        with engine_begin() as conn:
            result = conn.execute(
                delete(chat_messages).where(chat_messages.c.campaign_id == campaign_id)
            )

        return result.rowcount

    def generate_id(self) -> str:
        return uuid.uuid4().hex
