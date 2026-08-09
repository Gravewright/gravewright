from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.business.audit import AuditService
from app.config import config
from app.domain.roles import PlayerRole
from app.helpers.codes import generate_join_code, hash_join_code
from app.observability.audit import emit_audit
from app.persistence.repositories.auth_attempt_repository import AuthAttemptRepository
from app.persistence.repositories.campaign_join_code_repository import (
    CampaignJoinCodeRepository,
)
from app.persistence.repositories.campaign_repository import CampaignRepository


PUBLIC_UNAVAILABLE_ERROR = "campaign.join_code.errors.unavailable"
PERMISSION_ERROR = "campaign.join_code.errors.permission_denied"
RATE_LIMIT_ERROR = "http.errors.rate_limited"
_RATE_ACTION = "campaign_join_code_redeem"


@dataclass(frozen=True)
class GenerateJoinCodeResult:
    success: bool
    code: str | None = None
    message_key: str | None = None
    error_key: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JoinCodeManagementResult:
    success: bool
    message_key: str | None = None
    error_key: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RedeemJoinCodeResult:
    success: bool
    message_key: str | None = None
    error_key: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    rate_limited: bool = False


class CampaignJoinCodeService:
    """Product and abuse-policy boundary for reusable campaign join codes."""

    def __init__(self) -> None:
        self.codes = CampaignJoinCodeRepository()
        self.campaigns = CampaignRepository()
        self.attempts = AuthAttemptRepository()
        self.audit = AuditService()

    def generate_or_rotate(
        self,
        *,
        campaign_id: str,
        user_id: str,
        expires_in_hours: int | None = None,
        max_uses: int | None = None,
        role: str = PlayerRole.PLAYER.value,
    ) -> GenerateJoinCodeResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return GenerateJoinCodeResult(success=False, error_key=PERMISSION_ERROR)
        if role != PlayerRole.PLAYER.value:
            self.audit.record(
                campaign_id=campaign_id,
                actor_user_id=user_id,
                event_type="join_code.generated",
                subject_type="campaign",
                subject_id=campaign_id,
                action="validate",
                result="denied",
            )
            return GenerateJoinCodeResult(
                success=False, error_key="campaign.join_code.errors.invalid_role"
            )

        hours = (
            config.join_code_default_expires_hours if expires_in_hours is None else expires_in_hours
        )
        if not config.join_code_min_expires_hours <= hours <= config.join_code_max_expires_hours:
            self.audit.record(
                campaign_id=campaign_id,
                actor_user_id=user_id,
                event_type="join_code.generated",
                subject_type="campaign",
                subject_id=campaign_id,
                action="validate",
                result="denied",
            )
            return GenerateJoinCodeResult(
                success=False,
                error_key="campaign.join_code.errors.invalid_expiration",
            )
        if max_uses is not None and not 1 <= max_uses <= config.join_code_max_uses_limit:
            self.audit.record(
                campaign_id=campaign_id,
                actor_user_id=user_id,
                event_type="join_code.generated",
                subject_type="campaign",
                subject_id=campaign_id,
                action="validate",
                result="denied",
            )
            return GenerateJoinCodeResult(
                success=False,
                error_key="campaign.join_code.errors.invalid_max_uses",
            )

        previous = self.codes.get_status_for_campaign(campaign_id=campaign_id)
        now = int(time.time())
        for _ in range(3):
            plaintext = generate_join_code()
            try:
                status = self.codes.rotate_active_code(
                    campaign_id=campaign_id,
                    created_by_user_id=user_id,
                    code_hash=hash_join_code(plaintext),
                    expires_at=now + hours * 3600,
                    max_uses=max_uses,
                    now=now,
                )
                break
            except IntegrityError:


                continue
        else:
            return GenerateJoinCodeResult(
                success=False, error_key="campaign.join_code.errors.generation_failed"
            )

        action = (
            "rotated" if previous is not None and previous["revoked_at"] is None else "generated"
        )
        emit_audit(
            f"join_code.{action}",
            actor_id=user_id,
            campaign_id=campaign_id,
            join_code_id=status["id"],
            result="success",
        )
        self.audit.record(
            campaign_id=campaign_id,
            actor_user_id=user_id,
            event_type=f"join_code.{action}",
            subject_type="join_code",
            subject_id=status["id"],
            action=action,
            result="success",
            metadata={"expires_at": status["expires_at"], "max_uses": status["max_uses"]},
        )
        return GenerateJoinCodeResult(
            success=True,
            code=plaintext,
            message_key=f"campaign.join_code.{action}",
            payload=self._public_status(status),
        )

    def revoke(self, *, campaign_id: str, user_id: str) -> JoinCodeManagementResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return JoinCodeManagementResult(success=False, error_key=PERMISSION_ERROR)
        status = self.codes.revoke_active_code(campaign_id=campaign_id)
        if status is not None:
            emit_audit(
                "join_code.revoked",
                actor_id=user_id,
                campaign_id=campaign_id,
                join_code_id=status["id"],
                result="success",
            )
            self.audit.record(
                campaign_id=campaign_id,
                actor_user_id=user_id,
                event_type="join_code.revoked",
                subject_type="join_code",
                subject_id=status["id"],
                action="revoke",
                result="success",
            )
        return JoinCodeManagementResult(
            success=True,
            message_key="campaign.join_code.revoked",
            payload={} if status is None else self._public_status(status),
        )

    def status(self, *, campaign_id: str, user_id: str) -> JoinCodeManagementResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return JoinCodeManagementResult(success=False, error_key=PERMISSION_ERROR)
        status = self.codes.get_status_for_campaign(campaign_id=campaign_id)
        return JoinCodeManagementResult(
            success=True,
            payload={"join_code": None if status is None else self._public_status(status)},
        )

    def redeem(self, *, code: str, user_id: str, client_ip: str) -> RedeemJoinCodeResult:
        keys = self._rate_keys(user_id=user_id, client_ip=client_ip)
        if any(self._is_blocked(key) for key in keys):
            emit_audit(
                "join_code.redemption",
                actor_id=user_id,
                result="rate_limited",
                reason="rate_limited",
            )
            return RedeemJoinCodeResult(
                success=False, error_key=RATE_LIMIT_ERROR, rate_limited=True
            )

        try:
            digest = hash_join_code(code)
        except (TypeError, ValueError):
            self._record_failure(keys)
            self._audit_denied(user_id=user_id, reason="invalid_format")
            return RedeemJoinCodeResult(success=False, error_key=PUBLIC_UNAVAILABLE_ERROR)

        outcome = self.codes.redeem_for_user(code_hash=digest, user_id=user_id)
        if not outcome.success:
            self._record_failure(keys)
            self._audit_denied(user_id=user_id, reason=outcome.status)
            return RedeemJoinCodeResult(success=False, error_key=PUBLIC_UNAVAILABLE_ERROR)

        for key in keys:
            self.attempts.clear(action=_RATE_ACTION, attempt_key=key)
        campaign = self.campaigns.get_for_user(
            campaign_id=str(outcome.campaign_id), user_id=user_id
        )
        member = self.campaigns.get_member(campaign_id=str(outcome.campaign_id), user_id=user_id)
        emit_audit(
            "join_code.redeemed",
            actor_id=user_id,
            campaign_id=outcome.campaign_id,
            join_code_id=outcome.join_code_id,
            membership_created=outcome.membership_created,
            result="success",
        )
        if outcome.membership_created:
            self.audit.record(
                campaign_id=str(outcome.campaign_id),
                actor_user_id=user_id,
                event_type="membership.created",
                subject_type="user",
                subject_id=user_id,
                action="create",
                result="success",
                metadata={"role": "player", "source": "join_code"},
            )
        message = (
            "campaign.join_code.redeemed"
            if outcome.membership_created
            else "campaign.join_code.already_member"
        )
        return RedeemJoinCodeResult(
            success=True,
            message_key=message,
            payload={
                "campaign": None if campaign is None else dict(campaign),
                "member": None if member is None else dict(member),
                "membership_created": outcome.membership_created,
            },
        )

    def _can_manage(self, *, campaign_id: str, user_id: str) -> bool:




        member_role = self.campaigns.get_member_role(
            campaign_id=campaign_id,
            user_id=user_id,
        )
        allowed = member_role == PlayerRole.GM.value
        if not allowed:
            campaign = self.campaigns.get(campaign_id)
            emit_audit(
                "join_code.management_denied",
                actor_id=user_id,
                campaign_id=campaign_id,
                member_role=member_role,
                campaign_exists=campaign is not None,
                owner_matches=bool(campaign and campaign.get("owner_user_id") == user_id),
                result="denied",
                level="warning",
            )
        return allowed

    @staticmethod
    def _public_status(status: dict) -> dict:
        return {
            "id": status["id"],
            "campaign_id": status["campaign_id"],
            "masked_code": "****-****-****",
            "role": status["role"],
            "max_uses": status["max_uses"],
            "use_count": status["use_count"],
            "expires_at": status["expires_at"],
            "revoked_at": status["revoked_at"],
            "last_used_at": status["last_used_at"],
        }

    @staticmethod
    def _rate_keys(*, user_id: str, client_ip: str) -> tuple[str, str, str]:

        ip_digest = hashlib.sha256(client_ip.strip().encode("utf-8")).hexdigest()[:32]
        return (f"user:{user_id}", f"ip:{ip_digest}", f"user_ip:{user_id}:{ip_digest}")

    def _is_blocked(self, key: str) -> bool:
        since = int(time.time()) - config.join_code_redeem_window_seconds
        return (
            self.attempts.count_failures_since(action=_RATE_ACTION, attempt_key=key, since=since)
            >= config.join_code_redeem_max_attempts
        )

    def _record_failure(self, keys: tuple[str, str, str]) -> None:
        for key in keys:
            self.attempts.record(action=_RATE_ACTION, attempt_key=key, success=False)

    @staticmethod
    def _audit_denied(*, user_id: str, reason: str) -> None:
        emit_audit(
            "join_code.redemption",
            actor_id=user_id,
            result="denied",
            reason=reason,
        )
