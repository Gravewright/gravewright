from __future__ import annotations

import inspect
import json
from app.persistence.rows import Row
from typing import Any
from urllib.parse import urlencode

from litestar import Request, get, post
from litestar.exceptions import NotAuthorizedException, NotFoundException
from litestar.params import FromPath
from litestar.response import File, Redirect, Response, Template

from app.engine.journals.journal_asset_service import JournalAssetService
from app.engine.journals.journal_asset_read_service import JournalAssetReadService
from app.engine.journals.journal_page_service import JournalPageService
from app.engine.journals.journal_service import JournalResult, JournalService
from app.business.game_page_service import GamePageService
from app.helpers.env import PROJECT_ROOT
from app.helpers.view import view_context
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


def _wants_json(request: Any) -> bool:
    return "application/json" in request.headers.get("accept", "")


def _str(form: Any, key: str, default: str = "") -> str:
    return str(form.get(key) or default)


def _bool(form: Any, key: str) -> bool:
    return key in form and str(form.get(key)).lower() not in {"", "0", "false", "off"}


def _list(form: Any, key: str) -> list[str]:
    # Litestar's FormMultiDict exposes repeated values via ``getall`` (not
    # ``getlist``); ``form.get`` only returns the first value, which silently
    # dropped extra entries (e.g. board reorder / multi-owner shares).
    getall = getattr(form, "getall", None)
    if callable(getall):
        values = getall(key, [])
    elif hasattr(form, "getlist"):
        values = form.getlist(key)
    else:
        value = form.get(key)
        values = value if isinstance(value, list) else [value]
    return [str(value) for value in values if value]


def _json_field(form: Any, key: str) -> list:
    try:
        decoded = json.loads(_str(form, key, "[]"))
    except (TypeError, ValueError):
        return []
    return decoded if isinstance(decoded, list) else []


def _json_object(form: Any, key: str) -> dict:
    try:
        decoded = json.loads(_str(form, key, "{}"))
    except (TypeError, ValueError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _has_field(form: Any, key: str) -> bool:
    return key in form


async def _read_upload_file(upload: object) -> bytes:
    read = getattr(upload, "read", None)
    if read is None:
        return b""
    data = read()
    if inspect.isawaitable(data):
        data = await data
    return data


def _build_data(form: Any, journal_type: str) -> dict | None:
    """Translate flat form fields into the structured ``data`` dict per type."""
    if journal_type == "diary":
                                                                                
                                                                              
        if not _has_field(form, "content_doc"):
            return None
        return {
            "content": _json_object(form, "content_doc"),
            "cover": {"src": _str(form, "diary_image_src")},
            "gm": {
                "notes": _json_object(form, "gm_notes_doc"),
                "secrets": _json_object(form, "gm_secrets_doc"),
            },
        }
    if journal_type == "quest":
        return {
            "status": _str(form, "quest_status", "draft"),
            "public": {
                "summary": _str(form, "public_summary"),
                "description": _json_object(form, "public_description_doc"),
                "image": {"src": _str(form, "public_image_src")},
                "location": _str(form, "public_location"),
                "giver": _str(form, "public_giver"),
            },
            "gm": {
                "notes": _json_object(form, "gm_notes_doc"),
                "secrets": _json_object(form, "gm_secrets_doc"),
            },
            "objectives": _json_field(form, "objectives_json"),
            "rewards": _json_field(form, "rewards_json"),
            "tags": [tag.strip() for tag in _str(form, "tags").split(",") if tag.strip()],
        }
    if journal_type == "quest_board":
        return {
            "description": _json_object(form, "board_description_doc"),
            "image": {"src": _str(form, "board_image_src")},
            "filters": {
                "showAvailable": _bool(form, "board_show_available"),
                "showActive": _bool(form, "board_show_active"),
                "showCompleted": _bool(form, "board_show_completed"),
                "showFailed": _bool(form, "board_show_failed"),
            },
        }
    return None


def _journal_redirect(campaign_id: str) -> Redirect:
    query = urlencode({"room": campaign_id, "open_modal": f"panel-journal-{campaign_id}"})
    return Redirect(path=f"/game?{query}")


async def _emit(event: TransportEvent, result: JournalResult, *, user_id: str) -> None:
    if not result.success or not result.campaign_id:
        return
    payload: dict[str, Any] = {
        "room_id": result.campaign_id,
        "journal_id": result.journal_id,
        "type": result.journal_type or "",
        "updated_by": user_id,
    }
    if result.version is not None:
        payload["version"] = result.version
    if result.changed_paths:
        payload["changed_paths"] = result.changed_paths
    await RealtimeTransport().to_room(
        room_id=result.campaign_id,
        event=event,
        payload=payload,
    )


async def _authenticated_form(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
) -> tuple[dict[str, Any] | None, Any, Response[dict[str, Any]] | Redirect | None]:
    form = await request.form()
    return current_user, form, None


@post("/game/journal")
async def create_journal(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_service: JournalService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    journal_type = _str(form, "type", "diary")
    result = journal_service.create_journal(
        campaign_id=_str(form, "campaign_id"),
        user_id=user["id"],
        journal_type=journal_type,
        title=_str(form, "title"),
        folder_id=_str(form, "folder_id"),
        visibility=_str(form, "visibility", "private"),
        content_markdown=_str(form, "content_markdown"),
        data=_build_data(form, journal_type),
        owner_user_ids=_list(form, "owner_user_ids") if _has_field(form, "owner_user_ids") else None,
    )
    await _emit(TransportEvent.JOURNAL_CREATED, result, user_id=user["id"])

    if _wants_json(request):
        if result.success:
            return Response({"journal_id": result.journal_id}, status_code=201)
        return Response({"error_key": result.error_key}, status_code=400)

    if result.success and result.journal_id:
        query = urlencode({
            "room": _str(form, "campaign_id"),
            "open_modal": f"journal-{result.journal_id}",
        })
        return Redirect(path=f"/game?{query}")
    return _journal_redirect(_str(form, "campaign_id"))


@post("/game/journal/update")
async def update_journal(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_service: JournalService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    journal_type = _str(form, "type", "diary")
    result = journal_service.update_journal(
        journal_id=_str(form, "journal_id"),
        user_id=user["id"],
        title=_str(form, "title"),
        folder_id=_str(form, "folder_id"),
        visibility=_str(form, "visibility", "private"),
        content_markdown=_str(form, "content_markdown"),
        data=_build_data(form, journal_type),
        owner_user_ids=_list(form, "owner_user_ids") if _has_field(form, "owner_user_ids") else None,
    )
    if result.success:
        result = JournalResult(
            success=True,
            journal_id=result.journal_id,
            campaign_id=result.campaign_id,
            journal_type=result.journal_type,
            version=result.version,
            changed_paths=["*"],
        )
    await _emit(TransportEvent.JOURNAL_UPDATED, result, user_id=user["id"])

    if _wants_json(request):
        if result.success:
            return Response({"ok": True, "version": result.version}, status_code=200)
        return Response({"error_key": result.error_key}, status_code=400)

    campaign_id = result.campaign_id or _str(form, "campaign_id")
    return _journal_redirect(campaign_id)


@post("/game/journal/delete")
async def delete_journal(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_service: JournalService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    result = journal_service.delete_journal(
        journal_id=_str(form, "journal_id"),
        requester_user_id=user["id"],
    )
    await _emit(TransportEvent.JOURNAL_DELETED, result, user_id=user["id"])

    if _wants_json(request):
        if result.success:
            return Response({"ok": True}, status_code=200)
        return Response({"error_key": result.error_key}, status_code=400)

    if not result.success:
        return Redirect(path="/game")
    return _journal_redirect(result.campaign_id or "")


@post("/game/journal/quest/status")
async def set_quest_status(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_service: JournalService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    result = journal_service.set_quest_status(
        quest_id=_str(form, "journal_id"),
        status=_str(form, "status"),
        requester_user_id=user["id"],
    )
    await _emit(TransportEvent.QUEST_STATUS_CHANGED, result, user_id=user["id"])

    if _wants_json(request):
        if result.success:
            return Response({"ok": True, "version": result.version}, status_code=200)
        return Response({"error_key": result.error_key}, status_code=400)

    if not result.success:
        return Redirect(path="/game")
    return _journal_redirect(result.campaign_id or "")


@post("/game/journal/quest/objective")
async def toggle_quest_objective(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_service: JournalService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    result = journal_service.toggle_objective(
        quest_id=_str(form, "journal_id"),
        objective_id=_str(form, "objective_id"),
        completed=_bool(form, "completed"),
        requester_user_id=user["id"],
    )
    await _emit(TransportEvent.QUEST_OBJECTIVE_UPDATED, result, user_id=user["id"])

    if _wants_json(request):
        if result.success:
            return Response({"ok": True, "version": result.version}, status_code=200)
        return Response({"error_key": result.error_key}, status_code=400)

    if not result.success:
        return Redirect(path="/game")
    return _journal_redirect(result.campaign_id or "")


@post("/game/journal/board/add")
async def board_add_quest(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_service: JournalService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    result = journal_service.add_quest_to_board(
        board_id=_str(form, "board_id"),
        quest_id=_str(form, "quest_id"),
        requester_user_id=user["id"],
        pinned=_bool(form, "pinned"),
    )
    await _emit(TransportEvent.QUEST_BOARD_UPDATED, result, user_id=user["id"])

    if _wants_json(request):
        if result.success:
            return Response({"ok": True}, status_code=200)
        return Response({"error_key": result.error_key}, status_code=400)

    if not result.success:
        return Redirect(path="/game")
    return _journal_redirect(result.campaign_id or "")


@post("/game/journal/board/remove")
async def board_remove_quest(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_service: JournalService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    result = journal_service.remove_quest_from_board(
        board_id=_str(form, "board_id"),
        quest_id=_str(form, "quest_id"),
        requester_user_id=user["id"],
    )
    await _emit(TransportEvent.QUEST_BOARD_UPDATED, result, user_id=user["id"])

    if _wants_json(request):
        if result.success:
            return Response({"ok": True}, status_code=200)
        return Response({"error_key": result.error_key}, status_code=400)

    if not result.success:
        return Redirect(path="/game")
    return _journal_redirect(result.campaign_id or "")


@post("/game/journal/board/reorder")
async def board_reorder(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_service: JournalService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    result = journal_service.reorder_board(
        board_id=_str(form, "board_id"),
        ordered_quest_ids=_list(form, "quest_ids"),
        requester_user_id=user["id"],
    )
    await _emit(TransportEvent.QUEST_BOARD_UPDATED, result, user_id=user["id"])

    if _wants_json(request):
        if result.success:
            return Response({"ok": True}, status_code=200)
        return Response({"error_key": result.error_key}, status_code=400)

    if not result.success:
        return Redirect(path="/game")
    return _journal_redirect(result.campaign_id or "")


@post("/game/journal/board/pin")
async def board_pin_quest(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_service: JournalService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    result = journal_service.set_board_quest_pinned(
        board_id=_str(form, "board_id"),
        quest_id=_str(form, "quest_id"),
        pinned=_bool(form, "pinned"),
        requester_user_id=user["id"],
    )
    await _emit(TransportEvent.QUEST_BOARD_UPDATED, result, user_id=user["id"])

    if _wants_json(request):
        if result.success:
            return Response({"ok": True}, status_code=200)
        return Response({"error_key": result.error_key}, status_code=400)

    if not result.success:
        return Redirect(path="/game")
    return _journal_redirect(result.campaign_id or "")


@post("/game/journal/folder")
async def create_journal_folder(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_service: JournalService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    result = journal_service.create_folder(
        campaign_id=_str(form, "campaign_id"),
        user_id=user["id"],
        name=_str(form, "name"),
        parent_id=_str(form, "parent_id"),
        color=_str(form, "color"),
    )

    if _wants_json(request):
        if result.success:
            return Response({"folder_id": result.folder_id}, status_code=201)
        return Response({"error_key": result.error_key}, status_code=400)

    return _journal_redirect(_str(form, "campaign_id"))


@get("/game/journals/panel/{campaign_id:str}")
async def journals_panel_fragment(
    campaign_id: FromPath[str], cookies: dict[str, str], current_user: Row, game_page_service: GamePageService
) -> Redirect | Template:
    """Server-rendered Journals tree, fetched to refresh the panel in place."""
    user = current_user
    room = next(
        (r for r in game_page_service.build_context(user_id=user["id"]).rooms
         if r["id"] == campaign_id),
        None,
    )
    if room is None:
        return Redirect(path="/game")
    return Template(
        template_name="pages/game/_journals_panel.html",
        context=view_context(cookies, room=room),
    )


@get("/game/journal/modal/{journal_id:str}")
async def show_journal_modal(
    journal_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    journal_page_service: JournalPageService,
) -> Redirect | Template:
    page = journal_page_service.build_modal(
        journal_id=journal_id,
        user_id=current_user["id"],
    )
    if page is None:
        return Redirect(path="/game")

    context = view_context(
        cookies,
        journal=page.journal,
        view=page.view,
        room_id=page.journal["campaign_id"],
        member_role=page.campaign["member_role"],
        is_gm=page.is_gm,
        can_edit=page.can_edit,
        journal_folders=page.journal_folders,
        room_members=page.room_members,
        board_quest_options=page.board_quest_options,
    )

    return Template(
        template_name="pages/game/_journal_modal.html",
        context=context,
    )


@get("/game/journal/modal/new/{campaign_id:str}")
async def show_journal_create_modal(
    campaign_id: FromPath[str],
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_page_service: JournalPageService,
) -> Redirect | Template:
    page = journal_page_service.build_create_modal(
        campaign_id=campaign_id,
        user_id=current_user["id"],
    )
    if page is None:
        return Redirect(path="/game")

    folder_id = request.query_params.get("folder_id", "") or ""
    default_type = request.query_params.get("type", "diary") or "diary"
    if default_type not in {"diary", "quest", "quest_board"}:
        default_type = "diary"

    context = view_context(
        cookies,
        room_id=campaign_id,
        member_role=page.campaign["member_role"],
        is_gm=page.is_gm,
        default_type=default_type,
        default_folder_id=folder_id,
        journal_folders=page.journal_folders,
        room_members=page.room_members,
    )

    return Template(
        template_name="pages/game/_journal_create_modal.html",
        context=context,
    )


@post("/game/journal/owner")
async def toggle_journal_owner(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_service: JournalService,
    journal_page_service: JournalPageService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    journal_id = _str(form, "journal_id")
    owner_user_id = _str(form, "owner_user_id")

    result = journal_service.toggle_owner(
        journal_id=journal_id,
        user_id_to_toggle=owner_user_id,
        requester_user_id=user["id"],
    )

    if _wants_json(request):
        if not result.success:
            return Response({"error_key": result.error_key}, status_code=400)
        owners = journal_page_service.list_owners(journal_id=journal_id)
        return Response(
            {
                "journal_id": journal_id,
                "toggled_user_id": owner_user_id,
                "is_owner": result.is_owner,
                "owners": owners,
            },
            status_code=200,
        )

    if not result.success:
        return Redirect(path="/game")
    return _journal_redirect(result.campaign_id or "")


@post("/game/journal/move")
async def move_journal(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_service: JournalService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    result = journal_service.move_journal(
        journal_id=_str(form, "journal_id"),
        target_folder_id=_str(form, "folder_id"),
        requester_user_id=user["id"],
    )

    if _wants_json(request):
        if not result.success:
            return Response({"error_key": result.error_key}, status_code=400)
        return Response({"folder_id": result.folder_id or ""}, status_code=200)

    if not result.success:
        return Redirect(path="/game")
    return _journal_redirect(result.campaign_id or "")


@post("/game/journal/folder/move")
async def move_journal_folder(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_service: JournalService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    result = journal_service.move_folder(
        folder_id=_str(form, "folder_id"),
        target_parent_id=_str(form, "parent_id"),
        requester_user_id=user["id"],
    )

    if _wants_json(request):
        if not result.success:
            return Response({"error_key": result.error_key}, status_code=400)
        return Response({"folder_id": result.folder_id or ""}, status_code=200)

    if not result.success:
        return Redirect(path="/game")
    return _journal_redirect(result.campaign_id or "")


@post("/game/journal/asset")
async def upload_journal_asset(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    journal_asset_service: JournalAssetService,
) -> Response[dict[str, Any]] | Redirect:
    user, form, early_response = await _authenticated_form(request, cookies, current_user)
    if early_response is not None:
        return early_response

    assert user is not None
    upload = form.get("file")
    data = await _read_upload_file(upload)
    result = journal_asset_service.upload_image(
        journal_id=_str(form, "journal_id"),
        user_id=user["id"],
        filename=str(getattr(upload, "filename", "") or ""),
        content_type=str(getattr(upload, "content_type", "") or ""),
        data=data,
        purpose=_str(form, "purpose", "journal_image"),
    )
    if result.success:
        return Response(
            {
                "asset_id": result.asset_id,
                "src": result.src,
                "width": result.width,
                "height": result.height,
            },
            status_code=201,
        )
    return Response({"error_key": result.error_key}, status_code=400)


                                                                             
                                                                               
@get("/game/journal/asset/{asset_id:str}")
async def serve_journal_asset(
    asset_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    journal_asset_read_service: JournalAssetReadService,
) -> File:
    result = journal_asset_read_service.get_asset(
        asset_id=asset_id,
        user_id=current_user["id"],
        project_root=PROJECT_ROOT,
    )
    if result.error_key == "not_found":
        raise NotFoundException()
    if not result.success:
        raise NotAuthorizedException()
    if result.path is None:
        raise NotFoundException()

    return File(path=result.path, media_type=result.media_type or "image/png")
