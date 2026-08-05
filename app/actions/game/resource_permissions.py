from __future__ import annotations

from app.persistence.rows import Row
from typing import Any
from urllib.parse import urlencode

from litestar import Request, get, post
from litestar.params import FromPath
from litestar.response import Redirect, Response, Template

from app.engine.actors.actor_service import ActorService
from app.engine.items.item_service import ItemService
from app.engine.journals.journal_service import JournalService
from app.engine.resources.resource_permission_page_service import ResourcePermissionPageService
from app.helpers.view import view_context
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


def _str(form: Any, key: str, default: str = "") -> str:
    return str(form.get(key) or default)


def _resource_modal_id(resource_type: str, resource_id: str) -> str:
    return f"{resource_type}-{resource_id}"


def _redirect_to_resource(
    resource_type: str, resource_id: str, *, campaign_id: str | None = None
) -> Redirect:
    params = {"open_modal": _resource_modal_id(resource_type, resource_id)}
    if campaign_id:
        params["room"] = campaign_id
    return Redirect(path=f"/game?{urlencode(params)}")


def _set_member_access(
    resource_type: str,
    resource_id: str,
    target_user_id: str,
    access: str,
    requester: str,
    *,
    actor_service: ActorService,
    item_service: ItemService,
    journal_service: JournalService,
):
    if resource_type == "actor":
        return actor_service.set_member_access(
            actor_id=resource_id,
            target_user_id=target_user_id,
            access_level=access,
            requester_user_id=requester,
        )
    if resource_type == "item":
        return item_service.set_member_access(
            item_id=resource_id,
            target_user_id=target_user_id,
            access_level=access,
            requester_user_id=requester,
        )
    return journal_service.set_member_access(
        journal_id=resource_id,
        target_user_id=target_user_id,
        access_level=access,
        requester_user_id=requester,
    )


@get("/game/resource-permissions/{resource_type:str}/{resource_id:str}")
async def show_resource_permissions(
    resource_type: FromPath[str],
    resource_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    resource_permission_page_service: ResourcePermissionPageService,
) -> Redirect | Template:
    page = resource_permission_page_service.build_page(
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=current_user["id"],
    )
    if page is None:
        return Redirect(path="/game")

    return Template(
        template_name="pages/game/resource_permissions_modal.html",
        context=view_context(
            cookies,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_title=page.title,
            rows=page.rows,
        ),
    )


@post("/game/resource-permissions")
async def update_resource_permissions(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    actor_service: ActorService,
    item_service: ItemService,
    journal_service: JournalService,
    resource_permission_page_service: ResourcePermissionPageService,
) -> Response[dict[str, Any]] | Redirect:
    user = current_user
    wants_json = "application/json" in request.headers.get("accept", "")
    form = await request.form()
    resource_type = _str(form, "resource_type")
    resource_id = _str(form, "resource_id")
    resource, campaign = resource_permission_page_service.load_resource(
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user["id"],
    )

    if resource is None or campaign is None or campaign.get("member_role") != "gm":
        if wants_json:
            return Response({"error_key": "permissions.errors.denied"}, status_code=403)
        return Redirect(path="/game")

    members = resource_permission_page_service.list_non_gm_members(
        campaign_id=resource["campaign_id"]
    )

    for member in members:
        access = _str(form, f"access__{member['user_id']}", "none")
        result = _set_member_access(
            resource_type,
            resource_id,
            member["user_id"],
            access,
            user["id"],
            actor_service=actor_service,
            item_service=item_service,
            journal_service=journal_service,
        )
        if not result.success:
            if wants_json:
                return Response({"error_key": result.error_key}, status_code=400)
            return Redirect(path="/game")

                                                                               
    if resource_type == "actor":
        await RealtimeTransport().to_room(
            room_id=resource["campaign_id"],
            event=TransportEvent.ACTOR_UPDATED,
            payload={
                "room_id": resource["campaign_id"],
                "actor_id": resource_id,
                "updated_by": user["id"],
            },
        )
    elif resource_type == "item":
        await RealtimeTransport().to_room(
            room_id=resource["campaign_id"],
            event=TransportEvent.ITEM_UPDATED,
            payload={
                "room_id": resource["campaign_id"],
                "item_id": resource_id,
                "updated_by": user["id"],
            },
        )
    else:
        await RealtimeTransport().to_room(
            room_id=resource["campaign_id"],
            event=TransportEvent.JOURNAL_ACCESS_CHANGED,
            payload={
                "room_id": resource["campaign_id"],
                "journal_id": resource_id,
                "updated_by": user["id"],
            },
        )

    if wants_json:
        return Response({"ok": True}, status_code=200)

    return _redirect_to_resource(
        resource_type, resource_id, campaign_id=resource["campaign_id"]
    )
