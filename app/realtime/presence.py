from __future__ import annotations

import time

from app.contracts.transport import RealtimeGatewayContract
from app.helpers.async_blocking import run_blocking
from app.realtime.events import TransportEvent
from app.persistence.repositories.presence_repository import PresenceRepository


ONLINE_THRESHOLD_SECONDS = 12


class PresenceService:
    def __init__(self) -> None:
        self.presence = PresenceRepository()

    async def touch(
        self,
        *,
        user_id: str,
        room_ids: list[str],
        transport: RealtimeGatewayContract,
    ) -> None:
        now = int(time.time())

        await run_blocking(self.presence.touch, user_id)

        changed_room_ids = await run_blocking(
            self.presence.touch_user_rooms,
            user_id=user_id,
            room_ids=room_ids,
            threshold_seconds=ONLINE_THRESHOLD_SECONDS,
        )

        for room_id in changed_room_ids:
            await transport.to_room(
                room_id=room_id,
                event=TransportEvent.PRESENCE_UPDATED,
                payload={
                    "room_id": room_id,
                    "user_id": user_id,
                    "is_online": True,
                    "last_seen_at": now,
                },
            )

    async def leave(
        self,
        *,
        user_id: str,
        room_ids: list[str],
        transport: RealtimeGatewayContract,
    ) -> None:
        now = int(time.time())

        changed_room_ids = await run_blocking(
            self.presence.leave_user_rooms,
            user_id=user_id,
            room_ids=room_ids,
        )

        for room_id in changed_room_ids:
            await transport.to_room_except(
                room_id=room_id,
                excluded_player_ids=[user_id],
                event=TransportEvent.PRESENCE_UPDATED,
                payload={
                    "room_id": room_id,
                    "user_id": user_id,
                    "is_online": False,
                    "last_seen_at": now,
                },
            )

    def list_online_user_ids(self, user_ids: list[str]) -> set[str]:
        return self.presence.list_online_user_ids(
            user_ids=user_ids,
            threshold_seconds=ONLINE_THRESHOLD_SECONDS,
        )

    def list_online_user_ids_by_room(self, room_ids: list[str]) -> dict[str, set[str]]:
        self.presence.mark_stale_room_presence_offline(
            threshold_seconds=ONLINE_THRESHOLD_SECONDS,
        )

        return self.presence.list_online_user_ids_by_room(
            room_ids=room_ids,
            threshold_seconds=ONLINE_THRESHOLD_SECONDS,
        )

    async def send_snapshot(
        self,
        *,
        player_id: str,
        room_id: str,
        players: list[dict[str, str | bool]],
        transport: RealtimeGatewayContract,
    ) -> None:
        await transport.to_player(
            player_id=player_id,
            event=TransportEvent.PRESENCE_SNAPSHOT,
            payload={
                "room_id": room_id,
                "players": players,
            },
        )
