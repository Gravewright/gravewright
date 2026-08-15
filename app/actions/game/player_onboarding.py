from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from litestar import post
from litestar.params import Body
from litestar.response import Response

from app.business.onboarding import PlayerOnboardingService
from app.helpers.async_blocking import run_blocking
from app.persistence.rows import Row


@dataclass
class PlayerOnboardingBody:
    campaign_id: str = ""


@post("/game/player-onboarding/claim")
async def claim_player_onboarding(
    current_user: Row,
    player_onboarding_service: PlayerOnboardingService,
    data: Annotated[PlayerOnboardingBody, Body()],
) -> Response[dict[str, Any]]:
    result = await run_blocking(
        player_onboarding_service.claim_first_visit,
        campaign_id=data.campaign_id.strip(),
        user_id=current_user["id"],
    )
    if result.success:
        return Response({"ok": True, "show": result.show}, status_code=200)
    status = 404 if result.error_key == "onboarding.errors.not_found" else 403
    return Response({"ok": False, "error_key": result.error_key}, status_code=status)
