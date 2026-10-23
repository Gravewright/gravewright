"""Public ownership calls retain private GM snapshots and native retry semantics."""

import json
from unittest.mock import patch
from uuid import uuid4

from django.db import transaction
from django.test import TestCase, override_settings

from api import API_VERSION, actors, capabilities, events, ownership
from api.errors import JournalError
from gravewright.accounts.models import User
from gravewright.actors.models import Actor, Folder
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps.models import Receipt


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class PublicOwnershipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gm = User.objects.create(email="public-ownership-gm@example.test", name="GM", role="owner")
        cls.player = User.objects.create(email="public-ownership-player@example.test", name="Player")
        cls.inactive = User.objects.create(email="public-ownership-inactive@example.test", name="Inactive private", is_active=False)
        cls.foreign_user = User.objects.create(email="public-ownership-foreign@example.test", name="Foreign private")
        cls.campaign = Campaign.objects.create(owner=cls.gm, name="Public ownership")
        cls.foreign_campaign = Campaign.objects.create(owner=cls.gm, name="Foreign ownership")
        for campaign in (cls.campaign, cls.foreign_campaign):
            Membership.objects.create(campaign=campaign, user=cls.gm, role="gm")
        Membership.objects.create(campaign=cls.campaign, user=cls.player, role="player")
        Membership.objects.create(campaign=cls.campaign, user=cls.inactive, role="player")
        Membership.objects.create(campaign=cls.foreign_campaign, user=cls.foreign_user, role="player")
        cls.actor = Actor.objects.create(campaign=cls.campaign, name="Private actor", data={"secret": "PRIVATE_SHEET_DATA"},
                                         permissions={str(cls.player.pk): "owner"})
        cls.foreign_actor = Actor.objects.create(campaign=cls.foreign_campaign, name="Foreign actor", data={"secret": "FOREIGN_SHEET_DATA"})

    def state(self, kind="actors", resource_id=None, user=None):
        return ownership.state(self.campaign.pk, (user or self.gm).pk, kind, str(resource_id or self.actor.pk))

    def command(self, payload, request_id=None, *, kind="actors", resource_id=None, user=None):
        return ownership.command(self.campaign.pk, (user or self.gm).pk, kind, str(resource_id or self.actor.pk), payload, request_id or uuid4())

    def test_facade_returns_current_gm_snapshot_without_sheet_data_or_foreign_members(self):
        from gravewright.table import permission_services
        self.assertIs(ownership.state, permission_services.state)
        self.assertIs(ownership.command, permission_services.command)
        current = self.state()
        self.assertEqual(current["title"], "Private actor")
        self.assertEqual(current["permissions"], {"default": "none", str(self.player.pk): "owner"})
        self.assertEqual(current["version"], 1)
        self.assertEqual({member["id"] for member in current["members"]}, {str(self.gm.pk), str(self.player.pk)})
        self.assertNotIn("PRIVATE_SHEET_DATA", json.dumps(current))
        self.assertNotIn("Inactive private", json.dumps(current))
        self.assertNotIn("Foreign private", json.dumps(current))
        self.assertTrue(all(set(member) == {"id", "name", "role"} for member in current["members"]))

    def test_explicit_revision_and_uuid_replay_commit_and_notify_exactly_once(self):
        request, changes = uuid4(), []
        def changed(sender, change, **kwargs): changes.append((sender, change))
        events.resource_changed.connect(changed, weak=False, dispatch_uid="public-ownership-once")
        self.addCleanup(events.resource_changed.disconnect, dispatch_uid="public-ownership-once")
        with patch("gravewright.realtime.dispatch.send") as send:
            with self.captureOnCommitCallbacks(execute=True):
                result = self.command({"version": self.state()["version"], "permissions": {"default": "read"}}, request)
                self.assertFalse(send.called)
                self.assertEqual(changes, [])
            self.assertTrue(send.called)
            self.assertEqual(result["version"], 2)
            self.assertEqual(len(changes), 1)
            self.assertEqual(changes[0][0], "actors")
            self.assertEqual(changes[0][1].request_id, request)
            self.assertEqual(changes[0][1].action, "permissions")
            send.reset_mock()
            with self.captureOnCommitCallbacks(execute=True):
                replay = self.command({"version": 1, "permissions": {"default": "none"}}, request)
            self.assertEqual(replay, result)
            self.assertFalse(send.called)
            self.assertEqual(len(changes), 1)
        self.actor.refresh_from_db()
        self.assertEqual(self.actor.permissions, {"default": "read"})
        self.assertEqual(self.actor.version, 2)
        self.assertEqual(Receipt.objects.filter(campaign=self.campaign, user=self.gm, request_id=request).count(), 1)

    def test_stale_boolean_and_wrong_revision_types_and_invalid_request_uuid_do_not_write(self):
        self.command({"version": 1, "permissions": {"default": "read"}})
        before = self.state()
        with patch("gravewright.realtime.dispatch.send") as send:
            with self.captureOnCommitCallbacks(execute=True):
                for version in (1, True, False, "2", 2.0, None):
                    with self.subTest(version=version), self.assertRaises(JournalError) as caught:
                        self.command({"version": version, "permissions": {"default": "owner"}})
                    self.assertEqual(caught.exception.code, "conflict")
                with self.assertRaises(JournalError):
                    self.command({"version": 2, "permissions": {"default": "owner"}}, "invalid-request-uuid")
            self.assertFalse(send.called)
        self.assertEqual(self.state(), before)
        self.assertEqual(Receipt.objects.count(), 1)

    def test_players_revoked_members_and_cross_campaign_ids_cannot_inspect_or_change_grants(self):
        for user in (self.player,):
            with self.assertRaises(JournalError) as caught: self.state(user=user)
            self.assertEqual(caught.exception.code, "forbidden")
            with self.assertRaises(JournalError) as caught:
                self.command({"version": 1, "permissions": {"default": "owner"}}, user=user)
            self.assertEqual(caught.exception.code, "forbidden")
        self.assertEqual(ownership.state(self.foreign_campaign.pk, self.gm.pk, "actors", str(self.foreign_actor.pk))["id"], str(self.foreign_actor.pk))
        with self.assertRaises(JournalError) as caught: self.state(resource_id=self.foreign_actor.pk)
        self.assertEqual(caught.exception.code, "not_found")
        with self.assertRaises(JournalError) as caught:
            self.command({"version": 1, "permissions": {"default": "read"}}, resource_id=self.foreign_actor.pk)
        self.assertEqual(caught.exception.code, "not_found")
        self.campaign.memberships.filter(user=self.gm).delete()
        with self.assertRaises(JournalError) as caught: self.state()
        self.assertEqual(caught.exception.code, "not_a_member")
        with self.assertRaises(JournalError): self.command({"version": 1, "permissions": {"default": "read"}})
        self.actor.refresh_from_db(); self.foreign_actor.refresh_from_db()
        self.assertEqual(self.actor.version, 1)
        self.assertEqual(self.foreign_actor.permissions, {})
        self.assertEqual(Receipt.objects.count(), 0)

    def test_outer_rollback_preserves_grants_without_receipt_notification_or_hook(self):
        request, changes = uuid4(), []
        def changed(sender, change, **kwargs): changes.append(change)
        events.resource_changed.connect(changed, weak=False, dispatch_uid="public-ownership-rollback")
        self.addCleanup(events.resource_changed.disconnect, dispatch_uid="public-ownership-rollback")
        before = self.state()
        with patch("gravewright.realtime.dispatch.send") as send:
            with self.captureOnCommitCallbacks(execute=True):
                try:
                    with transaction.atomic():
                        self.command({"version": before["version"], "permissions": {"default": "owner"}}, request)
                        raise RuntimeError("Abort enclosing transaction")
                except RuntimeError: pass
            self.assertFalse(send.called)
        self.assertEqual(changes, [])
        self.assertEqual(self.state(), before)
        self.assertFalse(Receipt.objects.filter(request_id=request).exists())

    def test_folder_opaque_revision_detects_child_changes_and_bulk_edit_preserves_descendants(self):
        folder = Folder.objects.create(campaign=self.campaign, name="Party")
        nested_folder = Folder.objects.create(campaign=self.campaign, parent=folder, name="Nested")
        self.actor.folder = folder
        self.actor.permissions = {str(self.player.pk): "none"}
        self.actor.save()
        nested = Actor.objects.create(campaign=self.campaign, folder=nested_folder, name="Nested private", permissions={})
        current = self.state("actor-folders", folder.pk)
        self.assertIsInstance(current["version"], str)
        result = self.command({"version": current["version"], "permissions": {"default": "read", str(self.player.pk): "unchanged"}},
                              kind="actor-folders", resource_id=folder.pk)
        self.actor.refresh_from_db(); nested.refresh_from_db()
        self.assertEqual(self.actor.permissions, {"default": "read", str(self.player.pk): "none"})
        self.assertEqual(nested.permissions, {})
        newcomer = Actor.objects.create(campaign=self.campaign, folder=folder, name="New child")
        with self.assertRaises(JournalError) as caught:
            self.command({"version": result["version"], "permissions": {"default": "owner"}}, kind="actor-folders", resource_id=folder.pk)
        self.assertEqual(caught.exception.code, "conflict")
        fresh = self.state("actor-folders", folder.pk)
        actors.command(self.campaign.pk, self.gm.pk, "actor.update", {"id": str(newcomer.pk), "version": newcomer.version, "name": "Changed child"}, uuid4())
        with self.assertRaises(JournalError) as caught:
            self.command({"version": fresh["version"], "permissions": {"default": "owner"}}, kind="actor-folders", resource_id=folder.pk)
        self.assertEqual(caught.exception.code, "conflict")
        newcomer.refresh_from_db()
        self.assertEqual(newcomer.permissions, {})

    def test_local_capability_catalog_needs_no_queries_and_caller_edits_are_isolated(self):
        with self.assertNumQueries(0):
            current = capabilities()
            current["browser"]["domains"]["actors"]["create"] = "caller-change"
            current["browser"]["binary"]["maps"].clear()
            fresh = capabilities()
        self.assertEqual(fresh["pythonVersion"], API_VERSION)
        self.assertEqual(fresh["browser"]["domains"]["actors"]["create"], "actor.create")
        self.assertEqual(fresh["browser"]["binary"]["maps"]["upload"], "upload")
        self.assertNotIn(str(self.campaign.pk), json.dumps(fresh))
        self.assertNotIn(str(self.actor.pk), json.dumps(fresh))
