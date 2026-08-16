from __future__ import annotations

from litestar import post
from litestar.response import Redirect

from app.business.users import UserPreferenceService
from app.helpers.auth import require_user
from app.persistence.rows import Row


@post("/inside/package-onboarding/dismiss", guards=[require_user], sync_to_thread=True)
def dismiss_package_onboarding(
    current_user: Row,
    user_preference_service: UserPreferenceService,
) -> Redirect:
    user_preference_service.mark_package_onboarding_seen(str(current_user["id"]))
    return Redirect(path="/inside")
