"""Campaign WebSocket transport for commands, subscriptions and recipient projections.

Synchronous domain work runs through database_sync_to_async. Each connection keeps
subscription and preview state, while durable mutations remain in domain services."""

import asyncio
import json
import logging
from contextlib import suppress
from time import monotonic

from channels.db import database_sync_to_async as db
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from gravewright.accounts.services import AuthError
from gravewright.actors import services as actors
from gravewright.chat import services as chat
from gravewright.dice import services as dice
from gravewright.dice.engine import RollError, evaluate
from gravewright.journals import services as journals
from gravewright.maps import services as maps
from gravewright.tokens import services as tokens

from . import services
from .scene_stream import SceneStreamMixin

logger = logging.getLogger(__name__)


class TableConsumer(SceneStreamMixin, AsyncWebsocketConsumer):
    """A socket is bound to one authenticated campaign for its entire lifetime."""

    async def connect(self):
        self.init_stream()
        self.connection_id = None
        self.heartbeat_task = None
        self.joined_group = False
        self.campaign_id = self.scope["url_route"]["kwargs"]["campaign_id"]
        self.group = f"table.{self.campaign_id.hex}"
        self.session_key = self.scope["session"].session_key
        self.member = await db(services.authorize)(self.session_key, self.campaign_id)
        if self.member is None:
            await self.close(code=4403)
            return
        self.user_id = self.member.user_id
        self.command_tokens = float(settings.WS_BURST_COMMANDS)
        self.command_sample = monotonic()
        self.last_pong = monotonic()
        await self.channel_layer.group_add(self.group, self.channel_name)
        self.joined_group = True
        self.connection_id = await db(services.arrive)(self.member)
        await self.accept()
        await self.emit(
            "table.joined", {"tableId": str(self.campaign_id), "role": self.member.role}
        )
        await self.emit(
            "chat.history",
            {
                "tableId": str(self.campaign_id),
                "messages": await db(chat.history)(self.campaign_id, self.user_id),
            },
        )
        await self.publish_presence()
        self.heartbeat_task = asyncio.create_task(self.heartbeat())

    async def emit(self, kind, payload):
        await self.send(text_data=json.dumps({"type": kind, "payload": payload}))

    async def close(self, code=None, reason=None):
        if getattr(self, "closing", False):
            return
        self.closing = True
        await super().close(code=code, reason=reason)

    async def authorized(self):
        if getattr(self, "closing", False):
            return False
        member = await db(services.authorize)(
            self.session_key, self.campaign_id, self.user_id
        )
        if member is None:
            await self.close(code=4403)
            return False
        self.member = member
        return True

    async def receive(self, text_data=None, bytes_data=None):
        if (
            bytes_data is not None
            or text_data is None
            or len(text_data.encode("utf-8")) > settings.WS_MAX_MESSAGE_BYTES
        ):
            await self.close(code=1009)
            return
        now = monotonic()
        self.command_tokens = min(float(settings.WS_BURST_COMMANDS),
            self.command_tokens + (now - self.command_sample) * settings.WS_COMMANDS_PER_SECOND)
        self.command_sample = now
        if self.command_tokens < 1:
            await self.close(code=4429)
            return
        self.command_tokens -= 1
        try:
            message = json.loads(text_data)
        except ValueError, RecursionError:
            await self.emit("error", {"code": "invalid_input"})
            return
        if not isinstance(message, dict) or not isinstance(
            message.get("payload", {}), dict
        ):
            await self.emit("error", {"code": "invalid_input"})
            return
        if not await self.authorized():
            return
        kind, payload = message.get("type"), message.get("payload", {})
        if self.member.role == 'streamer' and kind not in {
            'session.pong','api.watch','resources.sync','lobby.sync','table.search','actors.sync','tokens.sync',
            'scene.viewport','scene.viewport.stop','maps.layers','maps.sync','journals.sync','chat.sync'
        }:
            await self.emit('error', {'code':'read_only','message':'Streamers have read-only access.'})
            return
        if (
            kind
            not in (
                "journals.command",
                "maps.command",
                "actors.command",
                "tokens.command",
                "token.drag",
            )
            and len(text_data.encode("utf-8")) > 16_384
        ):
            await self.close(code=1009)
            return
        if payload.get("tableId", str(self.campaign_id)) != str(self.campaign_id):
            await self.emit("error", {"code": "not_a_member"})
            return
        if kind == "session.pong":
            self.last_pong = now
            if await db(services.renew)(self.connection_id):
                await self.publish_presence()
        elif kind == 'api.watch':
            self.api_watching = True
        elif kind in ('resources.sync','resources.command'):
            from gravewright.table import domain
            area=payload.get('module')
            request_id=payload.get('requestId')
            try:
                domain.module(area)
                if kind=='resources.sync':
                    if not hasattr(self,'table_modules'):self.table_modules={}
                    self.table_modules[area]=payload.get('sceneId')
                    if area=='audio':self.audio_preview_token=payload.get('previewTokenId')
                    await self.room_resources({'module':area})
                else:
                    result=await db(domain.command)(self.campaign_id,self.user_id,area,payload.get('action'),payload.get('data'),request_id)
                    await self.emit('resources.ack',{'requestId':request_id,'result':result})
            except (maps.MapError,journals.JournalError,RollError,AuthError) as error:
                await self.emit('resources.error',{'requestId':request_id,'module':area,'message':str(error),'code':getattr(error,'code','invalid_input')})
        elif kind in ('lobby.sync', 'lobby.update', 'table.search'):
            from gravewright.table import services as table_services
            try:
                if kind == 'table.search':
                    results = await db(table_services.search)(self.campaign_id, self.user_id, payload.get('query', ''))
                    await self.emit('table.search', {'requestId': payload.get('requestId'), 'results': results})
                elif kind == 'lobby.update':
                    await db(table_services.update_lobby)(self.campaign_id, self.user_id, payload)
                else:
                    self.lobby_subscribed = True
                    await self.room_lobby({})
            except (journals.JournalError, maps.MapError) as error:
                await self.emit('table.tool_error', {'requestId': payload.get('requestId'), 'tool': kind, 'code': error.code, 'message': str(error)})
        elif kind == "chat.say":
            request_id = payload.get("requestId")
            try:
                entry, created = await db(chat.say)(
                    self.member.pk, payload.get("text"), request_id, payload.get("mapId")
                )
            except AuthError as error:
                await self.emit(
                    "error",
                    {
                        "code": error.code,
                        "requestId": request_id
                        if isinstance(request_id, str)
                        else None,
                    },
                )
                return
            await self.emit("chat.ack", {"requestId": request_id, "message": entry})
        elif kind == "actors.sync":
            self.actors_subscribed = True
            await self.room_actors({})
        elif kind == "tokens.sync":
            await self.end_drag("cancel")
            self.token_map_id = payload.get("mapId")
            self.seen_drag = {}
            await self.room_tokens({})
        elif kind in ("actors.command", "tokens.command"):
            await self.resource_command(kind.split(".")[0], payload)
        elif kind == "token.drag":
            await self.token_drag(payload)
        elif kind == "scene.viewport":
            await self.scene_viewport(payload)
        elif kind == "scene.viewport.stop":
            await self.stop_stream()
        elif kind == "maps.ping":
            if monotonic() - getattr(self, "last_map_ping", 0) < 0.25:
                return
            self.last_map_ping = monotonic()
            try:
                value = await db(maps.ping)(self.campaign_id, self.user_id, payload)
                await self.channel_layer.group_send(
                    self.group, {"type": "room.map_ping", "payload": value}
                )
            except maps.MapError, journals.JournalError:
                pass
        elif kind == "maps.layers":
            self.map_layer_id = payload.get("mapId")
            await self.room_map_layers({})
        elif kind == "maps.sync":
            self.maps_subscribed = True
            await self.room_maps({})
        elif kind == "maps.command":
            await self.map_command(payload)
        elif kind == "journals.sync":
            self.journals_subscribed = True
            await self.room_journals({})
        elif kind == "journals.command":
            await self.journal_command(payload)
        elif kind == "dice.roll":
            await self.roll(payload)
        elif kind in ("chat.delete", "chat.clear"):
            try:
                if kind == 'chat.delete' and payload.get('messageId') is None:
                    raise AuthError('invalid_input')
                result = await db(chat.remove)(self.campaign_id, self.user_id,
                    payload.get('messageId') if kind == 'chat.delete' else None)
                await self.emit('chat.moderated', result)
            except AuthError as error:
                await self.emit('error', {'code': error.code})
        elif kind == "chat.sync":
            self.chat_map_id = payload.get("mapId")
            await self.chat_history()
        else:
            await self.emit("error", {"code": "unknown_command"})

    async def chat_history(self):
        try:
            await self.emit(
                "chat.history",
                {
                    "tableId": str(self.campaign_id),
                    "messages": await db(chat.history)(self.campaign_id, self.user_id, getattr(self, "chat_map_id", None)),
                },
            )
        except AuthError as error:
            await self.emit("chat.history", {"tableId": str(self.campaign_id), "messages": []})

    async def resource_command(self, area, payload):
        request_id = payload.get("requestId")
        try:
            service = actors if area == "actors" else tokens
            result = await db(service.command)(
                self.campaign_id,
                self.user_id,
                payload.get("action"),
                payload.get("data"),
                request_id,
            )
            if not await self.authorized():
                return
            await self.emit(area + ".ack", {"requestId": request_id, "result": result})
        except (
            maps.MapError,
            journals.JournalError,
            ValueError,
            TypeError,
            KeyError,
        ) as error:
            await self.emit(
                area + ".error",
                {
                    "requestId": request_id if isinstance(request_id, str) else None,
                    "code": getattr(error, "code", "invalid_input"),
                    "message": str(error)
                    if isinstance(error, (maps.MapError, journals.JournalError))
                    else "Invalid command.",
                },
            )

    async def api_changed(self, domain):
        # No documents or identifiers cross this invalidation boundary. The
        # browser reads a fresh projection using its own authorized API context.
        if getattr(self, 'api_watching', False) and await self.authorized():
            await self.emit('api.changed', {'domain': domain})

    async def room_modules(self, event):
        if await self.authorized():
            await self.emit("modules.updated", event["state"])

    async def room_actors(self, event):
        await self.api_changed('actors')
        if getattr(self, "actors_subscribed", False) and await self.authorized():
            try:
                await self.emit(
                    "actors.state",
                    await db(actors.state)(self.campaign_id, self.user_id),
                )
            except journals.JournalError:
                pass

    async def room_tokens(self, event):
        await self.api_changed('tokens')
        await self.room_resources({'module':'audio'})
        await self.room_resources({'module':'combat'})
        if not getattr(self, "token_map_id", None) or not await self.authorized():
            return
        try:
            await self.emit(
                "tokens.state",
                await db(tokens.state)(
                    self.campaign_id, self.user_id, self.token_map_id
                ),
            )
        except maps.MapError, journals.JournalError:
            await self.emit("tokens.state", {"mapId": self.token_map_id, "tokens": []})
            self.token_map_id = None

    async def end_drag(self, phase):
        packet = getattr(self, "drag_packet", None)
        if packet:
            await self.channel_layer.group_send(
                self.group,
                {
                    "type": "room.token_drag",
                    "payload": {**packet, "phase": phase, "positions": []},
                    "sender": self.channel_name,
                },
            )
        self.drag_packet = None
        self.drag_positions = {}

    async def token_drag(self, payload):
        try:
            stream = str(journals.identifier(payload.get("stream")))
            if payload.get("mapId") != getattr(self, "token_map_id", None):
                return
            if payload.get("phase") in ("end", "cancel"):
                if (
                    getattr(self, "drag_packet", None)
                    and self.drag_packet["stream"] == stream
                ):
                    await self.end_drag(payload["phase"])
                return
            if (
                payload.get("phase") != "update"
                or monotonic() - getattr(self, "last_drag", 0) < 0.075
            ):
                return
            self.last_drag = monotonic()
            if (
                getattr(self, "drag_packet", None)
                and self.drag_packet["stream"] != stream
            ):
                await self.end_drag("cancel")
            positions = await db(tokens.preview)(
                self.campaign_id,
                self.user_id,
                self.token_map_id,
                payload.get("positions"),
                getattr(self, "drag_positions", {}),
            )
            self.drag_positions = {p["id"]: (p["gridX"], p["gridY"]) for p in positions}
            self.drag_packet = {
                "scene_id": self.token_map_id,
                "connection": str(self.connection_id),
                "stream": stream,
                "phase": "update",
                "positions": positions,
            }
            await self.channel_layer.group_send(
                self.group,
                {
                    "type": "room.token_drag",
                    "payload": self.drag_packet,
                    "sender": self.channel_name,
                },
            )
        except maps.MapError, journals.JournalError, ValueError, TypeError, KeyError:
            await self.end_drag("cancel")

    async def room_token_drag(self, event):
        p = event["payload"]
        if (
            event["sender"] == self.channel_name
            or p["scene_id"] != getattr(self, "token_map_id", None)
            or not await self.authorized()
        ):
            return
        key = (p["connection"], p["stream"])
        seen = {
            key: expires
            for key, expires in getattr(self, "seen_drag", {}).items()
            if expires > monotonic()
        }
        self.seen_drag = seen
        if p["phase"] == "update":
            try:
                positions = await db(tokens.motion_for)(
                    self.campaign_id, self.user_id, self.token_map_id, p["positions"]
                )
                if not positions:
                    return
                seen[key] = monotonic() + 2
                self.seen_drag = seen
                await self.emit("token.drag", {**p, "positions": positions})
            except maps.MapError, journals.JournalError:
                return
        elif key in seen:
            seen.pop(key, None)
            await self.emit("token.drag", p)

    async def room_map_ping(self, event):
        if not await self.authorized():
            return
        try:
            who = await db(maps.member)(self.campaign_id, self.user_id)
            await db(maps.scene)(event["payload"]["mapId"], who)
        except maps.MapError, journals.JournalError:
            return
        await self.emit("maps.ping", event["payload"])

    async def map_command(self, payload):
        request_id = payload.get("requestId")
        try:
            result = await db(maps.command)(
                self.campaign_id,
                self.user_id,
                payload.get("action"),
                payload.get("data"),
                request_id,
            )
            if not await self.authorized():
                return
            await self.emit("maps.ack", {"requestId": request_id, "result": result})
        except (maps.MapError, journals.JournalError) as error:
            await self.emit(
                "maps.error",
                {
                    "requestId": request_id if isinstance(request_id, str) else None,
                    "code": error.code,
                    "message": str(error),
                },
            )

    async def room_map_layers(self, event):
        await self.api_changed('maps.layers')
        await self.room_resources({'module':'audio'})
        if not getattr(self, "map_layer_id", None) or not await self.authorized():
            return

        def read():
            from gravewright.maps.objects import layer_state

            who = maps.member(self.campaign_id, self.user_id)
            scene = maps.scene(self.map_layer_id, who)
            return layer_state(scene, who)

        try:
            await self.emit("maps.layers", await db(read)())
        except maps.MapError, journals.JournalError:
            self.map_layer_id = None

    async def room_maps(self, event):
        await self.api_changed('maps')
        if await self.authorized():
            await self.chat_history()
        if getattr(self, "maps_subscribed", False) and await self.authorized():
            try:
                await self.emit(
                    "maps.state", await db(maps.state)(self.campaign_id, self.user_id)
                )
            except maps.MapError, journals.JournalError:
                await self.close(code=4403)

    async def journal_command(self, payload):
        request_id = payload.get("requestId")
        try:
            result = await db(journals.command)(
                self.campaign_id,
                self.user_id,
                payload.get("action"),
                payload.get("data"),
                request_id,
            )
            if not await self.authorized():
                return
            await self.emit("journals.ack", {"requestId": request_id, "result": result})
        except journals.JournalError as error:
            await self.emit(
                "journals.error",
                {
                    "requestId": request_id if isinstance(request_id, str) else None,
                    "code": error.code,
                    "message": str(error),
                },
            )

    async def room_handout(self, event):
        if not await self.authorized(): return
        value = event['payload']
        if value['target'] and value['target'] != str(self.user_id): return
        from gravewright.journals.presentations import ticket, resolve
        issued = ticket(value, self.user_id)
        try:
            await db(resolve)(issued, self.user_id, self.campaign_id)
        except journals.JournalError:
            return
        await self.emit('handout.presented', {'ticket': issued, 'requestId': event['request_id'], 'resource_type': 'journal'})

    async def room_journals(self, event):
        await self.api_changed('journals')
        if getattr(self, "journals_subscribed", False) and await self.authorized():
            try:
                await self.emit(
                    "journals.state",
                    await db(journals.state)(self.campaign_id, self.user_id),
                )
            except journals.JournalError:
                await self.close(code=4403)

    async def roll(self, payload):
        reservation = None
        request_id = payload.get("requestId")
        try:
            data = dice.validate(payload)
            reservation, previous = await db(dice.claim)(self.member.pk, data)
            if previous:
                entry, audience = previous
            else:
                # Engine work is isolated from both the event loop and the DB executor.
                result = await asyncio.to_thread(
                    evaluate, data["expression"], data["repeat"]
                )
                entry, audience = await db(dice.complete)(
                    reservation,
                    data,
                    result,
                    self.session_key,
                    self.campaign_id,
                    self.user_id,
                )
            if not await self.authorized():
                return
            # A replay can recover delivery after a worker lost its transport.
            if previous:
                await self.channel_layer.group_send(self.group, {'type':'room.message','message':entry,'audience':audience})
            await self.emit("dice.ack", {"requestId": request_id, "message": entry})
        except (RollError, AuthError) as error:
            if reservation:
                await db(dice.fail)(reservation, error)
            if not await self.authorized():
                return
            await self.emit(
                "dice.error",
                {
                    "requestId": request_id if isinstance(request_id, str) else None,
                    "code": error.code
                    if isinstance(error, AuthError)
                    else "invalid_roll",
                    "message": str(error)
                    if isinstance(error, RollError)
                    else {
                        "too_many_messages": "Too many rolls. Please wait a moment.",
                        "roll_in_progress": "Rolling…",
                    }.get(error.code, "Could not roll dice."),
                },
            )

    async def publish_presence(self):
        await self.channel_layer.group_send(self.group, {"type": "room.presence"})
        await self.channel_layer.group_send(self.group, {"type": "room.lobby"})

    async def room_resources(self,event):
        await self.api_changed(event.get('module'))
        from gravewright.table import domain
        area=event.get('module')
        if area not in getattr(self,'table_modules',{}) or not await self.authorized():return
        scene_id=self.table_modules[area]
        try:
            value=await db(domain.state)(self.campaign_id,self.user_id,area,scene_id,getattr(self,'audio_preview_token',None))
            await self.emit('resources.state',{'module':area,'sceneId':scene_id,'state':value})
        except (maps.MapError,journals.JournalError):
            await self.emit('resources.state',{'module':area,'sceneId':scene_id,'state':{},'unavailable':True})

    async def room_lobby(self, event):
        if getattr(self, 'lobby_subscribed', False) and settings.LOBBY_READY_CHECK_ENABLED and await self.authorized():
            from gravewright.table.services import lobby
            await self.emit('lobby.state', await db(lobby)(self.campaign_id, self.user_id))

    async def room_zone(self,event):
        if not await self.authorized():return
        def visible():
            from gravewright.maps.models import SceneObject
            from gravewright.maps.zones import visible as zone_visible
            obj=SceneObject.objects.select_related('scene').filter(pk=event['zoneId'],scene__campaign_id=self.campaign_id).first()
            if not obj or not zone_visible(obj.data,self.member):return False
            try:
                maps.scene(obj.scene_id,self.member)
                return any(t['id']==event['tokenId'] for t in tokens.rows(obj.scene,self.member))
            except maps.MapError:return False
        if await db(visible)():
            await self.emit(event['event'],{k:v for k,v in event.items() if k not in ('type','event')})

    async def room_presence(self, event):
        if await self.authorized():
            await self.emit(
                "table.presence", await db(services.roster)(self.campaign_id)
            )

    async def room_message(self, event):
        if await self.authorized():
            from gravewright.chat.context import readable
            entry = event['message']
            from gravewright.chat.models import Message
            if entry.get('deleted') or not await db(Message.objects.filter(pk=entry['id'], campaign_id=self.campaign_id, deleted=False).exists)():
                return
            if not await db(readable)(self.campaign_id, self.user_id, entry.get('sceneId')): return
            selected = getattr(self, 'chat_map_id', None)
            if selected and entry.get('sceneId') and selected != entry['sceneId']: return
            audience = event.get("audience", entry.get('audience'))
            if audience is None or str(self.user_id) in audience:
                await self.emit("chat.message", event["message"])

    async def room_chat_refresh(self, event):
        if await self.authorized():
            await self.chat_history()

    async def heartbeat(self):
        try:
            while True:
                await asyncio.sleep(settings.GRAVEWRIGHT_HEARTBEAT_SECONDS)
                if monotonic() - self.last_pong > settings.GRAVEWRIGHT_PRESENCE_TTL:
                    await self.close(code=4000)
                    return
                if not await self.authorized():
                    return
                # Keep Redis group membership alive beyond its default expiry.
                await self.channel_layer.group_add(self.group, self.channel_name)
                await self.emit("session.ping", {})
                # Refresh names/roles and remove expired leases after worker failures.
                await self.emit(
                    "table.presence", await db(services.roster)(self.campaign_id)
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Table heartbeat failed for %s", self.campaign_id)
            await self.close(code=1011)

    async def disconnect(self, code):
        await self.stop_stream()
        await self.end_drag("cancel")
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.heartbeat_task
        if self.joined_group:
            await self.channel_layer.group_discard(self.group, self.channel_name)
        if self.connection_id:
            await db(services.depart)(self.connection_id)
            await self.publish_presence()
