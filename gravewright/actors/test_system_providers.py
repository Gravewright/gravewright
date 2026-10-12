"""Host resources use registered capabilities, never a particular ruleset ID."""

import uuid
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.shortcuts import render

from gravewright.accounts.models import User
from gravewright.campaigns import systems
from gravewright.campaigns.catalog import get_ruleset, list_rulesets
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps.services import MapError
from gravewright.modules.models import ModuleSet
from gravewright.modules.operations import invoke

from . import services
from .models import Actor, Asset


@override_settings(
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
)
class SystemProviderTests(TestCase):
    def setUp(self):
        registry = patch.dict(systems._bundled)
        registry.start()
        self.addCleanup(registry.stop)
        default = patch.object(systems, '_default_system', systems.default_system_id())
        default.start()
        self.addCleanup(default.stop)
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        storage = override_settings(MEDIA_ROOT=media.name)
        storage.enable()
        self.addCleanup(storage.disable)
        self.user = User.objects.create_user(
            'providers@example.test', 'test-password', name='GM', role='owner',
        )
        self.descriptor = {
            'systemId': 'example.cards', 'title': 'Card rules',
            'actorTypes': [{'id': 'crew', 'label': 'Crew'}],
            'itemTypes': [{'id': 'card', 'label': 'Card'}],
        }

        def validate_upload(file):
            if not file or file.size > 80:
                raise MapError('Card files must contain at most 80 bytes.')
            raw = file.read()
            if not raw.startswith(b'CARD:'):
                raise MapError('Choose a card file.')
            return raw, '.card'

        systems.register(
            'example.cards', descriptor=self.descriptor, sheet={},
            normalize=lambda raw, previous=None, gm=True: dict(raw), default=True,
            assets={'kind': 'card', 'content_type': 'application/x-test-card',
                    'validate_upload': validate_upload,
                    'template': {'dataPath': ['card', 'source'], 'icon': 'FileText', 'label': 'Card'}},
            templates=lambda campaign_id: [
                {'id': str(row.pk), 'name': row.name}
                for row in Asset.objects.filter(campaign_id=campaign_id, kind='card')
            ],
        )
        self.campaign = Campaign.objects.create(owner=self.user, name='Registered provider')
        Membership.objects.create(campaign=self.campaign, user=self.user, role='gm')
        self.client.force_login(self.user)

    def test_defaults_are_resolved_from_registration_after_app_ready(self):
        self.assertEqual(self.campaign.system, 'example.cards')
        self.assertEqual(Asset(campaign=self.campaign).kind, 'card')
        with self.assertNumQueries(0):
            self.assertEqual(get_ruleset(''), self.descriptor)
            self.assertEqual(get_ruleset('example.cards'), self.descriptor)
        self.assertEqual(list_rulesets()[0], self.descriptor)
        from gravewright.campaigns.catalog import activate_selected_system
        activate_selected_system(self.campaign)
        self.assertFalse(ModuleSet.objects.filter(campaign=self.campaign).exists())

    def test_host_does_not_invent_defaults_without_a_registered_provider(self):
        with patch.dict(systems._bundled, {}, clear=True), patch.object(systems, '_default_system', ''):
            self.assertEqual(Campaign(owner=self.user).system, '')
            self.assertEqual(Asset(campaign=self.campaign).kind, '')
            self.assertIsNone(get_ruleset(''))
            raw = {'crew': {'fate': 7}, 'inventory': []}
            self.assertEqual(systems.normalize_actor('', raw), raw)

    def test_templates_and_toolbar_follow_the_active_provider(self):
        actor = Actor.objects.create(campaign=self.campaign, name='Captain', type='crew')
        Asset.objects.create(campaign=self.campaign, kind='pdf', name='Old template', file='old.pdf')
        asset = Asset.objects.create(campaign=self.campaign, name='Card template', file='source.card')
        state = services.state(self.campaign.pk, self.user.pk)
        self.assertEqual(state['templates'], [{'id': str(asset.pk), 'name': asset.name}])
        self.assertEqual(state['templateConfig']['dataPath'], ['card', 'source'])
        self.assertEqual(state['actors'][0]['systemId'], 'example.cards')
        self.assertEqual(services.sheet(self.campaign.pk, self.user.pk, actor.pk)['data'], {})
        with patch('gravewright.table.views.render', wraps=render) as rendering:
            response = self.client.get('/game/' + str(self.campaign.pk))
        self.assertContains(response, 'data-system-id="example.cards"')
        self.assertNotContains(response, 'accept="application/pdf"')
        icons = re.search(r'<template id="actor-icons"[\s\S]*?</template>', response.content.decode()).group()
        self.assertNotIn('data-icon="FilePdf"', icons)
        self.assertIn('items', [row['id'] for row in rendering.call_args.args[2]['directories']])

    def test_an_unregistered_system_never_inherits_templates_or_item_capability(self):
        self.campaign.system = 'external.unknown'
        self.campaign.save(update_fields=['system'])
        Asset.objects.create(campaign=self.campaign, kind='pdf', name='Old template', file='old.pdf')
        state = services.state(self.campaign.pk, self.user.pk)
        self.assertEqual(state['templates'], [])
        self.assertIsNone(state['templateConfig'])
        with patch('gravewright.table.views.render', wraps=render) as rendering:
            self.client.get('/game/' + str(self.campaign.pk))
        self.assertNotIn('items', [row['id'] for row in rendering.call_args.args[2]['directories']])

    def test_native_upload_delegates_validation_and_mime_without_pdf_rules(self):
        url = f'/api/containers/{self.campaign.pk}/actor-upload'
        response = self.client.post(url, {'file': SimpleUploadedFile('source.card', b'CARD:crew')})
        self.assertEqual(response.status_code, 200, response.content)
        asset = Asset.objects.get(pk=response.json()['id'])
        self.assertEqual(asset.kind, 'card')
        self.assertTrue(asset.file.name.endswith('.card'))
        download = self.client.get('/game/actors/asset/' + str(asset.pk))
        self.assertEqual(download['Content-Type'], 'application/x-test-card')
        self.assertEqual(b''.join(download.streaming_content), b'CARD:crew')
        rejected = self.client.post(url, {'file': SimpleUploadedFile('bad.card', b'not a card')})
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(rejected.json()['message'], 'Choose a card file.')

    def test_sdk_library_assets_keep_their_registered_kind_after_system_switch(self):
        self.campaign.system = 'external.unknown'
        self.campaign.save(update_fields=['system'])
        file = SimpleUploadedFile('source.card', b'CARD:crew', content_type='application/x-test-card')
        request = RequestFactory().post('/upload', {'file': file})
        request.user = self.user
        uploaded = invoke(request, self.campaign.pk, None, 'asset.upload', {}, upload=request.FILES['file'])
        self.assertEqual(uploaded['contentType'], 'application/x-test-card')
        actor = Actor.objects.create(campaign=self.campaign, name='Private actor', type='crew')
        Asset.objects.create(campaign=self.campaign, actor=actor, kind='portrait', name='Private', file='private.png')
        request = SimpleNamespace(user=self.user)
        listed = invoke(request, self.campaign.pk, None, 'asset.list', {})
        self.assertEqual([row['id'] for row in listed['items']], [uploaded['id']])
        response = invoke(request, self.campaign.pk, None, 'asset.download', {'id': uploaded['id']})
        self.assertEqual(response['Content-Type'], 'application/x-test-card')
        self.assertEqual(b''.join(response.streaming_content), b'CARD:crew')
        # This response came directly from invoke(), outside Django's request
        # handler. Close its file without emitting request_finished inside the
        # TestCase transaction (CONN_MAX_AGE=0 would close that connection).
        response.file_to_stream.close()
        services.command(self.campaign.pk, self.user.pk, 'asset.delete', {'id': uploaded['id']}, uuid.uuid4())
        self.assertFalse(Asset.objects.filter(pk=uploaded['id']).exists())
