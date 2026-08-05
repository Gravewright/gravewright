from __future__ import annotations

from enum import StrEnum


class CampaignStateReason(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    SYSTEM_CHANGED = "system_changed"
    IMPORTED = "imported"
    RESET_FROM_INITIAL = "reset_from_initial"


class InvitationStatus(StrEnum):
    """Lifecycle states for a campaign invitation. The single source of truth
    for the ``campaign_invitations.status`` database check constraint."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
