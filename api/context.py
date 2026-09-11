"""Identifiers only: a context never caches roles or grants authority."""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Context:
    """A normalized campaign/user pair, without a cached role or permission grant."""
    campaign_id: UUID
    user_id: UUID

    def __post_init__(self):
        object.__setattr__(self, 'campaign_id', UUID(str(self.campaign_id)))
        object.__setattr__(self, 'user_id', UUID(str(self.user_id)))

    @classmethod
    def from_request(cls, request, campaign_id):
        """Build a context after checking the authenticated user's live membership."""
        from gravewright.journals.services import member, JournalError
        if not request.user.is_authenticated:
            raise JournalError('Authentication required.', 'not_a_member')
        context = cls(campaign_id, request.user.pk)
        member(context.campaign_id, context.user_id)
        return context
