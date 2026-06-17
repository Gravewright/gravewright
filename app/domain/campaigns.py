from __future__ import annotations

from enum import StrEnum


class CampaignStateReason(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    SYSTEM_CHANGED = "system_changed"
    IMPORTED = "imported"
    RESET_FROM_INITIAL = "reset_from_initial"
