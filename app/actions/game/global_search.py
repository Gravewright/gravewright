from __future__ import annotations

from litestar import get
from litestar.exceptions import NotFoundException
from litestar.params import FromQuery
from litestar.response import Response

from app.business.search import GlobalSearchService
from app.config import config
from app.helpers.http_responses import json_error, json_ok
from app.persistence.rows import Row


@get("/game/search", sync_to_thread=True)
def global_search(
    current_user: Row,
    global_search_service: GlobalSearchService,
    campaign_id: FromQuery[str],
    q: FromQuery[str] = "",
    limit: FromQuery[int] = 20,
) -> Response:
    if not config.command_palette_enabled:
        raise NotFoundException()
    result = global_search_service.search(
        campaign_id=campaign_id,
        user_id=str(current_user["id"]),
        query=q,
        limit=limit,
    )
    if not result.success:
        return json_error(error_key=result.error_key or "search.errors.denied", status_code=403)
    return json_ok(data={"results": result.results})
