from __future__ import annotations

import time
import uuid

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update

from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import password_reset_tokens


class PasswordResetRepository:
    def create(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: int,
    ) -> dict:
        now = int(time.time())
        reset_id = uuid.uuid4().hex

        with engine_begin() as connection:
            connection.execute(
                insert(password_reset_tokens).values(
                    id=reset_id,
                    user_id=user_id,
                    token_hash=token_hash,
                    created_at=now,
                    expires_at=expires_at,
                    used_at=None,
                )
            )

            return one_or_none(
                connection.execute(
                    select(password_reset_tokens)
                    .where(password_reset_tokens.c.id == reset_id)
                    .limit(1)
                )
            )

    def get_valid_by_hash(self, token_hash: str) -> dict | None:
        now = int(time.time())

        with engine_connect() as connection:
            return one_or_none(
                connection.execute(
                    select(password_reset_tokens)
                    .where(password_reset_tokens.c.token_hash == token_hash)
                    .where(password_reset_tokens.c.used_at.is_(None))
                    .where(password_reset_tokens.c.expires_at > now)
                    .limit(1)
                )
            )

    def mark_used(self, reset_id: str) -> None:
        now = int(time.time())
        with engine_begin() as connection:
            connection.execute(
                update(password_reset_tokens)
                .where(password_reset_tokens.c.id == reset_id)
                .values(used_at=now)
            )

    def delete_expired(self) -> None:
        now = int(time.time())
        with engine_begin() as connection:
            connection.execute(
                delete(password_reset_tokens).where(
                    or_(
                        password_reset_tokens.c.expires_at <= now,
                        password_reset_tokens.c.used_at.is_not(None),
                    )
                )
            )
