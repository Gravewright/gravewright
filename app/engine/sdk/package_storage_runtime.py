"""Storage runtime for SDK packages.

Part of the SDK 1 surface frozen by Alpha 2.0.0.

Executes a package's declared named queries against a Gravewright-managed SQLite
database. The package never sees a path or raw SQL: storage paths are derived
from the validated ``(kind, id, scope, campaign_id)``, and only named queries
loaded from the validated package on disk are executed, with parameters
whitelisted per query.

Permissions:

| scope    | read             | write |
|----------|------------------|-------|
| campaign | campaign members | GM    |
| global   | GM               | GM    |
"""

from __future__ import annotations

import sqlite3
import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.engine.sdk import package_registry
from app.engine.sdk.diagnostics import SdkError
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_storage import (
    PARAM_TYPES,
    STORAGE_SCOPES,
    storage_block,
    validate_named_queries,
)
from app.persistence.repositories.campaign_package_repository import CampaignPackageRepository
from app.persistence.repositories.campaign_repository import CampaignRepository

MIGRATIONS_TABLE = "gravewright_package_migrations"
MIGRATION_STATE_TABLE = "gravewright_package_migration_state"
DB_FILENAME = "data.sqlite3"
DEFAULT_MAX_SIZE_MB = 50
QUERY_TIMEOUT_MS = 3000
MAX_ROWS_RETURNED = 1000
MAX_RESULT_BYTES = 1024 * 1024
BUSY_TIMEOUT_MS = 1000


class StorageError(Exception):
    """A storage runtime failure carrying a structured :class:`SdkError`."""

    def __init__(self, code: str, message: str = "", **details: Any) -> None:
        super().__init__(message or code)
        self.error = SdkError(code=code, message=message, details=details)


@dataclass(frozen=True)
class StorageContext:
    """The authenticated context a storage call runs under."""

    is_gm: bool
    is_member: bool = True


def permission_allows(scope: str, *, write: bool, ctx: StorageContext) -> bool:
    if scope == "global":
        return ctx.is_gm  # read and write are GM-only
    if scope == "campaign":
        return ctx.is_gm if write else ctx.is_member
    return False


class PackageStorageRuntime:
    def __init__(self) -> None:
        self.install = PackageInstallService()
        self.campaigns = CampaignRepository()
        self.campaign_packages = CampaignPackageRepository()

    # --- resolution ------------------------------------------------------------

    def _block(self, package_id: str) -> tuple[str, dict]:
        """Return ``(kind, storage_block)`` for an enabled package with storage."""
        manifest = self.install.get_active_manifest(package_id)
        if manifest is None:
            raise StorageError("sdk.storage.capability_missing", "package not enabled")
        if "storage.sqlite" not in manifest.capabilities:
            raise StorageError("sdk.storage.capability_missing")
        block = storage_block(manifest.raw)
        if block is None:
            raise StorageError("sdk.storage.capability_missing")
        return manifest.kind, block

    def db_path(self, package_id: str, scope: str, campaign_id: str | None) -> Path:
        """Resolve the managed db path for a validated (kind, id, scope)."""
        kind, block = self._block(package_id)
        declared = block.get("scopes") or list(STORAGE_SCOPES)
        if scope not in STORAGE_SCOPES or scope not in declared:
            raise StorageError("sdk.storage.scope_forbidden", scope=scope)

        root = package_registry.storage_dir_for(kind, package_id)
        if root is None:
            raise StorageError("sdk.storage.path_forbidden")
        if scope == "global":
            return root / "global" / DB_FILENAME
        if not campaign_id or not _safe_segment(campaign_id):
            raise StorageError("sdk.storage.scope_forbidden", reason="missing_campaign")
        return root / "campaigns" / campaign_id / DB_FILENAME

    # --- public operations -----------------------------------------------------

    def status(
        self,
        package_id: str,
        scope: str,
        campaign_id: str | None = None,
        *,
        ctx: StorageContext,
    ) -> dict:
        if not permission_allows(scope, write=False, ctx=ctx):
            raise StorageError("sdk.storage.scope_forbidden", reason="permission")
        if scope == "campaign":
            self._ensure_campaign_package_active(package_id, campaign_id)
        path = self.db_path(package_id, scope, campaign_id)
        size = path.stat().st_size if path.is_file() else 0
        return {"scope": scope, "ready": path.is_file(), "size_bytes": size}

    def query(
        self,
        package_id: str,
        scope: str,
        query_name: str,
        params: dict | None = None,
        *,
        campaign_id: str | None = None,
        ctx: StorageContext,
    ) -> list[dict]:
        return self._run(
            package_id, scope, query_name, params or {}, campaign_id=campaign_id, ctx=ctx, write=False
        )

    def execute(
        self,
        package_id: str,
        scope: str,
        query_name: str,
        params: dict | None = None,
        *,
        campaign_id: str | None = None,
        ctx: StorageContext,
    ) -> dict:
        return self._run(
            package_id, scope, query_name, params or {}, campaign_id=campaign_id, ctx=ctx, write=True
        )

    # --- internals -------------------------------------------------------------

    def _run(
        self,
        package_id: str,
        scope: str,
        query_name: str,
        params: dict,
        *,
        campaign_id: str | None,
        ctx: StorageContext,
        write: bool,
    ):
        if not permission_allows(scope, write=write, ctx=ctx):
            raise StorageError("sdk.storage.scope_forbidden", reason="permission")
        if scope == "campaign":
            self._ensure_campaign_package_active(package_id, campaign_id)

        path = self.db_path(package_id, scope, campaign_id)
        query = self._named_query(package_id, query_name)

        declared_type = query.get("type")
        if (write and declared_type != "write") or (not write and declared_type != "read"):
            raise StorageError("sdk.storage.sqlite.query_invalid", query=query_name)

        bound = self._validate_params(query.get("params") or {}, params, query_name)

        path.parent.mkdir(parents=True, exist_ok=True)
        if write:
            self._enforce_size_limit(package_id, path)
        connection = sqlite3.connect(path)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
            self._apply_migrations(connection, package_id)
            self._ensure_storage_clean(connection)
            deadline = time.monotonic() + (QUERY_TIMEOUT_MS / 1000)

            def _deadline_guard() -> int:
                return 1 if time.monotonic() > deadline else 0

            connection.set_progress_handler(_deadline_guard, 1000)
            cursor = connection.execute(query["sql"], bound)
            if write:
                connection.commit()
                self._enforce_size_limit(package_id, path)
                return {"rowcount": cursor.rowcount}
            rows = [dict(row) for row in cursor.fetchmany(MAX_ROWS_RETURNED + 1)]
            if len(rows) > MAX_ROWS_RETURNED:
                raise StorageError(
                    "sdk.storage.sqlite.result_limit_exceeded",
                    rows=MAX_ROWS_RETURNED,
                )
            self._enforce_result_size(rows)
            return rows
        except StorageError:
            raise
        except sqlite3.OperationalError as exc:
            if "interrupted" in str(exc).lower():
                raise StorageError("sdk.storage.sqlite.query_timeout", query=query_name)
            raise StorageError("sdk.storage.sqlite.query_invalid", str(exc), query=query_name)
        except sqlite3.Error as exc:
            raise StorageError("sdk.storage.sqlite.query_invalid", str(exc), query=query_name)
        finally:
            try:
                connection.set_progress_handler(None, 0)
            except Exception:
                pass
            connection.close()

    def _named_query(self, package_id: str, query_name: str) -> dict:
        """Load the named query from the validated package on disk."""
        loaded = package_registry.load_by_package_id(package_id)
        if loaded is None:
            raise StorageError("sdk.storage.sqlite.query_missing", "package not on disk")
        block = storage_block(loaded.raw) or {}
        queries_rel = block.get("queries")
        from app.engine.sdk.package_paths import safe_join

        resolved = safe_join(loaded.package_dir, queries_rel) if queries_rel else None
        if resolved is None or not resolved.is_file():
            raise StorageError("sdk.storage.sqlite.query_missing", "queries file missing")
        import json

        try:
            data = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise StorageError("sdk.storage.sqlite.query_missing", "queries unreadable")
        codes = validate_named_queries(data)
        if codes:
            raise StorageError("sdk.storage.sqlite.query_invalid", codes=codes)
        query = (data.get("queries") or {}).get(query_name)
        if not isinstance(query, dict) or not query.get("sql"):
            raise StorageError("sdk.storage.sqlite.query_missing", query=query_name)
        return query

    def _ensure_campaign_package_active(
        self, package_id: str, campaign_id: str | None
    ) -> None:
        if not campaign_id:
            raise StorageError("sdk.storage.scope_forbidden", reason="missing_campaign")
        campaign = self.campaigns.get(campaign_id)
        if campaign is None:
            raise StorageError("sdk.storage.scope_forbidden", reason="campaign_missing")
        if campaign.get("active_system_id") == package_id:
            return
        activation = self.campaign_packages.get(
            campaign_id=campaign_id,
            package_id=package_id,
        )
        if activation and activation.get("status") == "active":
            return
        raise StorageError("sdk.storage.scope_forbidden", reason="package_inactive")

    @staticmethod
    def _validate_params(declared: dict, provided: dict, query_name: str) -> dict:
        declared_keys = set(declared)
        provided_keys = set(provided)
        if provided_keys - declared_keys:
            raise StorageError(
                "sdk.storage.sqlite.param_invalid", reason="extra", query=query_name
            )
        if declared_keys - provided_keys:
            raise StorageError(
                "sdk.storage.sqlite.param_invalid", reason="missing", query=query_name
            )
        bound: dict[str, Any] = {}
        for key, declared_type in declared.items():
            value = provided[key]
            if declared_type not in PARAM_TYPES or not _value_matches(declared_type, value):
                raise StorageError(
                    "sdk.storage.sqlite.param_invalid", reason="type", param=key
                )
            bound[key] = value
        return bound

    def _apply_migrations(self, connection: sqlite3.Connection, package_id: str) -> None:
        loaded = package_registry.load_by_package_id(package_id)
        if loaded is None:
            return
        block = storage_block(loaded.raw) or {}
        migrations_rel = block.get("migrations")
        if not migrations_rel:
            return
        from app.engine.sdk.package_paths import safe_join

        migrations_dir = safe_join(loaded.package_dir, migrations_rel)
        if migrations_dir is None or not migrations_dir.is_dir():
            return

        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} "
            "(version TEXT PRIMARY KEY, name TEXT NOT NULL, sha256 TEXT NOT NULL, "
            "applied_at INTEGER NOT NULL)"
        )
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {MIGRATION_STATE_TABLE} "
            "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        state = connection.execute(
            f"SELECT value FROM {MIGRATION_STATE_TABLE} WHERE key = 'status'"
        ).fetchone()
        if state is not None and state[0] != "clean":
            raise StorageError("sdk.storage.sqlite.migration_dirty", state=state[0])
        applied = {
            row[0]: row[1]
            for row in connection.execute(f"SELECT version, sha256 FROM {MIGRATIONS_TABLE}")
        }

        for sql_file in sorted(migrations_dir.glob("*.sql")):
            version = sql_file.stem
            text = sql_file.read_text(encoding="utf-8")
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if version in applied:
                if applied[version] != digest:
                    raise StorageError(
                        "sdk.storage.sqlite.migration_hash_mismatch",
                        version=version,
                    )
                continue
            try:
                self._set_migration_state(connection, "running")
                connection.executescript(text)
            except sqlite3.Error as exc:
                self._set_migration_state(connection, "failed")
                connection.commit()
                raise StorageError("sdk.storage.sqlite.migration_failed", str(exc), version=version)
            connection.execute(
                f"INSERT INTO {MIGRATIONS_TABLE} (version, name, sha256, applied_at) "
                "VALUES (?, ?, ?, ?)",
                (version, sql_file.name, digest, int(time.time())),
            )
            self._set_migration_state(connection, "clean")
        connection.commit()

    @staticmethod
    def _set_migration_state(connection: sqlite3.Connection, state: str) -> None:
        connection.execute(
            f"INSERT INTO {MIGRATION_STATE_TABLE} (key, value) VALUES ('status', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (state,),
        )

    @staticmethod
    def _ensure_storage_clean(connection: sqlite3.Connection) -> None:
        exists = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (MIGRATION_STATE_TABLE,),
        ).fetchone()
        if not exists:
            return
        row = connection.execute(
            f"SELECT value FROM {MIGRATION_STATE_TABLE} WHERE key = 'status'"
        ).fetchone()
        if row is not None and row[0] != "clean":
            raise StorageError("sdk.storage.sqlite.migration_dirty", state=row[0])

    def _enforce_size_limit(self, package_id: str, path: Path) -> None:
        if not path.exists():
            return
        _kind, block = self._block(package_id)
        max_mb = block.get("maxSizeMB", DEFAULT_MAX_SIZE_MB)
        try:
            max_bytes = int(max_mb) * 1024 * 1024
        except (TypeError, ValueError):
            max_bytes = DEFAULT_MAX_SIZE_MB * 1024 * 1024
        if path.stat().st_size > max_bytes:
            raise StorageError(
                "sdk.storage.sqlite.size_limit_exceeded",
                maxSizeMB=max_mb,
            )

    @staticmethod
    def _enforce_result_size(rows: list[dict]) -> None:
        import json

        size = len(json.dumps(rows, separators=(",", ":"), default=str).encode("utf-8"))
        if size > MAX_RESULT_BYTES:
            raise StorageError(
                "sdk.storage.sqlite.result_limit_exceeded",
                bytes=MAX_RESULT_BYTES,
            )


def _safe_segment(value: str) -> bool:
    return bool(value) and "/" not in value and "\\" not in value and ".." not in value


def _value_matches(declared_type: str, value: Any) -> bool:
    if declared_type == "string":
        return isinstance(value, str)
    if declared_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if declared_type == "boolean":
        return isinstance(value, bool)
    if declared_type in {"json-string", "uuid", "id"}:
        return isinstance(value, str)
    if declared_type == "json":
        return isinstance(value, (dict, list, str, int, float, bool)) or value is None
    return False
