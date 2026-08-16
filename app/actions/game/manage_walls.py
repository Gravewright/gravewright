from __future__ import annotations
from typing import Any
from litestar import Request, get, post
from litestar.params import FromPath, FromQuery
from litestar.response import Response
from app.engine.scenes.scene_wall_service import SceneWallService
from app.config import config
from app.helpers.async_blocking import run_blocking
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport

async def body(request: Request) -> dict[str, Any]:
    try: value = await request.json()
    except Exception: return {}
    return value if isinstance(value, dict) else {}
DENIED = {"lighting.errors.denied", "lighting.errors.locked"}
def response(result, created=False):
    return Response(result.payload if result.success else {"error_key": result.error_key}, status_code=(201 if created else 200) if result.success else (403 if result.error_key in DENIED else 400))
def disabled() -> Response[dict[str, Any]] | None:
    return None if config.dynamic_lighting_enabled else Response({"error_key":"lighting.errors.disabled"},status_code=404)
async def broadcast(campaign_id: str, scene_id: str):
    await RealtimeTransport().to_room(room_id=campaign_id, event=TransportEvent.SCENE_WALLS_UPDATED, payload={"room_id": campaign_id, "scene_id": scene_id})

@get("/game/walls/{scene_id:str}")
async def get_walls(scene_id: FromPath[str], campaign_id: FromQuery[str], current_user: dict, scene_wall_service: SceneWallService) -> Response[dict[str, Any]]:
    if off := disabled(): return off
    return response(await run_blocking(scene_wall_service.state, campaign_id=campaign_id, scene_id=scene_id, user_id=current_user["id"]))
@post("/game/walls")
async def create_wall(request: Request, current_user: dict, scene_wall_service: SceneWallService) -> Response[dict[str, Any]]:
    if off := disabled(): return off
    d=await body(request); cid=str(d.get("campaign_id") or ""); sid=str(d.get("scene_id") or "")
    try: coords={k:float(d.get(k)) for k in ("x1","y1","x2","y2")}
    except (TypeError,ValueError): coords={k:float("nan") for k in ("x1","y1","x2","y2")}
    result=await run_blocking(scene_wall_service.create,campaign_id=cid,scene_id=sid,user_id=current_user["id"],kind=str(d.get("kind") or "wall"),**coords)
    if result.success: await broadcast(cid,sid)
    return response(result,True)
@post("/game/walls/move-node")
async def move_wall_node(request: Request, current_user: dict, scene_wall_service: SceneWallService) -> Response[dict[str, Any]]:
    if off := disabled(): return off
    d=await body(request); cid=str(d.get("campaign_id") or ""); sid=str(d.get("scene_id") or "")
    try: coords={k:float(d.get(k)) for k in ("from_x","from_y","to_x","to_y")}
    except (TypeError,ValueError): coords={k:float("nan") for k in ("from_x","from_y","to_x","to_y")}
    result=await run_blocking(scene_wall_service.move_node,campaign_id=cid,scene_id=sid,user_id=current_user["id"],**coords)
    if result.success: await broadcast(cid,sid)
    return response(result)
@post("/game/walls/move-endpoint")
async def move_wall_endpoint(request: Request, current_user: dict, scene_wall_service: SceneWallService) -> Response[dict[str, Any]]:
    if off := disabled(): return off
    d=await body(request); cid=str(d.get("campaign_id") or ""); sid=str(d.get("scene_id") or "")
    try: endpoint=int(d.get("endpoint")); to_x=float(d.get("to_x")); to_y=float(d.get("to_y"))
    except (TypeError,ValueError): endpoint=0; to_x=to_y=float("nan")
    result=await run_blocking(scene_wall_service.move_endpoint,campaign_id=cid,scene_id=sid,
        wall_id=str(d.get("wall_id") or ""),endpoint=endpoint,user_id=current_user["id"],to_x=to_x,to_y=to_y)
    if result.success: await broadcast(cid,sid)
    return response(result)
@post("/game/walls/move-many")
async def move_walls(request: Request, current_user: dict, scene_wall_service: SceneWallService) -> Response[dict[str, Any]]:
    if off := disabled(): return off
    d=await body(request); cid=str(d.get("campaign_id") or ""); sid=str(d.get("scene_id") or "")
    try: dx=float(d.get("dx")); dy=float(d.get("dy"))
    except (TypeError,ValueError): dx=dy=float("nan")
    ids=d.get("wall_ids")
    result=await run_blocking(scene_wall_service.move_many,campaign_id=cid,scene_id=sid,
                              wall_ids=ids if isinstance(ids,list) else [],user_id=current_user["id"],dx=dx,dy=dy)
    if result.success: await broadcast(cid,sid)
    return response(result)
@post("/game/walls/door-state")
async def set_door_state(request: Request,current_user:dict,scene_wall_service:SceneWallService) -> Response[dict[str, Any]]:
    if off := disabled(): return off
    d=await body(request); cid=str(d.get("campaign_id") or ""); result=await run_blocking(scene_wall_service.set_door_state,campaign_id=cid,wall_id=str(d.get("wall_id") or ""),user_id=current_user["id"],door_state=str(d.get("door_state") or ""))
    if result.success: await broadcast(cid,result.payload["wall"]["scene_id"])
    return response(result)
@post("/game/walls/delete")
async def delete_wall(request: Request,current_user:dict,scene_wall_service:SceneWallService) -> Response[dict[str, Any]]:
    if off := disabled(): return off
    d=await body(request); cid=str(d.get("campaign_id") or ""); wid=str(d.get("wall_id") or ""); result=await run_blocking(scene_wall_service.delete,campaign_id=cid,wall_id=wid,user_id=current_user["id"])
    if result.success: await broadcast(cid,result.payload["scene_id"])
    return response(result)

@post("/game/walls/delete-many")
async def delete_walls(request: Request, current_user: dict, scene_wall_service: SceneWallService) -> Response[dict[str, Any]]:
    """Apagar uma selecao inteira. Um pedido, uma transacao, um aviso.

    Em laco pelo cliente, apagar trinta paredes eram trinta requisicoes e trinta
    avisos de tempo real para todo mundo na mesa, e a cena aparecia sumindo aos
    pedacos na tela dos outros.
    """
    if off := disabled(): return off
    d = await body(request); cid = str(d.get("campaign_id") or "")
    ids = d.get("wall_ids")
    result = await run_blocking(scene_wall_service.delete_many, campaign_id=cid,
                                wall_ids=ids if isinstance(ids, list) else [],
                                user_id=current_user["id"])

    if result.success and result.payload.get("scene_id"):
        await broadcast(cid, result.payload["scene_id"])
    return response(result)

@post("/game/walls/split")
async def split_wall(request: Request, current_user: dict, scene_wall_service: SceneWallService) -> Response[dict[str, Any]]:
    if off := disabled(): return off
    d = await body(request); cid = str(d.get("campaign_id") or "")
    result = await run_blocking(scene_wall_service.split, campaign_id=cid,
                                wall_id=str(d.get("wall_id") or ""), user_id=current_user["id"],
                                x=float(d.get("x") or 0.0), y=float(d.get("y") or 0.0))
    if result.success: await broadcast(cid, result.payload["scene_id"])
    return response(result)
