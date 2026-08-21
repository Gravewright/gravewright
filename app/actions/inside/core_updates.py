from __future__ import annotations

from litestar import post
from litestar.response import Response

from app.business.core_update_service import CoreUpdateService
from app.domain.roles import SystemRole
from app.helpers.auth import require_user
from app.persistence.rows import Row


@post("/inside/updates/core/check", guards=[require_user], sync_to_thread=True)
def check_core_update(current_user: Row) -> Response[dict]:
    if str(current_user["system_role"]) != SystemRole.OWNER.value:
        return Response({"ok": False, "errorKey": "sdk.errors.owner_required"}, status_code=403)
    result = CoreUpdateService().check()
    return Response({"ok": result.get("status") != "failed", "update": result},
                    status_code=200 if result.get("status") != "failed" else 502)
