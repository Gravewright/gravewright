from __future__ import annotations

from typing import Any

from litestar import get
from litestar.exceptions import NotAuthorizedException

from app.domain.roles import SystemRole
from app.helpers.auth import require_user
from app.observability.diagnostics import diagnostics_recorder
from app.persistence.rows import Row
from app.realtime.metrics import realtime_metrics


def _ensure_owner(current_user: Row) -> None:
    if str(current_user["system_role"]) != SystemRole.OWNER.value:
        raise NotAuthorizedException(detail="Owner privileges required.")


@get("/inside/diagnostics", guards=[require_user])
async def show_diagnostics(current_user: Row) -> dict[str, Any]:
    """Return lightweight in-memory diagnostics for the instance owner."""
    _ensure_owner(current_user)
    return {
        "metrics": realtime_metrics.snapshot(),
        "recent_events": diagnostics_recorder.recent(limit=100),
    }
