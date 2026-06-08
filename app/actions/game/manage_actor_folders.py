"""Actor owner toggle + folder CRUD (mirrors the journals folder/owner actions).

Form-urlencoded POST endpoints used by the Actors panel context menu. They
return JSON when the client sends ``Accept: application/json`` (the panel does),
otherwise redirect back to ``/game``.
"""

from __future__ import annotations

from app.persistence.rows import Row
from typing import Any

from litestar import Request, get, post
from litestar.params import FromPath
from litestar.response import Redirect, Response, Template

from app.business.game_page_service import GamePageService
from app.engine.actors.actor_service import ActorService
from app.helpers.view import view_context


@get("/game/actors/panel/{campaign_id:str}")
async def actors_panel_fragment(
    campaign_id: FromPath[str], cookies: dict[str, str], current_user: Row, game_page_service: GamePageService
) -> Redirect | Template:
    """Server-rendered Actors panel body, fetched by the client to refresh the
    panel in place after a mutation (no full-page reload)."""
    user = current_user
    room = next(
        (r for r in game_page_service.build_context(user_id=user["id"]).rooms
         if r["id"] == campaign_id),
        None,
    )
    if room is None:
        return Redirect(path="/game")
    return Template(
        template_name="pages/game/_actors_panel.html",
        context=view_context(cookies, room=room),
    )


def _str(form: Any, key: str, default: str = "") -> str:
    return str(form.get(key) or default)


def _wants_json(request: Request) -> bool:
    return "application/json" in request.headers.get("accept", "")


async def _authenticated_form(request: Request, cookies: dict[str, str], current_user: Row):
    form = await request.form()
    return current_user, form, None


def _result_response(request: Request, result, *, payload: dict | None = None, created: bool = False):
    if _wants_json(request):
        if not result.success:
            return Response({"error_key": result.error_key}, status_code=400)
        return Response(payload or {"ok": True}, status_code=201 if created else 200)
    return Redirect(path="/game")


@post("/game/actor/owner")
async def toggle_actor_owner(request: Request, cookies: dict[str, str], current_user: Row, actor_service: ActorService) -> Response[dict[str, Any]] | Redirect:
    user, form, early = await _authenticated_form(request, cookies, current_user)
    if early is not None:
        return early
    assert user is not None
    actor_id = _str(form, "actor_id")
    owner_user_id = _str(form, "owner_user_id")
    result = actor_service.toggle_owner(
        actor_id=actor_id, user_id_to_toggle=owner_user_id, requester_user_id=user["id"]
    )
    if _wants_json(request) and result.success:
        owners = actor_service.list_owners(actor_id=actor_id)
        return Response(
            {
                "actor_id": actor_id,
                "toggled_user_id": owner_user_id,
                "is_owner": result.is_owner,
                "owners": owners,
            },
            status_code=200,
        )
    return _result_response(request, result)


@post("/game/actor/move")
async def move_actor(request: Request, cookies: dict[str, str], current_user: Row, actor_service: ActorService) -> Response[dict[str, Any]] | Redirect:
    user, form, early = await _authenticated_form(request, cookies, current_user)
    if early is not None:
        return early
    assert user is not None
    result = actor_service.move_actor(
        actor_id=_str(form, "actor_id"),
        target_folder_id=_str(form, "folder_id"),
        user_id=user["id"],
    )
    return _result_response(request, result, payload={"folder_id": result.folder_id or ""})


@post("/game/actor-folder")
async def create_actor_folder(request: Request, cookies: dict[str, str], current_user: Row, actor_service: ActorService) -> Response[dict[str, Any]] | Redirect:
    user, form, early = await _authenticated_form(request, cookies, current_user)
    if early is not None:
        return early
    assert user is not None
    result = actor_service.create_folder(
        campaign_id=_str(form, "campaign_id"),
        user_id=user["id"],
        name=_str(form, "name"),
        parent_id=_str(form, "parent_id"),
        color=_str(form, "color"),
    )
    return _result_response(request, result, payload={"folder_id": result.folder_id}, created=True)


@post("/game/actor-folder/rename")
async def rename_actor_folder(request: Request, cookies: dict[str, str], current_user: Row, actor_service: ActorService) -> Response[dict[str, Any]] | Redirect:
    user, form, early = await _authenticated_form(request, cookies, current_user)
    if early is not None:
        return early
    assert user is not None
    result = actor_service.rename_folder(
        folder_id=_str(form, "folder_id"), name=_str(form, "name"), user_id=user["id"]
    )
    return _result_response(request, result, payload={"folder_id": result.folder_id or ""})


@post("/game/actor-folder/color")
async def set_actor_folder_color(request: Request, cookies: dict[str, str], current_user: Row, actor_service: ActorService) -> Response[dict[str, Any]] | Redirect:
    user, form, early = await _authenticated_form(request, cookies, current_user)
    if early is not None:
        return early
    assert user is not None
    result = actor_service.set_folder_color(
        folder_id=_str(form, "folder_id"), color=_str(form, "color"), user_id=user["id"]
    )
    return _result_response(request, result, payload={"folder_id": result.folder_id or ""})


@post("/game/actor-folder/delete")
async def delete_actor_folder(request: Request, cookies: dict[str, str], current_user: Row, actor_service: ActorService) -> Response[dict[str, Any]] | Redirect:
    user, form, early = await _authenticated_form(request, cookies, current_user)
    if early is not None:
        return early
    assert user is not None
    result = actor_service.delete_folder(folder_id=_str(form, "folder_id"), user_id=user["id"])
    return _result_response(request, result)


@post("/game/actor-folder/move")
async def move_actor_folder(request: Request, cookies: dict[str, str], current_user: Row, actor_service: ActorService) -> Response[dict[str, Any]] | Redirect:
    user, form, early = await _authenticated_form(request, cookies, current_user)
    if early is not None:
        return early
    assert user is not None
    result = actor_service.move_folder(
        folder_id=_str(form, "folder_id"),
        target_parent_id=_str(form, "parent_id"),
        user_id=user["id"],
    )
    return _result_response(request, result, payload={"folder_id": result.folder_id or ""})
