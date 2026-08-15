"""enum check constraints for membership, invitations and permission effect

Revision ID: 0016_enum_check_constraints
Revises: 0015_journal_assets_folder_id
Create Date: 2026-08-04

Adds portable CHECK constraints so the database rejects out-of-domain values in
priority enum columns even when a service validation is bypassed (maintenance
plan, Etapa 6). Before applying, it audits existing rows and refuses to run if it
finds values outside the allowed set: it never silently coerces unknown values.

The value sets are a point-in-time snapshot of the domain enums
(``PlayerRole``, ``InvitationStatus`` in ``app.domain.campaigns``, and
``PermissionEffect``); ``tests/unit/test_enum_constraints.py`` guards that the
live enums and the database still agree.
"""

from __future__ import annotations

from alembic import op

revision = "0016_enum_check_constraints"
down_revision = "0015_journal_assets_folder_id"
branch_labels = None
depends_on = None

# (table, column, constraint_name, allowed_values)
_CHECKS = [
    (
        "campaign_members",
        "role",
        "ck_campaign_members_role",
        ("gm", "assistant_gm", "player", "streamer"),
    ),
    (
        "campaign_invitations",
        "role",
        "ck_campaign_invitations_role",
        ("gm", "assistant_gm", "player", "streamer"),
    ),
    (
        "campaign_invitations",
        "status",
        "ck_campaign_invitations_status",
        ("pending", "accepted", "declined"),
    ),
    (
        "campaign_permission_overrides",
        "effect",
        "ck_campaign_permission_overrides_effect",
        ("allow", "deny"),
    ),
]


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    allowed = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({allowed})"


def _audit_or_fail(bind) -> None:
    from sqlalchemy import inspect, text

    existing_tables = set(inspect(bind).get_table_names())
    problems: list[str] = []
    for table, column, _name, values in _CHECKS:
        if table not in existing_tables:
            continue
        allowed = ", ".join(f"'{value}'" for value in values)
        rows = bind.execute(
            text(
                f"SELECT DISTINCT {column} AS value FROM {table} WHERE {column} NOT IN ({allowed})"
            )
        ).fetchall()
        bad = [row.value for row in rows]
        if bad:
            problems.append(f"{table}.{column}: {sorted(bad)}")

    if problems:
        raise RuntimeError(
            "Refusing to add enum CHECK constraints: found out-of-domain values. "
            "Fix or migrate these rows manually first (no automatic coercion):\n  "
            + "\n  ".join(problems)
        )


def upgrade() -> None:
    bind = op.get_bind()
    _audit_or_fail(bind)
    for table, column, name, values in _CHECKS:
        with op.batch_alter_table(table) as batch:
            batch.create_check_constraint(name, _in_clause(column, values))


def downgrade() -> None:
    for table, _column, name, _values in _CHECKS:
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(name, type_="check")
