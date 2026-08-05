from __future__ import annotations

import time
import uuid

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import select

from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.tables import auth_attempts


class AuthAttemptRepository:
    def record(
        self,
        *,
        action: str,
        attempt_key: str,
        success: bool,
    ) -> None:
        with engine_begin() as connection:
            connection.execute(
                insert(auth_attempts).values(
                    id=uuid.uuid4().hex,
                    action=action,
                    attempt_key=attempt_key,
                    success=1 if success else 0,
                    created_at=int(time.time()),
                )
            )

    def count_failures_since(
        self,
        *,
        action: str,
        attempt_key: str,
        since: int,
    ) -> int:
        with engine_connect() as connection:
            return int(
                connection.execute(
                    select(func.count())
                    .select_from(auth_attempts)
                    .where(auth_attempts.c.action == action)
                    .where(auth_attempts.c.attempt_key == attempt_key)
                    .where(auth_attempts.c.success == 0)
                    .where(auth_attempts.c.created_at >= since)
                ).scalar_one()
            )

    def clear(
        self,
        *,
        action: str,
        attempt_key: str,
    ) -> None:
        with engine_begin() as connection:
            connection.execute(
                delete(auth_attempts)
                .where(auth_attempts.c.action == action)
                .where(auth_attempts.c.attempt_key == attempt_key)
            )

    def delete_old(self, older_than: int) -> None:
        with engine_begin() as connection:
            connection.execute(
                delete(auth_attempts).where(auth_attempts.c.created_at < older_than)
            )
