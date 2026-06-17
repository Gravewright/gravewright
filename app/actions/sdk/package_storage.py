"""Managed SQLite storage endpoints for SDK packages.

Part of the SDK 1 surface frozen by Alpha 2.0.0.

A package's browser SDK calls ``sdk.storage.sqlite.query/execute/status``; those
post here. The backend is the authority: it resolves the package and the
caller's role, builds the :class:`StorageContext`, and runs the declared named
query. The client never supplies SQL or a path — only a scope, a query name, and
typed params. Errors are returned with the structured ``code``.
"""

from __future__ import annotations

from typing import Any

from litestar import Request, post
from litestar.params import FromPath
from litestar.response import Response

from app.domain.roles import PlayerRole, SystemRole
from app.engine.sdk.package_storage_runtime import (
    PackageStorageRuntime,
    StorageContext,
    StorageError,
)
from app.helpers.auth import require_user
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.rows import Row


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


def _context(current_user: Row, campaign_id: str | None) -> StorageContext:
    """Resolve the caller's GM/membership for storage permission checks."""
    is_owner = str(current_user["system_role"]) == SystemRole.OWNER.value
    if not campaign_id:
        # Global scope: GM means the instance owner.
        return StorageContext(is_gm=is_owner, is_member=is_owner)
    role = CampaignRepository().get_member_role(
        campaign_id=campaign_id, user_id=current_user["id"]
    )
    return StorageContext(is_gm=role == PlayerRole.GM.value, is_member=role is not None)


def _error_response(error: StorageError) -> Response[dict[str, Any]]:
    sdk_error = error.error
    return Response(
        {
            "success": False,
            "code": sdk_error.code,
            "error_key": sdk_error.code,
        },
        status_code=400,
    )


@post("/sdk/packages/{package_id:str}/storage/sqlite/query", guards=[require_user])
async def storage_sqlite_query(
    package_id: FromPath[str], request: Request, current_user: Row
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "").strip() or None
    try:
        rows = PackageStorageRuntime().query(
            package_id,
            str(body.get("scope") or ""),
            str(body.get("query") or ""),
            body.get("params") if isinstance(body.get("params"), dict) else {},
            campaign_id=campaign_id,
            ctx=_context(current_user, campaign_id),
        )
    except StorageError as error:
        return _error_response(error)
    return Response({"success": True, "rows": rows})


@post("/sdk/packages/{package_id:str}/storage/sqlite/execute", guards=[require_user])
async def storage_sqlite_execute(
    package_id: FromPath[str], request: Request, current_user: Row
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "").strip() or None
    try:
        result = PackageStorageRuntime().execute(
            package_id,
            str(body.get("scope") or ""),
            str(body.get("query") or ""),
            body.get("params") if isinstance(body.get("params"), dict) else {},
            campaign_id=campaign_id,
            ctx=_context(current_user, campaign_id),
        )
    except StorageError as error:
        return _error_response(error)
    return Response({"success": True, **result})


@post("/sdk/packages/{package_id:str}/storage/sqlite/status", guards=[require_user])
async def storage_sqlite_status(
    package_id: FromPath[str], request: Request, current_user: Row
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "").strip() or None
    try:
        status = PackageStorageRuntime().status(
            package_id,
            str(body.get("scope") or ""),
            campaign_id,
            ctx=_context(current_user, campaign_id),
        )
    except StorageError as error:
        return _error_response(error)
    return Response({"success": True, **status})
