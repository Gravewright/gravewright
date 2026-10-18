"""Automation transport rechecks audience and document access before delivery."""

from types import SimpleNamespace
import uuid
from unittest.mock import AsyncMock

from channels.db import database_sync_to_async as db
from django.test import TransactionTestCase, override_settings

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.journals.models import Journal
from gravewright.maps.models import Broadcast, Scene
from gravewright.realtime.consumers import TableConsumer


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AutomationPresentationTests(TransactionTestCase):
    def setUp(self):
        self.gm = User.objects.create_user("presentation-gm@example.test", "synthetic-password", name="GM")
        self.player = User.objects.create_user("presentation-player@example.test", "synthetic-password", name="Player")
        self.campaign = Campaign.objects.create(owner=self.gm, name="Presentation table")
        Membership.objects.create(campaign=self.campaign, user=self.gm, role="gm")
        Membership.objects.create(campaign=self.campaign, user=self.player, role="player")
        self.scene = Scene.objects.create(campaign=self.campaign, name="Room", width=512, height=512)
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        self.journal = Journal.objects.create(campaign=self.campaign, title="Shared", visibility="shared")

    def recipient(self):
        return SimpleNamespace(user_id=self.player.pk, campaign_id=self.campaign.pk,
                               authorized=AsyncMock(return_value=True), emit=AsyncMock())

    def event(self, **payload):
        return {"recipients": [str(self.player.pk)], "payload": {"id": str(uuid.uuid4()),
            "sceneId": str(self.scene.pk), "type": "message", "text": "Readable", **payload}}

    async def test_only_an_authorized_named_recipient_receives_the_wire_payload(self):
        recipient, event = self.recipient(), self.event()
        await TableConsumer.room_automation_presentation(recipient, event)
        recipient.emit.assert_awaited_once_with("automation.presentation", event["payload"])
        recipient.emit.reset_mock()
        await TableConsumer.room_automation_presentation(recipient, {**event, "recipients": [str(self.gm.pk)]})
        recipient.emit.assert_not_awaited()
        recipient.authorized.return_value = False
        await TableConsumer.room_automation_presentation(recipient, event)
        recipient.emit.assert_not_awaited()

    async def test_late_document_revocation_drops_the_presentation_without_a_grant(self):
        recipient = self.recipient()
        event = self.event(type="handout", journalId=str(self.journal.pk))
        await db(Journal.objects.filter(pk=self.journal.pk).update)(visibility="private")
        await TableConsumer.room_automation_presentation(recipient, event)
        recipient.emit.assert_not_awaited()
        self.assertFalse(await db(self.journal.access.exists)())

    async def test_late_scene_and_membership_changes_drop_the_event(self):
        recipient, event = self.recipient(), self.event()
        await db(Scene.objects.filter(pk=self.scene.pk).update)(visibility="gm")
        await TableConsumer.room_automation_presentation(recipient, event)
        recipient.emit.assert_not_awaited()
        await db(Scene.objects.filter(pk=self.scene.pk).update)(visibility="players")
        await db(Membership.objects.filter(campaign=self.campaign, user=self.player).delete)()
        await TableConsumer.room_automation_presentation(recipient, event)
        recipient.emit.assert_not_awaited()
