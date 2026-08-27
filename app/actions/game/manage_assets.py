from __future__ import annotations

import inspect
from typing import Any

from litestar import Request
from litestar import get
from litestar import post
from litestar.params import FromPath
from litestar.response import File
from litestar.response import Response

from app.engine.assets.asset_library_service import MAX_AUDIO_BYTES
from app.engine.assets.asset_library_service import MAX_PDF_BYTES
from app.engine.assets.asset_library_service import AssetLibraryService
from app.engine.assets.asset_read_service import AssetReadService
from app.engine.sdk.package_asset_import_service import PackageAssetImportService
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport
from app.engine.sheets.pdf_system_policy import is_pdf_sheet_system
from app.persistence.repositories.campaign_repository import CampaignRepository


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


async def _read_upload_file(upload: object) -> bytes:
    read = getattr(upload, "read", None)
    if read is None:
        return b""
    data = read()
    if inspect.isawaitable(data):
        data = await data
    return data


def _response(result, *, status_code: int = 200) -> Response[dict[str, Any]]:
    if not result.success:
        code = 403 if result.error_key == "permissions.errors.denied" else 409 if result.error_key == "game.assets.errors.asset_in_use" else 400
        return Response({"error_key": result.error_key}, status_code=code)
    return Response(result.payload, status_code=status_code)


async def _broadcast_library(campaign_id: str, user_id: str) -> None:
    await RealtimeTransport().to_room(
        room_id=campaign_id,
        event=TransportEvent.ASSETS_LIBRARY_UPDATED,
        payload={"room_id": campaign_id, "updated_by": user_id},
    )


@get("/game/assets/packages/{campaign_id:str}", sync_to_thread=True)
def list_asset_packages(
    campaign_id: FromPath[str],
    current_user: dict,
    package_asset_import_service: PackageAssetImportService,
) -> Response[dict[str, Any]]:
    packages = package_asset_import_service.list_active_packages(
        campaign_id=str(campaign_id), user_id=current_user["id"]
    )
    return Response({"packages": packages})


@get("/game/assets/packages/{campaign_id:str}/{package_id:str}", sync_to_thread=True)
def list_asset_package_entries(
    campaign_id: FromPath[str],
    package_id: FromPath[str],
    current_user: dict,
    package_asset_import_service: PackageAssetImportService,
) -> Response[dict[str, Any]]:
    entries = package_asset_import_service.list_entries(
        campaign_id=str(campaign_id), package_id=str(package_id), user_id=current_user["id"]
    )
    return Response({"assets": entries})


@post("/game/assets/packages/import")
async def import_asset_package_entry(
    request: Request,
    current_user: dict,
    package_asset_import_service: PackageAssetImportService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    package_id = str(body.get("package_id") or "")
    folder_id = str(body.get("folder_id") or "") or None
    asset_ids = body.get("asset_ids")
    if not isinstance(asset_ids, list):
        asset_ids = [str(body.get("asset_id") or "")]
    imported = 0
    for asset_id in asset_ids:
        asset = package_asset_import_service.import_entry(
            campaign_id=campaign_id,
            package_id=package_id,
            asset_id=str(asset_id),
            user_id=current_user["id"],
            folder_id=folder_id,
        )
        imported += int(asset is not None)
    if imported:
        await _broadcast_library(campaign_id, current_user["id"])
    return Response({"imported": imported})


@get("/game/assets/state/{campaign_id:str}")
async def get_asset_library_state(
    campaign_id: FromPath[str],
    current_user: dict,
    asset_library_service: AssetLibraryService,
) -> Response[dict[str, Any]]:
    result = asset_library_service.get_state(campaign_id=campaign_id, user_id=current_user["id"])
    return _response(result)


@post("/game/assets/folders")
async def create_asset_folder(
    request: Request,
    current_user: dict,
    asset_library_service: AssetLibraryService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    parent_id = (
        body.get("parent_id")
        if isinstance(body.get("parent_id"), str) and body.get("parent_id")
        else None
    )
    result = asset_library_service.create_folder(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        name=str(body.get("name") or ""),
        parent_id=parent_id,
    )
    if result.success:
        await _broadcast_library(campaign_id, current_user["id"])
    return _response(result, status_code=201)


@post("/game/assets/move")
async def move_asset_to_folder(
    request: Request,
    current_user: dict,
    asset_library_service: AssetLibraryService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    folder_id = (
        body.get("folder_id")
        if isinstance(body.get("folder_id"), str) and body.get("folder_id")
        else None
    )
    result = asset_library_service.move_asset(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        asset_id=str(body.get("asset_id") or ""),
        folder_id=folder_id,
    )
    if result.success:
        await _broadcast_library(campaign_id, current_user["id"])
    return _response(result)


@post("/game/assets/delete")
async def delete_library_asset(
    request: Request,
    current_user: dict,
    asset_library_service: AssetLibraryService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    result = asset_library_service.delete_asset(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        asset_id=str(body.get("asset_id") or ""),
    )
    if result.success:
        await _broadcast_library(campaign_id, current_user["id"])
    return _response(result)


@post(
    "/game/assets/upload",




    request_max_body_size=max(MAX_AUDIO_BYTES, MAX_PDF_BYTES) + 1024 * 1024,
)
async def upload_asset_library_image(
    request: Request,
    current_user: dict,
    asset_library_service: AssetLibraryService,
) -> Response[dict[str, Any]]:
    form = await request.form()
    upload = form.get("file")
    campaign_id = str(form.get("campaign_id") or "")
    folder_id = str(form.get("folder_id") or "") or None
    purpose = str(form.get("purpose") or "")
    if purpose == "pdf-sheet":
        campaign = CampaignRepository().get(campaign_id)
        if not campaign or not is_pdf_sheet_system(campaign.get("active_system_id")):
            return Response({"error_key":"game.assets.errors.pdf_system_required"},status_code=403)
    result = asset_library_service.upload_asset(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        filename=str(getattr(upload, "filename", "") or ""),
        content_type=str(getattr(upload, "content_type", "") or ""),
        data=await _read_upload_file(upload),
        folder_id=folder_id,
    )
    if result.success:
        if purpose in {"ambient", "effect"} and isinstance(result.payload.get("asset"), dict):
            from app.engine.audio.sound_domain_service import SoundDomainService
            asset=result.payload["asset"];filename=str(asset.get("filename") or getattr(upload,"filename","") or "Sound")
            SoundDomainService().create_sound(campaign_id=campaign_id,user_id=current_user["id"],values={"name":filename.rsplit(".",1)[0],"assetId":asset.get("id"),"kind":"ambience" if purpose=="ambient" else "sound-effect","defaultLoop":purpose=="ambient"})
        await _broadcast_library(campaign_id, current_user["id"])
    return _response(result, status_code=201)


@get("/game/assets/file/{asset_id:str}")
async def serve_asset(
    asset_id: FromPath[str],
    current_user: dict,
    asset_read_service: AssetReadService,
) -> File | Response[dict[str, Any]]:
    result = asset_read_service.get_asset(asset_id=asset_id, user_id=current_user["id"])
    if not result.success or result.path is None:
        code = 403 if result.error_key == "not_authorized" else 404
        return Response({"error_key": result.error_key}, status_code=code)

    media_type = result.media_type or "image/png"




    inline = media_type.startswith("image/")
    return File(
        path=result.path,
        media_type=media_type,
        content_disposition_type="inline" if inline else "attachment",
    )
