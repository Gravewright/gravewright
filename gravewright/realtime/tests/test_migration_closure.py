import json
import tempfile
import uuid
from unittest.mock import patch

from channels.db import database_sync_to_async as db
from django.core.files.base import ContentFile
from django.test import TransactionTestCase, override_settings

from gravewright.accounts.services import AuthError
from gravewright.campaigns.models import Membership
from gravewright.chat import services as chat
from gravewright.chat.models import Message
from gravewright.journals import presentations
from gravewright.journals import services as journals
from gravewright.journals.models import Asset, Journal
from gravewright.maps import services as maps
from gravewright.maps.models import Broadcast, Scene, Tile
from gravewright.maps.prefetch import candidates

from . import test_sockets as fixtures


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    ALLOWED_HOSTS=["testserver"],
    GRAVEWRIGHT_HEARTBEAT_SECONDS=0.1,
)
class ClosureTests(TransactionTestCase):
    socket = fixtures.SocketTests.socket
    event = fixtures.SocketTests.event
    finish = fixtures.SocketTests.finish

    def setUp(self):
        fixtures.SocketTests.setUp(self)
        self.scene = Scene.objects.create(
            campaign=self.campaign, name="Public", width=2048, height=2048
        )
        self.private = Scene.objects.create(
            campaign=self.campaign,
            name="Private",
            visibility="gm",
            width=512,
            height=512,
        )
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)

    def command(self, area, action, data, user=None):
        return maps.command(
            self.campaign.pk,
            (user or self.gm).pk,
            "objects",
            {"mapId": str(self.scene.pk), "area": area, "action": action, "data": data},
            uuid.uuid4(),
        )

    def test_whisper_scope_replay_and_history_isolation(self):
        observer = Membership.objects.create(campaign=self.campaign, user=self.outsider)
        gm = Membership.objects.get(campaign=self.campaign, user=self.gm)
        request = str(uuid.uuid4())
        message, _ = chat.say(gm.pk, "/w Player secret", request, str(self.scene.pk))
        self.assertEqual(message["visibility"], "whisper")
        self.assertEqual(message["sceneId"], str(self.scene.pk))
        self.assertEqual(message["blockId"], str(self.scene.block_id))
        self.assertEqual(chat.history(self.campaign.pk, self.outsider.pk), [])
        self.assertEqual(
            chat.history(self.campaign.pk, self.player.pk)[0]["text"], "secret"
        )
        self.assertFalse(chat.say(gm.pk, "/w Player changed", request)[1])
        chat.say(gm.pk, "Hidden room", str(uuid.uuid4()), str(self.private.pk))
        self.assertNotIn(
            "Hidden room", str(chat.history(self.campaign.pk, self.player.pk))
        )
        with self.assertRaises(AuthError):
            chat.say(observer.pk, "Attack", str(uuid.uuid4()), str(self.private.pk))
        with self.assertRaises(AuthError):
            chat.say(gm.pk, "/w Missing text", str(uuid.uuid4()))

    def test_presentations_bind_recipient_expire_and_filter_secrets(self):
        journal = Journal.objects.create(
            campaign=self.campaign,
            creator=self.gm,
            title="Secret book",
            data={
                "sections": [
                    {
                        "id": "public",
                        "title": "Public page",
                        "kind": "text",
                        "audience": "public",
                    },
                    {
                        "id": "gm",
                        "title": "GM secret",
                        "kind": "text",
                        "audience": "gm",
                    },
                ]
            },
        )
        who = journals.member(self.campaign.pk, self.gm.pk)
        event = presentations.present(
            who, {"journal_id": str(journal.pk), "target": str(self.player.pk)}
        )["presentation"]
        token = presentations.ticket(event, self.player.pk)
        _, view = presentations.resolve(token, self.player.pk, self.campaign.pk)
        self.assertFalse(view["can_edit"])
        self.assertNotIn("GM secret", str(view))
        self.assertEqual(
            journals.state(self.campaign.pk, self.player.pk)["journals"], []
        )
        with self.assertRaises(journals.JournalError):
            presentations.resolve(token, self.gm.pk)
        with self.assertRaises(journals.JournalError):
            presentations.resolve(token, self.player.pk, self.other.pk)
        with (
            patch("django.core.signing.time.time", return_value=10**12),
            self.assertRaises(journals.JournalError),
        ):
            presentations.resolve(token, self.player.pk)
        with self.assertRaises(journals.JournalError):
            presentations.present(
                journals.member(self.campaign.pk, self.player.pk),
                {"journal_id": str(journal.pk)},
            )

    def test_drawings_versions_effect_validation_and_authority(self):
        row = {
            "id": str(uuid.uuid4()),
            "kind": "line",
            "audience": "gm",
            "color": "#ffffff",
            "fill": "none",
            "width": 3,
            "opacity": 1,
            "fontSize": 21,
            "text": "",
            "points": [{"x": 1, "y": 2}, {"x": 20, "y": 30}],
        }
        result = self.command(
            "drawings", "replace", {"rows": [row], "expected_version": 0}
        )
        self.assertEqual(result["version"], 1)
        with self.assertRaises(maps.MapError):
            self.command("drawings", "replace", {"rows": [], "expected_version": 0})
        with self.assertRaises(maps.MapError):
            self.command(
                "drawings", "replace", {"rows": [], "expected_version": 1}, self.player
            )
        from gravewright.maps.objects import layer_state

        view = layer_state(
            self.scene, journals.member(self.campaign.pk, self.player.pk)
        )
        self.assertEqual(view["drawings"]["rows"], [])
        emitter = self.command(
            "particles", "create", {"x": 50, "y": 60, "kind": "firefly"}
        )["emitter"]
        self.assertEqual(emitter["kind"], "firefly")
        with self.assertRaises(maps.MapError):
            self.command("particles", "create", {"density": float("nan")})
        self.command(
            "effects",
            "transform",
            {
                "effects": [{"id": emitter["id"], "kind": "particle"}],
                "dx": 10,
                "dy": 5,
                "rotation": 15,
            },
        )
        self.assertEqual(self.scene.elements.get(pk=emitter["id"]).data["x"], 60)
        with self.assertRaises(maps.MapError):
            self.command("shaders", "create", {"source": "x" * 32001})

    def test_prefetch_orders_real_bytes_and_bounds_budget(self):
        Tile.objects.create(
            scene=self.scene, lod=0, x=0, y=0, file="unused", byte_size=1000
        )
        Tile.objects.create(
            scene=self.scene, lod=0, x=1, y=0, file="unused", byte_size=10
        )
        region = {
            "lod": 0,
            "firstColumn": 0,
            "lastColumn": 1,
            "firstRow": 0,
            "lastRow": 0,
        }
        values = candidates(self.scene.pk, region, 0.8, "utility_per_byte")
        self.assertEqual([v["x"] for v in values], [1, 0])
        self.assertGreater(
            values[0]["priority_per_byte"], values[1]["priority_per_byte"]
        )

    async def test_targeted_presentation_and_whisper_delivery(self):
        journal = await db(Journal.objects.create)(
            campaign=self.campaign, creator=self.gm, title="Present me"
        )
        gm, player = self.socket(self.gm), self.socket(self.player)
        try:
            for socket in (gm, player):
                self.assertTrue((await socket.connect())[0])
                await self.event(socket, "table.joined")
            await gm.send_json_to(
                {
                    "type": "journals.command",
                    "payload": {
                        "requestId": str(uuid.uuid4()),
                        "action": "present",
                        "data": {
                            "journal_id": str(journal.pk),
                            "target": str(self.player.pk),
                        },
                    },
                }
            )
            presented = await self.event(player, "handout.presented")
            _, view = await db(presentations.resolve)(
                presented["ticket"], self.player.pk
            )
            self.assertEqual(view["title"], "Present me")
            await gm.send_json_to(
                {
                    "type": "chat.say",
                    "payload": {
                        "requestId": str(uuid.uuid4()),
                        "text": "/w Player socket secret",
                        "mapId": str(self.scene.pk),
                    },
                }
            )
            entry = await self.event(player, "chat.message")
            self.assertEqual(entry["visibility"], "whisper")
            self.assertEqual(entry["text"], "socket secret")
        finally:
            await self.finish()

    def test_presentation_assets_do_not_expose_gm_files(self):
        with (
            tempfile.TemporaryDirectory() as media,
            override_settings(MEDIA_ROOT=media),
        ):
            journal = Journal.objects.create(
                campaign=self.campaign, creator=self.gm, title="Files"
            )
            public = Asset.objects.create(
                journal=journal,
                uploader=self.gm,
                name="public.png",
                content_type="image/png",
                file=ContentFile(b"public", name="public.png"),
            )
            secret = Asset.objects.create(
                journal=journal,
                uploader=self.gm,
                name="secret.png",
                content_type="image/png",
                file=ContentFile(b"secret", name="secret.png"),
            )
            journal.data = {
                "sections": [
                    {
                        "id": "visible",
                        "kind": "image",
                        "audience": "public",
                        "assetId": str(public.pk),
                    },
                    {
                        "id": "hidden",
                        "kind": "image",
                        "audience": "gm",
                        "assetId": str(secret.pk),
                    },
                ]
            }
            journal.save()
            event = presentations.present(
                journals.member(self.campaign.pk, self.gm.pk),
                {"journal_id": str(journal.pk)},
            )["presentation"]
            ticket = presentations.ticket(event, self.player.pk)
            self.client.force_login(self.player)
            prefix = f"/game/handouts/presentation/{ticket}/asset/"
            response = self.client.get(prefix + str(public.pk))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"public")
            response.close()
            self.assertEqual(self.client.get(prefix + str(secret.pk)).status_code, 404)
            self.assertEqual(
                self.client.get(f"/game/journal/asset/{public.pk}").status_code, 404
            )
            with patch("django.core.signing.time.time", return_value=10**12):
                self.assertEqual(
                    self.client.get(prefix + str(public.pk)).status_code, 404
                )

    def test_image_deletion_invalidates_live_scene_and_removes_file(self):
        from gravewright.maps.models import MapAsset, SceneObject, SceneState

        with (
            tempfile.TemporaryDirectory() as media,
            override_settings(MEDIA_ROOT=media),
        ):
            asset = MapAsset.objects.create(
                campaign=self.campaign,
                name="marker",
                width=2,
                height=2,
                file=ContentFile(b"png", name="marker.png"),
            )
            self.command("images", "create", {"asset_id": str(asset.pk)})
            before = SceneState.objects.get(scene=self.scene).version
            storage, name = asset.file.storage, asset.file.name
            self.client.force_login(self.gm)
            response = self.client.post(
                f"/api/containers/{self.campaign.pk}/library/assets/delete",
                json.dumps({"asset_id": str(asset.pk)}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertFalse(
                SceneObject.objects.filter(scene=self.scene, kind="images").exists()
            )
            self.assertGreater(SceneState.objects.get(scene=self.scene).version, before)
            self.assertFalse(storage.exists(name))

    def test_dice_and_table_rolls_remain_in_the_selected_scene(self):
        from gravewright.dice import services as dice

        gm = journals.member(self.campaign.pk, self.gm.pk)
        payload = dice.validate(
            {
                "expression": "1d6",
                "requestId": str(uuid.uuid4()),
                "mapId": str(self.private.pk),
            }
        )
        reservation, _ = dice.claim(gm.pk, payload)
        result = {"value": {"kind": "number", "value": 3}, "rolls": []}
        entry, _ = dice.complete(
            reservation,
            payload,
            result,
            self.sessions[self.gm.pk],
            self.campaign.pk,
            self.gm.pk,
        )
        self.assertEqual(entry["sceneId"], str(self.private.pk))
        self.assertEqual(entry["blockId"], str(self.private.block_id))
        self.assertEqual(chat.history(self.campaign.pk, self.player.pk), [])
        journal = Journal.objects.create(
            campaign=self.campaign,
            creator=self.gm,
            title="Encounter",
            type="roll_table",
            data={
                "entries": [
                    {"id": "one", "name": "Goblin", "result": "Goblin", "weight": 1}
                ]
            },
        )
        event = journals.command(
            self.campaign.pk,
            self.gm.pk,
            "roll",
            {"journal_id": str(journal.pk), "block_id": str(self.private.block_id)},
            str(uuid.uuid4()),
        )
        self.assertEqual(
            Message.objects.get(pk=event["message_id"]).scene_id, self.private.pk
        )
        with self.assertRaises(journals.JournalError):
            journals.command(
                self.campaign.pk,
                self.gm.pk,
                "roll",
                {"journal_id": str(journal.pk), "block_id": "invalid"},
                str(uuid.uuid4()),
            )
