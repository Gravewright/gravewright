from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from litestar import get, post
from litestar.params import Body, FromQuery
from litestar.response import Response

from app.business.lobby import LobbyService
from app.config import config
from app.helpers.async_blocking import run_blocking
from app.persistence.rows import Row
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport, websocket_manager


@dataclass
class LobbyStateBody:
    campaign_id: str = ""
    is_ready: bool = False
    selected_actor_id: str | None = None
    assets_state: str = "unknown"


def _disabled() -> Response[dict[str, Any]] | None:
    if config.lobby_ready_check_enabled:
        return None
    return Response({"ok": False, "error_key": "lobby.errors.disabled"}, status_code=404)


def _error(error_key: str | None) -> Response[dict[str, Any]]:
    return Response(
        {"ok": False, "error_key": error_key},
        status_code=403 if error_key == "lobby.errors.denied" else 400,
    )


@post("/game/lobby/state")
async def update_lobby_state(
    current_user: Row,
    lobby_service: LobbyService,
    data: Annotated[LobbyStateBody, Body()],
) -> Response[dict[str, Any]]:
    if disabled := _disabled():
        return disabled
    campaign_id = data.campaign_id.strip()
    result = await run_blocking(
        lobby_service.update,
        campaign_id=campaign_id, user_id=current_user["id"], is_ready=data.is_ready,
        selected_actor_id=data.selected_actor_id, assets_state=data.assets_state.strip(),
    )
    if not result.success:
        return _error(result.error_key)
    connected = (
        await websocket_manager.connected_user_ids_by_room([campaign_id.strip()])
    ).get(campaign_id.strip(), set())
    for member in result.members:
        if member["user_id"] in connected:
            member["is_online"] = True

    await RealtimeTransport().to_room(
        room_id=campaign_id, event=TransportEvent.LOBBY_UPDATED,
        payload={"room_id": campaign_id},
    )
    return Response({"ok": True, "state": result.state}, status_code=200)


@get("/game/lobby")
async def get_lobby(
    current_user: Row,
    lobby_service: LobbyService,
    campaign_id: FromQuery[str],
) -> Response[dict[str, Any]]:
    if disabled := _disabled():
        return disabled
    result = await run_blocking(
        lobby_service.snapshot, campaign_id=campaign_id.strip(), user_id=current_user["id"]
    )
    if not result.success:
        return _error(result.error_key)
    ready = sum(1 for member in result.members if member["is_ready"])
    return Response({
        "ok": True, "members": result.members, "actors": result.actors,
        "summary": {"ready": ready, "total": len(result.members)},
    }, status_code=200)
