"""Independent authorization regressions for mind-map resource links."""

from django.test import TestCase
from unittest.mock import patch

from gravewright.actors.models import Actor, Asset
from gravewright.campaigns.models import Membership
from gravewright.table import resource_links
from gravewright.table.models import DocumentAccess
from gravewright.table.tests import test_clocks as fixtures


class MindMapResourceAuthorizationReviewTests(TestCase):
    setUpTestData = fixtures.ProgressClockTests.__dict__['setUpTestData']

    def test_authorized_sheet_text_cannot_expose_another_actors_private_asset_metadata(self):
        private_actor = Actor.objects.create(campaign=self.campaign, name='Private actor', permissions={'default': 'none'})
        private_asset = Asset.objects.create(campaign=self.campaign, actor=private_actor, kind='pdf',
                                            name='PRIVATE ASSET TITLE', file='private-synthetic.pdf')
        Actor.objects.create(campaign=self.campaign, name='Player sheet', permissions={'default': 'owner'},
                             data={'notes': str(private_asset.pk), 'pdf': {'asset': str(private_asset.pk)}})
        who = Membership.objects.select_related('user', 'campaign').get(campaign=self.campaign, user=self.player)
        self.assertIsNone(resource_links.resolve(who, {'kind': 'actor-asset', 'id': str(private_asset.pk)}))

    def test_catalog_keeps_authorized_campaign_resources_when_broadcast_scene_access_is_denied(self):
        actor = Actor.objects.create(campaign=self.campaign, name='Readable campaign actor', permissions={'default': 'read'})
        DocumentAccess.objects.create(campaign=self.campaign, kind='scenes', resource_id=str(self.scene.pk), grants={'default': 'none'})
        who = Membership.objects.select_related('user', 'campaign').get(campaign=self.campaign, user=self.player)
        result = resource_links.catalog(who)
        self.assertIn(str(actor.pk), {row['id'] for row in result['resources']})
        self.assertNotIn(str(self.scene.pk), {row['id'] for row in result['resources']})

    def test_mapping_links_use_the_current_system_read_capability_without_a_system_name_condition(self):
        from gravewright.campaigns import system_api
        from gravewright.pdf_system.models import MappingTemplate
        mapping = MappingTemplate.objects.create(campaign=self.campaign, name='Provider-owned layout')
        self.campaign.system = 'synthetic-mapping-provider'
        self.campaign.save(update_fields=['system'])
        calls = []
        def read(campaign_id, user_id, payload, request_id, scene_id):
            calls.append((campaign_id, user_id, payload, request_id, scene_id))
            return {'items': [{'id': str(mapping.pk), 'name': mapping.name}]}
        with patch.dict(system_api._providers):
            system_api.register_api('synthetic-mapping-provider', {
                'pdf.templates.list': {'effect': 'read', 'handler': read}})
            who = Membership.objects.get(campaign=self.campaign, user=self.gm)
            resolved = resource_links.resolve(who, {'kind': 'pdf-mapping', 'id': str(mapping.pk)})
        self.assertEqual(resolved['label'], mapping.name)
        self.assertEqual(calls, [(self.campaign.pk, self.gm.pk, {}, None, None)])
