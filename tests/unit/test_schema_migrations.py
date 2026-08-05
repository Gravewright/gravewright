from __future__ import annotations

from sqlalchemy import inspect

import app.persistence.database as db_module
from app.persistence import engine as engine_module
from app.persistence.tables import metadata


CRITICAL_TABLES = {
    "users",
    "campaigns",
    "campaign_members",
    "actors_core",
    "tokens",
    "scenes",
    "scene_tiles",
    "scene_chunks",
    "journals",
    "items_core",
    "chat_messages",
    "session_store",
}


def test_database_startup_uses_sqlalchemy_metadata_schema(db):
    db_module.initialize_database()
    inspector = inspect(engine_module.get_engine())
    table_names = set(inspector.get_table_names())

    assert CRITICAL_TABLES.issubset(table_names)
    assert set(metadata.tables).issubset(table_names)


def test_metadata_has_named_constraints_for_migrations():
                                                                                
    assert metadata.naming_convention
    assert "pk" in metadata.naming_convention
    assert "fk" in metadata.naming_convention
    assert "uq" in metadata.naming_convention
