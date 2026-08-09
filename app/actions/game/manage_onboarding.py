from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from litestar import get, post
from litestar.params import Body, FromQuery
from litestar.response import Response

from app.business.onboarding import GmOnboardingService
from app.helpers.async_blocking import run_blocking
from app.persistence.rows import Row


@dataclass
class OnboardingPreferenceBody:
    campaign_id: str = ""
    dismissed: bool = True


def _response(result) -> Response[dict[str, Any]]:
    if result.success:
        return Response({"ok": True, "state": result.state}, status_code=200)
    status = 404 if result.error_key == "onboarding.errors.not_found" else 403
    return Response({"ok": False, "error_key": result.error_key}, status_code=status)


@get("/game/onboarding")
async def get_gm_onboarding(
    current_user: Row,
    gm_onboarding_service: GmOnboardingService,
    campaign_id: FromQuery[str],
) -> Response[dict[str, Any]]:
    result = await run_blocking(
        gm_onboarding_service.get,
        campaign_id=campaign_id.strip(), user_id=current_user["id"],
    )
    return _response(result)


@post("/game/onboarding/preference")
async def update_gm_onboarding_preference(
    current_user: Row,
    gm_onboarding_service: GmOnboardingService,
    data: Annotated[OnboardingPreferenceBody, Body()],
) -> Response[dict[str, Any]]:
    result = await run_blocking(
        gm_onboarding_service.set_dismissed,
        campaign_id=data.campaign_id.strip(), user_id=current_user["id"], dismissed=data.dismissed,
    )
    return _response(result)
