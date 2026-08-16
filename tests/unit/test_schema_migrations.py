from __future__ import annotations

import ast
from pathlib import Path

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


# ``0001_initial_schema`` cria o schema inteiro de uma vez; a partir dele toda
# migracao aditiva precisa ser reentrante, porque ``test_schema_legacy_upgrade``
# roda ``upgrade head`` sobre um banco que ja tem os objetos mais novos. A
# convencao foi seguida ate a 0016 e depois abandonada por nove revisoes seguidas
# sem que nada acusasse: este teste e o que acusa.
_UNGUARDED_BASELINE = {"0001_initial_schema"}


def _creating_migrations():
    versions = Path(__file__).resolve().parents[2] / "migrations" / "versions"
    for path in sorted(versions.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        if {"create_table", "add_column"} & calls:
            yield path.stem, calls, names


def test_additive_migrations_are_reentrant():
    missing = []
    for stem, calls, names in _creating_migrations():
        if stem in _UNGUARDED_BASELINE:
            continue
        # a guarda pode ser um helper local ou a inspecao direta do bind
        guarded = ("_has_table" in names or "_has_column" in names
                   or {"get_table_names", "get_columns"} & calls)
        if not guarded:
            missing.append(stem)

    assert not missing, (
        "migracoes aditivas sem guarda de reentrancia (ver _has_table em "
        f"0009_cards_system): {missing}"
    )


def test_alembic_revision_ids_fit_the_version_table_limit():
    versions = Path(__file__).resolve().parents[2] / "migrations" / "versions"
    oversized = []
    for path in sorted(versions.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(
                isinstance(target, ast.Name) and target.id == "revision"
                for target in node.targets
            ):
                continue
            revision = ast.literal_eval(node.value)
            if isinstance(revision, str) and len(revision) > 32:
                oversized.append((path.name, revision))

    assert not oversized, f"Alembic revision IDs exceed varchar(32): {oversized}"
