from __future__ import annotations

from dataclasses import dataclass, field

from app.persistence.repositories.gm_onboarding_repository import GmOnboardingRepository


@dataclass(frozen=True)
class OnboardingResult:
    success: bool
    error_key: str | None = None
    state: dict = field(default_factory=dict)


class GmOnboardingService:
    STEP_KEYS = ("campaign", "system", "character", "scene", "code")

    def __init__(self) -> None:
        self.repository = GmOnboardingRepository()

    def get(self, *, campaign_id: str, user_id: str) -> OnboardingResult:
        raw = self.repository.progress(campaign_id=campaign_id, user_id=user_id)
        if raw is None:
            return OnboardingResult(False, "onboarding.errors.not_found")
        if raw["role"] != "gm":
            return OnboardingResult(False, "onboarding.errors.denied")
        steps = {
            "campaign": True,
            "system": raw["has_system"],
            "character": raw["has_actor"],
            "scene": raw["has_scene"],
            "code": raw["has_join_code"],
        }
        completed = sum(bool(value) for value in steps.values())
        return OnboardingResult(True, state={
            "campaign_id": campaign_id,
            "steps": steps,
            "completed": completed,
            "total": len(self.STEP_KEYS),
            "finished": completed == len(self.STEP_KEYS),
            "dismissed": raw["dismissed"],
        })

    def set_dismissed(self, *, campaign_id: str, user_id: str, dismissed: bool) -> OnboardingResult:
        current = self.get(campaign_id=campaign_id, user_id=user_id)
        if not current.success:
            return current
        self.repository.set_dismissed(
            campaign_id=campaign_id, user_id=user_id, dismissed=dismissed
        )
        return self.get(campaign_id=campaign_id, user_id=user_id)
