from __future__ import annotations

from dataclasses import dataclass
from app.persistence.rows import Row
from typing import Annotated, Any

from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Response

from app.business.users import UserPreferenceService


@dataclass
class UpdateLayoutPreferenceForm:
    layout_mode: str = ""


@post("/game/preferences/layout")
async def update_layout_preference(
    cookies: dict[str, str],
    current_user: Row,
    user_preference_service: UserPreferenceService,
    data: Annotated[UpdateLayoutPreferenceForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, Any]]:
    user = current_user

    result = user_preference_service.set_game_layout_mode(
        user_id=user["id"],
        layout_mode=data.layout_mode,
    )

    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)

    return Response({"ok": True, "layout_mode": result.layout_mode}, status_code=200)
