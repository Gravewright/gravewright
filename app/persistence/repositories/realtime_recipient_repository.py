from __future__ import annotations

import threading
import time

from sqlalchemy import select

from app.domain.roles import PlayerRole
from app.persistence.database import all_dicts
from app.persistence.database import engine_connect
from app.persistence.tables import campaign_members as members_table
from app.persistence.tables import users as users_table


# P2: every realtime broadcast used to issue one role-filtered SELECT per
# audience (GM, players, streamers, ...). Room membership barely changes during
# a session, so we cache the full (user_id, role) roster per room and derive any
# audience subset in memory. A short TTL bounds staleness (a freshly added/
# removed member or role change is reflected within the TTL) without having to
# hook every membership mutation — broadcasts are eventually consistent anyway
# (clients also receive a fresh roster snapshot when they (re)connect).
_CACHE_TTL_SECONDS = 3.0
_GM_ROLES = frozenset({PlayerRole.GM.value, PlayerRole.ASSISTANT_GM.value})

_cache: dict[str, tuple[float, tuple[tuple[str, str], ...]]] = {}
_cache_lock = threading.Lock()


def invalidate(room_id: str) -> None:
    """Drop the cached roster for a room (call after a membership change)."""
    with _cache_lock:
        _cache.pop(room_id, None)


def invalidate_all() -> None:
    with _cache_lock:
        _cache.clear()


class RealtimeRecipientRepository:
    def _members(self, room_id: str) -> tuple[tuple[str, str], ...]:
        """Cached ``(user_id, role)`` roster for a room, newest-membership last."""
        now = time.monotonic()
        with _cache_lock:
            cached = _cache.get(room_id)
            if cached is not None and cached[0] > now:
                return cached[1]

        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(members_table.c.user_id, members_table.c.role)
                    .where(members_table.c.campaign_id == room_id)
                    .order_by(members_table.c.created_at.asc())
                )
            )
        members = tuple((row["user_id"], row["role"]) for row in rows)

        with _cache_lock:
            _cache[room_id] = (now + _CACHE_TTL_SECONDS, members)
        return members

    def list_room_member_user_ids(self, room_id: str) -> list[str]:
        return [user_id for user_id, _ in self._members(room_id)]

    def list_room_member_user_ids_except(self, *, room_id: str, excluded_player_ids: list[str]) -> list[str]:
        excluded = set(excluded_player_ids)
        return [user_id for user_id, _ in self._members(room_id) if user_id not in excluded]

    def list_role_member_user_ids(self, *, room_id: str, role: PlayerRole) -> list[str]:
        return [user_id for user_id, member_role in self._members(room_id) if member_role == role.value]

    def list_gm_user_ids(self, room_id: str) -> list[str]:
        return [user_id for user_id, role in self._members(room_id) if role in _GM_ROLES]

    def list_players_in_room_user_ids(self, room_id: str) -> list[str]:
        return self.list_role_member_user_ids(room_id=room_id, role=PlayerRole.PLAYER)

    def list_streamer_user_ids(self, room_id: str) -> list[str]:
        return self.list_role_member_user_ids(room_id=room_id, role=PlayerRole.STREAMER)

    def list_token_audience_user_ids(self, *, room_id: str, include_players: bool) -> list[str]:
        """Recipients for a token event: the whole room, or the room minus plain
        players when the token is hidden. Lets the caller fan out with a single
        delivery (one event-log row, one send) instead of one per audience."""
        if include_players:
            return [user_id for user_id, _ in self._members(room_id)]
        return [
            user_id
            for user_id, role in self._members(room_id)
            if role != PlayerRole.PLAYER.value
        ]

    def list_all_user_ids(self) -> list[str]:
        with engine_connect() as conn:
            rows = all_dicts(conn.execute(select(users_table.c.id).order_by(users_table.c.created_at.asc())))
        return [row["id"] for row in rows]
