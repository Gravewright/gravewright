"""One refresh envelope per commit, delivered once per projection."""

from collections import Counter
from unittest.mock import patch
import uuid

import msgpack
from channels.db import database_sync_to_async as db
from django.db import transaction
from django.test import TransactionTestCase, override_settings

from gravewright.campaigns.models import Membership
from gravewright.realtime import dispatch
from gravewright.realtime.tests import test_scene_update_priority as priority

MODULES = ("items", "combat", "cards", "audio", "compendiums")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"])
class DispatchEnvelopeTests(TransactionTestCase):
    setUp = priority.SceneUpdatePriorityTests.setUp
    consumer = priority.SceneUpdatePriorityTests.consumer

    def subscribed(self, user):
        consumer = self.consumer(user)
        consumer.actors_subscribed = consumer.journals_subscribed = True
        consumer.table_modules = {name: str(self.scene.pk) for name in MODULES}
        return consumer

    def commit(self, resource, action, result=None, fail=False):
        sent = []
        with patch.object(dispatch, "send", side_effect=lambda _campaign, event: sent.append(event)), \
                patch("gravewright.table.events.resource_changed.send_robust", return_value=[]) as notify:
            try:
                with transaction.atomic():
                    dispatch.changed(self.campaign.pk, self.gm.pk, resource, action, uuid.uuid4(), result)
                    self.assertEqual((sent, notify.call_count), ([], 0))
                    if fail:
                        raise RuntimeError("rolled back")
            except RuntimeError:
                pass
        return sent, notify.call_count

    def test_one_envelope_per_commit(self):
        sent, notified = self.commit("audio", "play")
        self.assertEqual(sent, [{"type": "room.changes", "resource": "audio", "action": "play",
                                 "refresh": ["resources:audio"], "revision": 1}])
        self.assertEqual(notified, 1)

    def test_rollback_sends_nothing(self):
        self.assertEqual(self.commit("tokens", "move", fail=True), ([], 0))

    def test_handouts_keep_their_own_event_before_the_envelope(self):
        presentation = {"issuer": str(self.gm.pk), "target": None}
        sent, _ = self.commit("journals", "present", {"presentation": presentation})
        self.assertEqual([event["type"] for event in sent], ["room.handout", "room.changes"])
        self.assertEqual(sent[1]["refresh"], ["journals"])

    def test_envelope_survives_msgpack_round_trip(self):
        marker = {"id": str(uuid.uuid4()), "version": 4}
        [envelope], _ = self.commit("tokens", "teleport", {"mapId": str(self.scene.pk), "teleports": [marker]})
        # channels_redis serializes events with msgpack: only plain types may cross.
        self.assertEqual(msgpack.unpackb(msgpack.packb(envelope)), envelope)

    async def test_each_projection_is_delivered_once(self):
        [envelope], _ = await db(self.commit)("actors", "sheet.save")
        consumer = self.subscribed(self.gm)
        await consumer.room_changes(envelope)
        kinds = Counter(call.args[0] for call in consumer.emit.await_args_list)
        modules = Counter(call.args[1]["module"] for call in consumer.emit.await_args_list
                          if call.args[0] == "resources.state")
        self.assertEqual((kinds["maps.layers"], kinds["tokens.state"], kinds["actors.state"]), (1, 1, 1))
        self.assertEqual(modules, Counter({"audio": 1, "combat": 1}))
        domains = Counter(call.args[1]["domain"] for call in consumer.emit.await_args_list
                          if call.args[0] == "api.changed")
        self.assertEqual(set(domains.values()), {1})
        self.assertEqual(set(domains), {"maps.layers", "tokens", "actors", "audio", "combat"})

    async def test_board_is_delivered_before_dependent_resources(self):
        [envelope], _ = await db(self.commit)("tokens", "move")
        consumer = self.subscribed(self.player)
        await consumer.room_changes(envelope)
        kinds = [call.args[0] for call in consumer.emit.await_args_list if call.args[0] != "api.changed"]
        self.assertEqual(kinds, ["maps.layers", "tokens.state", "resources.state"])

    async def test_revocation_during_delivery_stops_dependent_resources(self):
        [envelope], _ = await db(self.commit)("tokens", "move")
        consumer = self.subscribed(self.player)

        async def emit(kind, _payload):
            if kind == "tokens.state":
                await db(Membership.objects.filter(pk=self.player_membership.pk).delete)()
        consumer.emit.side_effect = emit
        await consumer.room_changes(envelope)
        self.assertNotIn("resources.state", [call.args[0] for call in consumer.emit.await_args_list])
        consumer.close.assert_awaited()

    async def test_revoked_member_receives_nothing(self):
        [envelope], _ = await db(self.commit)("actors", "sheet.save")
        await db(Membership.objects.filter(pk=self.player_membership.pk).delete)()
        consumer = self.subscribed(self.player)
        await consumer.room_changes(envelope)
        self.assertEqual(consumer.emit.await_args_list, [])
        consumer.close.assert_awaited()
