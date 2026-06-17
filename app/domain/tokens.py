from __future__ import annotations

from enum import StrEnum


class TokenDisposition(StrEnum):
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    HOSTILE = "hostile"
    UNKNOWN = "unknown"


class TokenActorLinkMode(StrEnum):
    LINKED = "linked"
    UNLINKED = "unlinked"


class TokenControlledByRole(StrEnum):
    GM = "gm"
    OWNER = "owner"
    PARTY = "party"
    NONE = "none"


class TokenConditionKind(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class TokenBarVisibility(StrEnum):
    GM_ONLY = "gm_only"
    OWNER_ONLY = "owner_only"
    OWNER_AND_GM = "owner_and_gm"
    EVERYONE = "everyone"
    HIDDEN = "hidden"
