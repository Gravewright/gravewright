"""Token transport metadata follows the recipient's live, scene-scoped projection."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

from channels.db import database_sync_to_async as db
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from gravewright.accounts.models import User
from gravewright.actors.models import Actor
from gravewright.campaigns.models import Campaign, Membership, StreamerLink
from gravewright.maps.models import Broadcast, Scene
from gravewright.realtime.consumers import TableConsumer
from gravewright.tokens.models import Token


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TokenTeleportTests(TransactionTestCase):
    def setUp(self):
        self.users = {role: User.objects.create_user(f"teleport-{role}@example.test", "synthetic-password", name=role)
                      for role in ("gm", "player", "streamer")}
        self.campaign = Campaign.objects.create(owner=self.users["gm"], name="Transport table")
        for role, user in self.users.items():
            Membership.objects.create(campaign=self.campaign, user=user, role=role)
        StreamerLink.objects.create(campaign=self.campaign, guest=self.users["streamer"], digest="a" * 64,
                                    expires_at=timezone.now() + timedelta(hours=1))
        self.scene = Scene.objects.create(campaign=self.campaign, name="Room", width=512, height=512,
                                          visibility="players")
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        actor = Actor.objects.create(campaign=self.campaign, name="Traveler", data={}, permissions={"default": "read"})
        self.visible = Token.objects.create(scene=self.scene, actor=actor, version=3)
        self.hidden = Token.objects.create(scene=self.scene, actor=actor, hidden=True, version=5)
        self.foreign_scene = Scene.objects.create(campaign=self.campaign, name="Other room", width=512, height=512)
        self.foreign = Token.objects.create(scene=self.foreign_scene, actor=actor, version=7)

    def recipient(self, role):
        return SimpleNamespace(campaign_id=self.campaign.pk, user_id=self.users[role].pk,
            token_map_id=str(self.scene.pk), authorized=AsyncMock(return_value=True), emit=AsyncMock(),
            api_changed=AsyncMock(), room_resources=AsyncMock())

    def marker(self, token, **values):
        return {"id": str(token.pk), "version": token.version, **values}

    async def test_only_current_visible_markers_reach_each_recipient(self):
        event = {"mapId": str(self.scene.pk), "teleports": [self.marker(self.visible), self.marker(self.hidden),
            self.marker(self.foreign), {"id": str(uuid.uuid4()), "version": 3},
            self.marker(self.visible, version=2), self.marker(self.visible)]}
        for role in self.users:
            with self.subTest(role=role):
                recipient = self.recipient(role)
                await TableConsumer.room_tokens(recipient, event)
                kind, projection = recipient.emit.await_args.args
                self.assertEqual(kind, "tokens.state")
                self.assertEqual(projection["teleports"], [self.marker(self.visible)] +
                                 ([self.marker(self.hidden)] if role == "gm" else []))
                self.assertNotIn(str(self.foreign.pk), str(projection))
                if role != "gm":
                    self.assertNotIn(str(self.hidden.pk), str(projection))

    async def test_unscoped_foreign_stale_and_ordinary_refreshes_have_no_markers(self):
        for event in ({}, {"teleports": [self.marker(self.visible)]},
                      {"mapId": str(self.foreign_scene.pk), "teleports": [self.marker(self.visible)]},
                      {"mapId": str(self.scene.pk), "teleports": [self.marker(self.visible, version=2)]}):
            with self.subTest(event=event):
                recipient = self.recipient("player")
                await TableConsumer.room_tokens(recipient, event)
                self.assertNotIn("teleports", recipient.emit.await_args.args[1])

    async def test_hidden_and_revoked_scene_access_is_rechecked_before_delivery(self):
        event = {"mapId": str(self.scene.pk), "teleports": [self.marker(self.visible), self.marker(self.hidden)]}
        await db(Token.objects.filter(pk=self.visible.pk).update)(hidden=True)
        recipient = self.recipient("player")
        await TableConsumer.room_tokens(recipient, event)
        self.assertEqual(recipient.emit.await_args.args[1], {"mapId": str(self.scene.pk), "tokens": []})
        await db(Scene.objects.filter(pk=self.scene.pk).update)(visibility="gm")
        recipient = self.recipient("player")
        await TableConsumer.room_tokens(recipient, event)
        self.assertEqual(recipient.emit.await_args.args[1], {"mapId": str(self.scene.pk), "tokens": []})
        self.assertIsNone(recipient.token_map_id)

    async def test_an_unauthorized_recipient_receives_no_projection_or_markers(self):
        recipient = self.recipient("player")
        recipient.authorized.return_value = False
        await TableConsumer.room_tokens(recipient,
            {"mapId": str(self.scene.pk), "teleports": [self.marker(self.visible)]})
        recipient.emit.assert_not_awaited()
