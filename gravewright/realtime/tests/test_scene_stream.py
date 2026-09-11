import asyncio
from unittest.mock import patch

from channels.db import database_sync_to_async as db
from django.test import TransactionTestCase, override_settings

from gravewright.maps.models import Broadcast, Scene
from gravewright.maps.services import DEFAULTS
from gravewright.realtime.gm_guided_prefetch import GmGuidedPrefetchBroker

from . import test_sockets as fixtures


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    ALLOWED_HOSTS=["testserver"],
    GRAVEWRIGHT_HEARTBEAT_SECONDS=0.1,
)
class StreamTests(TransactionTestCase):
    socket = fixtures.SocketTests.socket
    event = fixtures.SocketTests.event
    finish = fixtures.SocketTests.finish

    def setUp(self):
        fixtures.SocketTests.setUp(self)
        self.scene = Scene.objects.create(
            campaign=self.campaign,
            name="Map",
            width=8192,
            height=8192,
            max_lod=4,
            settings=DEFAULTS,
        )
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        self.region = dict(
            mapId=str(self.scene.pk),
            lod=0,
            firstColumn=2,
            firstRow=2,
            lastColumn=3,
            lastRow=3,
            generation=1,
        )

    async def viewport(self, socket, **changes):
        await socket.send_json_to(
            {"type": "scene.viewport", "payload": self.region | changes}
        )

    async def test_priority_batches_bounds_and_stale_generation(self):
        socket = self.socket(self.player)
        try:
            self.assertTrue((await socket.connect())[0])
            await self.event(socket, "table.joined")
            await self.viewport(socket)
            ready = await self.event(socket, "scene.viewport.ready")
            self.assertEqual(len(ready["tiles"]), 16)
            self.assertEqual([v["priority"] for v in ready["tiles"][:4]], [1] * 4)
            self.assertEqual(ready["tiles"][-1]["priority"], 3)
            self.assertNotIn("url", str(ready))
            await self.viewport(socket, firstColumn=True)
            self.assertEqual(
                (await self.event(socket, "scene.viewport.error"))["code"],
                "invalid_input",
            )
            await self.viewport(socket, lastColumn=10000)
            await self.event(socket, "scene.viewport.error")
            await self.viewport(socket, firstColumn=4, lastColumn=5)
            await self.event(socket, "scene.viewport.error")
            await asyncio.sleep(0.21)
            await self.viewport(socket, generation=2, firstColumn=4, lastColumn=5)
            self.assertEqual(
                (await self.event(socket, "scene.viewport.ready"))["region"][
                    "generation"
                ],
                2,
            )
            await socket.send_json_to({"type": "scene.viewport.stop"})
        finally:
            await self.finish()

    async def test_gm_hint_uses_recipient_lod_and_cannot_reveal_private_scene(self):
        now = [1000]
        observations = asyncio.Queue()

        def broker(**kwargs):
            result = GmGuidedPrefetchBroker(**kwargs, clock_ms=lambda: now[0])
            observe = result.observe_gm_viewport

            def sample(**values):
                hints = observe(**values)
                observations.put_nowait(now[0])
                return hints

            result.observe_gm_viewport = sample
            return result

        with (
            patch(
                "gravewright.realtime.scene_stream.GmGuidedPrefetchBroker",
                side_effect=broker,
            ),
            patch(
                "gravewright.realtime.scene_stream.time",
                side_effect=lambda: now[0] / 1000,
            ),
        ):
            gm, player = self.socket(self.gm), self.socket(self.player)
            try:
                for socket in (gm, player):
                    self.assertTrue((await socket.connect())[0])
                    await self.event(socket, "table.joined")
                # Player sees base chunks 2..3; GM is adjacent at base chunk 4.
                await self.viewport(
                    player, lod=1, firstColumn=1, firstRow=1, lastColumn=1, lastRow=1
                )
                await self.event(player, "scene.viewport.ready")
                await self.viewport(
                    gm, firstColumn=4, firstRow=2, lastColumn=4, lastRow=3
                )
                await self.event(gm, "scene.viewport.ready")
                await asyncio.wait_for(observations.get(), timeout=3)
                # Automatic admission requires sustained evidence, not a toggle.
                for _ in range(6):
                    await asyncio.sleep(0.21)
                    now[0] += 2000
                    await self.viewport(
                        gm, firstColumn=4, firstRow=2, lastColumn=4, lastRow=3
                    )
                    # Do not advance the fake clock while a sample is in flight.
                    await asyncio.wait_for(observations.get(), timeout=3)
                hint = await self.event(player, "scene.gm_prefetch.hint")
                self.assertEqual(hint["region"]["lod"], 1)
                self.assertEqual(hint["region"]["firstColumn"], 2)
                self.assertEqual(hint["materialization"], "blob_only")
                self.assertEqual(hint["policy"], "utility_per_byte")
                self.assertNotIn("user_id", hint)
                # Revoke map access; both direct viewports and queued GM samples are filtered.
                await db(Scene.objects.filter(pk=self.scene.pk).update)(visibility="gm")
                await self.viewport(player)
                await self.event(player, "scene.viewport.error")
                await asyncio.sleep(0.25)
                now[0] += 16000
                await self.viewport(
                    gm, firstColumn=4, firstRow=2, lastColumn=4, lastRow=3
                )
                await player.send_json_to({"type": "chat.sync"})
                while True:
                    message = await player.receive_json_from(timeout=2)
                    self.assertNotEqual(message["type"], "scene.gm_prefetch.hint")
                    if message["type"] == "chat.history":
                        break
                    if message["type"] == "session.ping":
                        await player.send_json_to({"type": "session.pong"})
                # A barrier drains pending channel messages; any hint is a failure.
                for _ in range(4):
                    msg = await player.receive_json_from(timeout=2)
                    self.assertNotEqual(msg["type"], "scene.gm_prefetch.hint")
                    if msg["type"] == "session.ping":
                        await player.send_json_to({"type": "session.pong"})
            finally:
                await self.finish()

    @override_settings(
        GRAVEWRIGHT_GM_PREFETCH_ENABLED=False,
        GRAVEWRIGHT_GM_HINT_POLICY="invalid-old-setting",
        GRAVEWRIGHT_GM_HINT_MAX_DISTANCE_CHUNKS=0,
    )
    def test_automatic_prefetch_ignores_obsolete_deployment_settings(self):
        from gravewright.realtime.scene_stream import SceneStreamMixin

        stream = SceneStreamMixin()
        stream.init_stream()
        self.assertEqual(stream.prefetch_broker.policy, "utility_per_byte")
        self.assertEqual(stream.prefetch_broker.max_distance_chunks, 1)
