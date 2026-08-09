from __future__ import annotations

import json

from litestar import get
from litestar.exceptions import NotFoundException
from litestar.params import FromQuery
from litestar.response import Response

from app.business.audit import AuditService
from app.config import config
from app.helpers.auth import require_user
from app.helpers.http_responses import json_error, json_ok
from app.persistence.rows import Row


def _enabled() -> None:
    if not config.administrative_audit_enabled:
        raise NotFoundException()


@get("/campaigns/audit", guards=[require_user], sync_to_thread=False)
def list_administrative_audit(
    campaign_id: FromQuery[str],
    current_user: Row,
    audit_service: AuditService,
    event_type: FromQuery[str | None] = None,
    page: FromQuery[int] = 1,
    page_size: FromQuery[int] = 50,
) -> Response:
    _enabled()
    result = audit_service.list(
        campaign_id=campaign_id,
        user_id=str(current_user["id"]),
        event_type=event_type or None,
        page=page,
        page_size=page_size,
    )
    if not result.success:
        status = 403 if result.error_key == "audit.errors.denied" else 400
        return json_error(error_key=result.error_key or "audit.errors.failed", status_code=status)
    return json_ok(data={"events": result.events, "total": result.total, "page": page})


@get("/campaigns/audit/export", guards=[require_user], sync_to_thread=False)
def export_administrative_audit(
    campaign_id: FromQuery[str],
    current_user: Row,
    audit_service: AuditService,
    event_type: FromQuery[str | None] = None,
) -> Response:
    _enabled()
    result = audit_service.export(
        campaign_id=campaign_id,
        user_id=str(current_user["id"]),
        event_type=event_type or None,
    )
    if not result.success:
        status = 403 if result.error_key == "audit.errors.denied" else 400
        return json_error(error_key=result.error_key or "audit.errors.failed", status_code=status)
    payload = {
        "format": "gravewright.audit-export",
        "catalog_version": 1,
        "campaign_id": campaign_id,
        "event_count": len(result.events),
        "total_matching": result.total,
        "events": result.events,
    }
    return Response(
        content=json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="gravewright-audit-{campaign_id}.json"',
            "Cache-Control": "no-store",
        },
    )


route_handlers = [list_administrative_audit, export_administrative_audit]
