"""Opt-in smoke tests against real database backends.

STABILIZATION_V1 P1.2 classification: the two skips this module reports in a
default run are *legitimate external-dependency skips*, not dormant debt. Both
are gated on ``GRAVEWRIGHT_TEST_DATABASE_URLS``:

- ``test_sqlalchemy_core_schema_and_upsert_smoke`` is parametrized over the
  configured URLs; with none set the parameter set is empty and pytest skips it.
- ``test_database_backend_smoke_is_opt_in`` is the visible companion that always
  emits an explicit, reasoned skip when no URLs are configured, so the gating is
  never silent.

To actually exercise a backend (PostgreSQL is the V1 production target), set e.g.
``GRAVEWRIGHT_TEST_DATABASE_URLS=postgresql+psycopg://user:pass@host/db``.
"""

from __future__ import annotations

import os
import time
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy import delete
from sqlalchemy import inspect
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.engine import make_url

from app.persistence.engine import upsert_statement
from app.persistence.tables import campaigns
from app.persistence.tables import session_store
from app.persistence.tables import users


def _skip_if_dbapi_missing(database_url: str) -> None:
    url = make_url(database_url)
    backend = url.get_backend_name()
    driver = url.get_driver_name()

    module_by_driver = {
        "psycopg": "psycopg",
        "psycopg2": "psycopg2",
        "asyncpg": "asyncpg",
    }

    module_name = module_by_driver.get(driver)
    if module_name is None and backend == "postgresql":
        module_name = "psycopg"

    if module_name is not None:
        pytest.importorskip(module_name, reason=f"DBAPI driver required for {database_url!r}")


def _configured_urls() -> list[str]:
    raw = os.environ.get("GRAVEWRIGHT_TEST_DATABASE_URLS", "")
    return [url.strip() for url in raw.split(",") if url.strip()]


@pytest.mark.parametrize("database_url", _configured_urls())
def test_sqlalchemy_core_schema_and_upsert_smoke(database_url: str):
    """Opt-in smoke test for real PostgreSQL/MySQL/MariaDB/SQLite backends.

    Run with for example:
        GRAVEWRIGHT_TEST_DATABASE_URLS=postgresql+psycopg://... pytest tests/integration/test_database_backends.py -q

    Alembic must already have migrated the database. This test only inspects and
    exercises that schema; it never creates or repairs schema objects.
    """
    _skip_if_dbapi_missing(database_url)
    engine = create_engine(database_url, future=True)
    user_id = uuid.uuid4().hex
    campaign_id = uuid.uuid4().hex
    session_key = f"pytest:{uuid.uuid4().hex}"
    now = int(time.time())

    inspector = inspect(engine)
    assert {
        "users",
        "campaigns",
        "campaign_members",
        "campaign_invitations",
        "session_store",
        "scenes",
    } <= set(inspector.get_table_names())
    assert {column["name"] for column in inspector.get_columns("campaign_invitations")} >= {
        "campaign_id",
        "invited_user_id",
        "role",
        "status",
        "responded_at",
    }
    assert any(
        index["name"] == "idx_scenes_active_campaign" and index["unique"]
        for index in inspector.get_indexes("scenes")
    )
    member_uniques = {
        tuple(item["column_names"]) for item in inspector.get_unique_constraints("campaign_members")
    }
    assert ("campaign_id", "user_id") in member_uniques
    invitation_fks = {
        (tuple(item["constrained_columns"]), item["referred_table"])
        for item in inspector.get_foreign_keys("campaign_invitations")
    }
    assert (("campaign_id",), "campaigns") in invitation_fks
    assert (("invited_user_id",), "users") in invitation_fks
    invitation_checks = inspector.get_check_constraints("campaign_invitations")
    if invitation_checks:
        check_sql = " ".join(str(item["sqltext"]) for item in invitation_checks)
        assert "status" in check_sql
        assert "revoked" in check_sql

    with engine.begin() as conn:
        conn.execute(
            insert(users).values(
                id=user_id,
                name="Backend Smoke",
                email=f"backend-smoke-{user_id}@example.test",
                password_hash="not-a-real-password-hash",
                system_role="user",
                created_at=now,
                updated_at=now,
            )
        )
        conn.execute(
            insert(campaigns).values(
                id=campaign_id,
                owner_user_id=user_id,
                title="Backend Smoke Campaign",
                description="",
                active_system_id=None,
                initial_state_json="{}",
                persistent_state_json="{}",
                state_version=1,
                created_at=now,
                updated_at=now,
            )
        )

        conn.execute(
            upsert_statement(
                dialect_name=conn.dialect.name,
                table=session_store,
                values={
                    "key": session_key,
                    "value": b"first",
                    "expires_at": now + 3600,
                    "user_id": user_id,
                },
                index_elements=["key"],
                set_={
                    "value": b"second",
                    "expires_at": now + 7200,
                    "user_id": user_id,
                },
            )
        )
        conn.execute(
            upsert_statement(
                dialect_name=conn.dialect.name,
                table=session_store,
                values={
                    "key": session_key,
                    "value": b"third",
                    "expires_at": now + 10800,
                    "user_id": user_id,
                },
                index_elements=["key"],
                set_={
                    "value": b"third",
                    "expires_at": now + 10800,
                    "user_id": user_id,
                },
            )
        )

        row = conn.execute(
            select(session_store.c.value, session_store.c.expires_at).where(
                session_store.c.key == session_key
            )
        ).one()
        assert bytes(row.value) == b"third"
        assert row.expires_at == now + 10800

        conn.execute(
            update(campaigns)
            .where(campaigns.c.id == campaign_id)
            .values(title="Backend Smoke Updated")
        )
        assert (
            conn.execute(
                select(campaigns.c.title).where(campaigns.c.id == campaign_id)
            ).scalar_one()
            == "Backend Smoke Updated"
        )

        nested = conn.begin_nested()
        conn.execute(
            update(campaigns).where(campaigns.c.id == campaign_id).values(title="Must Roll Back")
        )
        nested.rollback()
        assert (
            conn.execute(
                select(campaigns.c.title).where(campaigns.c.id == campaign_id)
            ).scalar_one()
            == "Backend Smoke Updated"
        )

        conn.execute(delete(session_store).where(session_store.c.key == session_key))
        conn.execute(delete(campaigns).where(campaigns.c.id == campaign_id))
        conn.execute(delete(users).where(users.c.id == user_id))


@pytest.mark.skipif(_configured_urls(), reason="integration database URLs were configured")
def test_database_backend_smoke_is_opt_in():
    pytest.skip("Set GRAVEWRIGHT_TEST_DATABASE_URLS to run real backend smoke tests.")
