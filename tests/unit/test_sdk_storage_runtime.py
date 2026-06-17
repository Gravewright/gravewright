<<<<<<< HEAD
"""storage.sqlite runtime (SDK 1, frozen by Alpha 2.0.0).
=======
"""Phase 7B — storage runtime (experimental).
>>>>>>> origin/main

Executes managed SQLite named queries: path derived from the validated
(kind, id, scope, campaign_id), migrations applied on first use, parameters
whitelisted per query, permissions enforced, and no raw SQL / absolute path ever
exposed.
"""

from __future__ import annotations

import inspect
<<<<<<< HEAD
import json
import shutil
=======
>>>>>>> origin/main
from pathlib import Path

import pytest

from app.engine.sdk import package_registry
from app.engine.sdk.package_install_service import PackageInstallService
<<<<<<< HEAD
from app.engine.sdk.package_activation_service import PackageActivationService
=======
>>>>>>> origin/main
from app.engine.sdk.package_storage_runtime import (
    PackageStorageRuntime,
    StorageContext,
    StorageError,
)
<<<<<<< HEAD
from tests.conftest import seed_campaign, seed_user
=======
from tests.conftest import seed_user
>>>>>>> origin/main

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "sdk_packages" / "valid"
GM = StorageContext(is_gm=True, is_member=True)
PLAYER = StorageContext(is_gm=False, is_member=True)
STORAGE_PKG = "valid-addon-sqlite-contract"


@pytest.fixture
def storage_env(db, monkeypatch, tmp_path):
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", FIXTURES)
    monkeypatch.setattr(package_registry, "STORAGE_PACKAGES_DIR", tmp_path / "storage" / "packages")
    gm = seed_user(email="storage-runtime@test.com")
    svc = PackageInstallService()
    svc.install(package_id=STORAGE_PKG, user_id=gm)
    svc.enable(package_id=STORAGE_PKG)
    svc.install(package_id="valid-addon", user_id=gm)
    svc.enable(package_id="valid-addon")
<<<<<<< HEAD
    campaign_id = seed_campaign(gm)
    result = PackageActivationService().activate_package(campaign_id, STORAGE_PKG, gm)
    assert result.success, result.error_key
    runtime = PackageStorageRuntime()
    runtime.campaign_id = campaign_id
    runtime.gm_user_id = gm
    return runtime
=======
    return PackageStorageRuntime()
>>>>>>> origin/main


# --- capability + paths ------------------------------------------------------


def test_storage_sqlite_requires_capability(storage_env):
    with pytest.raises(StorageError) as exc:
<<<<<<< HEAD
        storage_env.status("valid-addon", "global", ctx=GM)
=======
        storage_env.status("valid-addon", "global")
>>>>>>> origin/main
    assert exc.value.error.code == "sdk.storage.capability_missing"


def test_storage_path_uses_validated_kind_and_package_id(storage_env):
    path = storage_env.db_path(STORAGE_PKG, "global", None)
    assert path.as_posix().endswith(f"storage/packages/addons/{STORAGE_PKG}/global/data.sqlite3")


def test_storage_does_not_expose_absolute_path_to_frontend(storage_env):
<<<<<<< HEAD
    status = storage_env.status(STORAGE_PKG, "global", ctx=GM)
=======
    status = storage_env.status(STORAGE_PKG, "global")
>>>>>>> origin/main
    assert "path" not in status
    assert set(status) == {"scope", "ready", "size_bytes"}


def test_storage_rejects_raw_sql_from_frontend():
    # No public runtime method accepts a SQL string — only a query *name*.
    for name in ("query", "execute"):
        params = set(inspect.signature(getattr(PackageStorageRuntime, name)).parameters)
        assert "sql" not in params
        assert "query_name" in params


# --- execution ---------------------------------------------------------------


def test_global_storage_db_created_under_data_storage_packages(storage_env):
    storage_env.execute(
        STORAGE_PKG, "global", "saveState", {"key": "k", "value_json": "{}"}, ctx=GM
    )
    path = storage_env.db_path(STORAGE_PKG, "global", None)
    assert path.is_file()
    assert "storage/packages/addons" in path.as_posix()


def test_campaign_storage_db_created_under_data_storage_packages(storage_env):
    storage_env.execute(
        STORAGE_PKG, "campaign", "saveState", {"key": "k", "value_json": "1"},
<<<<<<< HEAD
        campaign_id=storage_env.campaign_id, ctx=GM,
    )
    path = storage_env.db_path(STORAGE_PKG, "campaign", storage_env.campaign_id)
    assert path.is_file()
    assert f"campaigns/{storage_env.campaign_id}" in path.as_posix()
=======
        campaign_id="camp-1", ctx=GM,
    )
    path = storage_env.db_path(STORAGE_PKG, "campaign", "camp-1")
    assert path.is_file()
    assert "campaigns/camp-1" in path.as_posix()
>>>>>>> origin/main


def test_storage_named_query_write_then_read_executes(storage_env):
    storage_env.execute(
        STORAGE_PKG, "global", "saveState", {"key": "panel", "value_json": "\"open\""}, ctx=GM
    )
    rows = storage_env.query(STORAGE_PKG, "global", "getState", {"key": "panel"}, ctx=GM)
    assert rows == [{"value_json": '"open"'}]


def test_storage_migrations_are_applied_on_first_use(storage_env):
    storage_env.execute(STORAGE_PKG, "global", "saveState", {"key": "k", "value_json": "1"}, ctx=GM)
    import sqlite3

    path = storage_env.db_path(STORAGE_PKG, "global", None)
    conn = sqlite3.connect(path)
    try:
        versions = {r[0] for r in conn.execute("SELECT version FROM gravewright_package_migrations")}
    finally:
        conn.close()
    assert "001_init" in versions


<<<<<<< HEAD
def test_runtime_revalidates_modified_queries_json(storage_env, monkeypatch, tmp_path):
    packages = tmp_path / "packages"
    shutil.copytree(FIXTURES / "addons" / STORAGE_PKG, packages / "addons" / STORAGE_PKG)
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", packages)
    queries_path = packages / "addons" / STORAGE_PKG / "storage" / "sqlite" / "queries.json"
    queries = json.loads(queries_path.read_text(encoding="utf-8"))
    queries["queries"]["getState"]["sql"] = "SELECT 1; DROP TABLE addon_state"
    queries_path.write_text(json.dumps(queries), encoding="utf-8")

    with pytest.raises(StorageError) as exc:
        storage_env.query(STORAGE_PKG, "global", "getState", {"key": "k"}, ctx=GM)
    assert exc.value.error.code == "sdk.storage.sqlite.query_invalid"
    assert "sdk.storage.sqlite.query_sql_disallowed" in exc.value.error.details["codes"]


def test_modified_applied_migration_is_detected(storage_env, monkeypatch, tmp_path):
    packages = tmp_path / "packages"
    shutil.copytree(FIXTURES / "addons" / STORAGE_PKG, packages / "addons" / STORAGE_PKG)
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", packages)

    storage_env.execute(
        STORAGE_PKG, "global", "saveState", {"key": "k", "value_json": "1"}, ctx=GM
    )
    migration = (
        packages
        / "addons"
        / STORAGE_PKG
        / "storage"
        / "sqlite"
        / "migrations"
        / "001_init.sql"
    )
    migration.write_text(migration.read_text(encoding="utf-8") + "\n-- changed\n", encoding="utf-8")

    with pytest.raises(StorageError) as exc:
        storage_env.query(STORAGE_PKG, "global", "getState", {"key": "k"}, ctx=GM)
    assert exc.value.error.code == "sdk.storage.sqlite.migration_hash_mismatch"


=======
>>>>>>> origin/main
# --- rejection paths ---------------------------------------------------------


def test_storage_rejects_unknown_query(storage_env):
    with pytest.raises(StorageError) as exc:
        storage_env.query(STORAGE_PKG, "global", "nonexistent", {}, ctx=GM)
    assert exc.value.error.code == "sdk.storage.sqlite.query_missing"


def test_storage_rejects_extra_params(storage_env):
    with pytest.raises(StorageError) as exc:
        storage_env.query(STORAGE_PKG, "global", "getState", {"key": "k", "extra": 1}, ctx=GM)
    assert exc.value.error.code == "sdk.storage.sqlite.param_invalid"


def test_storage_rejects_missing_params(storage_env):
    with pytest.raises(StorageError) as exc:
        storage_env.query(STORAGE_PKG, "global", "getState", {}, ctx=GM)
    assert exc.value.error.code == "sdk.storage.sqlite.param_invalid"


def test_storage_rejects_invalid_param_type(storage_env):
    with pytest.raises(StorageError) as exc:
        storage_env.query(STORAGE_PKG, "global", "getState", {"key": 123}, ctx=GM)
    assert exc.value.error.code == "sdk.storage.sqlite.param_invalid"


def test_storage_rejects_wrong_operation_for_query_type(storage_env):
    # getState is a read; calling execute() (write) on it is rejected.
    with pytest.raises(StorageError) as exc:
        storage_env.execute(STORAGE_PKG, "global", "getState", {"key": "k"}, ctx=GM)
    assert exc.value.error.code == "sdk.storage.sqlite.query_invalid"


def test_storage_rejects_cross_campaign_traversal(storage_env):
    with pytest.raises(StorageError) as exc:
        storage_env.db_path(STORAGE_PKG, "campaign", "../other")
    assert exc.value.error.code == "sdk.storage.scope_forbidden"


def test_storage_campaign_write_requires_gm(storage_env):
    with pytest.raises(StorageError) as exc:
        storage_env.execute(
<<<<<<< HEAD
            STORAGE_PKG,
            "campaign",
            "saveState",
            {"key": "k", "value_json": "1"},
            campaign_id=storage_env.campaign_id,
            ctx=PLAYER,
=======
            STORAGE_PKG, "campaign", "saveState", {"key": "k", "value_json": "1"},
            campaign_id="camp-1", ctx=PLAYER,
>>>>>>> origin/main
        )
    assert exc.value.error.code == "sdk.storage.scope_forbidden"


def test_storage_campaign_read_allowed_for_member(storage_env):
    storage_env.execute(
        STORAGE_PKG, "campaign", "saveState", {"key": "k", "value_json": "5"},
<<<<<<< HEAD
        campaign_id=storage_env.campaign_id, ctx=GM,
    )
    rows = storage_env.query(
        STORAGE_PKG,
        "campaign",
        "getState",
        {"key": "k"},
        campaign_id=storage_env.campaign_id,
        ctx=PLAYER,
=======
        campaign_id="camp-1", ctx=GM,
    )
    rows = storage_env.query(
        STORAGE_PKG, "campaign", "getState", {"key": "k"}, campaign_id="camp-1", ctx=PLAYER
>>>>>>> origin/main
    )
    assert rows == [{"value_json": "5"}]


<<<<<<< HEAD
def test_storage_rejects_enabled_but_inactive_campaign_package(storage_env):
    inactive_campaign = seed_campaign(storage_env.gm_user_id)
    with pytest.raises(StorageError) as exc:
        storage_env.query(
            STORAGE_PKG,
            "campaign",
            "getState",
            {"key": "k"},
            campaign_id=inactive_campaign,
            ctx=GM,
        )
    assert exc.value.error.code == "sdk.storage.scope_forbidden"
    assert exc.value.error.details["reason"] == "package_inactive"


def test_storage_campaign_status_requires_membership(storage_env):
    with pytest.raises(StorageError) as exc:
        storage_env.status(
            STORAGE_PKG,
            "campaign",
            storage_env.campaign_id,
            ctx=StorageContext(is_gm=False, is_member=False),
        )
    assert exc.value.error.code == "sdk.storage.scope_forbidden"


def test_storage_isolates_packages_and_campaigns(storage_env):
    # Each package/campaign resolves to its own db file; never another's.
    a_global = storage_env.db_path(STORAGE_PKG, "global", None)
    a_camp1 = storage_env.db_path(STORAGE_PKG, "campaign", storage_env.campaign_id)
    a_camp2 = storage_env.db_path(STORAGE_PKG, "campaign", "camp-2")
    assert a_global != a_camp1 != a_camp2
    assert STORAGE_PKG in a_camp1.as_posix()
    assert storage_env.campaign_id in a_camp1.as_posix() and "camp-2" not in a_camp1.as_posix()
=======
def test_storage_isolates_packages_and_campaigns(storage_env):
    # Each package/campaign resolves to its own db file; never another's.
    a_global = storage_env.db_path(STORAGE_PKG, "global", None)
    a_camp1 = storage_env.db_path(STORAGE_PKG, "campaign", "camp-1")
    a_camp2 = storage_env.db_path(STORAGE_PKG, "campaign", "camp-2")
    assert a_global != a_camp1 != a_camp2
    assert STORAGE_PKG in a_camp1.as_posix()
    assert "camp-1" in a_camp1.as_posix() and "camp-2" not in a_camp1.as_posix()
>>>>>>> origin/main
