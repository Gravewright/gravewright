"""Shared authority and value rules for the SDK semantic runtimes.

Durable workflows, gameplay flows, token transfers and semantic timelines are
separate domains, but they answer the same three questions the same way: is this
identifier well formed, is this value safe to persist, and may this principal
address this audience. Those answers live here so the domains cannot drift apart
on the parts that must stay identical.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from app.persistence.repositories.campaign_repository import CampaignRepository


#: Identifiers a package may choose for its own definitions and context keys.
IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]{1,191}$")
#: A registered action reference: ``package:action@version``.
ACTION_REFERENCE = re.compile(r"^([A-Za-z0-9._-]+):([A-Za-z0-9._-]+)@([1-9][0-9]*)$")
#: Statuses no semantic instance may leave.
TERMINAL_STATUSES = {"COMPLETED", "CANCELLED", "FAILED"}


@dataclass(frozen=True)
class SemanticResult:
    """Outcome of a semantic operation, carrying a stable error key on failure."""

    success: bool
    value: Any = None
    error_key: str | None = None


def role_of(campaign_id: str, user_id: str) -> str | None:
    return CampaignRepository().get_member_role(campaign_id=campaign_id, user_id=user_id)


def is_gm(campaign_id: str, user_id: str) -> bool:
    return role_of(campaign_id, user_id) in {"gm", "assistant_gm"}


def is_json_safe(value: Any) -> bool:
    """Reject anything that cannot round-trip as bounded, finite JSON."""
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return len(value) <= 128 and all(is_json_safe(item) for item in value)
    if isinstance(value, dict):
        return len(value) <= 128 and all(
            isinstance(key, str) and len(key) <= 191 and is_json_safe(item)
            for key, item in value.items()
        )
    return False


def resolve_audience(campaign_id: str, user_id: str, value: Any) -> dict:
    """Expand an audience to concrete members, refusing to widen a player's reach.

    Raises ``ValueError`` for a malformed audience and ``PermissionError`` when a
    non-GM addresses anyone other than themselves.
    """
    if not isinstance(value, dict) or set(value) - {"kind", "ids"} or value.get("kind") not in {
        "self", "campaign", "gm", "users"
    }:
        raise ValueError
    members = CampaignRepository().list_members(campaign_id=campaign_id)
    member_ids = {row["user_id"] for row in members}
    kind = value["kind"]
    if kind == "self":
        ids = [user_id]
    elif kind == "campaign":
        ids = list(member_ids)
    elif kind == "gm":
        ids = [row["user_id"] for row in members if row.get("role") in {"gm", "assistant_gm"}]
    else:
        raw_ids = value.get("ids", [])
        if not isinstance(raw_ids, list):
            raise ValueError
        ids = list(dict.fromkeys(map(str, raw_ids)))
    if len(ids) > 64 or any(item not in member_ids for item in ids):
        raise ValueError
    if set(ids) != {user_id} and not is_gm(campaign_id, user_id):
        raise PermissionError
    return {"kind": kind, "ids": ids}
