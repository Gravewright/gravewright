"""Campaign WebSocket transport for commands, subscriptions and recipient projections.

Synchronous domain work runs through database_sync_to_async on a thread owned by
each connection, so one slow player cannot stall the table or another socket's
cleanup. Samples (cursor, viewport, drag) use a second per-connection thread and pongs
renew presence on a pool thread, so neither waits behind commands. Commits arrive as
one refresh envelope; each socket sends only projections that changed for it. Each
connection keeps subscription and preview state, while durable mutations remain in
domain services."""

import asyncio
import contextvars
import functools
import json
import logging
from contextlib import suppress
from time import monotonic

from asgiref.sync import SyncToAsync, ThreadSensitiveContext
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import OperationalError
from django.utils import timezone

from gravewright.accounts.services import AuthError
from gravewright.actors import services as actors
from gravewright.chat import services as chat
from gravewright.dice import services as dice
from gravewright.dice.engine import RollError, evaluate
from gravewright.journals import services as journals
from gravewright.maps import services as maps
from gravewright.tokens import services as tokens

from . import access, dispatch, metrics, projections, services
from .errors import database_busy
from .scene_stream import SceneStreamMixin

logger = logging.getLogger(__name__)

# Same behavior as Channels' adapter; it also counts SQL inside a measured handler.
db = metrics.database_sync_to_async

# Daphne kills a closed socket's application after 10 seconds; finish before that.
DEPART_TIMEOUT = 5

# Client message types this consumer understands. Only these names reach the logs.
CLIENT_TYPES = frozenset({
    'session.pong', 'api.watch', 'resources.sync', 'resources.command', 'lobby.sync',
    'lobby.update', 'table.search', 'chat.say', 'actors.sync', 'tokens.sync',
    'actors.command', 'tokens.command', 'token.drag', 'scene.viewport',
    'scene.viewport.stop', 'maps.ping', 'maps.cursor', 'maps.layers', 'maps.sync',
    'maps.command', 'journals.sync', 'journals.command', 'dice.roll', 'chat.delete',
    'chat.clear', 'chat.sync',
})
# Commands answer SQLite contention on their own error channel with code `busy`;
# the browser retries them silently with the same request ID.
BUSY_REPLIES = {
    'resources.command': 'resources.error', 'actors.command': 'actors.error',
    'tokens.command': 'tokens.error', 'maps.command': 'maps.error',
    'journals.command': 'journals.error', 'dice.roll': 'dice.error', 'chat.say': 'error',
    'chat.delete': 'error', 'chat.clear': 'error',
}
# Reads and idempotent state updates without a client retry are replayed on the
# next heartbeat upkeep instead; samples that a newer one replaces are dropped.
DEFERRED_ON_BUSY = frozenset({
    'resources.sync', 'lobby.sync', 'lobby.update', 'table.search', 'actors.sync',
    'tokens.sync', 'maps.layers', 'maps.sync', 'journals.sync', 'chat.sync',
})
BUSY_MESSAGE = 'The table is busy. Retrying.'

# Samples where only the newest value matters use their own lane and synchronous
# thread, so they never wait behind commands. A newer sample replaces an unprocessed
# one with the same key; drag streams have one key each, so an end or cancel is never
# replaced by another stream's update. Slots run in order of their latest arrival.
EPHEMERAL_TYPES = frozenset({'maps.cursor', 'scene.viewport', 'scene.viewport.stop', 'token.drag'})
PEER_EPHEMERAL_EVENTS = frozenset({'room.map_cursor', 'room.token_drag'})
EPHEMERAL_SLOTS = 8
PEER_SLOTS = 512
# Ordered frames waiting for the command lane; a client beyond this is closed (4429).
INBOX_LIMIT = 256

# A socket may reuse its last successful authorization for this many seconds (approved
# by the project owner on 2026-11-09), never beyond the session or streamer-link expiry
# and never after an access change (access.revoke). Write commands are still authorized
# by their services.
AUTHORIZATION_TTL = 2.0

# Expired-lease cleanup runs from heartbeat upkeep at most once per half presence TTL
# in each process, instead of on every pong of every socket.
_last_lease_cleanup = 0.0


def abandoned(task):
    """Report failures of a handler whose client disconnected before it finished."""
    if not task.cancelled() and task.exception() is not None:
        logger.error("Handler failed after its socket closed", exc_info=task.exception())


class TableConsumer(SceneStreamMixin, AsyncWebsocketConsumer):
    """A socket is bound to one authenticated campaign for its entire lifetime."""

    async def __call__(self, scope, receive, send):
        """Give the socket its own synchronous thread, as Django does per HTTP request.

        Tasks started by this consumer inherit the context and the same thread,
        so its own commands stay ordered while other sockets keep running.

        This replaces Channels' dispatch loop, which reads the next client or
        channel-layer message only after the current handler returns. Two readers
        feed one ordered queue instead: the client reader admits frames by their
        arrival time and notices a disconnect immediately, and both readers move
        samples and pongs to their own lanes (see EPHEMERAL_TYPES and
        presence_lane) without waiting for the handler in progress.
        """
        self.scope = scope
        self.channel_layer = get_channel_layer(self.channel_layer_alias)
        if self.channel_layer is not None:
            self.channel_name = await self.channel_layer.new_channel()
            self.channel_receive = functools.partial(self.channel_layer.receive, self.channel_name)
        self.base_send = send
        self.socket_closed = asyncio.Event()
        self.inbox = inbox = asyncio.Queue()
        self.queued_frames = 0
        self.slots = {}
        self.slots_ready = asyncio.Event()
        self.presence_due = asyncio.Event()

        async def read_client():
            while True:
                message = await receive()
                # Arrival time lets the handler measure how long the frame waited.
                message["_gw_arrived"] = arrived = monotonic()
                if message["type"] == "websocket.receive":
                    # Any client frame proves liveness, even while handlers queue up.
                    self.last_pong = arrived
                    admitted = await self.admit(message.get("text"), message.get("bytes"), arrived)
                    if admitted is None or await self.divert(message.get("text"), admitted):
                        continue
                    if self.queued_frames >= INBOX_LIMIT:
                        await self.close(code=4429)
                        continue
                    message["_gw_admitted"] = admitted
                    self.queued_frames += 1
                if message["type"] == "websocket.disconnect":
                    self.socket_closed.set()
                await inbox.put(message)
                if message["type"] == "websocket.disconnect":
                    return

        async def read_channel():
            while True:
                event = await self.channel_receive()
                if event.get("type") in PEER_EPHEMERAL_EVENTS:
                    self.queue_peer_sample(event)
                else:
                    await inbox.put(event)

        async def guarded(reader):
            # A failing reader (for example a lost Redis connection) still ends the
            # consumer with that error, as Channels' own loop would.
            try:
                await reader()
            except asyncio.CancelledError:
                raise
            except Exception as error:  # noqa: BLE001 - re-raised by the dispatch loop
                await inbox.put({"type": "_gw.reader_failed", "error": error})

        async with ThreadSensitiveContext():
            readers = [asyncio.ensure_future(guarded(read_client))]
            if self.channel_layer is not None:
                readers.append(asyncio.ensure_future(guarded(read_channel)))
            try:
                while True:
                    message = await inbox.get()
                    if message["type"] == "_gw.reader_failed":
                        raise message["error"]
                    if message["type"] == "websocket.receive":
                        self.queued_frames -= 1
                    await self.dispatch(message)
            except StopConsumer:
                pass
            finally:
                for reader in readers:
                    reader.cancel()
                    with suppress(asyncio.CancelledError):
                        await reader

    async def dispatch(self, message):
        """Stop waiting for a handler once its client is gone, then skip the backlog.

        asgiref cannot interrupt a running synchronous call: a cancelled handler
        still waits for it. The abandoned handler therefore finishes in the
        background (its database work commits or rolls back normally) while
        disconnect cleanup runs before Daphne's close timeout.
        """
        if message.get("type") == "websocket.disconnect":
            # This socket's thread may still be busy with an abandoned call, and
            # Channels runs close_old_connections on it; clean up from the shared one.
            context = contextvars.copy_context()
            context.run(SyncToAsync.thread_sensitive_context.set, None)
            return await asyncio.get_running_loop().create_task(self.handle(message), context=context)
        if self.socket_closed.is_set():
            return
        if message.get("type") in PEER_EPHEMERAL_EVENTS and hasattr(self, "slots"):
            # Another socket's cursor or drag sample: only its newest value matters.
            self.queue_peer_sample(message)
            return
        task = asyncio.ensure_future(self.handle(message))
        closed = asyncio.ensure_future(self.socket_closed.wait())
        try:
            await asyncio.wait({task, closed}, return_when=asyncio.FIRST_COMPLETED)
        except asyncio.CancelledError:
            task.cancel()
            raise
        finally:
            closed.cancel()
        if task.done():
            return task.result()
        task.cancel()
        task.add_done_callback(abandoned)

    async def handle(self, message):
        """Run one Channels handler with payload-free measurements.

        A delivery that meets SQLite contention keeps the socket open and is queued
        again on the next heartbeat upkeep; other database faults still fail loudly.
        """
        kind = message.get("type", "")
        lane = {"websocket.receive": "command", "websocket.connect": "connect",
                "websocket.disconnect": "disconnect"}.get(kind, "delivery")
        # Channel-layer event types are server-generated, so they are safe to log.
        with metrics.handler(lane, message.get("_gw_arrived"),
                             kind if lane == "delivery" else None):
            try:
                return await super().dispatch(message)
            except OperationalError as error:
                if lane != "delivery" or not database_busy(error):
                    raise
                metrics.database_busy()
                self.deferred_after_busy()[(kind, message.get("module"))] = message

    async def admit(self, text_data, bytes_data, now):
        """Check size, parse and rate-limit a frame by its arrival time.

        Returns ``(message, now)``, or None when the frame is dropped or the socket
        closes. Limits use the arrival time, so frames that waited behind a slow
        command are not mistaken for a burst when they are finally handled.
        """
        if (
            bytes_data is not None
            or text_data is None
            or len(text_data.encode("utf-8")) > settings.WS_MAX_MESSAGE_BYTES
        ):
            await self.close(code=1009)
            return None
        try:
            message = json.loads(text_data)
        except ValueError, RecursionError:
            message = None
        if isinstance(message, dict) and message.get('type') == 'maps.cursor':
            if len(text_data.encode('utf-8')) > 512:
                await self.close(code=1009)
                return None
            payload = message.get('payload')
            hiding = isinstance(payload, dict) and payload.get('position') is None
            # A pending sample has not set cursor_packet yet; its hide must still run.
            showing = getattr(self, 'cursor_packet', None) or ('own', 'cursor') in getattr(self, 'slots', {})
            if hiding and not showing:
                return None
            if not hiding and now - getattr(self, 'last_cursor_input', 0) < .075:
                return None
            self.last_cursor_input = now
        else:
            self.command_tokens = min(float(settings.WS_BURST_COMMANDS),
                self.command_tokens + (now - self.command_sample) * settings.WS_COMMANDS_PER_SECOND)
            self.command_sample = now
            if self.command_tokens < 1:
                await self.close(code=4429)
                return None
            self.command_tokens -= 1
        return message, now

    async def divert(self, text_data, admitted):
        """Move a pong to the presence lane or a sample to its slot; True when moved."""
        message = admitted[0]
        if not isinstance(message, dict) or not isinstance(message.get("payload", {}), dict):
            return False
        kind, payload = message.get("type"), message.get("payload", {})
        if kind == "session.pong":
            self.presence_due.set()
            return True
        if kind not in EPHEMERAL_TYPES:
            return False
        if kind == "token.drag":
            key = ("own", "drag", str(payload.get("stream"))[:64])
        else:
            key = ("own", "cursor") if kind == "maps.cursor" else ("own", "viewport")
        if key not in self.slots and sum(slot[0] == "own" for slot in self.slots) >= EPHEMERAL_SLOTS:
            await self.close(code=4429)
            return True
        self.slots.pop(key, None)
        self.slots[key] = (text_data, admitted)
        self.slots_ready.set()
        return True

    def queue_peer_sample(self, event):
        payload = event.get("payload") or {}
        stream = payload.get("stream") if event["type"] == "room.token_drag" else None
        key = ("peer", event["type"], event.get("sender"), stream)
        self.slots.pop(key, None)
        peers = [slot for slot in self.slots if slot[0] == "peer"]
        if len(peers) >= PEER_SLOTS:
            self.slots.pop(peers[0])
        self.slots[key] = event
        self.slots_ready.set()

    async def ephemeral_lane(self):
        """Run the newest samples on this socket's second synchronous thread.

        The task starts in an empty context, so this ThreadSensitiveContext gets a
        thread of its own instead of reusing the command thread.
        """
        try:
            async with ThreadSensitiveContext():
                while True:
                    await self.slots_ready.wait()
                    self.slots_ready.clear()
                    while self.slots and not self.socket_closed.is_set():
                        key = next(iter(self.slots))
                        await self.run_sample(key, self.slots.pop(key))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Sample lane failed for campaign %s", self.campaign_id)
            await self.close(code=1011)

    async def run_sample(self, key, item):
        if key[0] == "own":
            text_data, admitted = item
            with metrics.handler("ephemeral", admitted[1]):
                await self.receive(text_data=text_data, admitted=admitted)
            return
        with metrics.handler("ephemeral", None, item["type"]):
            try:
                await super().dispatch(item)
            except OperationalError as error:
                if not database_busy(error):
                    raise
                # A newer sample replaces this one; it is not replayed.
                metrics.database_busy()

    def renew_lease(self, revalidate=True):
        if not revalidate:
            return self.member, None, services.renew(self.connection_id, self.member.pk)
        member, valid_until = services.authorization(self.session_key, self.campaign_id, self.user_id)
        if member is None:
            return None, None, False
        return member, valid_until, services.renew(self.connection_id, member.pk)

    async def presence_lane(self):
        """Renew the lease after pongs on a pool thread, never behind commands or samples."""
        try:
            while True:
                await self.presence_due.wait()
                self.presence_due.clear()
                cached = self.authorization_cached()
                if cached and monotonic() < getattr(self, "lease_renew_after", 0):
                    continue  # Fresh lease and authorization: a pong costs no query.
                with metrics.handler("presence"):
                    epoch = access.epoch()
                    try:
                        member, valid_until, expired = await db(
                            self.renew_lease, thread_sensitive=False)(revalidate=not cached)
                    except OperationalError as error:
                        if not database_busy(error):
                            raise
                        metrics.database_busy()
                        continue
                if member is None:
                    await self.close(code=4403)
                    return
                if not cached:
                    self.remember_authorization(member, valid_until, epoch)
                self.lease_renew_after = monotonic() + settings.GRAVEWRIGHT_PRESENCE_TTL / 2
                if expired:
                    await self.publish_presence()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Presence lane failed for campaign %s", self.campaign_id)
            await self.close(code=1011)

    def start_lanes(self):
        if not hasattr(self, "slots"):
            return
        loop = asyncio.get_running_loop()
        self.lanes = [
            loop.create_task(self.ephemeral_lane(), name="gravewright-ephemeral",
                             context=contextvars.Context()),
            loop.create_task(self.presence_lane(), name="gravewright-presence"),
        ]

    async def websocket_receive(self, message):
        admitted = message.get("_gw_admitted")
        if admitted is None:
            return await super().websocket_receive(message)
        await self.receive(text_data=message.get("text"), admitted=admitted)

    def deferred_after_busy(self):
        if not hasattr(self, "deferred"):
            self.deferred = {}
        return self.deferred

    async def replay_deferred(self):
        """Queue work that met SQLite contention behind the frames already waiting."""
        deferred, self.deferred = self.deferred_after_busy(), {}
        for (kind, _), message in deferred.items():
            if kind == "frame":
                inbox = getattr(self, "inbox", None)
                if inbox is not None:
                    self.queued_frames += 1
                    await inbox.put({"type": "websocket.receive", "text": message,
                                     "_gw_arrived": monotonic()})
            else:
                await self.channel_layer.send(self.channel_name, message)

    async def connect(self):
        self.init_stream()
        self.connection_id = None
        self.heartbeat_task = None
        self.joined_group = False
        self.campaign_id = self.scope["url_route"]["kwargs"]["campaign_id"]
        self.group = f"table.{self.campaign_id.hex}"
        self.session_key = self.scope["session"].session_key
        epoch = access.epoch()
        self.member, valid_until = await db(services.authorization)(self.session_key, self.campaign_id)
        if self.member is None:
            await self.close(code=4403)
            return
        self.user_id = self.member.user_id
        self.remember_authorization(self.member, valid_until, epoch)
        # Envelopes after this number reach this socket; a gap means one was lost.
        self.revision = await db(dispatch.revision)(self.campaign_id)
        self.command_tokens = float(settings.WS_BURST_COMMANDS)
        self.command_sample = monotonic()
        self.last_pong = monotonic()
        await self.channel_layer.group_add(self.group, self.channel_name)
        # Access changes reach every socket of this user, in any process.
        await self.channel_layer.group_add(access.user_group(self.user_id), self.channel_name)
        self.joined_group = True
        self.connection_id = await db(services.arrive)(self.member)
        # Leases are renewed during the second half of their lifetime only.
        self.lease_renew_after = monotonic() + settings.GRAVEWRIGHT_PRESENCE_TTL / 2
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
        self.start_lanes()

    async def emit(self, kind, payload):
        text = json.dumps({"type": kind, "payload": payload})
        metrics.frame(text)
        await self.send(text_data=text)

    async def emit_projection(self, kind, key, payload):
        """Send only what this socket does not have yet.

        An identical projection sends nothing. Tokens and map layers send a delta
        computed from the recipient's own complete projection; the first projection
        after a subscription, scene change or resynchronization is sent whole.
        """
        if not hasattr(self, "sent_projections"):
            self.sent_projections = {}
        previous = self.sent_projections.get((kind, key))
        self.sent_projections[(kind, key)] = payload
        if previous is None:
            return await self.emit(kind, payload)
        if kind in projections.DELTA_KEYS:
            frame = projections.delta(kind, previous, payload)
        else:
            frame = None if projections.canonical(previous) == projections.canonical(payload) else payload
        if frame is not None:
            await self.emit(kind, frame)

    def forget_projections(self, kind, key=None, match=None):
        """The client asked for a complete projection: send the next one whole.

        ``key`` forgets one projection and ``match`` every key it accepts; with
        neither, every projection of ``kind`` is forgotten.
        """
        for sent in [sent for sent in getattr(self, "sent_projections", {})
                     if sent[0] == kind and (key is None or sent[1] == key)
                     and (match is None or match(sent[1]))]:
            del self.sent_projections[sent]

    async def close(self, code=None, reason=None):
        if getattr(self, "closing", False):
            return
        self.closing = True
        await super().close(code=code, reason=reason)

    def remember_authorization(self, member, valid_until, epoch):
        self.member = member
        self.authorization = (monotonic() + AUTHORIZATION_TTL, epoch, valid_until)

    def authorization_cached(self):
        cached = getattr(self, "authorization", None)
        return bool(cached and monotonic() < cached[0] and access.epoch() == cached[1]
                    and cached[2] is not None and timezone.now() < cached[2])

    async def authorized(self):
        if getattr(self, "closing", False):
            return False
        if self.authorization_cached():
            return True
        # Read the epoch first: a change committed during the check advances it again.
        epoch = access.epoch()
        member, valid_until = await db(services.authorization)(
            self.session_key, self.campaign_id, self.user_id
        )
        if member is None:
            self.authorization = None
            await self.close(code=4403)
            return False
        self.remember_authorization(member, valid_until, epoch)
        return True

    async def room_access(self, event):
        """Another process changed access: revalidate now instead of at the next frame."""
        self.authorization = None
        await self.authorized()

    async def receive(self, text_data=None, bytes_data=None, admitted=None):
        # The reader admits live frames on arrival; direct calls and replays are
        # admitted here with the same checks.
        if admitted is None:
            admitted = await self.admit(text_data, bytes_data, monotonic())
            if admitted is None:
                return
        message, now = admitted
        if not isinstance(message, dict) or not isinstance(
            message.get("payload", {}), dict
        ):
            await self.emit("error", {"code": "invalid_input"})
            return
        kind, payload = message.get("type"), message.get("payload", {})
        metrics.label(kind if kind in CLIENT_TYPES else "unknown")
        try:
            await self.route(kind, payload, text_data, now)
        except OperationalError as error:
            if not database_busy(error):
                raise
            await self.recover_busy(kind, payload, text_data)

    async def recover_busy(self, kind, payload, text_data):
        """Keep the socket open when SQLite contention interrupts a client frame."""
        metrics.database_busy()
        if kind in BUSY_REPLIES:
            request_id = payload.get("requestId")
            reply = {"requestId": request_id if isinstance(request_id, str) else None,
                     "code": "busy", "message": BUSY_MESSAGE}
            if kind == "resources.command":
                reply["module"] = payload.get("module")
            await self.emit(BUSY_REPLIES[kind], reply)
        elif kind in DEFERRED_ON_BUSY:
            # One replay per subscription: resources.sync arrives once per module.
            module = payload.get("module")
            self.deferred_after_busy()[("frame", (kind, module if isinstance(module, str) else ""))] = text_data

    async def route(self, kind, payload, text_data, now):
        if not await self.authorized():
            return
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
            if await db(services.renew)(self.connection_id, self.member.pk):
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
                    # Only this module asked for complete state; the others keep theirs.
                    # All of its scenes are dropped, so scenes the socket left are freed.
                    self.forget_projections('resources.state', match=lambda key: key[0] == area)
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
                    results = await db(table_services.search)(self.campaign_id, self.user_id, payload.get('query', ''), kind=payload.get('kind',''), recent=payload.get('recent'))
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
            self.forget_projections("actors.state")
            self.actors_subscribed = True
            await self.room_actors({})
        elif kind == "tokens.sync":
            self.forget_projections("tokens.state")
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
        elif kind == 'maps.cursor':
            await self.map_cursor(payload)
        elif kind == "maps.layers":
            self.forget_projections("maps.layers")
            if payload.get('mapId') != getattr(self, 'map_layer_id', None):
                await self.hide_cursor()
            self.map_layer_id = payload.get("mapId")
            await self.room_map_layers({})
        elif kind == "maps.sync":
            self.forget_projections("maps.state")
            self.maps_subscribed = True
            await self.room_maps({})
        elif kind == "maps.command":
            await self.map_command(payload)
        elif kind == "journals.sync":
            self.forget_projections("journals.state")
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

    async def notify_api(self, domain):
        # No documents or identifiers cross this invalidation boundary. The
        # browser reads a fresh projection using its own authorized API context.
        # Envelope deliveries authorize before calling this.
        if getattr(self, 'api_watching', False):
            await self.emit('api.changed', {'domain': domain})

    async def api_changed(self, domain):
        # Single-event deliveries recheck access before each notification.
        if getattr(self, 'api_watching', False) and await self.authorized():
            await self.emit('api.changed', {'domain': domain})

    async def room_modules(self, event):
        if await self.authorized():
            await self.emit("modules.updated", event["state"])

    async def room_changes(self, event):
        """Deliver one commit's projections once each, in dispatch.PROJECTIONS order.

        Authorization is checked once for the board and directories, and again
        before dependent resources, so a revocation during delivery stops them.
        """
        refresh = [name for name in event.get("refresh", ()) if isinstance(name, str)]
        revision, last = event.get("revision"), getattr(self, "revision", None)
        if type(revision) is int and last is not None:
            if revision <= last:
                return  # Late or repeated: a newer envelope already delivered current state.
            if revision > last + 1:
                # The channel layer dropped an envelope: refresh every projection.
                # Unchanged projections send nothing (see emit_projection).
                refresh = list(dispatch.PROJECTIONS)
        if not refresh or not await self.authorized():
            return
        await self.deliver_changes(refresh, event)
        if type(revision) is int:
            # Advance only after delivery, so a replay after `busy` is not skipped.
            self.revision = max(revision, last or 0)

    async def deliver_changes(self, refresh, event):
        checked = False
        for name in refresh:
            if name.startswith("resources:"):
                if not checked:
                    if not await self.authorized():
                        return
                    checked = True
                await self.deliver_resource(name.split(":", 1)[1])
            elif name == "maps.layers":
                await self.deliver_map_layers()
            elif name == "tokens":
                await self.deliver_tokens(event)
            elif name == "actors":
                await self.deliver_actors()
            elif name == "journals":
                await self.deliver_journals()
            elif name == "maps":
                await self.deliver_maps(chat="chat.history" in refresh)
            elif name == "chat.history" and "maps" not in refresh:
                await self.chat_history()

    async def room_actors(self, event):
        await self.deliver_actors(self.api_changed, recheck=True)

    async def deliver_actors(self, notify=None, recheck=False):
        await (notify or self.notify_api)('actors')
        if getattr(self, "actors_subscribed", False) and (not recheck or await self.authorized()):
            try:
                await self.emit_projection(
                    "actors.state", None,
                    await db(actors.state)(self.campaign_id, self.user_id),
                )
            except journals.JournalError:
                pass

    async def room_tokens(self, event):
        # Board updates must not wait for spatial audio or combat projections.
        # Dependent refreshes still perform their own live authorization check.
        if not await self.authorized():
            return
        await self.deliver_tokens(event, self.api_changed)
        if event.get('refresh_audio', True):
            await self.room_resources({'module':'audio'})
        if event.get('refresh_combat', True):
            await self.room_resources({'module':'combat'})

    async def deliver_tokens(self, event, notify=None):
        if getattr(self, "token_map_id", None):
            try:
                projection = await db(tokens.state)(
                    self.campaign_id, self.user_id, self.token_map_id
                )
                if event.get("mapId") == projection["mapId"]:
                    projection.update(tokens.teleport_metadata(projection["tokens"], event.get("teleports")))
                await self.emit_projection("tokens.state", projection["mapId"], projection)
            except maps.MapError, journals.JournalError:
                self.forget_projections("tokens.state")
                await self.emit("tokens.state", {"mapId": self.token_map_id, "tokens": []})
                self.token_map_id = None
        await (notify or self.notify_api)('tokens')

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
            if payload.get("mapId") != getattr(self, "token_map_id", None):
                # tokens.sync on the command lane moved to another map meanwhile.
                return
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

    async def hide_cursor(self):
        packet = getattr(self, 'cursor_packet', None)
        self.cursor_packet = None
        if packet and getattr(self, 'joined_group', False):
            await self.channel_layer.group_send(self.group, {'type': 'room.map_cursor',
                'sender': self.channel_name, 'payload': {**packet, 'position': None}})

    async def map_cursor(self, payload):
        if payload.get('position') is None:
            await self.hide_cursor()
            return
        if payload.get('mapId') != getattr(self, 'map_layer_id', None):
            return
        try:
            from gravewright.maps.cursors import project
            packet = await db(project)(self.member, payload)
        except maps.MapError, journals.JournalError:
            await self.hide_cursor()
            return
        if payload.get('mapId') != getattr(self, 'map_layer_id', None):
            # The command lane switched layers while this sample was projected.
            return
        packet['connectionId'] = str(self.connection_id)
        self.cursor_packet = packet
        await self.channel_layer.group_send(self.group, {'type': 'room.map_cursor',
            'sender': self.channel_name, 'payload': packet})

    async def room_map_cursor(self, event):
        packet = event['payload']
        if event['sender'] == self.channel_name or packet['mapId'] != getattr(self, 'map_layer_id', None):
            return
        if not await self.authorized():
            return
        try:
            await db(maps.scene)(packet['mapId'], self.member)
        except maps.MapError, journals.JournalError:
            return
        await self.emit('maps.cursor', packet)

    async def room_map_ping(self, event):
        if not await self.authorized():
            return
        try:
            who = await db(maps.member)(self.campaign_id, self.user_id)
            await db(maps.scene)(event["payload"]["mapId"], who)
        except maps.MapError, journals.JournalError:
            return
        await self.emit("maps.ping", event["payload"])

    async def room_automation_presentation(self, event):
        if str(self.user_id) not in event.get("recipients", []) or not await self.authorized():
            return
        from gravewright.maps.blueprint_world import presentation_for
        payload = await db(presentation_for)(self.campaign_id, self.user_id, event["payload"])
        if payload is not None:
            await self.emit("automation.presentation", payload)

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
        # Deliver committed scene changes before dependent resource refreshes.
        if not await self.authorized():
            return
        await self.deliver_map_layers(self.api_changed)
        if event.get('refresh_audio', True):
            await self.room_resources({'module':'audio'})

    async def deliver_map_layers(self, notify=None):
        def read():
            from gravewright.maps.objects import layer_state

            who = maps.member(self.campaign_id, self.user_id)
            scene = maps.scene(self.map_layer_id, who)
            return layer_state(scene, who)

        if getattr(self, "map_layer_id", None):
            try:
                state = await db(read)()
                await self.emit_projection("maps.layers", state["sceneId"], state)
            except maps.MapError, journals.JournalError:
                self.forget_projections("maps.layers")
                self.map_layer_id = None
        await (notify or self.notify_api)('maps.layers')

    async def room_maps(self, event):
        if await self.authorized():
            await self.deliver_maps(chat=True, notify=self.api_changed, recheck=True)

    async def deliver_maps(self, chat, notify=None, recheck=False):
        # Scene access may have changed: drop a pointer or tile stream that the
        # member can no longer see before delivering the new scene list.
        who = self.member
        for kind, value in (('cursor', getattr(self, 'cursor_packet', None)),
                            ('stream', getattr(self, 'stream_region', None))):
            if not value:
                continue
            try:
                await db(maps.scene)(value['mapId'], who)
            except maps.MapError, journals.JournalError:
                await (self.hide_cursor() if kind == 'cursor' else self.stop_stream())
        await (notify or self.notify_api)('maps')
        if recheck and not await self.authorized():
            return
        if chat:
            await self.chat_history()
        if getattr(self, "maps_subscribed", False) and (not recheck or await self.authorized()):
            try:
                await self.emit_projection(
                    "maps.state", None, await db(maps.state)(self.campaign_id, self.user_id)
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
        if value.get('issuer') == str(self.user_id): return
        if value.get('targets') is not None and str(self.user_id) not in value['targets']: return
        if value['target'] and value['target'] != str(self.user_id): return
        from gravewright.journals.presentations import ticket, resolve
        issued = ticket(value, self.user_id)
        try:
            await db(resolve)(issued, self.user_id, self.campaign_id)
        except journals.JournalError:
            return
        await self.emit('handout.presented', {'ticket': issued, 'requestId': event['request_id'], 'resource_type': 'journal'})

    async def room_journals(self, event):
        await self.deliver_journals(self.api_changed, recheck=True)

    async def deliver_journals(self, notify=None, recheck=False):
        await (notify or self.notify_api)('journals')
        if getattr(self, "journals_subscribed", False) and (not recheck or await self.authorized()):
            try:
                await self.emit_projection(
                    "journals.state", None,
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
                try:
                    entry, audience = await db(dice.complete)(
                        reservation,
                        data,
                        result,
                        self.session_key,
                        self.campaign_id,
                        self.user_id,
                    )
                except OperationalError as error:
                    if database_busy(error):
                        # The rolled-back result never left the server. Releasing the
                        # claim lets the `busy` retry roll again; if the release also
                        # meets the lock, the claim simply expires.
                        try:
                            await db(dice.release)(reservation)
                        except OperationalError as release_error:
                            if not database_busy(release_error):
                                raise
                    raise
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
        await self.deliver_resource(event.get('module'), self.api_changed, recheck=True)

    async def deliver_resource(self, area, notify=None, recheck=False):
        from gravewright.table import domain
        await (notify or self.notify_api)(area)
        if area not in getattr(self,'table_modules',{}) or (recheck and not await self.authorized()):return
        scene_id=self.table_modules[area]
        try:
            value=await db(domain.state)(self.campaign_id,self.user_id,area,scene_id,getattr(self,'audio_preview_token',None))
            await self.emit_projection('resources.state',(area,scene_id),{'module':area,'sceneId':scene_id,'state':value})
        except (maps.MapError,journals.JournalError):
            self.forget_projections('resources.state',(area,scene_id))
            await self.emit('resources.state',{'module':area,'sceneId':scene_id,'state':{},'unavailable':True})

    async def room_lobby(self, event):
        if getattr(self, 'lobby_subscribed', False) and settings.LOBBY_READY_CHECK_ENABLED and await self.authorized():
            from gravewright.table.services import lobby
            await self.emit('lobby.state', await db(lobby)(self.campaign_id, self.user_id))

    async def room_automation(self, event):
        # Blueprint runs are GM diagnostics; other roles never learn that one ran.
        if await self.authorized() and self.member.role == "gm":
            await self.emit("maps.automation", {"sceneId": event["sceneId"]})

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
        """Ping on a fixed cadence; database upkeep never delays the ping.

        The browser drops a socket after 20 seconds without frames, so a slow
        query must not hold back pings. Upkeep starts again only after the
        previous pass finished.
        """
        upkeep = None
        try:
            while True:
                await asyncio.sleep(settings.GRAVEWRIGHT_HEARTBEAT_SECONDS)
                if monotonic() - self.last_pong > settings.GRAVEWRIGHT_PRESENCE_TTL:
                    await self.close(code=4000)
                    return
                await self.emit("session.ping", {})
                if upkeep is not None:
                    if not upkeep.done():
                        continue
                    if not upkeep.result():
                        return
                upkeep = asyncio.ensure_future(self.heartbeat_upkeep())
        except asyncio.CancelledError:
            if upkeep is not None and not upkeep.done():
                upkeep.cancel()
                upkeep.add_done_callback(abandoned)
            raise
        except Exception:
            logger.exception("Table heartbeat failed for %s", self.campaign_id)
            await self.close(code=1011)

    async def heartbeat_upkeep(self):
        with metrics.handler("heartbeat"):
            try:
                if not await self.authorized():
                    return False
                # Keep Redis group membership alive beyond its default expiry.
                await self.channel_layer.group_add(self.group, self.channel_name)
                await self.channel_layer.group_add(access.user_group(self.user_id), self.channel_name)
                await self.remove_expired_leases()
                # Refresh names/roles after other sockets come and go.
                await self.emit("table.presence", await db(services.roster)(self.campaign_id))
            except OperationalError as error:
                if not database_busy(error):
                    raise
                # Contention must not close the socket; the next beat tries again.
                metrics.database_busy()
                return True
            await self.replay_deferred()
            return True

    async def remove_expired_leases(self):
        """Remove leases of crashed workers, at most once per half TTL per process."""
        global _last_lease_cleanup
        now = monotonic()
        if now - _last_lease_cleanup < settings.GRAVEWRIGHT_PRESENCE_TTL / 2:
            return
        _last_lease_cleanup = now
        if await db(services.remove_expired, thread_sensitive=False)():
            await self.publish_presence()

    async def disconnect(self, code):
        await self.hide_cursor()
        # Background tasks may be waiting on this socket's thread; do not wait for them.
        await self.stop_stream(wait=False)
        await self.end_drag("cancel")
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task.add_done_callback(abandoned)
        for lane in getattr(self, "lanes", ()):
            # A lane may be inside a synchronous call; it finishes in the background.
            lane.cancel()
            lane.add_done_callback(abandoned)
        if self.joined_group:
            await self.channel_layer.group_discard(self.group, self.channel_name)
            await self.channel_layer.group_discard(access.user_group(self.user_id), self.channel_name)
        if self.connection_id:
            # The socket's own thread may still be finishing an abandoned command.
            try:
                await asyncio.wait_for(db(services.depart, thread_sensitive=False)(self.connection_id),
                                       DEPART_TIMEOUT)
            except TimeoutError:
                logger.warning("Presence cleanup for %s timed out; the lease will expire.", self.connection_id)
            await self.publish_presence()
