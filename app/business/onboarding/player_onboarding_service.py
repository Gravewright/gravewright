from __future__ import annotations

from dataclasses import dataclass

from app.persistence.repositories.player_onboarding_repository import PlayerOnboardingRepository


@dataclass(frozen=True)
class PlayerOnboardingResult:
    success: bool
    show: bool = False
    error_key: str | None = None


class PlayerOnboardingService:
    def __init__(self, repository: PlayerOnboardingRepository | None = None) -> None:
        self.repository = repository or PlayerOnboardingRepository()

    def claim_first_visit(self, *, campaign_id: str, user_id: str) -> PlayerOnboardingResult:
        if not campaign_id:
            return PlayerOnboardingResult(False, error_key="onboarding.errors.not_found")
        state = self.repository.claim_first_visit(campaign_id=campaign_id, user_id=user_id)
        if state == "not_found":
            return PlayerOnboardingResult(False, error_key="onboarding.errors.not_found")
        if state == "denied":
            return PlayerOnboardingResult(False, error_key="onboarding.errors.denied")
        return PlayerOnboardingResult(True, show=state == "claimed")
