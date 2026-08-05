"""SQLAlchemy Core implementation of Litestar's :class:`Store`.

Keeps server-side session data in the configured Gravewright database so
sessions survive restarts without an extra service like Redis. The store uses
portable Core statements instead of SQLite-specific SQL so it works with the
configured SQLite, PostgreSQL or MySQL backend.
"""

from __future__ import annotations

import json
import time
from datetime import timedelta

from litestar.stores.base import Store
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import update

from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import session_store as session_store_table


def _user_id_of(value: bytes) -> str | None:
    """Return the serialized session's ``user_id`` when present.

    Litestar serializes session data as JSON; storing this denormalized value
    lets the auth layer invalidate every session belonging to a user after
    security-sensitive actions such as password reset.
    """
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError, UnicodeDecodeError):
        return None
    return parsed.get("user_id") if isinstance(parsed, dict) else None


def _seconds(value: int | timedelta | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, timedelta):
        return int(value.total_seconds())
    return int(value)


class SQLiteStore(Store):
    """A Litestar ``Store`` over the ``session_store`` table.

    The class name is kept for compatibility with the existing auth/session
    wiring, but the implementation is backend-agnostic SQLAlchemy Core.
    """

    async def set(self, key: str, value: str | bytes, expires_in: int | timedelta | None = None) -> None:
        data = value.encode() if isinstance(value, str) else value
        ttl = _seconds(expires_in)
        expires_at = int(time.time()) + ttl if ttl is not None else None
        user_id = _user_id_of(data)
        values = {
            "key": key,
            "value": data,
            "expires_at": expires_at,
            "user_id": user_id,
        }

        with engine_begin() as connection:
            statement = upsert_statement(
                dialect_name=connection.dialect.name,
                table=session_store_table,
                values=values,
                index_elements=[session_store_table.c.key],
                set_={
                    "value": data,
                    "expires_at": expires_at,
                    "user_id": user_id,
                },
            )
            connection.execute(statement)

    @staticmethod
    def delete_user_sessions(user_id: str) -> None:
        """Synchronously drop every session belonging to a user."""
        with engine_begin() as connection:
            connection.execute(
                delete(session_store_table).where(session_store_table.c.user_id == user_id)
            )

    async def get(self, key: str, renew_for: int | timedelta | None = None) -> bytes | None:
        now = int(time.time())
        with engine_begin() as connection:
            row = (
                connection.execute(
                    select(session_store_table.c.value, session_store_table.c.expires_at)
                    .where(session_store_table.c.key == key)
                    .limit(1)
                )
                .mappings()
                .first()
            )
            if row is None:
                return None

            expires_at = row["expires_at"]
            if expires_at is not None and int(expires_at) <= now:
                connection.execute(
                    delete(session_store_table).where(session_store_table.c.key == key)
                )
                return None

            if renew_for is not None and expires_at is not None:
                renewal_seconds = _seconds(renew_for)
                connection.execute(
                    update(session_store_table)
                    .where(session_store_table.c.key == key)
                    .values(expires_at=now + renewal_seconds)
                )

            value = row["value"]
            return bytes(value) if isinstance(value, memoryview) else value

    async def delete(self, key: str) -> None:
        with engine_begin() as connection:
            connection.execute(delete(session_store_table).where(session_store_table.c.key == key))

    async def delete_all(self) -> None:
        with engine_begin() as connection:
            connection.execute(delete(session_store_table))

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None

    async def expires_in(self, key: str) -> int | None:
        now = int(time.time())
        with engine_connect() as connection:
            row = (
                connection.execute(
                    select(session_store_table.c.expires_at)
                    .where(session_store_table.c.key == key)
                    .limit(1)
                )
                .mappings()
                .first()
            )
        if row is None or row["expires_at"] is None:
            return None
        return max(0, int(row["expires_at"]) - now)
