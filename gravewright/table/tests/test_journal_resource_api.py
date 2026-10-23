"""Public journal resource reads retain native access and mounted context."""

from uuid import uuid4

from django.test import TestCase

from gravewright.actors.models import Actor
from gravewright.journals.models import Receipt
from gravewright.journals.models import Journal
from gravewright.modules.frontend import invoke
from gravewright.modules.packages import ModuleFailure
from gravewright.table.models import ProgressClock
from gravewright.table.tests import test_clocks as fixtures


class JournalResourceApiTests(TestCase):
    setUpTestData = fixtures.ProgressClockTests.__dict__['setUpTestData']

    def test_guest_journal_refresh_uses_authorized_uncached_get_without_relaxing_post_write_ban(self):
        public = Journal.objects.create(campaign=self.campaign, title='Visible diary', visibility='shared')
        hidden = Journal.objects.create(campaign=self.campaign, title='PRIVATE DIARY')
        self.client.force_login(self.streamer)
        response = self.client.get(f'/api/containers/{self.campaign.pk}/journals')
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual([row['id'] for row in response.json()['journals']], [str(public.pk)])
        self.assertNotIn(str(hidden.pk), response.content.decode())
        response = self.client.post(f'/api/tables/{self.campaign.pk}/api',
            {'domain': 'journals', 'method': 'create', 'payload': {'title': 'Forbidden'}}, content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'stream_read_only')

    def test_resource_catalog_and_resolve_are_authorized_reads_without_receipts(self):
        actor = Actor.objects.create(campaign=self.campaign, name='Readable sheet', permissions={'default': 'read'})
        secret = ProgressClock.objects.create(campaign=self.campaign, name='PRIVATE LINK TARGET')
        foreign = ProgressClock.objects.create(campaign=self.foreign, name='FOREIGN TARGET')
        for user in (self.player, self.streamer):
            catalog = invoke(self.campaign.pk, user.pk, 'journals', 'resources', {'kinds': ['actor']})
            self.assertEqual([row['id'] for row in catalog['resources']], [str(actor.pk)])
            for clock in (secret, foreign):
                self.assertEqual(invoke(self.campaign.pk, user.pk, 'journals', 'resolve',
                    {'reference': {'kind': 'clock', 'id': str(clock.pk)}}), {'resource': None})
        resolved = invoke(self.campaign.pk, self.gm.pk, 'journals', 'resolve',
            {'reference': {'kind': 'clock', 'id': str(secret.pk)}})
        self.assertEqual(resolved['resource']['label'], secret.name)
        self.assertFalse(Receipt.objects.filter(campaign=self.campaign).exists())

    def test_read_context_cannot_be_retargeted_and_unknown_payload_fields_are_rejected(self):
        for method, payload in [('resources', {'query': '', 'userId': str(self.gm.pk)}),
                                ('resolve', {'reference': {'kind': 'actor', 'id': str(uuid4())}, 'forged': True}),
                                ('resources', {'sceneId': str(self.scene.pk), 'mapId': str(self.other_scene.pk)})]:
            with self.subTest(method=method, payload=payload), self.assertRaises(ModuleFailure) as error:
                invoke(self.campaign.pk, self.player.pk, 'journals', method, payload)
            self.assertEqual(error.exception.code, 'invalid_data')
        with self.assertRaises(ModuleFailure) as error:
            invoke(self.campaign.pk, self.gm.pk, 'journals', 'resources', {'sceneId': str(self.other_scene.pk)},
                   scene_id=self.scene.pk)
        self.assertEqual(error.exception.code, 'stale_context')
