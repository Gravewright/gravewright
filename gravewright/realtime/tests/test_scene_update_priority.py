"""Committed scene changes reach the board before dependent resource refreshes."""

import asyncio
from unittest.mock import AsyncMock, patch
import uuid

from channels.db import database_sync_to_async as db
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.test import Client, TransactionTestCase, override_settings
from django.db import transaction

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps.models import Broadcast, Scene, SceneObject
from gravewright.realtime.consumers import TableConsumer
from gravewright.realtime.dispatch import changed
from config.asgi import application


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
                   ALLOWED_HOSTS=["testserver"])
class SceneUpdatePriorityTests(TransactionTestCase):
    def setUp(self):
        self.gm = User.objects.create_user("scene-priority-gm@example.test", "synthetic-password", name="GM")
        self.player = User.objects.create_user("scene-priority-player@example.test", "synthetic-password", name="Player")
        self.campaign = Campaign.objects.create(owner=self.gm, name="Scene delivery")
        Membership.objects.create(campaign=self.campaign, user=self.gm, role="gm")
        self.player_membership = Membership.objects.create(campaign=self.campaign, user=self.player, role="player")
        self.scene = Scene.objects.create(campaign=self.campaign, name="Room", width=512, height=512)
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        self.visible = SceneObject.objects.create(scene=self.scene, kind="images", data={"name": "Visible", "layer": "image-layer"})
        self.hidden = SceneObject.objects.create(scene=self.scene, kind="images", data={"name": "Private", "layer": "gm-image-layer"})
        self.sessions = {}
        for user in (self.gm, self.player):
            client = Client()
            client.force_login(user)
            self.sessions[user.pk] = client.cookies[settings.SESSION_COOKIE_NAME].value

    def consumer(self, user):
        consumer = TableConsumer()
        consumer.campaign_id = self.campaign.pk
        consumer.user_id = user.pk
        consumer.session_key = self.sessions[user.pk]
        consumer.map_layer_id = str(self.scene.pk)
        consumer.token_map_id = str(self.scene.pk)
        consumer.api_watching = True
        consumer.table_modules = {"audio": str(self.scene.pk), "combat": str(self.scene.pk)}
        consumer.emit = AsyncMock()
        consumer.close = AsyncMock()
        return consumer

    async def test_scene_projection_is_delivered_before_a_slow_audio_refresh(self):
        consumer = self.consumer(self.player)
        refreshing, resume = asyncio.Event(), asyncio.Event()

        async def refresh(_event):
            refreshing.set()
            await resume.wait()

        consumer.room_resources = AsyncMock(side_effect=refresh)
        task = asyncio.create_task(consumer.room_map_layers({}))
        try:
            await asyncio.wait_for(refreshing.wait(), timeout=3)
            deliveries = consumer.emit.await_args_list
            self.assertEqual(deliveries[0].args[0], "maps.layers")
            projection = deliveries[0].args[1]
            self.assertEqual([row["id"] for row in projection["images"]], [str(self.visible.pk)])
            self.assertNotIn(str(self.hidden.pk), str(projection))
            self.assertIn("api.changed", [call.args[0] for call in deliveries])
        finally:
            resume.set()
            await task

    async def test_tokens_are_delivered_before_audio_and_combat_refreshes(self):
        consumer = self.consumer(self.player)
        order = []

        async def emit(kind, _payload):
            order.append(kind)

        async def refresh(event):
            order.append(event["module"])

        consumer.emit.side_effect = emit
        consumer.room_resources = AsyncMock(side_effect=refresh)
        await consumer.room_tokens({})
        self.assertEqual(order[0], "tokens.state")
        self.assertEqual(order[-2:], ["audio", "combat"])
        self.assertIn("api.changed", order)

    async def test_live_socket_pushes_the_scene_before_waiting_on_dependent_audio(self):
        socket = WebsocketCommunicator(application, f"/ws/tables/{self.campaign.pk}/", headers=[
            (b"host", b"testserver"), (b"origin", b"http://testserver"),
            (b"cookie", f"{settings.SESSION_COOKIE_NAME}={self.sessions[self.player.pk]}".encode())])
        refreshing, resume = asyncio.Event(), asyncio.Event()
        original = TableConsumer.room_resources

        async def next_event(*kinds):
            for _ in range(30):
                message = await socket.receive_json_from(timeout=3)
                if message["type"] in kinds:
                    return message
            self.fail(f"Missing socket event: {kinds}")

        async def refresh(consumer, event):
            if event.get("module") == "audio":
                refreshing.set()
                await resume.wait()
            await original(consumer, event)

        try:
            self.assertTrue((await socket.connect(timeout=5))[0])
            await next_event("chat.history")
            await socket.send_json_to({"type": "maps.layers", "payload": {"mapId": str(self.scene.pk)}})
            await next_event("maps.layers")
            await socket.send_json_to({"type": "api.watch"})
            await socket.send_json_to({"type": "resources.sync", "payload": {
                "module": "audio", "sceneId": str(self.scene.pk)}})
            await next_event("resources.state")
            with patch.object(TableConsumer, "room_resources", refresh):
                await db(changed)(self.campaign.pk, self.gm.pk, "maps", "objects", uuid.uuid4())
                await asyncio.wait_for(refreshing.wait(), timeout=3)
                message = await next_event("maps.layers", "api.changed")
                self.assertEqual(message["type"], "maps.layers")
                self.assertEqual([row["id"] for row in message["payload"]["images"]], [str(self.visible.pk)])
                resume.set()
                await next_event("resources.state")
        finally:
            resume.set()
            await socket.disconnect()

    async def test_scene_refresh_still_rechecks_authorization_for_later_deliveries(self):
        consumer = self.consumer(self.player)

        async def revoke(kind, _payload):
            if kind == "maps.layers":
                await db(Membership.objects.filter(pk=self.player_membership.pk).delete)()

        consumer.emit.side_effect = revoke
        await consumer.room_map_layers({})
        self.assertEqual([call.args[0] for call in consumer.emit.await_args_list], ["maps.layers"])
        consumer.close.assert_awaited()

    async def test_revoked_membership_receives_no_scene_or_token_projection(self):
        consumer = self.consumer(self.player)
        await db(Membership.objects.filter(pk=self.player_membership.pk).delete)()
        await consumer.room_map_layers({})
        await consumer.room_tokens({})
        consumer.emit.assert_not_awaited()
        consumer.close.assert_awaited()

    async def test_scene_access_is_rechecked_without_suppressing_resource_invalidations(self):
        consumer = self.consumer(self.player)
        await db(Scene.objects.filter(pk=self.scene.pk).update)(visibility="gm")
        await consumer.room_map_layers({})
        self.assertIsNone(consumer.map_layer_id)
        deliveries = [call.args for call in consumer.emit.await_args_list]
        self.assertNotIn("maps.layers", [kind for kind, _ in deliveries])
        self.assertIn(("api.changed", {"domain": "maps.layers"}), deliveries)
        self.assertIn(("api.changed", {"domain": "audio"}), deliveries)

    def test_scene_event_is_first_and_all_resource_notifications_still_wait_for_commit(self):
        for resource, action in (("tokens", "move"), ("actors", "update")):
            with self.subTest(resource=resource), patch("gravewright.realtime.dispatch.send") as send:
                with transaction.atomic():
                    changed(self.campaign.pk, self.gm.pk, resource, action, uuid.uuid4())
                    send.assert_not_called()
                events = [call.args[1] for call in send.call_args_list]
                expected = [{"type": "room.map_layers", "refresh_audio": False}]
                if resource == "actors":
                    expected.append({"type": "room.actors"})
                expected.append({"type": "room.tokens", **({"refresh_combat": False}
                                                            if resource == "tokens" else {})})
                self.assertEqual(events[:len(expected)], expected)
                if resource == "actors":
                    self.assertIn({"type": "room.resources", "module": "combat"}, events)
