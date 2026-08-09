from __future__ import annotations

import time
import uuid
from pathlib import Path

import pytest
from sqlalchemy import delete, inspect, insert, select, update
from sqlalchemy.exc import IntegrityError

import app.persistence.database as db_module
from app.persistence import engine as engine_module
from app.persistence.database import engine_begin, engine_connect
from app.persistence.tables import (
    campaign_join_code_redemptions,
    campaign_join_codes,
    campaigns,
)
from tests.conftest import seed_campaign, seed_user


def _code_values(*, campaign_id: str, user_id: str, suffix: str = "a", **overrides):
    now = int(time.time())
    values = {
        "id": uuid.uuid4().hex,
        "campaign_id": campaign_id,
        "code_hash": suffix * 64,
        "created_by_user_id": user_id,
        "role": "player",
        "max_uses": None,
        "use_count": 0,
        "expires_at": now + 3600,
        "revoked_at": None,
        "last_used_at": None,
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return values


def test_join_code_metadata_constraints_and_partial_active_index(db):
    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    first = _code_values(campaign_id=campaign_id, user_id=gm_id, suffix="a")
    with engine_begin() as connection:
        connection.execute(insert(campaign_join_codes).values(**first))

    with pytest.raises(IntegrityError):
        with engine_begin() as connection:
            connection.execute(
                insert(campaign_join_codes).values(
                    **_code_values(campaign_id=campaign_id, user_id=gm_id, suffix="b")
                )
            )

    with engine_begin() as connection:
        connection.execute(
            update(campaign_join_codes)
            .where(campaign_join_codes.c.id == first["id"])
            .values(revoked_at=int(time.time()))
        )
        connection.execute(
            insert(campaign_join_codes).values(
                **_code_values(campaign_id=campaign_id, user_id=gm_id, suffix="b")
            )
        )

    indexes = inspect(engine_module.get_engine()).get_indexes("campaign_join_codes")
    assert any(
        index["name"] == "uq_campaign_join_codes_active_campaign" and index["unique"]
        for index in indexes
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"role": "assistant_gm"},
        {"use_count": -1},
        {"max_uses": 0},
        {"max_uses": -1},
    ],
)
def test_join_code_checks_reject_invalid_values(db, overrides):
    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    with pytest.raises(IntegrityError):
        with engine_begin() as connection:
            connection.execute(
                insert(campaign_join_codes).values(
                    **_code_values(campaign_id=campaign_id, user_id=gm_id, **overrides)
                )
            )


def test_join_code_hash_and_redemption_uniques(db):
    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    first_campaign = seed_campaign(gm_id, title="First")
    second_campaign = seed_campaign(gm_id, title="Second")
    code = _code_values(campaign_id=first_campaign, user_id=gm_id)
    now = int(time.time())
    with engine_begin() as connection:
        connection.execute(insert(campaign_join_codes).values(**code))
        connection.execute(
            insert(campaign_join_code_redemptions).values(
                id=uuid.uuid4().hex,
                join_code_id=code["id"],
                campaign_id=first_campaign,
                user_id=player_id,
                redeemed_at=now,
            )
        )

    with pytest.raises(IntegrityError):
        with engine_begin() as connection:
            connection.execute(
                insert(campaign_join_codes).values(
                    **_code_values(campaign_id=second_campaign, user_id=gm_id)
                )
            )
    with pytest.raises(IntegrityError):
        with engine_begin() as connection:
            connection.execute(
                insert(campaign_join_code_redemptions).values(
                    id=uuid.uuid4().hex,
                    join_code_id=code["id"],
                    campaign_id=first_campaign,
                    user_id=player_id,
                    redeemed_at=now,
                )
            )


def test_campaign_delete_cascades_join_codes_and_redemptions(db):
    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    campaign_id = seed_campaign(gm_id)
    code = _code_values(campaign_id=campaign_id, user_id=gm_id)
    with engine_begin() as connection:
        connection.execute(insert(campaign_join_codes).values(**code))
        connection.execute(
            insert(campaign_join_code_redemptions).values(
                id=uuid.uuid4().hex,
                join_code_id=code["id"],
                campaign_id=campaign_id,
                user_id=player_id,
                redeemed_at=int(time.time()),
            )
        )
        connection.execute(delete(campaigns).where(campaigns.c.id == campaign_id))

    with engine_connect() as connection:
        assert connection.execute(select(campaign_join_codes.c.id)).first() is None
        assert connection.execute(select(campaign_join_code_redemptions.c.id)).first() is None


def test_join_code_migration_downgrade_and_reupgrade(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config

    db_path = tmp_path / "join-code-migration.sqlite3"
    monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)
    monkeypatch.setattr(db_module, "_initialized", False)
    engine_module.reset_engine()
    root = Path(__file__).resolve().parents[2]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))

    command.upgrade(cfg, "head")
    engine_module.reset_engine()
    engine = engine_module.get_engine()
    assert "campaign_join_codes" in inspect(engine).get_table_names()
    engine_module.reset_engine()

    command.downgrade(cfg, "0017_invitation_revoked_status")
    engine_module.reset_engine()
    engine = engine_module.get_engine()
    assert "campaign_join_codes" not in inspect(engine).get_table_names()
    engine_module.reset_engine()

    command.upgrade(cfg, "head")
    engine_module.reset_engine()
    engine = engine_module.get_engine()
    assert "campaign_join_codes" in inspect(engine).get_table_names()
    engine_module.reset_engine()


def test_join_code_migration_is_static():
    source = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / "versions"
        / "0018_campaign_join_codes.py"
    ).read_text(encoding="utf-8")
    assert "metadata.create_all" not in source
    assert "app.persistence.tables" not in source
