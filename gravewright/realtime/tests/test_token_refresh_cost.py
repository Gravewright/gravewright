"""Native moves refresh changing state once and retain live authorization."""

import uuid
from unittest.mock import patch

from channels.db import database_sync_to_async as db
from django.test import TestCase, TransactionTestCase, override_settings

from gravewright.actors import services as actors
from gravewright.campaigns.models import Membership
from gravewright.combat import services as combat
from gravewright.combat.models import Encounter
from gravewright.journals.services import member
from gravewright.maps.tests import test_blueprint_world as portals
from gravewright.maps.tests import test_regions as regions
from gravewright.realtime.dispatch import changed
from gravewright.realtime.tests import test_scene_update_priority as priority
from gravewright.tokens.models import Token


def prepare_encounter(fixture, token):
    """Exercise public/hidden combatants, linked/snapshot bars and actor entries."""
    fixture.actor.data = {"token": {"name": "Linked traveler"}, "bars": {"bar_1": {"value": 7, "max": 10}}}
    fixture.actor.save(update_fields=["data"])
    hidden = Token.objects.create(scene=fixture.scene, actor=fixture.actor, hidden=True, linked=False,
        snapshot={"token": {"name": "Private traveler"}, "bars": {"bar_2": {"value": 2, "max": 5}}})
    Encounter.objects.create(scene=fixture.scene, active=True, round=3, turn=0, combatants=[
        {"tokenId": str(token.pk), "initiative": 15}, {"tokenId": str(hidden.pk), "initiative": 10},
        {"actorId": str(fixture.actor.pk), "initiative": 5}])


def combat_views(fixture):
    return {user.pk: combat.state(member(fixture.campaign.pk, user.pk), str(fixture.scene.pk))
            for user in (fixture.gm, fixture.player)}


class TokenRefreshDispatchTests(TestCase):
    def notifications(self, resource, action, result=None):
        with patch("gravewright.realtime.dispatch.send") as send, \
                patch("gravewright.table.events.resource_changed.send_robust", return_value=[]) as notify, \
                self.captureOnCommitCallbacks(execute=True):
            changed(uuid.uuid4(), uuid.uuid4(), resource, action, uuid.uuid4(), result)
            send.assert_not_called()
            notify.assert_not_called()
        notify.assert_called_once()
        return [call.args[1] for call in send.call_args_list]

    def test_moves_and_teleports_defer_duplicate_audio_and_omit_unchanged_actors(self):
        for action in ("move", "teleport"):
            with self.subTest(action=action):
                marker = {"id": str(uuid.uuid4()), "version": 3}
                scene = str(uuid.uuid4())
                result = {"mapId": scene, "teleports": [marker]} if action == "teleport" else None
                events = self.notifications("tokens", action, result)
                self.assertEqual(events, [{"type": "room.map_layers", "refresh_audio": False},
                    {"type": "room.tokens", "refresh_combat": False, **({"mapId": scene, "teleports": [marker]}
                                              if action == "teleport" else {})}])

    def test_other_token_and_actor_commands_keep_actor_and_combat_notifications(self):
        for resource, action in (("actors", "actor.permissions"), ("actors", "sheet.save"),
                                 ("tokens", "place"), ("tokens", "remove"),
                                 ("tokens", "configure"), ("tokens", "condition-add")):
            with self.subTest(resource=resource, action=action):
                events = self.notifications(resource, action)
                self.assertEqual(events[:3], [{"type": "room.map_layers", "refresh_audio": False},
                                             {"type": "room.actors"}, {"type": "room.tokens"}])
                if resource == "actors" or action != "place":
                    self.assertIn({"type": "room.resources", "module": "combat"}, events)

    def test_map_only_changes_keep_their_independent_audio_refresh(self):
        self.assertEqual(self.notifications("maps", "objects"), [{"type": "room.map_layers"}])


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class NativePresenceRefreshTests(TestCase):
    setUp = regions.RegionTests.setUp
    asset = regions.RegionTests.asset
    post = regions.RegionTests.post
    save = regions.RegionTests.save
    generate = regions.RegionTests.generate
    generated = regions.RegionTests.generated
    token_command = regions.RegionTests.token_command
    place = regions.RegionTests.place
    move = regions.RegionTests.move

    def test_presence_changes_keep_actor_directory_unchanged_and_extension_hooks_intact(self):
        self.generated()
        token = self.place()
        prepare_encounter(self, token)
        combat_before = combat_views(self)
        self.move(token, 1, user=self.player)
        self.assertEqual(combat_views(self), combat_before)
        before = {user.pk: actors.state(self.campaign.pk, user.pk) for user in (self.gm, self.player)}
        rid = uuid.uuid4()
        with patch("gravewright.realtime.dispatch.send") as send, \
                patch("gravewright.table.events.resource_changed.send_robust", return_value=[]) as notify, \
                self.captureOnCommitCallbacks(execute=True):
            self.move(token, 2, user=self.player, rid=rid)
            self.assertFalse(send.called)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.assertEqual([call.args[1]["type"] for call in send.call_args_list],
                         ["room.automation", "room.map_layers", "room.tokens"])
        notify.assert_called_once()
        change = notify.call_args.kwargs["change"]
        self.assertEqual((change.resource, change.action, change.request_id), ("tokens", "move", rid))
        for user in (self.gm, self.player):
            self.assertEqual(actors.state(self.campaign.pk, user.pk), before[user.pk])
        self.assertEqual(combat_views(self), combat_before)
        self.move(token, 0, user=self.player)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertEqual(combat_views(self), combat_before)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class NativeTeleportRefreshTests(TestCase):
    setUp = portals.PortalTests.setUp
    asset = portals.PortalTests.asset
    post = portals.PortalTests.post
    save = portals.PortalTests.save
    generate = portals.PortalTests.generate
    generated = portals.PortalTests.generated
    token_command = portals.PortalTests.token_command
    place = portals.PortalTests.place
    move = portals.PortalTests.move
    area = portals.PortalTests.area

    def test_teleport_and_arrival_effects_leave_complete_combat_projections_unchanged(self):
        self.generated()
        token = self.place()
        prepare_encounter(self, token)
        before = combat_views(self)
        result = self.move(token, 2, user=self.player)
        self.assertEqual((token.grid_x, token.grid_y), (6, 5))
        self.assertEqual(result["teleports"], [{"id": str(token.pk), "version": token.version}])
        self.assertEqual(combat_views(self), before)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"])
class TokenRefreshDeliveryTests(TransactionTestCase):
    setUp = priority.SceneUpdatePriorityTests.setUp
    consumer = priority.SceneUpdatePriorityTests.consumer

    async def test_paired_move_delivers_tokens_then_one_authorized_audio_projection(self):
        consumer = self.consumer(self.player)
        await consumer.room_map_layers({"refresh_audio": False})
        self.assertFalse(any(call.args[0] == "resources.state" for call in consumer.emit.await_args_list))
        await consumer.room_tokens({"refresh_combat": False})
        deliveries = [call.args for call in consumer.emit.await_args_list]
        resources = [payload["module"] for kind, payload in deliveries if kind == "resources.state"]
        self.assertEqual(resources, ["audio"])
        kinds = [kind for kind, _ in deliveries]
        self.assertLess(kinds.index("maps.layers"), kinds.index("tokens.state"))
        self.assertLess(kinds.index("tokens.state"), kinds.index("resources.state"))
        self.assertIn(("api.changed", {"domain": "tokens"}), deliveries)
        self.assertNotIn(("api.changed", {"domain": "combat"}), deliveries)

    async def test_direct_token_sync_keeps_audio_and_combat_refreshes(self):
        consumer = self.consumer(self.player)
        await consumer.room_tokens({})
        resources = [call.args[1]["module"] for call in consumer.emit.await_args_list
                     if call.args[0] == "resources.state"]
        self.assertEqual(resources, ["audio", "combat"])

    async def test_direct_layer_refresh_still_delivers_audio(self):
        consumer = self.consumer(self.player)
        await consumer.room_map_layers({})
        resources = [call.args[1]["module"] for call in consumer.emit.await_args_list
                     if call.args[0] == "resources.state"]
        self.assertEqual(resources, ["audio"])

    async def test_revocation_after_token_delivery_prevents_deferred_audio_and_combat(self):
        consumer = self.consumer(self.player)
        async def emit(kind, _payload):
            if kind == "tokens.state":
                await db(Membership.objects.filter(pk=self.player_membership.pk).delete)()
        consumer.emit.side_effect = emit
        await consumer.room_map_layers({"refresh_audio": False})
        await consumer.room_tokens({})
        self.assertFalse(any(call.args[0] == "resources.state" for call in consumer.emit.await_args_list))
        consumer.close.assert_awaited()
