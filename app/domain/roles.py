from __future__ import annotations

from enum import StrEnum


class PlayerRole(StrEnum):
    GM = "gm"
    ASSISTANT_GM = "assistant_gm"
    PLAYER = "player"
    STREAMER = "streamer"


class SystemRole(StrEnum):
    OWNER = "owner"
    USER = "user"


def has_full_view(member_role: str | None) -> bool:
    """Roles that read the entire table like the GM.

    STREAMER is a strictly read-only *omniscient viewer* — it sees everything the
    GM sees (hidden tokens, the map under fog, GM-only sheets/journals) but holds
    no write authority. Use this only for read/visibility branches; write and
    edit checks must keep comparing against ``PlayerRole.GM`` so a streamer can
    never mutate table state.
    """
    return member_role in (PlayerRole.GM.value, PlayerRole.STREAMER.value)
