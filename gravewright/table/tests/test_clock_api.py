"""The clock browser domain keeps native permissions and bound-scene identity."""
import uuid
from unittest.mock import patch

from django.test import TestCase

from gravewright.modules.frontend import invoke
from gravewright.modules.packages import ModuleFailure
from gravewright.campaigns.models import Membership
from gravewright.table.models import ClockReceipt, ProgressClock
from gravewright.table.tests import test_clocks as clock_fixtures


class ClockFrontendTests(TestCase):
    setUpTestData = clock_fixtures.ProgressClockTests.__dict__['setUpTestData']

    def call(self, method, payload=None, request_id=None):
        return self.client.post(f'/api/tables/{self.campaign.pk}/api', {
            'domain': 'clocks', 'method': method, 'payload': payload or {},
            'requestId': str(request_id or uuid.uuid4()),
        }, content_type='application/json')

    def test_browser_creation_updates_and_conflicts_keep_the_native_receipt(self):
        self.client.force_login(self.gm)
        rid = uuid.uuid4()
        payload = {'name': 'Browser clock', 'segments': 8, 'visibility': 'players', 'playersCanEdit': True,
                   'scopeSceneId': None, 'sceneId': str(self.scene.pk), 'mapId': str(self.scene.pk)}
        with patch('gravewright.realtime.dispatch.send') as published, self.captureOnCommitCallbacks(execute=True):
            first = self.call('create', payload, rid)
        self.assertEqual(first.status_code, 200, first.content)
        clock = first.json()['value']['clock']
        self.assertIsNone(clock['sceneId'])
        self.assertEqual(published.call_args.args[1], {'type': 'room.resources', 'module': 'clocks'})
        self.assertEqual(self.call('create', payload, rid).json(), first.json())
        self.assertEqual(ProgressClock.objects.count(), 1)
        self.client.force_login(self.player)
        advanced = self.call('advance', {'id': clock['id'], 'version': clock['version'], 'delta': 1})
        self.assertEqual(advanced.status_code, 200, advanced.content)
        self.assertFalse(advanced.json()['value']['clock']['canConfigure'])
        conflict = self.call('advance', {'id': clock['id'], 'version': clock['version'], 'delta': 1})
        self.assertEqual(conflict.status_code, 409, conflict.content)
        self.assertEqual(ProgressClock.objects.get().value, 1)

    def test_private_clocks_and_cross_campaign_records_never_reach_player_projection(self):
        ProgressClock.objects.create(campaign=self.campaign, name='Never reveal clock')
        ProgressClock.objects.create(campaign=self.foreign, name='Foreign campaign', visibility='players')
        public = ProgressClock.objects.create(campaign=self.campaign, name='Public clock', visibility='players')
        self.client.force_login(self.player)
        response = self.call('state')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([c['id'] for c in response.json()['value']['clocks']], [str(public.pk)])
        self.assertNotIn('Never reveal', response.content.decode())
        self.assertNotIn('Foreign campaign', response.content.decode())
        self.assertEqual(self.call('create', {'name': 'Forbidden'}).status_code, 403)

    def test_mounted_scene_context_cannot_be_used_to_create_a_clock_in_another_scene(self):
        for target in (self.other_scene, self.foreign_scene):
            with self.subTest(target=target.pk), self.assertRaises(ModuleFailure) as rejected:
                invoke(self.campaign.pk, self.gm.pk, 'clocks', 'create', {
                    'name': 'Bound clock', 'scopeSceneId': str(target.pk),
                }, uuid.uuid4(), scene_id=str(self.scene.pk))
            self.assertEqual(rejected.exception.code, 'stale_context')
        for target in (None, str(self.scene.pk)):
            result = invoke(self.campaign.pk, self.gm.pk, 'clocks', 'create', {
                'name': 'Authorized clock', 'scopeSceneId': target,
            }, uuid.uuid4(), scene_id=str(self.scene.pk))
            self.assertEqual(result['clock']['sceneId'], target)

    def test_mounted_metadata_update_does_not_move_a_campaign_clock(self):
        clock = ProgressClock.objects.create(campaign=self.campaign, name='Global clock')
        result = invoke(self.campaign.pk, self.gm.pk, 'clocks', 'update', {
            'id': str(clock.pk), 'version': clock.version, 'name': 'Changed global clock',
        }, uuid.uuid4(), scene_id=str(self.scene.pk))
        self.assertIsNone(result['clock']['sceneId'])
        self.assertEqual(result['clock']['name'], 'Changed global clock')

    def test_stream_guest_uses_native_read_route_and_retains_http_write_ban(self):
        ProgressClock.objects.create(campaign=self.campaign, name='Private clock')
        public = ProgressClock.objects.create(campaign=self.campaign, name='Public clock', visibility='players', players_can_edit=True)
        self.client.force_login(self.streamer)
        response = self.client.get(f'/api/containers/{self.campaign.pk}/modules-native/clocks', {'sceneId': str(self.scene.pk)})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([clock['id'] for clock in response.json()['clocks']], [str(public.pk)])
        self.assertFalse(response.json()['clocks'][0]['canEdit'])
        self.assertFalse(response.json()['clocks'][0]['canConfigure'])
        self.assertEqual(self.call('advance', {'id': str(public.pk), 'version': 1, 'delta': 1}).status_code, 403)
        public.refresh_from_db()
        self.assertEqual(public.value, 0)

    def test_private_clock_receipt_cannot_be_replayed_after_downgrade_through_another_browser_domain(self):
        self.client.force_login(self.gm)
        request_id = uuid.uuid4()
        created = self.call('create', {'name': 'PRIVATE_CLOCK_RECEIPT'}, request_id)
        self.assertEqual(created.status_code, 200, created.content)
        self.assertEqual(ClockReceipt.objects.filter(request_id=request_id).count(), 1)
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role='player')
        direct = self.call('create', {'name': 'PRIVATE_CLOCK_RECEIPT'}, request_id)
        self.assertEqual(direct.status_code, 403, direct.content)
        cross_resource = self.client.post(f'/api/tables/{self.campaign.pk}/api', {
            'domain': 'items', 'method': 'create', 'payload': {'name': 'Unrelated', 'type': 'unused'},
            'requestId': str(request_id),
        }, content_type='application/json')
        self.assertEqual(cross_resource.status_code, 403, cross_resource.content)
        self.assertNotIn('PRIVATE_CLOCK_RECEIPT', direct.content.decode())
        self.assertNotIn('PRIVATE_CLOCK_RECEIPT', cross_resource.content.decode())
