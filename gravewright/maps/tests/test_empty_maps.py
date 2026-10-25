import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings
from PIL import Image

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps import empty_maps, services, tiling
from gravewright.maps.models import Broadcast, Folder, Receipt, Scene, SceneNavigation, Tile


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class EmptyMapTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        override = override_settings(MEDIA_ROOT=self.temp.name)
        override.enable()
        self.addCleanup(override.disable)
        self.gm = User.objects.create_user('empty-gm@example.test', 'password-123')
        self.player = User.objects.create_user('empty-player@example.test', 'password-123')
        self.campaign = Campaign.objects.create(owner=self.gm, name='Empty maps')
        self.member = Membership.objects.create(campaign=self.campaign, user=self.gm, role='gm')
        Membership.objects.create(campaign=self.campaign, user=self.player)
        self.payload = {'requestId': str(uuid.uuid4()), 'width': 513, 'height': 257,
                        'color': '#123456', 'gridVisible': False}

    def create(self, **changes):
        return empty_maps.create(self.campaign.pk, self.gm.pk, {**self.payload, **changes})

    def test_create_exact_color_dimensions_grid_folder_and_publication(self):
        folder = Folder.objects.create(campaign=self.campaign, label='Battles')
        with patch('gravewright.realtime.dispatch.send') as notify:
            with self.captureOnCommitCallbacks(execute=True):
                result = self.create(groupId=str(folder.pk), name='Dangerous crossing', activate=True)
                self.assertFalse(notify.called)
            self.assertTrue(notify.called)
        row = Scene.objects.get(pk=result['id'])
        self.assertEqual((row.width, row.height, row.folder_id), (513, 257, folder.pk))
        self.assertFalse(row.settings['gridVisible'])
        self.assertEqual(row.name, 'Dangerous crossing')
        self.assertEqual(Broadcast.objects.get(campaign=self.campaign).scene_id, row.pk)
        self.assertIsNone(SceneNavigation.objects.get(membership=self.member).scene_id)
        self.assertEqual(Tile.objects.filter(scene=row).count(), tiling.tile_count(513, 257))
        for tile in Tile.objects.filter(scene=row):
            with tile.file.open('rb') as stream, Image.open(stream) as image:
                self.assertEqual(image.convert('RGB').getextrema(), ((18, 18), (52, 52), (86, 86)))
                w, h = tiling.level_size(513, 257, tile.lod)
                self.assertEqual(image.size, (min(512, w - 512 * tile.x), min(512, h - 512 * tile.y)))
        self.assertEqual(services.manifest(row)['maxLod'], row.max_lod)

    def test_retry_returns_one_scene_without_creating_more_files(self):
        result = self.create(gridVisible=True)
        files = sorted(Path(self.temp.name).rglob('*.webp'))
        self.assertEqual(self.create(gridVisible=True), result)
        self.assertEqual(Scene.objects.count(), 1)
        self.assertEqual(Receipt.objects.count(), 1)
        self.assertEqual(sorted(Path(self.temp.name).rglob('*.webp')), files)
        self.assertTrue(Scene.objects.get().settings['gridVisible'])

    def test_unactivated_map_preserves_broadcast_and_opens_only_for_creator(self):
        active = self.create(name='Active scene')
        prepared = self.create(requestId=str(uuid.uuid4()), name='Prepared scene', activate=False, gridVisible=True)
        self.assertEqual(str(Broadcast.objects.get(campaign=self.campaign).scene_id), active['id'])
        self.assertEqual(str(SceneNavigation.objects.get(membership=self.member).scene_id), prepared['id'])
        player_state = services.state(self.campaign.pk, self.player.pk)
        self.assertEqual(player_state['activeMapId'], active['id'])
        self.assertEqual(services.state(self.campaign.pk, self.gm.pk)['navigatingMapId'], prepared['id'])

    def test_unactivated_first_map_does_not_create_a_broadcast(self):
        prepared = self.create(activate=False)
        self.assertFalse(Broadcast.objects.filter(campaign=self.campaign).exists())
        self.assertEqual(str(SceneNavigation.objects.get(membership=self.member).scene_id), prepared['id'])

    def test_rejects_invalid_values_and_configured_limits_without_files(self):
        for patch_data in ({'width': True}, {'width': 1.5}, {'height': 0}, {'width': -1},
                           {'height': '100'}, {'color': 'red'}, {'gridVisible': 'false'},
                           {'activate': 'false'}, {'activate': 1}, {'name': ''}, {'name': 'x' * 121}):
            with self.subTest(patch_data=patch_data), self.assertRaises(services.MapError):
                self.create(**patch_data)
        for setting in ({'GRAVEWRIGHT_MAP_MAX_PIXELS': 100}, {'MAP_MAX_TILE_COUNT': 1},
                        {'MAP_IMAGE_MAX_WIDTH': 100}, {'MAP_IMAGE_MAX_HEIGHT': 100}):
            with self.subTest(setting=setting), override_settings(**setting), self.assertRaises(services.MapError):
                self.create()
        self.assertFalse(Scene.objects.exists())
        self.assertFalse(Receipt.objects.exists())
        self.assertFalse(list(Path(self.temp.name).rglob('*.webp')))

    def test_http_authentication_permissions_and_foreign_folder(self):
        url = f'/api/containers/{self.campaign.pk}/scene-empty'
        self.assertEqual(self.client.post(url, self.payload, content_type='application/json').status_code, 403)
        self.client.force_login(self.player)
        self.assertEqual(self.client.post(url, self.payload, content_type='application/json').status_code, 400)
        self.client.force_login(self.gm)
        other = Campaign.objects.create(owner=self.gm, name='Other')
        folder = Folder.objects.create(campaign=other, label='Private')
        with self.assertRaises(services.MapError):
            self.create(groupId=str(folder.pk))
        for body in ('[]', '{', 'null'):
            self.assertEqual(self.client.post(url, body, content_type='application/json').status_code, 400)
        self.assertFalse(Scene.objects.exists())
        response = self.client.post(url, self.payload, content_type='application/json')
        self.assertEqual(response.status_code, 201, response.content)

    def test_generation_and_commit_failures_clean_up_files_and_rows(self):
        original = tiling.generate_solid_pyramid

        def fail_after_tiles(*args):
            original(*args)
            raise OSError('Storage unavailable')

        for target, error in (('gravewright.maps.empty_maps.tiling.generate_solid_pyramid', fail_after_tiles),
                              ('gravewright.maps.empty_maps.Tile.objects.bulk_create', OSError('Storage unavailable'))):
            with patch(target, side_effect=error), self.assertRaises(OSError):
                self.create()
            self.assertFalse(Scene.objects.exists())
            self.assertFalse(Receipt.objects.exists())
            self.assertFalse(list(Path(self.temp.name).rglob('*.webp')))
