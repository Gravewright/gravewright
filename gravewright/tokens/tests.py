import uuid
from copy import deepcopy

from channels.db import database_sync_to_async as db
from django.test import TransactionTestCase, override_settings

from gravewright.actors import services as actors
from gravewright.actors.models import Actor
from gravewright.journals.services import JournalError
from gravewright.maps.models import Broadcast, Scene, SceneObject
from gravewright.maps.services import DEFAULTS, MapError
from gravewright.pdf_system.schema import normalize
from gravewright.realtime.tests import test_sockets as fixtures

from . import services
from .models import Token


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    ALLOWED_HOSTS=["testserver"],
    GRAVEWRIGHT_HEARTBEAT_SECONDS=0.1,
)
class TokenTests(TransactionTestCase):
    socket = fixtures.SocketTests.socket
    event = fixtures.SocketTests.event
    finish = fixtures.SocketTests.finish

    def setUp(self):
        fixtures.SocketTests.setUp(self)
        self.map = Scene.objects.create(
            campaign=self.campaign,
            name="Map",
            width=1400,
            height=1000,
            settings=DEFAULTS,
        )
        Broadcast.objects.create(campaign=self.campaign, scene=self.map)
        self.actor = Actor.objects.create(
            campaign=self.campaign,
            name="Hero",
            data=normalize({}),
            permissions={str(self.player.pk): "owner"},
        )

    def cmd(self, action, data, user=None, rid=None):
        return services.command(
            self.campaign.pk,
            (user or self.gm).pk,
            action,
            {"mapId": str(self.map.pk), **data},
            rid or uuid.uuid4(),
        )

    def place(self):
        self.cmd("place", {"actorId": str(self.actor.pk), "gridX": 1, "gridY": 1})
        return Token.objects.latest("created_at")

    def test_link_promotion_snapshot_and_sheet_revisions(self):
        one = self.place()
        self.assertTrue(one.linked)
        two = self.place()
        one.refresh_from_db()
        self.assertFalse(one.linked)
        self.assertFalse(two.linked)
        view = actors.sheet(self.campaign.pk, self.player.pk, self.actor.pk, two.pk)
        data = deepcopy(view["data"])
        data["bars"]["bar_1"] = {"value": 7, "max": 10}
        actors.command(
            self.campaign.pk,
            self.player.pk,
            "sheet.save",
            {
                "actorId": str(self.actor.pk),
                "tokenId": str(two.pk),
                "data": data,
                "name": "Hero",
                "version": view["version"],
                "sheetVersion": view["sheetVersion"],
            },
            uuid.uuid4(),
        )
        two.refresh_from_db()
        one.refresh_from_db()
        self.actor.refresh_from_db()
        self.assertEqual(two.snapshot["bars"]["bar_1"]["value"], 7)
        self.assertEqual(one.snapshot["bars"]["bar_1"]["value"], 0)
        self.assertEqual(self.actor.data["bars"]["bar_1"]["value"], 0)
        with self.assertRaises(MapError):
            actors.command(
                self.campaign.pk,
                self.player.pk,
                "sheet.save",
                {"tokenId": str(two.pk), "data": data, "sheetVersion": 1},
                uuid.uuid4(),
            )
        data["token"]["size"] = 3
        with self.assertRaises(MapError):
            actors.command(
                self.campaign.pk,
                self.player.pk,
                "sheet.save",
                {"tokenId": str(two.pk), "data": data, "sheetVersion": 2},
                uuid.uuid4(),
            )

    def test_control_collision_path_elevation_and_scope(self):
        t = self.place()
        SceneObject.objects.create(
            scene=self.map,
            kind="walls",
            data={
                "x1": 210,
                "y1": 0,
                "x2": 210,
                "y2": 500,
                "kind": "wall",
                "door_state": "closed",
                "movement_behavior": "block",
            },
        )
        value = {"id": str(t.pk), "gridX": 5, "gridY": 1, "expectedVersion": t.version}
        with self.assertRaises(MapError):
            self.cmd("move", value, self.player)
        self.cmd(
            "move",
            {**value, "path": [{"gridX": 1, "gridY": 8}, {"gridX": 5, "gridY": 8}]},
            self.player,
        )
        t.refresh_from_db()
        self.assertEqual(t.grid_x, 5)
        with self.assertRaises(MapError):
            self.cmd("move", value, self.player)
        value.update(expectedVersion=t.version, gridX=1)
        self.cmd("move", value)  # GM crosses walls.
        t.refresh_from_db()
        self.cmd(
            "configure",
            {
                "tokenIds": [str(t.pk)],
                "expectedVersion": t.version,
                "values": {"locked": True},
            },
        )
        t.refresh_from_db()
        with self.assertRaises(MapError):
            self.cmd("move", {**value, "expectedVersion": t.version})
        with self.assertRaises(JournalError):
            services.state(self.campaign.pk, self.outsider.pk, self.map.pk)
        with self.assertRaises(MapError):
            self.cmd(
                "place",
                {"actorId": str(self.actor.pk), "gridX": float("nan"), "gridY": 0},
            )

    def test_hidden_conditions_bars_and_vision_are_recipient_specific(self):
        t = self.place()
        self.cmd(
            "condition-add",
            {
                "tokenIds": [str(t.pk)],
                "label": "Secret",
                "kind": "negative",
                "visibility": "gm",
            },
        )
        t.refresh_from_db()
        who = services.member(self.campaign.pk, self.player.pk)
        self.assertEqual(services.project(t, who)["conditions"], [])
        self.assertEqual(len(services.vision(self.map, who)), 1)
        self.cmd("hidden", {"tokenIds": [str(t.pk)], "hidden": True})
        self.assertEqual(
            services.state(self.campaign.pk, self.player.pk, self.map.pk)["tokens"], []
        )
        self.assertEqual(services.vision(self.map, who), [])
        with self.assertRaises(MapError):
            actors.sheet(self.campaign.pk, self.player.pk, self.actor.pk, t.pk)
        self.map.visibility = "gm"
        self.map.save()
        with self.assertRaises(MapError):
            services.state(self.campaign.pk, self.player.pk, self.map.pk)

    def test_idempotent_move_duplicate_and_remove_preserve_actor(self):
        t = self.place()
        rid = uuid.uuid4()
        p = {"id": str(t.pk), "gridX": 2, "gridY": 2, "expectedVersion": 1}
        first = self.cmd("move", p, rid=rid)
        second = self.cmd("move", p, rid=rid)
        self.assertEqual(first, second)
        t.refresh_from_db()
        self.assertEqual(t.version, 2)
        copied = self.cmd("duplicate", {"tokenIds": [str(t.pk)]})["createdIds"]
        self.assertEqual(len(copied), 1)
        copy = Token.objects.get(pk=copied[0])
        self.assertFalse(copy.linked)
        self.cmd("remove", {"tokenIds": [str(t.pk), str(copy.pk)]})
        self.assertEqual(Token.objects.count(), 0)
        self.assertTrue(Actor.objects.filter(pk=self.actor.pk).exists())

    async def test_socket_motion_authorization_and_non_persistence(self):
        t = await db(self.place)()
        gm, player = self.socket(self.gm), self.socket(self.player)
        try:
            for s in (gm, player):
                self.assertTrue((await s.connect())[0])
                await self.event(s, "table.joined")
                await s.send_json_to(
                    {"type": "tokens.sync", "payload": {"mapId": str(self.map.pk)}}
                )
                await self.event(s, "tokens.state")
            packet = {
                "mapId": str(self.map.pk),
                "stream": str(uuid.uuid4()),
                "phase": "update",
                "positions": [
                    {
                        "id": str(t.pk),
                        "version": 1,
                        "gridX": 2,
                        "gridY": 2,
                        "path": [[1, 1], [2, 2]],
                    }
                ],
            }
            await player.send_json_to({"type": "token.drag", "payload": packet})
            received = await self.event(gm, "token.drag")
            self.assertEqual(received["positions"][0]["gridX"], 2)
            await db(t.refresh_from_db)()
            self.assertEqual(t.grid_x, 1)
            self.assertEqual(t.version, 1)
            await player.send_json_to(
                {"type": "token.drag", "payload": {**packet, "phase": "cancel"}}
            )
            self.assertEqual((await self.event(gm, "token.drag"))["phase"], "cancel")
            await player.send_json_to(
                {
                    "type": "tokens.command",
                    "payload": {
                        "requestId": str(uuid.uuid4()),
                        "action": "hidden",
                        "data": {
                            "mapId": str(self.map.pk),
                            "tokenIds": [str(t.pk)],
                            "hidden": True,
                        },
                    },
                }
            )
            self.assertEqual(
                (await self.event(player, "tokens.error"))["code"], "forbidden"
            )
        finally:
            await self.finish()
