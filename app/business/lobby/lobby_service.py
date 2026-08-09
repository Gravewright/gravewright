from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import and_, or_, select

from app.persistence.database import engine_connect
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.lobby_repository import LobbyRepository
from app.persistence.repositories.presence_repository import PresenceRepository
from app.persistence.tables import actor_owners, actors_core, campaign_members, users
from app.realtime.presence import ONLINE_THRESHOLD_SECONDS

ASSET_STATES = {"unknown", "loading", "ready", "error"}


@dataclass(frozen=True)
class LobbyResult:
    success: bool
    state: dict | None = None
    members: list[dict] = field(default_factory=list)
    actors: list[dict] = field(default_factory=list)
    error_key: str | None = None


class LobbyService:
    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.repository = LobbyRepository()
        self.presence = PresenceRepository()

    def update(self, *, campaign_id: str, user_id: str, is_ready: bool,
               selected_actor_id: str | None, assets_state: str) -> LobbyResult:
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if role is None:
            return LobbyResult(False, error_key="lobby.errors.denied")
        if assets_state not in ASSET_STATES:
            return LobbyResult(False, error_key="lobby.errors.invalid_assets_state")
        actor_id = selected_actor_id.strip() if selected_actor_id else None
        if actor_id and not self._can_select_actor(
            campaign_id=campaign_id, user_id=user_id, role=role, actor_id=actor_id
        ):
            return LobbyResult(False, error_key="lobby.errors.invalid_actor")
        state = self.repository.set_state(
            campaign_id=campaign_id, user_id=user_id, is_ready=is_ready,
            selected_actor_id=actor_id, assets_state=assets_state,
        )
        return LobbyResult(True, state=state)

    def snapshot(self, *, campaign_id: str, user_id: str) -> LobbyResult:
        requester_role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if requester_role is None:
            return LobbyResult(False, error_key="lobby.errors.denied")
        self.presence.mark_stale_room_presence_offline(
            threshold_seconds=ONLINE_THRESHOLD_SECONDS
        )
        states = {row["user_id"]: row for row in self.repository.list_campaign(campaign_id)}
        with engine_connect() as connection:
            rows = connection.execute(select(
                campaign_members.c.user_id, campaign_members.c.role, users.c.name,
            ).join(users, users.c.id == campaign_members.c.user_id).where(
                campaign_members.c.campaign_id == campaign_id
            )).mappings().all()
            online = self.presence.list_online_user_ids_by_room(
                room_ids=[campaign_id], threshold_seconds=ONLINE_THRESHOLD_SECONDS
            ).get(campaign_id, set())
            actor_ids = {state["selected_actor_id"] for state in states.values() if state["selected_actor_id"]}
            actor_names = {}
            if actor_ids:
                actor_names = dict(connection.execute(select(
                    actors_core.c.id, actors_core.c.name
                ).where(actors_core.c.id.in_(actor_ids))).all())
            actor_statement = select(actors_core.c.id, actors_core.c.name).outerjoin(
                actor_owners,
                and_(actor_owners.c.actor_id == actors_core.c.id, actor_owners.c.user_id == user_id),
            ).where(
                actors_core.c.campaign_id == campaign_id,
                actors_core.c.status == "active",
                or_(requester_role == "gm", actor_owners.c.user_id == user_id),
            ).order_by(actors_core.c.name.asc())
            selectable_actors = [
                dict(row) for row in connection.execute(actor_statement).mappings()
            ]
        members = []
        for row in rows:
            state = states.get(row["user_id"], {})
            actor_id = state.get("selected_actor_id")
            members.append({
                "user_id": row["user_id"], "name": row["name"], "role": row["role"],
                "is_online": row["user_id"] in online,
                "is_ready": bool(state.get("is_ready", 0)),
                "selected_actor_id": actor_id,
                "selected_actor_name": actor_names.get(actor_id),
                "assets_state": state.get("assets_state", "unknown"),
                "updated_at": state.get("updated_at"),
            })
        return LobbyResult(True, members=members, actors=selectable_actors)

    @staticmethod
    def _can_select_actor(*, campaign_id: str, user_id: str, role: str, actor_id: str) -> bool:
        with engine_connect() as connection:
            statement = select(actors_core.c.id).outerjoin(
                actor_owners,
                and_(actor_owners.c.actor_id == actors_core.c.id, actor_owners.c.user_id == user_id),
            ).where(
                actors_core.c.id == actor_id, actors_core.c.campaign_id == campaign_id,
                actors_core.c.status == "active",
                or_(role == "gm", actor_owners.c.user_id == user_id),
            )
            return connection.execute(statement).first() is not None
