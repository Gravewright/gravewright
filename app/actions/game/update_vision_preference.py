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
class UpdateVisionPreferenceForm:
    vision_mode: str = ""


@post("/game/preferences/vision")
async def update_vision_preference(
    cookies: dict[str, str],
    current_user: Row,
    user_preference_service: UserPreferenceService,
    data: Annotated[UpdateVisionPreferenceForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, Any]]:
    user = current_user

    result = user_preference_service.set_vision_mode(
        user_id=user["id"],
        vision_mode=data.vision_mode,
    )

    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)

    return Response({"ok": True, "vision_mode": result.vision_mode}, status_code=200)
