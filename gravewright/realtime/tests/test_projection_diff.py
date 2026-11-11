"""Sockets receive only what changed, computed from each recipient's own projection."""

import json
import random
from unittest.mock import AsyncMock, patch
import uuid

from channels.db import database_sync_to_async as db
from django.db import transaction
from django.test import TestCase, TransactionTestCase, override_settings

from gravewright.accounts.models import User
from gravewright.actors.models import Actor
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps.models import Broadcast, Scene, SceneObject
from gravewright.realtime import dispatch, projections
from gravewright.realtime.consumers import TableConsumer
from gravewright.realtime.models import CampaignRevision
from gravewright.tokens import services as token_services
from gravewright.tokens.models import Token


class DeltaFormatTests(TestCase):
    def test_equal_projections_have_no_delta(self):
        state = {"mapId": "m", "tokens": [{"id": "a", "x": 1}]}
        self.assertIsNone(projections.delta("tokens.state", state, json.loads(json.dumps(state))))

    def test_rows_travel_as_upserts_removes_and_order(self):
        before = {"mapId": "m", "tokens": [{"id": "a", "x": 1}, {"id": "b", "x": 2}, {"id": "c", "x": 3}]}
        after = {"mapId": "m", "tokens": [{"id": "c", "x": 3}, {"id": "a", "x": 9}, {"id": "d", "x": 4}],
                 "teleports": [{"id": "a", "version": 2}]}
        frame = projections.delta("tokens.state", before, after)
        self.assertEqual(frame["upserts"], {"tokens": [{"id": "a", "x": 9}, {"id": "d", "x": 4}]})
        self.assertEqual(frame["removes"], {"tokens": ["b"]})
        self.assertEqual(frame["order"], {"tokens": ["c", "a", "d"]})
        self.assertEqual(frame["teleports"], [{"id": "a", "version": 2}])
        self.assertEqual(projections.apply(before, frame), after)
        # Dropped keys are unset; an order the merge already produces is not sent.
        back = projections.delta("tokens.state", after, {"mapId": "m", "tokens": after["tokens"]})
        self.assertEqual(back, {"delta": True, "mapId": "m", "unset": ["teleports"]})

    def test_lists_without_identified_rows_travel_whole(self):
        before = {"sceneId": "s", "drawings": {"rows": [1]}, "walls": [1, 2]}
        after = {"sceneId": "s", "drawings": {"rows": [2]}, "walls": [1, 3]}
        frame = projections.delta("maps.layers", before, after)
        self.assertEqual((frame["drawings"], frame["walls"]), ({"rows": [2]}, [1, 3]))
        self.assertEqual(projections.apply(before, frame), after)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ProjectionDiffTests(TransactionTestCase):
    def setUp(self):
        self.gm = User.objects.create_user("diff-gm@example.test", "password-12345", name="GM")
        self.owner = User.objects.create_user("diff-owner@example.test", "password-12345", name="Owner")
        self.other = User.objects.create_user("diff-other@example.test", "password-12345", name="Other")
        self.campaign = Campaign.objects.create(owner=self.gm, name="Diffs")
        for user, role in ((self.gm, "gm"), (self.owner, "player"), (self.other, "player")):
            Membership.objects.create(campaign=self.campaign, user=user, role=role)
        self.scene = Scene.objects.create(campaign=self.campaign, name="Room", width=1024, height=1024,
                                          visibility="players")
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        self.actor = Actor.objects.create(campaign=self.campaign, name="Hero", data={},
                                          permissions={"default": "read", str(self.owner.pk): "owner"})
        self.users = (self.gm, self.owner, self.other)

    def consumer(self, user):
        consumer = TableConsumer()
        consumer.campaign_id, consumer.user_id = self.campaign.pk, user.pk
        consumer.token_map_id = consumer.map_layer_id = str(self.scene.pk)
        consumer.authorized = AsyncMock(return_value=True)
        consumer.emit, consumer.close = AsyncMock(), AsyncMock()
        consumer.member = Membership.objects.get(campaign=self.campaign, user=user)
        return consumer

    def command(self, action, data):
        envelopes = []
        with patch.object(dispatch, "send", side_effect=lambda _c, event: envelopes.append(event)):
            token_services.command(self.campaign.pk, self.gm.pk, action, {"mapId": str(self.scene.pk), **data},
                                   str(uuid.uuid4()))
        return [event for event in envelopes if event["type"] == "room.changes"]

    async def deliver(self, consumer, envelopes):
        consumer.emit.reset_mock()
        for envelope in envelopes:
            await consumer.room_changes(envelope)
        return [call.args for call in consumer.emit.await_args_list]

    def frames(self, deliveries, kind):
        return [payload for name, payload in deliveries if name == kind]

    async def subscribe(self, consumer):
        await consumer.room_changes({"refresh": ["maps.layers", "tokens"]})
        consumer.emit.reset_mock()

    async def test_unchanged_projection_sends_no_frame(self):
        consumer = await db(self.consumer)(self.gm)
        await self.subscribe(consumer)
        deliveries = await self.deliver(consumer, [{"type": "room.changes", "refresh": ["maps.layers", "tokens"]}])
        self.assertEqual([name for name, _ in deliveries], [])

    async def test_token_move_sends_only_moved_token(self):
        tokens = await db(lambda: [Token.objects.create(scene=self.scene, actor=self.actor, grid_x=i % 10, grid_y=i // 10)
                                   for i in range(50)])()
        consumer = await db(self.consumer)(self.other)
        await self.subscribe(consumer)
        moved = tokens[7]
        envelopes = await db(self.command)("move", {"id": str(moved.pk), "gridX": 12, "gridY": 12,
                                                    "expectedVersion": moved.version})
        [frame] = self.frames(await self.deliver(consumer, envelopes), "tokens.state")
        self.assertTrue(frame["delta"])
        self.assertEqual([row["id"] for row in frame["upserts"]["tokens"]], [str(moved.pk)])
        self.assertNotIn("removes", frame)
        expected = await db(token_services.state)(self.campaign.pk, self.other.pk, str(self.scene.pk))
        self.assertEqual(frame["upserts"]["tokens"], [row for row in expected["tokens"] if row["id"] == str(moved.pk)])

    async def test_token_move_does_not_resend_unchanged_layers(self):
        token = await db(Token.objects.create)(scene=self.scene, actor=self.actor)
        sizes = {}
        for images in (2, 102):
            await db(SceneObject.objects.bulk_create)([
                SceneObject(scene=self.scene, kind="images", data={"name": f"Image {i}", "layer": "image-layer"})
                for i in range(images - (2 if sizes else 0))])
            observer, owner = await db(self.consumer)(self.other), await db(self.consumer)(self.owner)
            for consumer in (observer, owner):
                await self.subscribe(consumer)
            await db(token.refresh_from_db)()
            envelopes = await db(self.command)("move", {"id": str(token.pk), "gridX": images % 7, "gridY": 1,
                                                        "expectedVersion": token.version})
            watched = await self.deliver(observer, envelopes)
            # Nothing on the layers changed for this player: no layer frame at all.
            self.assertEqual(self.frames(watched, "maps.layers"), [])
            sizes[images] = sum(len(json.dumps(payload)) for _, payload in watched)
            # The owner's token vision moved: only that field travels, never the images.
            for frame in self.frames(await self.deliver(owner, envelopes), "maps.layers"):
                self.assertTrue(frame["delta"])
                self.assertNotIn("images", json.dumps({k: v for k, v in frame.items() if k != "sceneId"}))
        # Equal within a few digits of changing coordinates: no layer data travels.
        self.assertLess(abs(sizes[2] - sizes[102]), 16)

    async def test_hidden_token_never_leaks_to_player(self):
        token = await db(Token.objects.create)(scene=self.scene, actor=self.actor, hidden=True)
        consumer = await db(self.consumer)(self.other)
        await self.subscribe(consumer)
        frames = []
        for action, data in (("move", {"id": str(token.pk), "gridX": 3, "gridY": 3, "expectedVersion": 1}),
                             ("configure", {"tokenIds": [str(token.pk)], "values": {"rotation": 90},
                                            "expectedVersion": 2})):
            frames += await self.deliver(consumer, await db(self.command)(action, data))
        self.assertNotIn(str(token.pk), json.dumps(frames))

    async def test_hiding_and_revealing_token_for_player(self):
        token = await db(Token.objects.create)(scene=self.scene, actor=self.actor)
        consumer = await db(self.consumer)(self.other)
        await self.subscribe(consumer)
        hide = await db(self.command)("hidden", {"tokenIds": [str(token.pk)], "hidden": True})
        [frame] = self.frames(await self.deliver(consumer, hide), "tokens.state")
        self.assertEqual(frame["removes"], {"tokens": [str(token.pk)]})
        show = await db(self.command)("hidden", {"tokenIds": [str(token.pk)], "hidden": False})
        [frame] = self.frames(await self.deliver(consumer, show), "tokens.state")
        self.assertEqual([row["id"] for row in frame["upserts"]["tokens"]], [str(token.pk)])

    async def test_permission_change_reprojects_row(self):
        token = await db(Token.objects.create)(scene=self.scene, actor=self.actor)
        consumer = await db(self.consumer)(self.other)
        await self.subscribe(consumer)
        before = await db(token_services.state)(self.campaign.pk, self.other.pk, str(self.scene.pk))
        await db(Actor.objects.filter(pk=self.actor.pk).update)(
            permissions={"default": "read", str(self.other.pk): "owner"})
        envelopes = []
        with patch.object(dispatch, "send", side_effect=lambda _c, event: envelopes.append(event)):
            await db(dispatch.changed)(self.campaign.pk, self.gm.pk, "actors", "actor.permissions", uuid.uuid4())
        [frame] = self.frames(await self.deliver(consumer, envelopes), "tokens.state")
        after = await db(token_services.state)(self.campaign.pk, self.other.pk, str(self.scene.pk))
        self.assertNotEqual(before, after)
        self.assertEqual(projections.apply(before, frame), after)

    async def test_scene_switch_and_resubscribe_send_full_state(self):
        other = await db(Scene.objects.create)(campaign=self.campaign, name="Other", width=512, height=512)
        consumer = await db(self.consumer)(self.gm)
        await self.subscribe(consumer)
        consumer.token_map_id = str(other.pk)
        [frame] = self.frames(await self.deliver(consumer, [{"type": "room.changes", "refresh": ["tokens"]}]),
                              "tokens.state")
        self.assertNotIn("delta", frame)
        consumer.forget_projections("tokens.state")  # what a tokens.sync request does
        [frame] = self.frames(await self.deliver(consumer, [{"type": "room.changes", "refresh": ["tokens"]}]),
                              "tokens.state")
        self.assertNotIn("delta", frame)

    async def test_resource_sync_forgets_only_its_own_module(self):
        consumer = await db(self.consumer)(self.gm)

        async def sync(module, scene_id=None):
            payload = {"module": module, "sceneId": scene_id}
            await consumer.route("resources.sync", payload, json.dumps({"payload": payload}), 0)

        # The browser subscribes every module in one burst after connecting.
        await sync("items")
        await sync("clocks")
        refresh = {"type": "room.changes", "refresh": ["resources:items", "resources:clocks"]}
        self.assertEqual(self.frames(await self.deliver(consumer, [refresh]), "resources.state"), [])
        # A new scene for one module sends it whole and drops its previous scene.
        consumer.emit.reset_mock()
        await sync("items", str(self.scene.pk))
        self.assertEqual([payload["module"] for payload in
                          self.frames([call.args for call in consumer.emit.await_args_list], "resources.state")],
                         ["items"])
        self.assertEqual(sorted(key for kind, key in consumer.sent_projections if kind == "resources.state"),
                         [("clocks", None), ("items", str(self.scene.pk))])

    async def test_delta_replay_equals_full_projection(self):
        rng = random.Random(20261109)
        consumers = {user.pk: await db(self.consumer)(user) for user in self.users}
        states = {}
        for user_pk, consumer in consumers.items():
            await consumer.room_changes({"refresh": ["tokens"]})
            states[user_pk] = consumer.emit.await_args.args[1]

        def step():
            tokens = list(Token.objects.filter(scene=self.scene))
            action = rng.choice(["place", "move", "hidden", "configure", "remove", "permissions"] if tokens else ["place"])
            token = rng.choice(tokens) if tokens else None
            if action == "permissions":
                level = rng.choice(["owner", "read", "none"])
                Actor.objects.filter(pk=self.actor.pk).update(
                    permissions={"default": "read", str(rng.choice(self.users[1:]).pk): level})
                envelopes = []
                with patch.object(dispatch, "send", side_effect=lambda _c, event: envelopes.append(event)):
                    dispatch.changed(self.campaign.pk, self.gm.pk, "actors", "actor.permissions", uuid.uuid4())
                return [event for event in envelopes if event["type"] == "room.changes"]
            data = {
                "place": lambda: {"actorId": str(self.actor.pk), "gridX": rng.randrange(8), "gridY": rng.randrange(8)},
                "move": lambda: {"id": str(token.pk), "gridX": rng.randrange(8), "gridY": rng.randrange(8),
                                 "expectedVersion": token.version},
                "hidden": lambda: {"tokenIds": [str(token.pk)], "hidden": not token.hidden},
                "configure": lambda: {"tokenIds": [str(token.pk)], "values": {"rotation": rng.randrange(360)},
                                      "expectedVersion": token.version},
                "remove": lambda: {"tokenIds": [str(token.pk)]},
            }[action]()
            return self.command(action, data)

        for _ in range(40):
            envelopes = await db(step)()
            for user_pk, consumer in consumers.items():
                for frame in self.frames(await self.deliver(consumer, envelopes), "tokens.state"):
                    states[user_pk] = projections.apply(states[user_pk], frame) if frame.get("delta") else frame
                expected = await db(token_services.state)(self.campaign.pk, user_pk, str(self.scene.pk))
                self.assertEqual(json.loads(json.dumps(states[user_pk])), json.loads(json.dumps(expected)))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class RevisionTests(TransactionTestCase):
    def setUp(self):
        self.gm = User.objects.create_user("revision-gm@example.test", "password-12345", name="GM")
        self.campaign = Campaign.objects.create(owner=self.gm, name="Revisions")
        self.other = Campaign.objects.create(owner=self.gm, name="Elsewhere")
        Membership.objects.create(campaign=self.campaign, user=self.gm, role="gm")

    def envelope(self, campaign=None, fail=False):
        sent = []
        with patch.object(dispatch, "send", side_effect=lambda _c, event: sent.append(event)):
            try:
                with transaction.atomic():
                    dispatch.changed((campaign or self.campaign).pk, self.gm.pk, "audio", "play", uuid.uuid4())
                    if fail:
                        raise RuntimeError
            except RuntimeError:
                pass
        return sent

    def test_revision_increments_once_per_commit_and_not_on_rollback(self):
        self.assertEqual([event["revision"] for event in self.envelope()], [1])
        self.assertEqual(self.envelope(fail=True), [])
        self.assertEqual([event["revision"] for event in self.envelope()], [2])
        self.assertEqual(dispatch.revision(self.campaign.pk), 2)

    def test_revision_is_campaign_scoped(self):
        self.envelope()
        self.assertEqual([event["revision"] for event in self.envelope(self.other)], [1])
        self.assertEqual(CampaignRevision.objects.get(campaign=self.campaign).value, 1)

    def test_missing_campaign_sends_an_envelope_without_revision(self):
        sent = []
        with patch.object(dispatch, "send", side_effect=lambda _c, event: sent.append(event)):
            dispatch.changed(uuid.uuid4(), self.gm.pk, "audio", "play", uuid.uuid4())
        self.assertNotIn("revision", sent[0])

    async def test_revision_gap_triggers_resync(self):
        consumer = TableConsumer()
        consumer.campaign_id, consumer.user_id = self.campaign.pk, self.gm.pk
        consumer.authorized = AsyncMock(return_value=True)
        consumer.deliver_changes = AsyncMock()
        consumer.revision = 4
        await consumer.room_changes({"refresh": ["resources:audio"], "revision": 5})
        self.assertEqual(consumer.deliver_changes.await_args.args[0], ["resources:audio"])
        await consumer.room_changes({"refresh": ["resources:audio"], "revision": 7})
        self.assertEqual(consumer.deliver_changes.await_args.args[0], list(dispatch.PROJECTIONS))
        consumer.deliver_changes.reset_mock()
        await consumer.room_changes({"refresh": ["tokens"], "revision": 6})  # late: already covered
        consumer.deliver_changes.assert_not_awaited()
        self.assertEqual(consumer.revision, 7)

    async def test_failed_delivery_does_not_advance_the_revision(self):
        consumer = TableConsumer()
        consumer.campaign_id, consumer.user_id = self.campaign.pk, self.gm.pk
        consumer.authorized = AsyncMock(return_value=True)
        consumer.deliver_changes = AsyncMock(side_effect=RuntimeError("busy"))
        consumer.revision = 1
        with self.assertRaises(RuntimeError):
            await consumer.room_changes({"refresh": ["tokens"], "revision": 2})
        self.assertEqual(consumer.revision, 1)  # a replay of revision 2 still runs
