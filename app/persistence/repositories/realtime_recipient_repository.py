from __future__ import annotations

from sqlalchemy import select

from app.domain.roles import PlayerRole
from app.persistence.database import all_dicts
from app.persistence.database import engine_connect
from app.persistence.tables import campaign_members as members_table
from app.persistence.tables import users as users_table


class RealtimeRecipientRepository:
    def list_room_member_user_ids(self, room_id: str) -> list[str]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(members_table.c.user_id)
                    .where(members_table.c.campaign_id == room_id)
                    .order_by(members_table.c.created_at.asc())
                )
            )
        return [row["user_id"] for row in rows]

    def list_room_member_user_ids_except(self, *, room_id: str, excluded_player_ids: list[str]) -> list[str]:
        user_ids = self.list_room_member_user_ids(room_id)
        if not excluded_player_ids:
            return user_ids
        excluded = set(excluded_player_ids)
        return [user_id for user_id in user_ids if user_id not in excluded]

    def list_role_member_user_ids(self, *, room_id: str, role: PlayerRole) -> list[str]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(members_table.c.user_id)
                    .where(members_table.c.campaign_id == room_id)
                    .where(members_table.c.role == role.value)
                    .order_by(members_table.c.created_at.asc())
                )
            )
        return [row["user_id"] for row in rows]

    def list_gm_user_ids(self, room_id: str) -> list[str]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(members_table.c.user_id)
                    .where(members_table.c.campaign_id == room_id)
                    .where(members_table.c.role.in_([PlayerRole.GM.value, PlayerRole.ASSISTANT_GM.value]))
                    .order_by(members_table.c.created_at.asc())
                )
            )
        return [row["user_id"] for row in rows]

    def list_players_in_room_user_ids(self, room_id: str) -> list[str]:
        return self.list_role_member_user_ids(room_id=room_id, role=PlayerRole.PLAYER)

    def list_streamer_user_ids(self, room_id: str) -> list[str]:
        return self.list_role_member_user_ids(room_id=room_id, role=PlayerRole.STREAMER)

    def list_all_user_ids(self) -> list[str]:
        with engine_connect() as conn:
            rows = all_dicts(conn.execute(select(users_table.c.id).order_by(users_table.c.created_at.asc())))
        return [row["id"] for row in rows]
