from __future__ import annotations

from enum import StrEnum


class ChatVisibility(StrEnum):
    PUBLIC = "public"
    GM_ONLY = "gm_only"
    WHISPER = "whisper"
    SELF = "self"
    SYSTEM = "system"


class ChatMessageKind(StrEnum):
    TEXT = "text"
    ROLL = "roll"
    SYSTEM = "system"
    EMOTE = "emote"
