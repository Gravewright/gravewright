"""Phase 7A — storage contract (validation only, no runtime).

Validates the manifest ``storage.sqlite`` declaration, the declared migrations
directory, and the named-queries file (type/params/sql), with parameters
whitelisted per query. No database is opened and no query is executed here.
"""

from __future__ import annotations

import inspect
import json

from app.engine.sdk.package_loader import load_package
from app.engine.sdk.package_manifest_validator import validate_manifest
from app.engine.sdk.package_storage import (
    validate_named_queries,
    validate_storage_manifest,
)


def _manifest(**overrides) -> dict:
    manifest = {
        "schemaVersion": 1,
        "sdkVersion": "1",
        "kind": "addon",
        "id": "store-addon",
        "name": "Store Addon",
        "version": "0.1.0",
        "compatibility": {"minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1", "maximum": "1.x"},
        "capabilities": ["storage.sqlite"],
        "activation": {"scope": "campaign", "mode": "multiple"},
        "entrypoints": {},
        "provides": {},
        "storage": {
            "sqlite": {
                "status": "experimental",
                "scopes": ["campaign", "global"],
                "migrations": "storage/sqlite/migrations",
                "queries": "storage/sqlite/queries.json",
            }
        },
    }
    manifest.update(overrides)
    return manifest


_GOOD_QUERIES = {
    "queries": {
        "getState": {
            "type": "read",
            "params": {"key": "string"},
            "sql": "SELECT value_json FROM addon_state WHERE key = :key LIMIT 1",
        },
        "saveState": {
            "type": "write",
            "params": {"key": "string", "value_json": "json-string", "updated_at": "integer"},
            "sql": "INSERT INTO addon_state (key, value_json, updated_at) VALUES (:key, :value_json, :updated_at)",
        },
    }
}


# --- manifest declaration ----------------------------------------------------


def test_storage_sqlite_capability_requires_storage_block():
    raw = _manifest()
    del raw["storage"]
    assert "sdk.storage.declaration_invalid" in validate_storage_manifest(raw)
    # And it surfaces through the full validator.
    assert "sdk.storage.declaration_invalid" in validate_manifest(raw).errors


def test_storage_sqlite_storage_block_requires_capability():
    raw = _manifest(capabilities=["assets.scripts"])
    assert "sdk.storage.capability_missing" in validate_storage_manifest(raw)


def test_storage_migrations_path_must_be_safe():
    raw = _manifest()
    raw["storage"]["sqlite"]["migrations"] = "../escape"
    assert "sdk.storage.migration_path_unsafe" in validate_storage_manifest(raw)


def test_storage_queries_path_must_be_safe():
    raw = _manifest()
    raw["storage"]["sqlite"]["queries"] = "/etc/passwd"
    assert "sdk.storage.queries_path_unsafe" in validate_storage_manifest(raw)


def test_storage_scopes_must_be_known():
    raw = _manifest()
    raw["storage"]["sqlite"]["scopes"] = ["campaign", "actor"]
    assert "sdk.storage.declaration_invalid" in validate_storage_manifest(raw)


# --- named queries -----------------------------------------------------------


def test_storage_named_query_requires_type_params_and_sql():
    assert validate_named_queries(_GOOD_QUERIES) == []
    missing = {"queries": {"q": {"type": "read"}}}
    codes = validate_named_queries(missing)
    assert "sdk.storage.sqlite.query_missing_params" in codes
    assert "sdk.storage.sqlite.query_sql_missing" in codes


def test_storage_named_query_rejects_invalid_type():
    bad = {"queries": {"q": {"type": "delete-all", "params": {}, "sql": "SELECT 1"}}}
    assert "sdk.storage.sqlite.query_invalid_type" in validate_named_queries(bad)


def test_storage_named_query_rejects_invalid_param_type():
    bad = {
        "queries": {
            "q": {"type": "read", "params": {"key": "blob"}, "sql": "SELECT 1 WHERE x = :key"}
        }
    }
    assert "sdk.storage.sqlite.query_param_invalid_type" in validate_named_queries(bad)


def test_storage_named_query_rejects_disallowed_sql():
    multi = {
        "queries": {
            "q": {"type": "read", "params": {}, "sql": "SELECT 1; DROP TABLE addon_state"}
        }
    }
    assert "sdk.storage.sqlite.query_sql_disallowed" in validate_named_queries(multi)
    wrong_verb = {
        "queries": {"q": {"type": "read", "params": {}, "sql": "DELETE FROM addon_state"}}
    }
    assert "sdk.storage.sqlite.query_sql_disallowed" in validate_named_queries(wrong_verb)


def test_storage_contract_rejects_client_defined_queries():
    # The contract loads named queries only from disk: there is no API surface to
    # inject a query set or raw SQL from a client payload.
    params = set(inspect.signature(validate_named_queries).parameters)
    assert params == {"data"}  # a single parsed-file argument, no "sql"/"payload" source

    from app.engine.sdk import package_loader

    loader_params = set(inspect.signature(package_loader.load_package).parameters)
    assert "queries" not in loader_params
    assert "sql" not in loader_params


# --- loader / disk integration ----------------------------------------------


def _write_package(root, *, queries=_GOOD_QUERIES, with_migrations=True, with_queries=True):
    pkg = root / "store-addon"
    (pkg / "storage" / "sqlite" / "migrations").mkdir(parents=True)
    if with_migrations:
        (pkg / "storage" / "sqlite" / "migrations" / "001_init.sql").write_text(
            "CREATE TABLE addon_state (key TEXT PRIMARY KEY);", encoding="utf-8"
        )
    if with_queries:
        (pkg / "storage" / "sqlite" / "queries.json").write_text(
            json.dumps(queries), encoding="utf-8"
        )
    (pkg / "manifest.json").write_text(json.dumps(_manifest()), encoding="utf-8")
    return pkg


def test_storage_queries_file_must_exist(tmp_path):
    pkg = _write_package(tmp_path, with_queries=False)
    loaded = load_package(pkg, expected_id="store-addon", expected_kind_root="addons")
    assert "sdk.storage.queries_path_missing" in loaded.validation.errors


def test_valid_storage_contract_loads_clean(tmp_path):
    pkg = _write_package(tmp_path)
    loaded = load_package(pkg, expected_id="store-addon", expected_kind_root="addons")
    storage_errors = [c for c in loaded.validation.errors if c.startswith("sdk.storage.")]
    assert storage_errors == []


def test_loader_reports_invalid_named_query(tmp_path):
    bad = {"queries": {"q": {"type": "nope", "params": {}, "sql": "SELECT 1"}}}
    pkg = _write_package(tmp_path, queries=bad)
    loaded = load_package(pkg, expected_id="store-addon", expected_kind_root="addons")
    assert "sdk.storage.sqlite.query_invalid_type" in loaded.validation.errors


# --- doctor ------------------------------------------------------------------


def test_doctor_reports_invalid_storage_contract(db, monkeypatch):
    from pathlib import Path

    from app.engine.sdk import package_registry
    from app.engine.sdk.package_doctor_service import PackageDoctorService
    from app.engine.sdk.package_loader import LoadedPackage
    from app.engine.sdk.package_manifest import PackageManifest
    from app.engine.sdk.package_manifest_validator import PackageManifestValidation
    from tests.conftest import install_system, seed_user

    gm = seed_user(email="storage-doctor@test.com")
    install_system(gm, package_id="dnd5e")

    fake = LoadedPackage(
        package_dir=Path("x"),
        manifest=PackageManifest.from_dict(_manifest()),
        validation=PackageManifestValidation(errors=["sdk.storage.queries_path_missing"]),
        raw=_manifest(),
        kind_dir="rulesets",
    )
    monkeypatch.setattr(package_registry, "load_by_package_id", lambda pid, *a, **k: fake)
    codes = {f.code for f in PackageDoctorService().audit()}
    assert "sdk.storage.queries_path_missing" in codes
