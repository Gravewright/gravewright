from __future__ import annotations
from typing import Any
from litestar import Request, get, post
from litestar.params import FromPath, FromQuery
from litestar.response import Response
from app.engine.scenes.scene_shader_service import SceneShaderService
from app.config import config
from app.helpers.async_blocking import run_blocking
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport

EDITABLE = ("name", "source", "x", "y", "radius", "rotation", "blend_mode", "intensity", "opacity", "scale", "speed", "color", "enabled")

async def body(request: Request) -> dict[str, Any]:
    try: value = await request.json()
    except Exception: return {}
    return value if isinstance(value, dict) else {}
def response(result, created=False):
    return Response(result.payload if result.success else {"error_key": result.error_key}, status_code=(201 if created else 200) if result.success else (403 if result.error_key == "lighting.errors.denied" else 400))
def disabled() -> Response[dict[str, Any]] | None:
    return None if config.dynamic_lighting_enabled else Response({"error_key":"lighting.errors.disabled"},status_code=404)
async def broadcast(campaign_id: str, scene_id: str):
    await RealtimeTransport().to_room(room_id=campaign_id, event=TransportEvent.SCENE_SHADERS_UPDATED, payload={"room_id": campaign_id, "scene_id": scene_id})
def fields(data: dict) -> dict[str, Any]:
    return {key: data[key] for key in EDITABLE if key in data}

@get("/game/shaders/{scene_id:str}")
async def get_shaders(scene_id: FromPath[str], campaign_id: FromQuery[str], current_user: dict, scene_shader_service: SceneShaderService) -> Response[dict[str, Any]]:
    if off := disabled(): return off
    return response(await run_blocking(scene_shader_service.state, campaign_id=campaign_id, scene_id=scene_id, user_id=current_user["id"]))

@post("/game/shaders")
async def create_shader(request: Request, current_user: dict, scene_shader_service: SceneShaderService) -> Response[dict[str, Any]]:
    if off := disabled(): return off
    d=await body(request); cid=str(d.get("campaign_id") or ""); sid=str(d.get("scene_id") or "")
    result=await run_blocking(scene_shader_service.create,campaign_id=cid,scene_id=sid,user_id=current_user["id"],**fields(d))
    if result.success: await broadcast(cid,sid)
    return response(result,True)

@post("/game/shaders/update")
async def update_shader(request: Request, current_user: dict, scene_shader_service: SceneShaderService) -> Response[dict[str, Any]]:
    if off := disabled(): return off
    d=await body(request); cid=str(d.get("campaign_id") or "")
    result=await run_blocking(scene_shader_service.update,campaign_id=cid,shader_id=str(d.get("shader_id") or ""),user_id=current_user["id"],**fields(d))
    if result.success: await broadcast(cid,result.payload["shader"]["scene_id"])
    return response(result)

@post("/game/shaders/delete")
async def delete_shader(request: Request, current_user: dict, scene_shader_service: SceneShaderService) -> Response[dict[str, Any]]:
    if off := disabled(): return off
    d=await body(request); cid=str(d.get("campaign_id") or "")
    result=await run_blocking(scene_shader_service.delete,campaign_id=cid,shader_id=str(d.get("shader_id") or ""),user_id=current_user["id"])
    if result.success: await broadcast(cid,result.payload["scene_id"])
    return response(result)

@post("/game/shaders/delete-many")
async def delete_shaders(request: Request, current_user: dict, scene_shader_service: SceneShaderService) -> Response[dict[str, Any]]:
    """Apagar uma selecao inteira. Um pedido, uma transacao, um aviso.

    Em laco pelo cliente, apagar trinta paredes eram trinta requisicoes e trinta
    avisos de tempo real para todo mundo na mesa — e a cena aparecia sumindo aos
    pedacos na tela dos outros.
    """
    if off := disabled(): return off
    d = await body(request); cid = str(d.get("campaign_id") or "")
    ids = d.get("shader_ids")
    result = await run_blocking(scene_shader_service.delete_many, campaign_id=cid,
                                shader_ids=ids if isinstance(ids, list) else [],
                                user_id=current_user["id"])

    if result.success and result.payload.get("scene_id"):
        await broadcast(cid, result.payload["scene_id"])
    return response(result)
