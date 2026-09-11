"""Trusted in-process extension events, emitted only after commit."""
from dataclasses import dataclass
from uuid import UUID
from django.dispatch import Signal


@dataclass(frozen=True, slots=True)
class Change:
    campaign_id: UUID
    user_id: UUID
    resource: str
    action: str
    request_id: UUID


resource_changed = Signal()
