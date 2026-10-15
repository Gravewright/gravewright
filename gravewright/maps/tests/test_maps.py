import tempfile
import uuid
from io import BytesIO
from pathlib import Path

from channels.db import database_sync_to_async as db
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase, override_settings
from PIL import Image

from gravewright.maps import services
from gravewright.maps.models import Folder, Scene, Tile, SceneNavigation
from gravewright.realtime.tests import test_sockets as fixtures


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    GRAVEWRIGHT_HEARTBEAT_SECONDS=0.1,
    GRAVEWRIGHT_PRESENCE_TTL=3,
    ALLOWED_HOSTS=["testserver"],
)
class MapTests(TransactionTestCase):
    socket = fixtures.SocketTests.socket
    event = fixtures.SocketTests.event
    finish = fixtures.SocketTests.finish

    def setUp(self):
        fixtures.SocketTests.setUp(self)
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)

    def command(self, action, data, user=None, rid=None):
        return services.command(
            self.campaign.pk,
            (user or self.gm).pk,
            action,
            data,
            rid or str(uuid.uuid4()),
        )

    def upload(self, activate=True):
        image = BytesIO()
        Image.new("RGB", (1024, 512), "#354b66").save(image, "PNG")
        self.client.force_login(self.gm)
        response = self.client.post(
            f"/api/containers/{self.campaign.pk}/scene-upload",
            {
                "name": "The keep",
                "map": SimpleUploadedFile(
                    "map.png", image.getvalue(), content_type="image/png"
                ),
                "activate": str(activate).lower(),
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_upload_pyramid_and_authorized_tile_delivery(self):
        m = self.upload()
        self.assertEqual(m["maxLod"], 1)
        self.assertEqual(Tile.objects.count(), 3)
        manifest = self.client.get(f"/api/maps/{m['id']}/manifest").json()
        self.assertEqual(manifest["levels"][0]["columns"], 2)
        url = manifest["tileUrlTemplate"].format(lod=0, x=1, y=0)
        self.client.force_login(self.player)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        image = Image.open(BytesIO(b"".join(response.streaming_content)))
        self.assertEqual(image.size, (512, 512))
        image.close()
        response.close()
        self.command(
            "update",
            {
                "mapId": m["id"],
                "version": m["version"],
                "settings": {"visibility": "gm"},
            },
        )
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertIsNone(
            services.state(self.campaign.pk, self.player.pk)["activeMapId"]
        )
        self.client.force_login(self.outsider)
        self.assertEqual(
            self.client.get(f"/api/maps/{m['id']}/manifest").status_code, 404
        )

    def test_scene_settings_and_environment_save_atomically(self):
        from gravewright.maps.models import SceneState

        m = self.upload()
        payload = {
            'mapId': m['id'], 'version': m['version'],
            'settings': {'name': 'Prepared keep'}, 'environmentVersion': 1,
            'lighting': {'mode': 'manual', 'darkness': 0.35, 'lights_out': False},
        }
        with self.assertRaises(services.MapError):
            self.command('update', payload, user=self.player)
        self.command('update', payload)
        scene = Scene.objects.get(pk=m['id'])
        environment = SceneState.objects.get(scene=scene)
        self.assertEqual(scene.name, 'Prepared keep')
        self.assertEqual(environment.lighting['darkness'], 0.35)
        self.assertEqual(environment.version, 2)
        payload['version'] = scene.version
        payload['settings'] = {'name': 'Stale update'}
        with self.assertRaises(services.MapError):
            self.command('update', payload)
        scene.refresh_from_db()
        self.assertEqual(scene.name, 'Prepared keep')
        payload['environmentVersion'] = 2
        payload['settings'] = {'gridSize': -1}
        payload['lighting']['darkness'] = 0.8
        with self.assertRaises(services.MapError):
            self.command('update', payload)
        environment.refresh_from_db()
        self.assertEqual(environment.lighting['darkness'], 0.35)
        self.assertEqual(environment.version, 2)

    def test_image_resize_is_persisted_in_scene_state(self):
        from gravewright.maps.models import MapAsset, SceneObject

        scene = Scene.objects.create(campaign=self.campaign, name='Images', width=1024, height=512)
        asset = MapAsset.objects.create(campaign=self.campaign, name='Image', width=400, height=200,
                                        file='maps/assets/image.png')
        def image_command(action, data):
            return self.command('objects', {'mapId': str(scene.pk), 'area': 'images',
                                            'action': action, 'data': data})
        image_command('create', {'asset_id': str(asset.pk), 'x': 100, 'y': 200, 'scale': 1})
        placement = SceneObject.objects.get(scene=scene, kind='images')
        image_command('update', {'placement_id': str(placement.pk), 'x': 200, 'y': 250,
                                 'scale': 1.5, 'expected_version': placement.version})
        placement.refresh_from_db()
        self.assertEqual(placement.data['scale'], 1.5)
        self.command('navigate', {'mapId': str(scene.pk)})
        navigation = services.state(self.campaign.pk, self.gm.pk)
        state = services.layer_state(self.campaign.pk, self.gm.pk, navigation['navigatingMapId'])
        image = next(row for row in state['images'] if row['id'] == str(placement.pk))
        self.assertEqual((image['x'], image['y'], image['scale']), (200, 250, 1.5))

    def test_gm_image_support_layer_is_private_and_can_return_to_map(self):
        from gravewright.maps.models import MapAsset, SceneObject, Broadcast
        scene = Scene.objects.create(campaign=self.campaign, name='Images', width=1024, height=512)
        Broadcast.objects.update_or_create(campaign=self.campaign, defaults={'scene': scene})
        asset = MapAsset.objects.create(campaign=self.campaign, name='Private image', width=400, height=200,
                                       file='maps/assets/private.png')
        def change(action, data):
            return self.command('objects', {'mapId': str(scene.pk), 'area': 'images', 'action': action, 'data': data})
        change('create', {'asset_id': str(asset.pk), 'layer': 'gm-image-layer'})
        placement = SceneObject.objects.get(scene=scene, kind='images')
        self.assertEqual(placement.data['layer'], 'gm-image-layer')
        self.assertEqual(services.layer_state(self.campaign.pk, self.gm.pk, scene.pk)['images'][0]['layer'], 'gm-image-layer')
        self.assertEqual(services.layer_state(self.campaign.pk, self.player.pk, scene.pk)['images'], [])
        self.client.force_login(self.player)
        self.assertEqual(self.client.get(f'/game/map-assets/{asset.pk}').status_code, 404)
        change('update', {'placement_id': str(placement.pk), 'layer': 'map', 'expected_version': placement.version})
        self.assertEqual(len(services.layer_state(self.campaign.pk, self.player.pk, scene.pk)['images']), 1)
        # Existing hidden placements are projected into the support layer too.
        placement.refresh_from_db();placement.data['layer'] = 'gm';placement.save()
        self.assertEqual(services.layer_state(self.campaign.pk, self.player.pk, scene.pk)['images'], [])
        self.assertEqual(services.layer_state(self.campaign.pk, self.gm.pk, scene.pk)['images'][0]['layer'], 'gm-image-layer')

    def test_upload_limits_reject_before_decode_or_file_publication(self):
        from unittest.mock import patch
        self.client.force_login(self.gm)
        image = BytesIO()
        Image.new('RGB', (1024, 512)).save(image, 'PNG')
        for limits in ({'GRAVEWRIGHT_MAP_MAX_PIXELS': 100}, {'MAP_IMAGE_MAX_WIDTH': 500}, {'MAP_MAX_TILE_COUNT': 1}, {'MAP_UPLOAD_MAX_BYTES': 10}):
            with self.subTest(limits=limits), self.settings(**limits), patch('PIL.PngImagePlugin.PngImageFile.load', side_effect=AssertionError('decoded before limit')):
                response = self.client.post(f'/api/containers/{self.campaign.pk}/scene-upload', {'name': 'Too large', 'map': SimpleUploadedFile('map.png', image.getvalue())})
                self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(Tile.objects.exists())
        self.assertFalse(any(Path(self.media.name).rglob('*.webp')))

    def test_failed_tile_generation_removes_partial_files(self):
        from unittest.mock import patch
        from django.core.files.storage import default_storage
        save = default_storage.save
        for error in (OSError('simulated storage failure'), ValueError('storage rejected file')):
            with self.subTest(error=type(error).__name__):
                calls = 0
                def fail_second(*args, **kwargs):
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        raise error
                    return save(*args, **kwargs)
                with patch.object(default_storage, 'save', side_effect=fail_second), self.assertRaises(type(error)):
                    self.upload()
                self.assertFalse(Tile.objects.exists())
                self.assertFalse(Scene.objects.exists())
                self.assertFalse(any(Path(self.media.name).rglob('*.webp')))

    def test_invalid_json_settings_do_not_publish_a_scene(self):
        self.client.force_login(self.gm)
        response = self.client.post(
            f"/api/containers/{self.campaign.pk}/scene-upload",
            {"name": "Invalid settings", "settings": "{"},
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()["error"], "Invalid scene settings.")
        self.assertFalse(Scene.objects.exists())
        self.assertFalse(Tile.objects.exists())

    def test_configured_pixel_limit_accepts_images_above_original_pillow_guard(self):
        from unittest.mock import patch
        from gravewright.maps import tiling

        image = BytesIO()
        Image.new("RGB", (21, 21), "#354b66").save(image, "PNG")
        self.client.force_login(self.gm)
        with (self.settings(GRAVEWRIGHT_MAP_TILER="pillow", GRAVEWRIGHT_MAP_MAX_PIXELS=500,
                            GRAVEWRIGHT_MAP_PILLOW_MAX_PIXELS=500),
              patch.object(tiling, "_DEFAULT_MAX_IMAGE_PIXELS", 100),
              patch.object(Image, "MAX_IMAGE_PIXELS", 100)):
            tiling.configure_pillow_limit()
            response = self.client.post(
                f"/api/containers/{self.campaign.pk}/scene-upload",
                {"name": "Configured limit", "map": SimpleUploadedFile("map.png", image.getvalue())},
            )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual((response.json()["width"], response.json()["height"]), (21, 21))
        self.assertEqual(Tile.objects.count(), 1)

    def test_pillow_header_and_fallback_limits_have_actionable_errors(self):
        from unittest.mock import patch

        self.client.force_login(self.gm)
        with patch("gravewright.maps.tiling.Image.open", side_effect=Image.DecompressionBombError("too large")):
            response = self.client.post(
                f"/api/containers/{self.campaign.pk}/scene-upload",
                {"name": "Too large", "map": SimpleUploadedFile("map.png", b"image header")},
            )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()["error"], "This map exceeds the server image pixel limit.")
        image = BytesIO()
        Image.new("RGB", (21, 21)).save(image, "PNG")
        with self.settings(GRAVEWRIGHT_MAP_TILER="pillow", GRAVEWRIGHT_MAP_MAX_PIXELS=500,
                           GRAVEWRIGHT_MAP_PILLOW_MAX_PIXELS=440):
            response = self.client.post(
                f"/api/containers/{self.campaign.pk}/scene-upload",
                {"name": "Requires streaming", "map": SimpleUploadedFile("map.png", image.getvalue())},
            )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("vips", response.json()["error"])
        self.assertFalse(Scene.objects.exists())
        self.assertFalse(Tile.objects.exists())
        self.assertFalse(any(Path(self.media.name).rglob("*.webp")))

    def test_corrupt_input_does_not_publish_scene_or_tiles(self):
        self.client.force_login(self.gm)
        response = self.client.post(
            f"/api/containers/{self.campaign.pk}/scene-upload",
            {"name": "Corrupt map", "map": SimpleUploadedFile("map.png", b"not an image")},
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()["error"], "Choose a valid PNG, JPEG, WebP or TIFF image.")
        self.assertFalse(Scene.objects.exists())
        self.assertFalse(Tile.objects.exists())
        self.assertFalse(any(Path(self.media.name).rglob("*.webp")))

    def test_failed_tile_persistence_rolls_back_scene_and_removes_files(self):
        from unittest.mock import patch

        with patch.object(Tile.objects, "bulk_create", side_effect=OSError("simulated database failure")):
            with self.assertRaisesMessage(OSError, "simulated database failure"):
                self.upload()
        self.assertFalse(Scene.objects.exists())
        self.assertFalse(Tile.objects.exists())
        self.assertFalse(any(Path(self.media.name).rglob("*.webp")))

    def test_settings_conflicts_scope_and_folder_cycles(self):
        m = self.upload()
        first = self.command("folder-create", {"label": "First"})["folderId"]
        second = self.command("folder-create", {"label": "Second", "parentId": first})[
            "folderId"
        ]
        with self.assertRaises(services.MapError):
            self.command("folder-update", {"folderId": first, "parentId": second})
        self.command("move", {"mapId": m["id"], "groupId": second})
        with self.assertRaises(services.MapError):
            self.command(
                "update", {"mapId": m["id"], "version": 1, "settings": {"name": "Old"}}
            )
        for field, value in [
            ("gridSize", 0),
            ("gridOpacity", float("nan")),
            ("imageScale", True),
            ("gridOffsetX", "1"),
            ("initialView", {"x": 0, "y": 0, "scale": 0}),
        ]:
            with self.assertRaises(services.MapError):
                services.settings({field: value})
        self.command("folder-delete", {"folderId": second})
        self.assertEqual(str(Scene.objects.get(pk=m["id"]).folder_id), first)
        self.command("folder-delete", {"folderId": first, "recursive": True})
        self.assertFalse(Scene.objects.exists())
        self.assertFalse(Tile.objects.exists())
        self.assertEqual(list(Path(self.media.name).rglob("*.webp")), [])

    def test_player_cannot_upload_manage_or_read_unpublished_maps(self):
        m = self.upload(False)
        self.assertEqual(services.state(self.campaign.pk, self.player.pk)["maps"], [])
        with self.assertRaises(services.MapError):
            self.command("activate", {"mapId": m["id"]}, self.player)
        self.client.force_login(self.player)
        self.assertEqual(
            self.client.post(
                f"/api/containers/{self.campaign.pk}/scene-upload", {"name": "bad"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.get(f"/api/maps/{m['id']}/tiles/0/0/0").status_code, 404
        )
        rid = str(uuid.uuid4())
        first = self.command("folder-create", {"label": "Only once"}, rid=rid)
        self.assertEqual(
            first, self.command("folder-create", {"label": "Only once"}, rid=rid)
        )
        self.assertEqual(Folder.objects.count(), 1)

    async def test_websocket_publication_and_private_switch(self):
        m = await db(self.upload)(False)
        gm, player = self.socket(self.gm), self.socket(self.player)
        try:
            for socket in (gm, player):
                self.assertTrue((await socket.connect())[0])
                await self.event(socket, "chat.history")
                await socket.send_json_to({"type": "maps.sync"})
                await self.event(socket, "maps.state")
            await gm.send_json_to(
                {
                    "type": "maps.command",
                    "payload": {
                        "action": "activate",
                        "data": {"mapId": m["id"]},
                        "requestId": str(uuid.uuid4()),
                    },
                }
            )
            await self.event(gm, "maps.ack")
            self.assertEqual(
                (await self.event(player, "maps.state"))["activeMapId"], m["id"]
            )
            await gm.send_json_to(
                {
                    "type": "maps.command",
                    "payload": {
                        "action": "update",
                        "data": {
                            "mapId": m["id"],
                            "version": m["version"],
                            "settings": {"visibility": "gm"},
                        },
                        "requestId": str(uuid.uuid4()),
                    },
                }
            )
            await self.event(gm, "maps.ack")
            self.assertEqual((await self.event(player, "maps.state"))["maps"], [])
        finally:
            await self.finish()

    async def test_activation_and_uploaded_broadcast_survive_leaving_table(self):
        uploaded = await db(self.upload)()
        unpublished = await db(self.upload)(False)
        try:
            for expected, activate in ((uploaded, unpublished), (unpublished, None)):
                gm = self.socket(self.gm)
                self.assertTrue((await gm.connect())[0])
                await self.event(gm, "chat.history")
                await gm.send_json_to({"type": "maps.sync"})
                state = await self.event(gm, "maps.state")
                self.assertEqual(state["activeMapId"], expected["id"])
                self.assertEqual(state["navigatingMapId"], unpublished["id"])
                self.assertEqual(state["followingActiveMap"], activate is None)
                self.assertEqual(
                    {row["id"] for row in state["maps"]},
                    {uploaded["id"], unpublished["id"]},
                )
                if activate:
                    await gm.send_json_to({
                        "type": "maps.command",
                        "payload": {
                            "action": "activate",
                            "data": {"mapId": activate["id"]},
                            "requestId": str(uuid.uuid4()),
                        },
                    })
                    await self.event(gm, "maps.ack")
                    self.assertEqual(
                        (await self.event(gm, "maps.state"))["activeMapId"],
                        activate["id"],
                    )
                await gm.disconnect()
                self.sockets.remove(gm)
        finally:
            await self.finish()

    def test_private_navigation_is_scoped_and_deletion_resumes_broadcast(self):
        from gravewright.campaigns.models import Membership

        active = self.upload()
        private = self.upload(False)
        Membership.objects.create(campaign=self.campaign, user=self.outsider, role="gm")
        self.command("navigate", {"mapId": private["id"]})
        state = services.state(self.campaign.pk, self.gm.pk)
        self.assertEqual(state["activeMapId"], active["id"])
        self.assertEqual(state["navigatingMapId"], private["id"])
        self.assertFalse(state["followingActiveMap"])
        for user in (self.player, self.outsider):
            state = services.state(self.campaign.pk, user.pk)
            self.assertEqual(state["navigatingMapId"], active["id"])
            self.assertTrue(state["followingActiveMap"])
        with self.assertRaises(services.MapError):
            self.command("navigate", {"mapId": private["id"]}, self.player)
        foreign = Scene.objects.create(
            campaign=self.other, name="Other table", width=10, height=10,
        )
        with self.assertRaises(services.MapError):
            self.command("navigate", {"mapId": str(foreign.pk)})
        self.command("navigate", {"mapId": None})
        self.assertTrue(services.state(self.campaign.pk, self.gm.pk)["followingActiveMap"])
        self.command("navigate", {"mapId": private["id"]})
        self.command("delete", {"mapId": private["id"]})
        state = services.state(self.campaign.pk, self.gm.pk)
        self.assertEqual(state["navigatingMapId"], active["id"])
        self.assertTrue(state["followingActiveMap"])
        self.assertIsNone(SceneNavigation.objects.get(membership__user=self.gm).scene_id)

    def object_command(self, map_id, area, action, data, user=None, rid=None):
        if area == "fog" and "expected_version" not in data:
            from gravewright.maps.models import SceneState
            state = SceneState.objects.filter(scene_id=map_id).first()
            data = {**data, "expected_version": (state.fog or {}).get("version", 1) if state else 1}
        return self.command(
            "objects",
            {"mapId": map_id, "area": area, "action": action, "data": data},
            user,
            rid,
        )

    def test_effects_source_limits_permissions_and_atomic_mixed_selection(self):
        from gravewright.maps.models import SceneObject

        m = self.upload()
        shader = self.object_command(
            m["id"],
            "shaders",
            "create",
            {"source": "void main() { finalColor=vec4(1.); }\n/*" + "x" * 17000 + "*/"},
        )["shader"]
        with self.assertRaises(services.MapError):
            self.object_command(m["id"], "shaders", "create", {"source": "x" * 32001})
        particle = self.object_command(
            m["id"],
            "particles",
            "create",
            {"kind": "rain", "x": 30, "y": 40},
        )["emitter"]
        refs = [
            {"kind": "shader", "id": shader["id"]},
            {"kind": "particle", "id": particle["id"]},
        ]
        with self.assertRaises(services.MapError):
            self.object_command(
                m["id"], "effects", "delete", {"effects": refs}, self.player
            )
        with self.assertRaises(services.MapError):
            self.object_command(
                m["id"],
                "effects",
                "transform",
                {
                    "effects": refs + [{"kind": "shader", "id": str(uuid.uuid4())}],
                    "dx": 20,
                },
            )
        self.assertEqual(SceneObject.objects.get(pk=particle["id"]).data["x"], 30)
        self.object_command(
            m["id"],
            "effects",
            "transform",
            {
                "effects": refs,
                "dx": 20,
                "dy": 10,
                "rotation": -15,
            },
        )
        row = SceneObject.objects.get(pk=particle["id"])
        self.assertEqual(
            (row.data["x"], row.data["y"], row.data["rotation"]), (50, 50, 345)
        )
        self.object_command(m["id"], "effects", "delete", {"effects": refs})
        self.assertFalse(SceneObject.objects.filter(scene_id=m["id"]).exists())

    def test_effect_boundaries_conflicts_and_clear_preserves_lights(self):
        from gravewright.maps.extra_objects import PARTICLES
        from gravewright.maps.models import SceneObject

        m = self.upload()
        light = self.object_command(m["id"], "lights", "create", {"x": 20, "y": 30})["light"]
        for kind in PARTICLES:
            self.object_command(m["id"], "particles", "create", {"kind": kind})
        shader = self.object_command(
            m["id"],
            "shaders",
            "create",
            {"source": "void main(){finalColor=vec4(1.);}"},
        )["shader"]
        for area, patch in [
            ("particles", {"kind": "unknown"}),
            ("particles", {"density": -0.1}),
            ("particles", {"density": 1.1}),
            ("shaders", {"opacity": 1.1}),
            ("shaders", {"intensity": -0.1}),
            ("shaders", {"speed": 8.1}),
            ("shaders", {"radius": -1}),
            ("shaders", {"blend_mode": "unknown"}),
            ("shaders", {"source": ""}),
            ("shaders", {"source": "void main(){}\x00"}),
            ("shaders", {"light_response": 1.1}),
            ("shaders", {"light_emission": 2.1}),
            ("shaders", {"x": float("inf")}),
        ]:
            with (
                self.subTest(area=area, patch=patch),
                self.assertRaises(services.MapError),
            ):
                self.object_command(m["id"], area, "create", {**shader, **patch})
        with self.assertRaises(services.MapError):
            self.object_command(
                m["id"],
                "shaders",
                "update",
                {
                    "shader_id": shader["id"],
                    "expected_version": shader["version"] + 1,
                    "opacity": 0.5,
                },
            )
        for action, data in [
            ("create", shader),
            ("update", {"shader_id": shader["id"]}),
            ("delete", {"shader_id": shader["id"]}),
            ("clear", {}),
        ]:
            with self.subTest(action=action), self.assertRaises(services.MapError):
                self.object_command(m["id"], "shaders", action, data, self.player)
        self.object_command(m["id"], "effects", "clear", {})
        self.assertFalse(
            SceneObject.objects.filter(
                scene_id=m["id"], kind__in=("shaders", "particles")
            ).exists()
        )
        self.assertTrue(SceneObject.objects.filter(pk=light["id"]).exists())

    def test_wall_transactions_door_permissions_and_scene_state(self):
        m = self.upload()
        door = self.object_command(
            m["id"],
            "walls",
            "create",
            {"kind": "door", "x1": 10, "y1": 10, "x2": 100, "y2": 10},
        )["wall"]
        self.object_command(
            m["id"],
            "walls",
            "door",
            {"wall_id": door["id"], "door_state": "open"},
            self.player,
        )
        self.object_command(
            m["id"], "walls", "door", {"wall_id": door["id"], "door_state": "locked"}
        )
        with self.assertRaises(services.MapError):
            self.object_command(
                m["id"],
                "walls",
                "door",
                {"wall_id": door["id"], "door_state": "open"},
                self.player,
            )
        with self.assertRaises(services.MapError):
            self.object_command(
                m["id"],
                "walls",
                "create",
                {"x1": 0, "y1": 0, "x2": 1, "y2": 1},
                self.player,
            )
        w = self.object_command(
            m["id"], "walls", "create", {"x1": 0, "y1": 0, "x2": 100, "y2": 0}
        )["wall"]
        self.object_command(
            m["id"], "walls", "split", {"wall_id": w["id"], "x": 50, "y": 0}
        )
        self.object_command(
            m["id"],
            "walls",
            "move-node",
            {"from_x": 50, "from_y": 0, "to_x": 50, "to_y": 20},
        )
        self.client.force_login(self.player)
        state = self.client.get(f"/api/maps/{m['id']}/state").json()
        self.assertEqual(len(state["walls"]), 3)
        self.assertEqual(sum(20 in (row["y1"], row["y2"]) for row in state["walls"]), 2)
        self.object_command(
            m["id"],
            "walls",
            "update",
            {"wall_id": door["id"], "presentation": "secret"},
        )
        state = self.client.get(f"/api/maps/{m['id']}/state").json()
        self.assertEqual(
            next(w for w in state["walls"] if w["id"] == door["id"])["kind"], "wall"
        )
        rid = str(uuid.uuid4())
        data = {"x1": 300, "y1": 0, "x2": 400, "y2": 0}
        a = self.object_command(m["id"], "walls", "create", data, rid=rid)
        self.assertEqual(
            a, self.object_command(m["id"], "walls", "create", data, rid=rid)
        )
        self.object_command(m["id"], "wall-selection", "clear", {})
        self.assertEqual(
            self.client.get(f"/api/maps/{m['id']}/state").json()["walls"], []
        )

    def test_lighting_fog_validation_and_private_layers(self):
        m = self.upload()
        light = self.object_command(m["id"], "lights", "create", {"x": 20, "y": 30})[
            "light"
        ]
        self.object_command(
            m["id"],
            "light-selection",
            "transform",
            {
                "effects": [{"kind": "light", "id": light["id"]}],
                "dx": 10,
                "rotation": 15,
            },
        )
        self.object_command(
            m["id"],
            "lighting",
            "update",
            {"mode": "manual", "darkness": 0.75, "lights_out": False},
        )
        stroke = {
            "ops": [
                {
                    "mode": "reveal",
                    "shape": "circle",
                    "geom": {
                        "center_x_cells": 2,
                        "center_y_cells": 3,
                        "radius_cells": 1,
                    },
                }
            ]
        }
        with self.assertRaises(services.MapError):
            self.object_command(m["id"], "fog", "paint", stroke)
        self.object_command(m["id"], "fog", "enable", {"initial": "hide_all"})
        self.object_command(m["id"], "fog", "paint", stroke)
        self.client.force_login(self.player)
        state = self.client.get(f"/api/maps/{m['id']}/state").json()
        self.assertEqual(state["lights"][0]["x"], 30)
        self.assertEqual(state["lighting"]["effective_darkness"], 0)
        self.assertEqual(len(state["fog"]["ops"]), 1)
        with self.assertRaises(services.MapError):
            self.object_command(
                m["id"], "fog", "reset", {"to": "reveal_all"}, self.player
            )
        with self.assertRaises(services.MapError):
            self.object_command(
                m["id"],
                "lights",
                "update",
                {"light_id": light["id"], "x": float("nan")},
            )
        self.command(
            "update", {"mapId": m["id"], "version": 1, "settings": {"visibility": "gm"}}
        )
        self.assertEqual(self.client.get(f"/api/maps/{m['id']}/state").status_code, 404)

    async def test_websocket_wall_delivery_to_player(self):
        m = await db(self.upload)()
        gm, player = self.socket(self.gm), self.socket(self.player)
        try:
            for socket in (gm, player):
                self.assertTrue((await socket.connect())[0])
                await self.event(socket, "chat.history")
                await socket.send_json_to(
                    {"type": "maps.layers", "payload": {"mapId": m["id"]}}
                )
                self.assertEqual((await self.event(socket, "maps.layers"))["walls"], [])
            await gm.send_json_to(
                {
                    "type": "maps.command",
                    "payload": {
                        "action": "objects",
                        "data": {
                            "mapId": m["id"],
                            "area": "walls",
                            "action": "create",
                            "data": {
                                "x1": 0,
                                "y1": 0,
                                "x2": 50,
                                "y2": 0,
                                "kind": "door",
                            },
                        },
                        "requestId": str(uuid.uuid4()),
                    },
                }
            )
            await self.event(gm, "maps.ack")
            state = await self.event(player, "maps.layers")
            self.assertEqual(len(state["walls"]), 1)
            await player.send_json_to(
                {
                    "type": "maps.command",
                    "payload": {
                        "action": "objects",
                        "data": {
                            "mapId": m["id"],
                            "area": "walls",
                            "action": "door",
                            "data": {
                                "wall_id": state["walls"][0]["id"],
                                "door_state": "open",
                            },
                        },
                        "requestId": str(uuid.uuid4()),
                    },
                }
            )
            await self.event(player, "maps.ack")
            self.assertEqual(
                (await self.event(player, "maps.layers"))["walls"][0]["door_state"],
                "open",
            )
        finally:
            await self.finish()
