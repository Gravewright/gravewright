"""Import package content packs into a campaign (GM-only)."""

from __future__ import annotations

from typing import Any

from litestar import Request, get, post
from litestar.params import FromPath
from litestar.response import Response

from app.engine.sdk.package_content_service import PackageContentService
from app.helpers.auth import require_user
from app.observability.diagnostics import emit_diagnostic
from app.persistence.rows import Row
from app.realtime.events import TransportEvent
from app.realtime.metrics import realtime_metrics
from app.realtime.transport import RealtimeTransport


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        data = await request.json()
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


@get("/sdk/packages/{package_id:str}/content/packs", guards=[require_user], sync_to_thread=False)
def list_package_content_packs(
    package_id: FromPath[str],
    current_user: Row,
    package_content_service: PackageContentService,
) -> Response[dict[str, Any]]:
    return Response({"packs": package_content_service.list_packs(str(package_id))})


@get(
    "/sdk/packages/{package_id:str}/content/pack/{pack_id:str}",
    guards=[require_user],
    sync_to_thread=False,
)
def get_package_content_pack(
    package_id: FromPath[str],
    pack_id: FromPath[str],
    current_user: Row,
    package_content_service: PackageContentService,
) -> Response[dict[str, Any]]:
    pack = package_content_service.get_pack(str(package_id), str(pack_id))
    if pack is None:
        return Response({"error_key": "game.drop.errors.entry_not_found"}, status_code=404)
    return Response(pack)


@post("/sdk/packages/content/import", guards=[require_user])
async def import_package_content_entry(
    request: Request,
    current_user: Row,
    package_content_service: PackageContentService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    result = package_content_service.import_entry(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=current_user["id"],
        package_id=str(body.get("package_id", "")),
        pack_id=str(body.get("pack_id", "")),
        entry_id=str(body.get("entry_id", "")),
    )
    realtime_metrics.increment("packages.content.import.count")
    realtime_metrics.increment(
        f"packages.content.import.{'success' if result.success else 'failure'}"
    )
    emit_diagnostic(
        "packages.content.import",
        user_id=current_user["id"],
        campaign_id=str(body.get("campaign_id", "")),
        package_id=str(body.get("package_id", "")),
        pack_id=str(body.get("pack_id", "")),
        entry_id=str(body.get("entry_id", "")),
        success=result.success,
        error_key=result.error_key,
        pack_type=result.pack_type,
    )
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)

    if result.campaign_id:
        event = None
        payload: dict[str, Any] = {
            "room_id": result.campaign_id,
            "package_id": result.package_id or "",
            "updated_by": current_user["id"],
        }
        if result.actor_id:
            event = TransportEvent.ACTOR_CREATED
            payload.update({"actor_id": result.actor_id, "system_id": result.system_id or ""})
        elif result.item_id:
            event = TransportEvent.ITEM_CREATED
            payload.update({"item_id": result.item_id, "system_id": result.system_id or ""})
        elif result.journal_id:
            event = TransportEvent.JOURNAL_CREATED
            payload.update({"journal_id": result.journal_id})
        if event is not None:
            await RealtimeTransport().to_room(room_id=result.campaign_id, event=event, payload=payload)

    return Response(
        {
            "ok": True,
            "actor_id": result.actor_id,
            "item_id": result.item_id,
            "journal_id": result.journal_id,
            "pack_type": result.pack_type,
        },
        status_code=201,
    )
