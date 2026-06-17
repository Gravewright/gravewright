from __future__ import annotations

import time
import uuid

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update

from app.domain.roles import SystemRole
from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import users


class UserRepository:
    def count(self) -> int:
        with engine_connect() as connection:
            return int(connection.execute(select(func.count()).select_from(users)).scalar_one())

    def count_owners(self) -> int:
        with engine_connect() as connection:
            return int(
                connection.execute(
                    select(func.count())
                    .select_from(users)
                    .where(users.c.system_role == SystemRole.OWNER.value)
                ).scalar_one()
            )

    def list_all(self) -> list[dict]:
        with engine_connect() as connection:
            return all_dicts(
                connection.execute(
                    select(users).order_by(users.c.created_at.asc(), users.c.name.asc())
                )
            )

    def get_by_id(self, user_id: str) -> dict | None:
        with engine_connect() as connection:
            return one_or_none(
                connection.execute(select(users).where(users.c.id == user_id).limit(1))
            )

    def get_by_email(self, email: str) -> dict | None:
        with engine_connect() as connection:
            return one_or_none(
                connection.execute(select(users).where(users.c.email == email).limit(1))
            )

    def create_with_auto_role(
        self,
        *,
        name: str,
        email: str,
        password_hash: str,
    ) -> dict:
        now = int(time.time())
        user_id = uuid.uuid4().hex

        with engine_begin() as connection:
                                                                      
            existing = connection.execute(select(func.count()).select_from(users)).scalar_one()
            system_role = SystemRole.OWNER if int(existing) == 0 else SystemRole.USER

            connection.execute(
                insert(users).values(
                    id=user_id,
                    name=name,
                    email=email,
                    password_hash=password_hash,
                    system_role=system_role.value,
                    created_at=now,
                    updated_at=now,
                )
            )

            return one_or_none(
                connection.execute(select(users).where(users.c.id == user_id).limit(1))
            )

    def update_password(
        self,
        *,
        user_id: str,
        password_hash: str,
    ) -> None:
        now = int(time.time())
        with engine_begin() as connection:
            connection.execute(
                update(users)
                .where(users.c.id == user_id)
                .values(password_hash=password_hash, updated_at=now)
            )

    def delete(self, *, user_id: str) -> None:
                                                                       
        with engine_begin() as connection:
            connection.execute(delete(users).where(users.c.id == user_id))
