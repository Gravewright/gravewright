from __future__ import annotations

"""Enum CHECK constraints (Maintenance Plan - Etapa 6).

The database must reject out-of-domain values for the priority enum columns even
when a service validation is bypassed, and the allowed set must stay aligned with
the domain enums. Also verifies the migration's legacy-data audit refuses to run
against invalid rows instead of silently coercing them.
"""

import re
import time
import uuid
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, create_engine
from sqlalchemy.exc import IntegrityError

import app.persistence.database as db_module
from app.domain.campaigns import InvitationStatus
from app.domain.permissions.permissions import PermissionEffect
from app.domain.roles import PlayerRole
from app.persistence import engine as engine_module
from app.persistence.database import engine_begin
from app.persistence.tables import (
    campaign_invitations,
    campaign_members,
    campaign_permission_overrides,
)
from tests.conftest import seed_campaign, seed_user


def _seed_owner_and_campaign() -> tuple[str, str]:
    gm_id = seed_user(name="GM", email=f"gm-{uuid.uuid4().hex[:6]}@test.com")
    campaign_id = seed_campaign(gm_id)
    return gm_id, campaign_id


def _insert_member(campaign_id: str, user_id: str, role: str) -> None:
    now = int(time.time())
    with engine_begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO campaign_members (id, campaign_id, user_id, role, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, campaign_id, user_id, role, now, now),
        )


def test_member_role_rejects_out_of_domain_value(db):
    _, campaign_id = _seed_owner_and_campaign()
    player_id = seed_user(name="P", email="p-role@test.com")

    _insert_member(campaign_id, player_id, "player")  # valid → OK
    with engine_begin() as conn:  # clean slate for the invalid attempt
        conn.exec_driver_sql("DELETE FROM campaign_members WHERE user_id = ?", (player_id,))
    with pytest.raises(IntegrityError):
        _insert_member(campaign_id, player_id, "wizard")


def test_invitation_status_and_role_reject_out_of_domain(db):
    gm_id, campaign_id = _seed_owner_and_campaign()
    player_id = seed_user(name="P", email="p-inv@test.com")
    now = int(time.time())

    def insert_invitation(*, role: str, status: str) -> None:
        with engine_begin() as conn:
            conn.exec_driver_sql(
                "INSERT INTO campaign_invitations "
                "(id, campaign_id, invited_user_id, invited_by_user_id, role, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, campaign_id, player_id, gm_id, role, status, now, now),
            )

    insert_invitation(role="player", status="pending")  # valid → OK
    with pytest.raises(IntegrityError):
        insert_invitation(role="player", status="ghosted")
    with pytest.raises(IntegrityError):
        insert_invitation(role="overlord", status="pending")


def test_permission_effect_rejects_out_of_domain(db):
    _, campaign_id = _seed_owner_and_campaign()
    now = int(time.time())

    def insert_override(effect: str) -> None:
        with engine_begin() as conn:
            conn.exec_driver_sql(
                "INSERT INTO campaign_permission_overrides "
                "(id, campaign_id, subject_type, subject_id, permission_key, effect, created_at, updated_at) "
                "VALUES (?, ?, 'user', 's', 'k', ?, ?, ?)",
                (uuid.uuid4().hex, campaign_id, effect, now, now),
            )

    insert_override("deny")  # valid → OK
    with pytest.raises(IntegrityError):
        insert_override("maybe")


# --- allowed set stays aligned with the domain enums ---------------------------

def _check_allowed_values(table, column: str) -> set[str]:
    for constraint in table.constraints:
        if isinstance(constraint, CheckConstraint):
            sqltext = str(constraint.sqltext)
            if sqltext.startswith(f"{column} IN"):
                return set(re.findall(r"'([^']+)'", sqltext))
    raise AssertionError(f"no CHECK constraint on {table.name}.{column}")


@pytest.mark.parametrize(
    "table, column, enum",
    [
        (campaign_members, "role", PlayerRole),
        (campaign_invitations, "role", PlayerRole),
        (campaign_invitations, "status", InvitationStatus),
        (campaign_permission_overrides, "effect", PermissionEffect),
    ],
)
def test_check_constraint_matches_domain_enum(table, column, enum):
    assert _check_allowed_values(table, column) == {member.value for member in enum}


# --- migration path enforces the same constraints ------------------------------

def test_alembic_head_enforces_member_role_check(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config

    db_path = tmp_path / "head.sqlite3"
    monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)
    monkeypatch.setattr(db_module, "_initialized", False)
    engine_module.reset_engine()

    project_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(project_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(project_root / "migrations"))
    command.upgrade(cfg, "head")
    engine_module.reset_engine()

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    now = int(time.time())
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "INSERT INTO users (id, name, email, password_hash, system_role, created_at, updated_at) "
                "VALUES ('u', 'n', 'e@test', 'h', 'user', ?, ?)",
                (now, now),
            )
            conn.exec_driver_sql(
                "INSERT INTO campaigns (id, owner_user_id, title, description, initial_state_json, "
                "persistent_state_json, state_version, created_at, updated_at) "
                "VALUES ('c', 'u', 't', '', '{}', '{}', 1, ?, ?)",
                (now, now),
            )
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.exec_driver_sql(
                    "INSERT INTO campaign_members (id, campaign_id, user_id, role, created_at, updated_at) "
                    "VALUES ('m', 'c', 'u', 'wizard', ?, ?)",
                    (now, now),
                )

        # Revoking a pending invitation is a first-class state at head (Etapa 1).
        def insert_invitation(invitation_id: str, status: str) -> None:
            with engine.begin() as conn:
                conn.exec_driver_sql(
                    "INSERT INTO campaign_invitations (id, campaign_id, invited_user_id, "
                    "invited_by_user_id, role, status, created_at, updated_at) "
                    "VALUES (?, 'c', 'u', 'u', 'player', ?, ?, ?)",
                    (invitation_id, status, now, now),
                )

        insert_invitation("i-revoked", "revoked")
        with pytest.raises(IntegrityError):
            insert_invitation("i-bogus", "rescinded")
    finally:
        engine.dispose()


# --- migration audit refuses invalid legacy data -------------------------------

def test_migration_audit_raises_on_out_of_domain_rows(tmp_path):
    # Build a campaign_members table WITHOUT the check and insert a bad row, then
    # confirm the migration's audit refuses to proceed (no silent coercion).
    import importlib.util

    mig_path = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / "versions"
        / "0016_enum_check_constraints.py"
    )
    spec = importlib.util.spec_from_file_location("mig_0016", mig_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    engine = create_engine(f"sqlite:///{(tmp_path / 'legacy.sqlite3').as_posix()}")
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "CREATE TABLE campaign_members (id TEXT PRIMARY KEY, campaign_id TEXT, "
                "user_id TEXT, role TEXT, created_at INT, updated_at INT)"
            )
            conn.exec_driver_sql(
                "INSERT INTO campaign_members VALUES ('m', 'c', 'u', 'wizard', 0, 0)"
            )
        with engine.connect() as conn:
            with pytest.raises(RuntimeError, match="out-of-domain"):
                module._audit_or_fail(conn)
    finally:
        engine.dispose()
