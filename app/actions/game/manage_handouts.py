from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Annotated, Any

from litestar import get, post
from litestar.params import Body, FromPath, FromQuery
from litestar.response import File, Response, Template

from app.business.handouts import HandoutService
from app.business.handouts.presentation_ticket import (
    issue_presentation_ticket, verify_presentation_ticket,
)
from app.business.audit import AuditService
from app.config import config
from app.helpers.async_blocking import run_blocking
from app.persistence.rows import Row
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport
from app.persistence.repositories.realtime_recipient_repository import RealtimeRecipientRepository
from app.domain.roles import PlayerRole
from app.engine.assets.asset_read_service import AssetReadService
from app.engine.journals.journal_page_service import JournalPageService
from app.engine.sheets.item_sheet_service import ItemSheetService
from app.helpers.view import view_context


@dataclass
class GrantHandoutBody:
    campaign_id: str = ""
    resource_type: str = ""
    resource_id: str = ""
    subject_type: str = ""
    subject_id: str = ""


@dataclass
class RevokeHandoutBody:
    campaign_id: str = ""
    grant_id: str = ""


def _status_for(error_key: str | None) -> int:
    if error_key == "handout.errors.denied":
        return 403
    if error_key == "handout.errors.not_found":
        return 404
    return 400


def _disabled() -> Response[dict[str, Any]] | None:
    if config.targeted_handouts_enabled:
        return None
    return Response({"ok": False, "error_key": "handout.errors.disabled"}, status_code=404)


async def _announce_change(campaign_id: str) -> None:


    await RealtimeTransport().to_room(
        room_id=campaign_id,
        event=TransportEvent.HANDOUT_ACCESS_CHANGED,
        payload={"room_id": campaign_id},
    )


async def _present(grant: dict) -> None:
    recipients = RealtimeRecipientRepository()
    subject_type = grant["subject_type"]
    if subject_type == "user":
        user_ids = [grant["subject_id"]]
    elif subject_type == "role":
        try:
            role = PlayerRole(grant["subject_id"])
        except ValueError:
            return
        user_ids = await run_blocking(
            recipients.list_role_member_user_ids,
            room_id=grant["campaign_id"], role=role,
        )
    else:
        user_ids = await run_blocking(
            recipients.list_room_member_user_ids, grant["campaign_id"]
        )
    user_ids = [user_id for user_id in user_ids if user_id != grant["created_by_user_id"]]
    transport = RealtimeTransport()
    for user_id in user_ids:
        ticket = issue_presentation_ticket(
            campaign_id=grant["campaign_id"], user_id=user_id,
            resource_type=grant["resource_type"], resource_id=grant["resource_id"],
        )
        await transport.to_player(
            player_id=user_id, event=TransportEvent.HANDOUT_PRESENTED,
            payload={"ticket": ticket, "resource_type": grant["resource_type"]},
        )


@post("/game/handouts/present")
async def present_handout(
    current_user: Row,
    handout_service: HandoutService,
    audit_service: AuditService,
    data: Annotated[GrantHandoutBody, Body()],
) -> Response[dict[str, Any]]:
    if disabled := _disabled():
        return disabled
    result = await run_blocking(
        handout_service.prepare_presentation,
        campaign_id=data.campaign_id.strip(), user_id=current_user["id"],
        resource_type=data.resource_type.strip(), resource_id=data.resource_id.strip(),
        subject_type=data.subject_type.strip(), subject_id=data.subject_id.strip(),
    )
    if not result.success:
        return Response(
            {"ok": False, "error_key": result.error_key},
            status_code=_status_for(result.error_key),
        )
    await _present(result.grant)
    await run_blocking(
        audit_service.record,
        campaign_id=data.campaign_id.strip(), actor_user_id=current_user["id"],
        event_type="handout.presented", subject_type=data.resource_type.strip(),
        subject_id=data.resource_id.strip(), action="present", result="success",
        metadata={
            "resource_type": data.resource_type.strip(),
            "audience_type": data.subject_type.strip(),
        },
    )
    return Response({"ok": True}, status_code=200)


@get("/game/handouts/presentation/{ticket:str}")
async def get_handout_presentation(
    ticket: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    journal_page_service: JournalPageService,
    item_sheet_service: ItemSheetService,
    asset_read_service: AssetReadService,
) -> Response | Template | File:
    payload = verify_presentation_ticket(ticket, user_id=current_user["id"])
    if payload is None:
        return Response({"ok": False, "error_key": "handout.errors.presentation_expired"}, status_code=403)
    resource_id = str(payload["resource_id"])
    if payload["resource_type"] == "asset":
        result = await run_blocking(
            asset_read_service.get_asset,
            asset_id=resource_id, user_id=current_user["id"], presentation=True,
        )
        if not result.success or result.path is None:
            return Response({"ok": False, "error_key": "handout.errors.not_found"}, status_code=404)
        return File(path=result.path, media_type=result.media_type or "image/png")
    if payload["resource_type"] == "journal":
        page = await run_blocking(
            journal_page_service.build_modal,
            journal_id=resource_id, user_id=current_user["id"], presentation=True,
        )
        if page is None:
            return Response({"ok": False, "error_key": "handout.errors.not_found"}, status_code=404)
        return Template(template_name="pages/game/_journal_modal.html", context=view_context(
            cookies, journal=page.journal, view=page.view,
            room_id=page.journal["campaign_id"], member_role=page.campaign["member_role"],
            is_gm=False, can_edit=False, journal_folders=[], room_members=[],
            board_quest_options=[], targeted_handouts_enabled=False,
        ))
    base_context = view_context(cookies)
    bundle = await run_blocking(
        item_sheet_service.build_bundle,
        item_id=resource_id, user_id=current_user["id"],
        locale=base_context["locale"], presentation=True,
    )
    if bundle is None:
        return Response({"ok": False, "error_key": "handout.errors.not_found"}, status_code=404)
    return Template(template_name="pages/game/_item_sheet_modal.html", context={
        **base_context, "item": bundle,
        "bundle_json": json.dumps(item_sheet_service.to_dict(bundle), separators=(",", ":")),
        "room_id": bundle.campaign_id, "is_gm": False, "targeted_handouts_enabled": False,
    })


@post("/game/handouts/grant")
async def grant_handout(
    current_user: Row,
    handout_service: HandoutService,
    audit_service: AuditService,
    data: Annotated[GrantHandoutBody, Body()],
) -> Response[dict[str, Any]]:
    if disabled := _disabled():
        return disabled
    result = await run_blocking(
        handout_service.grant,
        campaign_id=data.campaign_id.strip(),
        user_id=current_user["id"],
        resource_type=data.resource_type.strip(),
        resource_id=data.resource_id.strip(),
        subject_type=data.subject_type.strip(),
        subject_id=data.subject_id.strip(),
    )
    if not result.success:
        return Response(
            {"ok": False, "error_key": result.error_key},
            status_code=_status_for(result.error_key),
        )
    await run_blocking(
        audit_service.record,
        campaign_id=data.campaign_id.strip(), actor_user_id=current_user["id"],
        event_type="handout.granted", subject_type="handout",
        subject_id=result.grant["id"], action="grant", result="success",
        metadata={"resource_type": data.resource_type.strip(), "audience_type": data.subject_type.strip()},
    )
    await _announce_change(data.campaign_id.strip())
    await _present(result.grant)
    return Response({"ok": True, "grant": result.grant}, status_code=200)


@post("/game/handouts/revoke")
async def revoke_handout(
    current_user: Row,
    handout_service: HandoutService,
    audit_service: AuditService,
    data: Annotated[RevokeHandoutBody, Body()],
) -> Response[dict[str, Any]]:
    if disabled := _disabled():
        return disabled
    result = await run_blocking(
        handout_service.revoke,
        campaign_id=data.campaign_id.strip(),
        user_id=current_user["id"],
        grant_id=data.grant_id.strip(),
    )
    if not result.success:
        return Response(
            {"ok": False, "error_key": result.error_key},
            status_code=_status_for(result.error_key),
        )
    await run_blocking(
        audit_service.record,
        campaign_id=data.campaign_id.strip(), actor_user_id=current_user["id"],
        event_type="handout.revoked", subject_type="handout",
        subject_id=data.grant_id.strip(), action="revoke", result="success",
        metadata={
            "resource_type": result.grant["resource_type"],
            "audience_type": result.grant["subject_type"],
        },
    )
    await _announce_change(data.campaign_id.strip())
    return Response({"ok": True}, status_code=200)


@get("/game/handouts")
async def list_handouts(
    current_user: Row,
    handout_service: HandoutService,
    campaign_id: FromQuery[str],
    resource_type: FromQuery[str],
    resource_id: FromQuery[str],
) -> Response[dict[str, Any]]:
    if disabled := _disabled():
        return disabled
    result = await run_blocking(
        handout_service.list,
        campaign_id=campaign_id.strip(),
        user_id=current_user["id"],
        resource_type=resource_type.strip(),
        resource_id=resource_id.strip(),
    )
    if not result.success:
        return Response(
            {"ok": False, "error_key": result.error_key},
            status_code=_status_for(result.error_key),
        )
    return Response({"ok": True, "grants": result.grants}, status_code=200)


@get("/game/handouts/received")
async def list_received_handouts(
    current_user: Row,
    handout_service: HandoutService,
    campaign_id: FromQuery[str],
) -> Response[dict[str, Any]]:
    if disabled := _disabled():
        return disabled
    result = await run_blocking(
        handout_service.list_received,
        campaign_id=campaign_id.strip(), user_id=current_user["id"],
    )
    if not result.success:
        return Response(
            {"ok": False, "error_key": result.error_key},
            status_code=_status_for(result.error_key),
        )
    return Response({"ok": True, "handouts": result.grants}, status_code=200)
