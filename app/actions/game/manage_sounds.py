"""Native Sound product endpoints. Audio bytes deliberately use a separate data plane."""
from __future__ import annotations

from typing import Any
from litestar import Request, get, post
from litestar.params import FromPath, FromQuery
from litestar.response import Response

from app.engine.audio.sound_domain_service import SoundDomainService, SoundResult
from app.helpers.env import PROJECT_ROOT
from app.persistence.repositories.asset_repository import AssetRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


async def _body(request: Request) -> dict[str, Any]:
    try: value = await request.json()
    except Exception: return {}
    return value if isinstance(value, dict) else {}


def _response(result: SoundResult, created: bool = False) -> Response:
    if result.success:
        value=dict(result.value) if isinstance(result.value,dict) else result.value
        if isinstance(value,dict):value.pop("_runtimePlayback",None)
        return Response(value, status_code=201 if created else 200)
    status = 403 if result.error_key == "sound.not_authorized" else 404 if result.error_key == "sound.not_found" else 409 if result.error_key in {"sound.stale", "sound.in_use"} else 400
    return Response({"error_key": result.error_key, "details": result.value}, status_code=status)

async def _broadcast(campaign_id: str, result: SoundResult) -> None:
    if result.success:
        playback=result.value.get("_runtimePlayback") if isinstance(result.value,dict) else None
        payload={"room_id":campaign_id,"native_sound_changed":True}
        if playback:payload.update(playback_id=playback["id"],playback=playback)
        await RealtimeTransport().to_room(room_id=campaign_id,event=TransportEvent.AUDIO_CHANGED,payload=payload)


@get("/game/sounds/{campaign_id:str}", sync_to_thread=True)
def list_sounds(campaign_id: FromPath[str], current_user: dict, q: FromQuery[str] = "", kind: FromQuery[str] = "", cursor: FromQuery[int] = 0, limit: FromQuery[int] = 50) -> Response:
    return _response(SoundDomainService().list_sounds(campaign_id=campaign_id,user_id=current_user["id"],q=q,kind=kind or None,cursor=cursor,limit=limit))


@post("/game/sounds")
async def create_sound(request: Request, current_user: dict) -> Response:
    d=await _body(request);cid=str(d.get("campaignId") or d.get("campaign_id") or "");result=SoundDomainService().create_sound(campaign_id=cid,user_id=current_user["id"],values=d);await _broadcast(cid,result);return _response(result,True)


@post("/game/sounds/update")
async def update_sound(request: Request, current_user: dict) -> Response:
    d=await _body(request);cid=str(d.get("campaignId") or "");result=SoundDomainService().update_sound(campaign_id=cid,user_id=current_user["id"],sound_id=str(d.get("soundId") or ""),patch=d.get("patch") or {},expected_version=int(d.get("expectedVersion") or 0));await _broadcast(cid,result);return _response(result)


@post("/game/sounds/delete")
async def delete_sound(request: Request, current_user: dict) -> Response:
    d=await _body(request);cid=str(d.get("campaignId") or "");result=SoundDomainService().delete_sound(campaign_id=cid,user_id=current_user["id"],sound_id=str(d.get("soundId") or ""),expected_version=int(d.get("expectedVersion") or 0));await _broadcast(cid,result);return _response(result)

@post("/game/sounds/play")
async def play_ambient_sound(request: Request, current_user: dict) -> Response:
    d=await _body(request);cid=str(d.get("campaignId") or "");result=SoundDomainService().play_ambient(campaign_id=cid,user_id=current_user["id"],sound_id=str(d.get("soundId") or ""));await _broadcast(cid,SoundResult(result.success,{"_runtimePlayback":result.value} if result.success else result.value,result.error_key));return _response(result)

@post("/game/sounds/stop")
async def stop_ambient_sound(request: Request, current_user: dict) -> Response:
    d=await _body(request);cid=str(d.get("campaignId") or "");result=SoundDomainService().stop_ambient(campaign_id=cid,user_id=current_user["id"],sound_id=str(d.get("soundId") or ""));await _broadcast(cid,SoundResult(result.success,{"_runtimePlayback":result.value} if result.success else result.value,result.error_key));return _response(result)

@post("/game/sounds/pause")
async def pause_ambient_sound(request: Request, current_user: dict) -> Response:
    d=await _body(request);cid=str(d.get("campaignId") or "");result=SoundDomainService().pause_ambient(campaign_id=cid,user_id=current_user["id"],sound_id=str(d.get("soundId") or ""));await _broadcast(cid,SoundResult(result.success,{"_runtimePlayback":result.value} if result.success else result.value,result.error_key));return _response(result)


@get("/game/sounds/{campaign_id:str}/compositions/{kind:str}", sync_to_thread=True)
def list_compositions(campaign_id: FromPath[str], kind: FromPath[str], current_user: dict) -> Response:
    return _response(SoundDomainService().list_compositions(campaign_id=campaign_id,user_id=current_user["id"],kind=kind))


@post("/game/sounds/compositions/{kind:str}")
async def create_composition(kind: FromPath[str], request: Request, current_user: dict) -> Response:
    d=await _body(request);cid=str(d.get("campaignId") or "");result=SoundDomainService().create_composition(campaign_id=cid,user_id=current_user["id"],kind=kind,values=d);await _broadcast(cid,result);return _response(result,True)


@get("/game/sounds/{campaign_id:str}/scenes/{scene_id:str}", sync_to_thread=True)
def list_scene_sounds(campaign_id: FromPath[str], scene_id: FromPath[str], current_user: dict) -> Response:
    return _response(SoundDomainService().list_spatial(campaign_id=campaign_id,scene_id=scene_id,user_id=current_user["id"]))

@get("/game/sounds/{campaign_id:str}/scenes/{scene_id:str}/acoustics", sync_to_thread=True)
def scene_sound_acoustics(campaign_id: FromPath[str], scene_id: FromPath[str], current_user: dict, preview_token_id: FromQuery[str | None] = None) -> Response:
    return _response(SoundDomainService().acoustic_projection(campaign_id=campaign_id,scene_id=scene_id,user_id=current_user["id"],preview_token_id=preview_token_id))

@get("/game/sounds/{campaign_id:str}/scenes/{scene_id:str}/soundscape", sync_to_thread=True)
def get_scene_soundscape(campaign_id: FromPath[str], scene_id: FromPath[str], current_user: dict) -> Response:
    return _response(SoundDomainService().get_scene_soundscape(campaign_id=campaign_id,scene_id=scene_id,user_id=current_user["id"]))

@post("/game/sounds/scenes/soundscape")
async def set_scene_soundscape(request: Request, current_user: dict) -> Response:
    d=await _body(request);cid=str(d.get("campaignId") or "");result=SoundDomainService().set_scene_soundscape(campaign_id=cid,scene_id=str(d.get("sceneId") or ""),user_id=current_user["id"],soundscape_id=str(d.get("soundscapeId") or "") or None,expected_version=int(d.get("expectedVersion") or 0));await _broadcast(cid,result);return _response(result)


@post("/game/sounds/spatial")
async def create_spatial_sound(request: Request, current_user: dict) -> Response:
    d=await _body(request);cid=str(d.get("campaignId") or "");result=SoundDomainService().create_spatial(campaign_id=cid,scene_id=str(d.get("sceneId") or ""),user_id=current_user["id"],values=d);await _broadcast(cid,result);return _response(result,True)


@post("/game/sounds/spatial/update")
async def update_spatial_sound(request: Request, current_user: dict) -> Response:
    d=await _body(request);cid=str(d.get("campaignId") or "");result=SoundDomainService().mutate_spatial(campaign_id=cid,user_id=current_user["id"],rid=str(d.get("id") or ""),patch=d.get("patch") or {},expected_version=int(d.get("expectedVersion") or 0));await _broadcast(cid,result);return _response(result)


@post("/game/sounds/spatial/delete")
async def delete_spatial_sound(request: Request, current_user: dict) -> Response:
    d=await _body(request);cid=str(d.get("campaignId") or "");result=SoundDomainService().mutate_spatial(campaign_id=cid,user_id=current_user["id"],rid=str(d.get("id") or ""),patch={},expected_version=int(d.get("expectedVersion") or 0),remove=True);await _broadcast(cid,result);return _response(result)


@get("/game/sounds/assets/{asset_id:str}/stream")
async def stream_sound_asset(asset_id: FromPath[str], request: Request, current_user: dict) -> Response:
    asset=AssetRepository().get_by_id(asset_id)
    if not asset: return Response({"error_key":"not_found"},status_code=404)
    if not CampaignRepository().get_member_role(campaign_id=asset["campaign_id"],user_id=current_user["id"]): return Response({"error_key":"not_authorized"},status_code=403)
    path=PROJECT_ROOT / str(asset.get("storage_path") or "")
    if not path.is_file() or not str(asset.get("content_type") or "").startswith("audio/"): return Response({"error_key":"not_found"},status_code=404)
    size=path.stat().st_size; start=0; end=size-1; status=200
    raw=request.headers.get("range","")
    if raw.startswith("bytes="):
        try:
            left,right=raw[6:].split("-",1); start=int(left) if left else max(0,size-int(right)); end=min(size-1,int(right)) if right else size-1
            if start<0 or start>end or start>=size: raise ValueError
            status=206
        except ValueError: return Response(status_code=416,headers={"Content-Range":f"bytes */{size}"})
    with path.open("rb") as stream: stream.seek(start); data=stream.read(end-start+1)
    headers={"Accept-Ranges":"bytes","Content-Length":str(len(data)),"Cache-Control":"private, max-age=3600"}
    if status==206: headers["Content-Range"]=f"bytes {start}-{end}/{size}"
    return Response(data,status_code=status,media_type=asset.get("content_type") or "application/octet-stream",headers=headers)
