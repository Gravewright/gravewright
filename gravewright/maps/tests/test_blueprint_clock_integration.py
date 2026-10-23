"""Clock bindings survive Builder saves, rehearsals, templates and campaign copies."""

from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase, override_settings

from gravewright.administration.archives import export_campaign, import_campaign
from gravewright.maps import blueprint_network, blueprint_templates, blueprint_testing, builder_services, services
from gravewright.maps.models import MapBuilderProject, Receipt, Scene
from gravewright.modules.frontend import invoke
from gravewright.modules.packages import ModuleFailure
from gravewright.table.models import ClockReceipt, ProgressClock

from . import test_blueprint_testing as fixtures
from .test_blueprint_references import node
from .test_blueprint_world import chain


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   ALLOWED_HOSTS=['testserver'], GRAVEWRIGHT_MAP_TILER='pillow', DYNAMIC_LIGHTING_ENABLED=True)
class BlueprintClockIntegrationTests(TestCase):
    asset = fixtures.BlueprintTestingTests.asset
    post = fixtures.BlueprintTestingTests.post
    save = fixtures.BlueprintTestingTests.save
    generate = fixtures.BlueprintTestingTests.generate
    files = fixtures.BlueprintTestingTests.files
    generated = fixtures.BlueprintTestingTests.generated
    command = fixtures.BlueprintTestingTests.command
    draft = fixtures.BlueprintTestingTests.draft

    def setUp(self):
        fixtures.BlueprintTestingTests.setUp(self)
        self.clock = ProgressClock.objects.create(campaign=self.campaign, name='Authored campaign clock', segments=6, value=1)

    def behavior(self, clock=None, **changes):
        return chain(node('clock', 'clockControl', clockId=str((clock or self.clock).pk), action='advance', amount=2, **changes))

    def test_gm_catalogs_filter_campaigns_and_native_scene_scope(self):
        self.generated()
        local = ProgressClock.objects.create(campaign=self.campaign, scene=self.scene, name='This scene')
        other_scene = Scene.objects.create(campaign=self.campaign, name='Other scene', width=500, height=500)
        other = ProgressClock.objects.create(campaign=self.campaign, scene=other_scene, name='Other scene clock')
        foreign = ProgressClock.objects.create(campaign=self.other, name='FOREIGN_CLOCK_SECRET')
        catalog = builder_services.catalog(self.campaign.pk, self.gm.pk)
        self.assertEqual({row['id'] for row in catalog['clocks']}, {str(c.pk) for c in (self.clock, local, other)})
        native = blueprint_network.state(self.campaign.pk, self.gm.pk, self.scene.pk)
        self.assertEqual({row['id'] for row in native['clocks']}, {str(c.pk) for c in (self.clock, local)})
        self.assertNotIn(str(foreign.pk), str(catalog))
        with self.assertRaises(services.MapError):
            blueprint_network.state(self.campaign.pk, self.player.pk, self.scene.pk)

    def test_draft_predicts_clock_changes_and_discards_receipts_notifications_and_files(self):
        self.doc['doors'][0]['blueprint'] = self.behavior()
        before = (list(ProgressClock.objects.values()), Receipt.objects.count(), ClockReceipt.objects.count(), self.files())
        with patch('gravewright.realtime.dispatch.send') as published, self.captureOnCommitCallbacks(execute=True):
            result = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, self.draft())
        self.assertTrue(result['ok'], result)
        change, = result['changes']['clocks']
        self.assertEqual(change['id'], str(self.clock.pk))
        self.assertEqual((change['before']['value'], change['after']['value']), (1, 3))
        self.assertEqual(change['after']['name'], self.clock.name)
        published.assert_not_called()
        self.assertEqual((list(ProgressClock.objects.values()), Receipt.objects.count(), ClockReceipt.objects.count(), self.files()), before)

    def test_linked_scene_bindings_save_update_and_rehearse_using_only_the_authorized_project(self):
        self.generated()
        scoped = ProgressClock.objects.create(campaign=self.campaign, scene=self.scene, name='Scoped progress', segments=8, value=2)
        self.doc['doors'][0]['blueprint'] = self.behavior(scoped)
        with self.assertRaises(services.MapError):
            builder_services.clean_document(self.doc, self.membership)
        response = self.save(expected_version=1)
        self.assertEqual(response.status_code, 200, response.content)
        result = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, self.draft(projectId=str(self.project_id)))
        self.assertTrue(result['ok'], result)
        change, = result['changes']['clocks']
        self.assertEqual((change['before']['value'], change['after']['value']), (2, 4))
        scoped.refresh_from_db()
        self.assertEqual(scoped.value, 2)
        self.scene.refresh_from_db()
        source = MapBuilderProject.objects.get(pk=self.project_id)
        builder_services.update(self.campaign.pk, self.gm.pk, source.pk, {
            'request_id': str(uuid4()), 'expected_version': source.version, 'expected_scene_version': self.scene.version})
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data['blueprint']['graphs']['interact']['nodes'][1]['clockId'], str(scoped.pk))
        with self.assertRaises(services.MapError):
            builder_services.generate(self.campaign.pk, self.gm.pk, source.pk,
                {'request_id': str(uuid4()), 'expected_version': source.version})

    def test_draft_project_id_cannot_cross_campaign_or_mounted_scene(self):
        self.generated()
        foreign = MapBuilderProject.objects.create(campaign=self.other, name='Foreign project', document={})
        with self.assertRaises(services.MapError):
            blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, self.draft(projectId=str(foreign.pk)))
        target = Scene.objects.create(campaign=self.campaign, name='Different mounted scene', width=500, height=500)
        with self.assertRaises(ModuleFailure) as rejected:
            invoke(self.campaign.pk, self.gm.pk, 'blueprints', 'testDraft', {
                'document': self.doc, 'elementId': self.doc['doors'][0]['id'], 'event': 'interact',
                'projectId': str(self.project_id)}, uuid4(), scene_id=str(target.pk))
        self.assertEqual(rejected.exception.code, 'conflict')

    def test_template_bindings_are_id_free_and_amount_parameters_use_the_same_limits(self):
        blueprint = self.behavior()
        blueprint['graphs']['interact']['nodes'][1]['clockId'] = {'binding': 'progress'}
        definition = {'version': 1, 'blueprint': blueprint,
            'bindings': [{'id': 'progress', 'type': 'clock', 'label': 'Progress'}],
            'parameters': [{'id': 'quantity', 'label': 'Quantity', 'type': 'number', 'default': 2,
                            'path': ['graphs', 'interact', 'nodes', 1, 'amount']}]}
        cleaned = blueprint_templates.clean_definition(definition)
        self.assertEqual(cleaned['blueprint']['graphs']['interact']['nodes'][1]['clockId'], {'binding': 'progress'})
        resolved = blueprint_templates.resolve_definition(definition, {'progress': str(self.clock.pk)},
            {'quantity': 6}, owner_id=self.doc['doors'][0]['id'])
        self.assertEqual(resolved['graphs']['interact']['nodes'][1]['amount'], 6)
        with self.assertRaises(services.MapError):
            blueprint_templates.resolve_definition(definition, {'progress': str(self.clock.pk)},
                {'quantity': 25}, owner_id=self.doc['doors'][0]['id'])

    def test_clones_remap_clock_bindings_and_omitted_clocks_never_bind_to_the_source(self):
        self.doc['doors'][0]['blueprint'] = self.behavior()
        self.generated()
        for included in (True, False):
            with self.subTest(included=included):
                clone = import_campaign(export_campaign(self.campaign, {'clocks': included}), self.gm, 'Clock copy')
                copied = MapBuilderProject.objects.get(campaign=clone)
                binding = copied.document['doors'][0]['blueprint']['graphs']['interact']['nodes'][1]['clockId']
                self.assertNotEqual(binding, str(self.clock.pk))
                live = copied.scene.elements.get(kind='walls', data__kind='door')
                self.assertEqual(live.data['blueprint']['graphs']['interact']['nodes'][1]['clockId'], binding)
                if included:
                    self.assertEqual(ProgressClock.objects.get(campaign=clone).pk.hex, binding.replace('-', ''))
                else:
                    self.assertFalse(ProgressClock.objects.filter(campaign=clone).exists())
