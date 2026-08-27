"""Canonical audience policy for persisted chat resources."""

from __future__ import annotations

from app.domain.chat import ChatVisibility
from app.domain.roles import PlayerRole


INTERNAL_AUDIENCE_KEY = "_audience_user_ids"


class ChatVisibilityPolicy:
    @staticmethod
    def can_view(*, message: dict, user_id: str, member_role: str | None) -> bool:
        if member_role is None:
            return False
        visibility = str(message.get("visibility") or "")
        author_id = str(message.get("author_user_id") or "")
        audience = {
            str(value) for value in message.get(INTERNAL_AUDIENCE_KEY) or [] if value
        }
        if visibility in {ChatVisibility.PUBLIC.value, ChatVisibility.SYSTEM.value}:
            return True
        if visibility == ChatVisibility.GM_ONLY.value:
            return (
                member_role == PlayerRole.GM.value
                or user_id == author_id
                or user_id in audience
            )
        if visibility == ChatVisibility.WHISPER.value:
            return user_id == author_id or user_id in audience
        if visibility == ChatVisibility.SELF.value:
            return user_id == author_id
        return False

