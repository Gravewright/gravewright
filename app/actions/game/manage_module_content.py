from __future__ import annotations

from typing import Any

from litestar import Request, get, post
from litestar.response import Response
from litestar.params import FromPath
from app.engine.modules.module_content_import_service import ModuleContentImportService
from app.engine.modules.module_content_pack_service import ModuleContentPackService
from app.persistence.rows import Row
from app.observability.diagnostics import emit_diagnostic
from app.realtime.metrics import realtime_metrics
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


async def _json_body(request: Request) -> dict[str, Any]:
    data = await request.json()
    return data if isinstance(data, dict) else {}


@get("/game/modules/content/packs/{campaign_id:str}/{module_id:str}")
async def list_module_content_packs(
    campaign_id: FromPath[str],
    module_id: FromPath[str],
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    module_content_pack_service: ModuleContentPackService,
) -> Response[dict[str, Any]]:
    return Response(
        {"packs": module_content_pack_service.list_packs(campaign_id=campaign_id, module_id=module_id, user_id=current_user["id"])},
        status_code=200,
    )


@get("/game/modules/content/pack/{campaign_id:str}/{module_id:str}/{pack_id:str}")
async def get_module_content_pack(
    campaign_id: FromPath[str],
    module_id: FromPath[str],
    pack_id: FromPath[str],
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    module_content_pack_service: ModuleContentPackService,
) -> Response[dict[str, Any]]:
    pack = module_content_pack_service.get_pack(campaign_id=campaign_id, module_id=module_id, pack_id=pack_id, user_id=current_user["id"])
    if pack is None:
        return Response({"error_key": "game.drop.errors.entry_not_found"}, status_code=404)
    return Response(pack, status_code=200)


@post("/game/modules/content/import")
async def import_module_content_entry(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    module_content_import_service: ModuleContentImportService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    result = module_content_import_service.import_entry(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=current_user["id"],
        module_id=str(body.get("module_id", "")),
        pack_id=str(body.get("pack_id", "")),
        entry_id=str(body.get("entry_id", "")),
    )
    realtime_metrics.increment("modules.content.import.count")
    if result.success:
        realtime_metrics.increment("modules.content.import.success")
    else:
        realtime_metrics.increment("modules.content.import.failure")
    emit_diagnostic(
        "modules.content.import",
        user_id=current_user["id"],
        campaign_id=str(body.get("campaign_id", "")),
        module_id=str(body.get("module_id", "")),
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
        payload: dict[str, Any] = {"room_id": result.campaign_id, "module_id": result.module_id or "", "updated_by": current_user["id"]}
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
