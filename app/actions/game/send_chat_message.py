from __future__ import annotations

from dataclasses import dataclass
from app.persistence.rows import Row
from typing import Annotated
from typing import Any

from litestar import Request
from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect
from litestar.response import Response

from app.engine.chat.chat_service import ChatService
from app.realtime.transport import RealtimeTransport


@dataclass
class ChatMessageForm:
    campaign_id: str = ""
    message: str = ""


@dataclass
class DeleteChatMessageForm:
    campaign_id: str = ""
    message_id: str = ""


@dataclass
class ClearChatMessagesForm:
    campaign_id: str = ""


def _wants_json(request: Request) -> bool:
    return "application/json" in request.headers.get("accept", "")


@post("/game/chat")
async def send_chat_message(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    chat_service: ChatService,
    data: Annotated[ChatMessageForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, Any]] | Redirect:
    user = current_user
    json_response = _wants_json(request)

    result = await chat_service.send_message(
        campaign_id=data.campaign_id,
        sender_user_id=user["id"],
        sender_name=user["name"],
        content=data.message,
        transport=RealtimeTransport(),
    )

    if json_response:
        if result.success:
            return Response(content={"ok": True}, status_code=200)
        return Response(
            content={"ok": False, "error_key": result.error_key or "game.chat.errors.empty_message"},
            status_code=400,
        )

    return Redirect(path="/game")


@post("/game/chat/delete")
async def delete_chat_message(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    chat_service: ChatService,
    data: Annotated[DeleteChatMessageForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, Any]] | Redirect:
    user = current_user
    json_response = _wants_json(request)

    result = await chat_service.delete_message(
        campaign_id=data.campaign_id,
        user_id=user["id"],
        message_id=data.message_id,
        transport=RealtimeTransport(),
    )

    if json_response:
        if result.success:
            return Response(content={"ok": True}, status_code=200)
        return Response(
            content={"ok": False, "error_key": result.error_key or "permissions.errors.denied"},
            status_code=400,
        )

    return Redirect(path="/game")


@post("/game/chat/clear")
async def clear_chat_messages(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    chat_service: ChatService,
    data: Annotated[ClearChatMessagesForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, Any]] | Redirect:
    user = current_user
    json_response = _wants_json(request)

    result = await chat_service.clear_messages(
        campaign_id=data.campaign_id,
        user_id=user["id"],
        transport=RealtimeTransport(),
    )

    if json_response:
        if result.success:
            return Response(content={"ok": True}, status_code=200)
        return Response(
            content={"ok": False, "error_key": result.error_key or "permissions.errors.denied"},
            status_code=400,
        )

    return Redirect(path="/game")
