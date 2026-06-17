"""Storage *contract* for SDK packages (Phase 7A) — validation only.

This module validates a package's declared ``storage.sqlite`` contract:

* the manifest ``storage.sqlite`` block (coherence with the capability, scopes,
  safe migration/queries paths);
* the declared named queries file (``queries.json``): every query must declare a
  ``type`` (``read``/``write``), a ``params`` whitelist of typed parameters, and
  a single ``sql`` statement.

It deliberately does **not** open a database, run a query, or expose any
endpoint — that is Phase 7B. Named queries are only ever loaded from the
validated package on disk; SQL or queries supplied by a client are never
accepted.
"""

from __future__ import annotations

from typing import Any

from app.engine.sdk.package_paths import path_is_safe

STORAGE_SCOPES = frozenset({"campaign", "global"})
QUERY_TYPES = frozenset({"read", "write"})

# Parameter types a named query may whitelist.
PARAM_TYPES = frozenset(
    {"string", "integer", "number", "boolean", "json", "json-string", "uuid", "id"}
)

# Leading SQL keyword allowed per query type.
_READ_VERBS = frozenset({"SELECT", "WITH"})
_WRITE_VERBS = frozenset({"INSERT", "UPDATE", "DELETE"})

# Upper bound for a package's declared per-database size cap (``maxSizeMB``).
# The runtime defaults to 50 MB; a package may raise it, but a managed SQLite
# database is not meant to be a bulk store, so the manifest cap is bounded.
MAX_SIZE_MB_LIMIT = 1024


def storage_block(raw: dict) -> dict | None:
    """Return the ``storage.sqlite`` block of a manifest, or ``None``."""
    storage = raw.get("storage") if isinstance(raw, dict) else None
    if not isinstance(storage, dict):
        return None
    sqlite = storage.get("sqlite")
    return sqlite if isinstance(sqlite, dict) else None


def validate_storage_manifest(raw: dict) -> list[str]:
    """Validate the manifest-level storage declaration (no disk access).

    Returns a list of stable ``sdk.storage.*`` error codes.
    """
    codes: list[str] = []
    capabilities = raw.get("capabilities") if isinstance(raw, dict) else None
    has_capability = isinstance(capabilities, list) and "storage.sqlite" in capabilities
    block = storage_block(raw)

    if block is None:
        if has_capability:
            # Capability declared without a storage.sqlite block.
            codes.append("sdk.storage.declaration_invalid")
        return codes

    if not has_capability:
        codes.append("sdk.storage.capability_missing")

    scopes = block.get("scopes")
    if scopes is not None:
        if not isinstance(scopes, list) or any(s not in STORAGE_SCOPES for s in scopes):
            codes.append("sdk.storage.declaration_invalid")

    migrations = block.get("migrations")
    if migrations is not None and not path_is_safe(migrations):
        codes.append("sdk.storage.migration_path_unsafe")

    queries = block.get("queries")
    if queries is not None and not path_is_safe(queries):
        codes.append("sdk.storage.queries_path_unsafe")

    max_size = block.get("maxSizeMB")
    if max_size is not None:
        # ``bool`` is an ``int`` subclass — reject it explicitly.
        if isinstance(max_size, bool) or not isinstance(max_size, (int, float)) or max_size <= 0:
            codes.append("sdk.storage.max_size_invalid")
        elif max_size > MAX_SIZE_MB_LIMIT:
            codes.append("sdk.storage.max_size_too_large")

    return codes


def validate_named_queries(data: object) -> list[str]:
    """Validate the parsed contents of a package ``queries.json``.

    The single source for named queries is this on-disk file. Returns stable
    ``sdk.storage.sqlite.*`` error codes.
    """
    codes: list[str] = []
    if not isinstance(data, dict) or not isinstance(data.get("queries"), dict):
        return ["sdk.storage.sqlite.query_invalid_type"]

    for name, query in data["queries"].items():
        if not isinstance(name, str) or not name:
            codes.append("sdk.storage.sqlite.query_missing_name")
            continue
        if not isinstance(query, dict):
            codes.append("sdk.storage.sqlite.query_invalid_type")
            continue

        query_type = query.get("type")
        if query_type not in QUERY_TYPES:
            codes.append("sdk.storage.sqlite.query_invalid_type")

        params = query.get("params")
        if not isinstance(params, dict):
            codes.append("sdk.storage.sqlite.query_missing_params")
        else:
            for param_type in params.values():
                if param_type not in PARAM_TYPES:
                    codes.append("sdk.storage.sqlite.query_param_invalid_type")
                    break

        sql = query.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            codes.append("sdk.storage.sqlite.query_sql_missing")
        elif not _sql_allowed(sql, query_type):
            codes.append("sdk.storage.sqlite.query_sql_disallowed")

    # De-duplicate while keeping deterministic order.
    seen: set[str] = set()
    return [c for c in codes if not (c in seen or seen.add(c))]


def _sql_allowed(sql: str, query_type: Any) -> bool:
    """A single statement whose leading verb matches the declared type."""
    stripped = sql.strip().rstrip(";")
    # Reject multiple statements (a ';' followed by more SQL).
    if ";" in stripped:
        return False
    upper = stripped.upper()
    if any(token in upper for token in (" ATTACH ", "PRAGMA ", " VACUUM")):
        return False
    verb = upper.split(None, 1)[0] if upper else ""
    if query_type == "read":
        return verb in _READ_VERBS
    if query_type == "write":
        return verb in _WRITE_VERBS
    return False
