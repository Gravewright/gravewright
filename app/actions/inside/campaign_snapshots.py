from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from litestar import Request, get, post
from litestar.enums import RequestEncodingType
from litestar.exceptions import NotFoundException
from litestar.params import Body, FromQuery
from litestar.response import Redirect, Response

from app.business.campaigns.campaign_snapshot_service import CampaignSnapshotService
from app.config import config
from app.helpers.auth import require_user
from app.helpers.http_responses import json_error, json_ok, wants_json
from app.persistence.rows import Row


@dataclass
class CreateSnapshotForm:
    campaign_id: str = ""
    name: str = ""
    description: str = ""


@dataclass
class SnapshotActionForm:
    campaign_id: str = ""
    snapshot_id: str = ""
    confirm: str = ""


def _enabled() -> None:
    if not config.campaign_snapshots_enabled:
        raise NotFoundException()


def _error(result) -> Response:
    status = 403 if result.error_key == "campaign.snapshot.errors.denied" else 400
    return json_error(error_key=result.error_key or "campaign.snapshot.errors.failed", status_code=status)


@get("/campaigns/snapshots", guards=[require_user], sync_to_thread=False)
def list_campaign_snapshots(
    campaign_id: FromQuery[str],
    current_user: Row,
    campaign_snapshot_service: CampaignSnapshotService,
) -> Response:
    _enabled()
    result = campaign_snapshot_service.list_for_campaign(
        campaign_id=campaign_id, user_id=str(current_user["id"])
    )
    return json_ok(data=result.preview) if result.success else _error(result)


@post("/campaigns/snapshots", guards=[require_user], sync_to_thread=True)
def create_campaign_snapshot(
    request: Request,
    current_user: Row,
    campaign_snapshot_service: CampaignSnapshotService,
    data: Annotated[CreateSnapshotForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response | Redirect:
    _enabled()
    result = campaign_snapshot_service.create(
        campaign_id=data.campaign_id,
        user_id=str(current_user["id"]),
        name=data.name,
        description=data.description,
    )
    if not result.success:
        return _error(result) if wants_json(request) else Redirect(path=f"/inside?campaign_error_key={result.error_key}")
    return json_ok(message_key="campaign.snapshot.created", data={"snapshot": result.snapshot}) if wants_json(request) else Redirect(path="/inside?campaign_message_key=campaign.snapshot.created")


@post("/campaigns/snapshots/preview", guards=[require_user], sync_to_thread=True)
def preview_campaign_snapshot(
    current_user: Row,
    campaign_snapshot_service: CampaignSnapshotService,
    data: Annotated[SnapshotActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response:
    _enabled()
    result = campaign_snapshot_service.preview(snapshot_id=data.snapshot_id, campaign_id=data.campaign_id, user_id=str(current_user["id"]))
    return json_ok(data={"snapshot": result.snapshot, "preview": result.preview}) if result.success else _error(result)


@post("/campaigns/snapshots/restore", guards=[require_user], sync_to_thread=True)
def restore_campaign_snapshot(
    request: Request,
    current_user: Row,
    campaign_snapshot_service: CampaignSnapshotService,
    data: Annotated[SnapshotActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response | Redirect:
    _enabled()
    if data.confirm != "RESTORE":
        return json_error(error_key="campaign.snapshot.errors.confirmation", status_code=400) if wants_json(request) else Redirect(path="/inside?campaign_error_key=campaign.snapshot.errors.confirmation")
    result = campaign_snapshot_service.restore(snapshot_id=data.snapshot_id, campaign_id=data.campaign_id, user_id=str(current_user["id"]))
    if not result.success:
        return _error(result)
    return json_ok(message_key="campaign.snapshot.restored", data={"snapshot": result.snapshot, "result": result.preview}) if wants_json(request) else Redirect(path="/inside?campaign_message_key=campaign.snapshot.restored")


@post("/campaigns/snapshots/delete", guards=[require_user], sync_to_thread=True)
def delete_campaign_snapshot(
    request: Request,
    current_user: Row,
    campaign_snapshot_service: CampaignSnapshotService,
    data: Annotated[SnapshotActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response | Redirect:
    _enabled()
    if data.confirm != "DELETE":
        return json_error(error_key="campaign.snapshot.errors.confirmation", status_code=400) if wants_json(request) else Redirect(path="/inside?campaign_error_key=campaign.snapshot.errors.confirmation")
    result = campaign_snapshot_service.delete(snapshot_id=data.snapshot_id, campaign_id=data.campaign_id, user_id=str(current_user["id"]))
    if not result.success:
        return _error(result)
    return json_ok(message_key="campaign.snapshot.deleted") if wants_json(request) else Redirect(path="/inside?campaign_message_key=campaign.snapshot.deleted")


route_handlers = [
    list_campaign_snapshots,
    create_campaign_snapshot,
    preview_campaign_snapshot,
    restore_campaign_snapshot,
    delete_campaign_snapshot,
]
