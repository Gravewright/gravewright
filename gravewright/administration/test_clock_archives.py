"""Clock configuration and progress survive bounded campaign archives safely."""

from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.accounts.services import AuthError
from gravewright.actors.models import Asset
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps.models import Scene
from gravewright.table.models import ProgressClock

from .archives import export_campaign, import_campaign, options, read_archive, records


class ClockArchiveTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.media = Path(temporary.name)
        media = override_settings(MEDIA_ROOT=temporary.name)
        media.enable()
        self.addCleanup(media.disable)
        self.user = User.objects.create(email='clock-archive@example.test', name='GM')
        self.campaign = Campaign.objects.create(owner=self.user, name='Synthetic clock campaign')
        Membership.objects.create(campaign=self.campaign, user=self.user, role='gm')
        self.scene = Scene.objects.create(campaign=self.campaign, name='Scene scope', width=500, height=500)
        self.global_clock = ProgressClock.objects.create(campaign=self.campaign,
            name='An authored reference ' + str(self.scene.pk), segments=12, value=9, color='#ABCDEF',
            description='  Authored description ' + str(self.scene.pk) + '\nSecond line á  ',
            visibility='players', players_can_edit=True, pinned=True, version=7)
        self.scene_clock = ProgressClock.objects.create(campaign=self.campaign, scene=self.scene,
            name=str(self.global_clock.pk), description=str(self.global_clock.pk), segments=6, value=5,
            color='#123456', visibility='gm', version=3)
        self.asset = Asset.objects.create(campaign=self.campaign, kind='pdf', name='Synthetic sheet.pdf',
            file=ContentFile(b'%PDF-1.4\n% Synthetic archive test, no licensed content\n%%EOF', name='synthetic.pdf'))

    def archive(self, selected=None, **kwargs):
        return export_campaign(self.campaign, selected, **kwargs)

    @staticmethod
    def rewrite_archive(raw, update):
        """Tamper with archive content while retaining a correct integrity manifest."""
        with ZipFile(BytesIO(raw)) as original:
            blobs = {name: original.read(name) for name in original.namelist()}
        manifest = json.loads(blobs['manifest.json'])
        payload = json.loads(blobs['campaign.json'])
        update(payload)
        content = json.dumps(payload, separators=(',', ':')).encode()
        blobs['campaign.json'] = content
        manifest['files']['campaign.json'] = {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
        blobs['manifest.json'] = json.dumps(manifest).encode()
        output = BytesIO()
        with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
            for name, blob in blobs.items():
                archive.writestr(name, blob)
        return output.getvalue()

    @staticmethod
    def clock_records(payload):
        return [record for record in payload['records'] if record['model'] == 'gravewright_table.progressclock']

    def snapshot_state(self):
        return {
            'campaigns': list(Campaign.objects.order_by('pk').values()),
            'members': list(Membership.objects.order_by('pk').values()),
            'scenes': list(Scene.objects.order_by('pk').values()),
            'clocks': list(ProgressClock.objects.order_by('pk').values()),
            'assets': list(Asset.objects.order_by('pk').values()),
            'files': {str(path.relative_to(self.media)): path.read_bytes()
                      for path in self.media.rglob('*') if path.is_file()},
        }

    def test_portable_import_remaps_ids_and_scene_references_without_rewriting_authored_names(self):
        raw = self.archive()
        payload, _ = read_archive(raw)
        self.assertEqual(len(self.clock_records(payload)), 2)
        cloned = import_campaign(raw, self.user, 'Cloned clock campaign')
        imported = {row.name: row for row in ProgressClock.objects.filter(campaign=cloned)}
        self.assertEqual(set(imported), {self.global_clock.name, self.scene_clock.name})
        global_clock = imported[self.global_clock.name]
        scene_clock = imported[self.scene_clock.name]
        self.assertNotEqual(global_clock.pk, self.global_clock.pk)
        self.assertNotEqual(scene_clock.pk, self.scene_clock.pk)
        self.assertIsNone(global_clock.scene_id)
        self.assertNotEqual(scene_clock.scene_id, self.scene.pk)
        self.assertEqual(scene_clock.scene.campaign_id, cloned.pk)
        self.assertEqual((global_clock.segments, global_clock.value, global_clock.color, global_clock.visibility,
                          global_clock.players_can_edit, global_clock.pinned, global_clock.version),
                         (12, 9, '#ABCDEF', 'players', True, True, 7))
        self.assertEqual((scene_clock.segments, scene_clock.value, scene_clock.visibility, scene_clock.version), (6, 5, 'gm', 3))
        self.assertEqual(global_clock.description, self.global_clock.description)
        self.assertEqual(scene_clock.description, self.scene_clock.description)
        imported_asset = Asset.objects.get(campaign=cloned)
        self.assertNotEqual(imported_asset.pk, self.asset.pk)
        self.assertNotEqual(imported_asset.file.name, self.asset.file.name)
        with imported_asset.file.open('rb') as copy, self.asset.file.open('rb') as source:
            self.assertEqual(copy.read(), source.read())
        self.assertEqual(ProgressClock.objects.get(pk=self.global_clock.pk).value, 9)

    def test_snapshot_restore_keeps_clock_ids_and_restores_configuration_progress_and_scope(self):
        raw = self.archive(snapshot=True)
        ids = {self.global_clock.pk, self.scene_clock.pk}
        ProgressClock.objects.filter(pk=self.global_clock.pk).update(name='Changed', value=0, pinned=False,
                                                                   description='Changed description', players_can_edit=False, version=8)
        ProgressClock.objects.filter(pk=self.scene_clock.pk).update(scene=None, value=0, version=4)
        extra = ProgressClock.objects.create(campaign=self.campaign, name='After snapshot')
        restored = import_campaign(raw, self.user, target=self.campaign)
        self.assertEqual(restored.pk, self.campaign.pk)
        self.assertEqual(set(ProgressClock.objects.filter(campaign=restored).values_list('pk', flat=True)), ids)
        self.assertFalse(ProgressClock.objects.filter(pk=extra.pk).exists())
        global_clock = ProgressClock.objects.get(pk=self.global_clock.pk)
        scene_clock = ProgressClock.objects.get(pk=self.scene_clock.pk)
        self.assertEqual((global_clock.name, global_clock.value, global_clock.pinned, global_clock.players_can_edit, global_clock.version),
                         (self.global_clock.name, 9, True, True, 7))
        self.assertEqual((scene_clock.name, scene_clock.scene_id, scene_clock.value, scene_clock.version),
                         (self.scene_clock.name, self.scene.pk, 5, 3))
        self.assertEqual(global_clock.description, self.global_clock.description)
        self.assertEqual(scene_clock.description, self.scene_clock.description)
        self.assertEqual(Membership.objects.get(campaign=restored, user=self.user).role, 'gm')

    def test_clock_and_scene_selection_options_preserve_only_the_selected_scopes(self):
        self.assertTrue(options()['clocks'])
        for selected, expected_clocks, expected_scenes in (
            ({'clocks': False}, 0, 1),
            ({'scenes': False}, 1, 0),
            ({'clocks': False, 'scenes': False}, 0, 0),
        ):
            with self.subTest(selected=selected):
                exported = records(self.campaign, options(selected))
                clock_rows = [row for row in exported if row['model'] == 'gravewright_table.progressclock']
                self.assertEqual(len(clock_rows), expected_clocks)
                imported = import_campaign(self.archive(selected), self.user, 'Selected clock content')
                clocks = ProgressClock.objects.filter(campaign=imported)
                self.assertEqual(clocks.count(), expected_clocks)
                self.assertEqual(Scene.objects.filter(campaign=imported).count(), expected_scenes)
                if not expected_scenes:
                    self.assertFalse(clocks.filter(scene__isnull=False).exists())
                    if expected_clocks:
                        self.assertEqual(clocks.get().name, self.global_clock.name)

    def test_invalid_clock_values_fail_atomically_before_replacing_target_records_or_files(self):
        raw = self.archive(snapshot=True)
        before = self.snapshot_state()
        cases = [
            {'segments': value} for value in (True, '6', 6.0, 1, 25, None)
        ] + [{'value': value} for value in (True, '1', 1.0, -1, 13, float('nan'), float('inf'))] + [
            {'players_can_edit': value} for value in (0, 'false', None)
        ] + [{'pinned': value} for value in (1, 'true', None)] + [
            {'color': '#fff'}, {'color': 'javascript:color'}, {'visibility': 'everyone'}, {'visibility': []},
            {'name': ''}, {'name': 'x' * 121}, {'name': None},
            {'description': None}, {'description': True}, {'description': 1}, {'description': []},
            {'description': {}}, {'description': 'x' * 4001},
            {'version': True}, {'version': 1.0}, {'version': 0}, {'version': -1}, {'version': 2**31},
            {'unknown_clock_field': 'reject me'},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                modified = self.rewrite_archive(raw, lambda payload: self.clock_records(payload)[0]['fields'].update(changes))
                with self.assertRaises(AuthError):
                    import_campaign(modified, self.user, target=self.campaign)
                self.assertEqual(self.snapshot_state(), before)

    def test_archives_from_before_descriptions_restore_with_empty_description(self):
        def older(payload):
            for row in self.clock_records(payload):
                row['fields'].pop('description')
        for snapshot in (False, True):
            with self.subTest(snapshot=snapshot):
                raw = self.rewrite_archive(self.archive(snapshot=snapshot), older)
                read_archive(raw)
                target = self.campaign if snapshot else None
                imported = import_campaign(raw, self.user, 'Legacy clock fields', target=target)
                self.assertEqual(set(ProgressClock.objects.filter(campaign=imported).values_list('description', flat=True)), {''})

    def test_missing_or_foreign_scene_references_fail_instead_of_becoming_campaign_clocks(self):
        foreign = Campaign.objects.create(owner=self.user, name='Foreign clock source')
        foreign_scene = Scene.objects.create(campaign=foreign, name='Foreign private scene', width=100, height=100)
        raw = self.archive(snapshot=True)
        before = self.snapshot_state()
        for invalid in (str(uuid4()), str(foreign_scene.pk), '', False, 0):
            with self.subTest(scene=invalid):
                modified = self.rewrite_archive(raw, lambda payload: self.clock_records(payload)[1]['fields'].update(scene=invalid))
                with self.assertRaises(AuthError):
                    import_campaign(modified, self.user, target=self.campaign)
                self.assertEqual(self.snapshot_state(), before)
        modified = self.rewrite_archive(raw, lambda payload: self.clock_records(payload)[1]['fields'].pop('scene'))
        with self.assertRaises(AuthError):
            import_campaign(modified, self.user, target=self.campaign)
        self.assertEqual(self.snapshot_state(), before)

    def test_archive_limit_and_duplicate_clock_records_roll_back_new_campaign_import(self):
        raw = self.archive()
        before = self.snapshot_state()
        def add_too_many(payload):
            template = deepcopy(self.clock_records(payload)[0])
            for _ in range(127):
                extra = deepcopy(template)
                extra['pk'] = str(uuid4())
                payload['records'].append(extra)
        too_many = self.rewrite_archive(raw, add_too_many)
        with self.assertRaises(AuthError):
            import_campaign(too_many, self.user, 'Rejected clock campaign')
        self.assertEqual(self.snapshot_state(), before)
        duplicate = self.rewrite_archive(raw, lambda payload: payload['records'].append(deepcopy(self.clock_records(payload)[0])))
        with self.assertRaises(AuthError):
            import_campaign(duplicate, self.user, 'Rejected duplicate campaign')
        self.assertEqual(self.snapshot_state(), before)

    def test_merge_limit_counts_existing_clocks_and_rolls_back_all_incoming_resources(self):
        target = Campaign.objects.create(owner=self.user, name='Existing clock target')
        Membership.objects.create(campaign=target, user=self.user, role='gm')
        ProgressClock.objects.bulk_create([ProgressClock(campaign=target, name=f'Existing {index}') for index in range(127)])
        before = self.snapshot_state()
        with self.assertRaises(AuthError):
            import_campaign(self.archive(), self.user, target=target, merge=True)
        self.assertEqual(self.snapshot_state(), before)

    def test_merge_remaps_clocks_and_their_scene_without_changing_existing_target_clocks(self):
        target = Campaign.objects.create(owner=self.user, name='Merged clock target')
        Membership.objects.create(campaign=target, user=self.user, role='gm')
        original = ProgressClock.objects.create(campaign=target, name='Existing clock', segments=4, value=2, version=2)
        result = import_campaign(self.archive(), self.user, target=target, merge=True)
        self.assertEqual(result.pk, target.pk)
        self.assertEqual(ProgressClock.objects.filter(campaign=target).count(), 3)
        original.refresh_from_db()
        self.assertEqual((original.name, original.value, original.version), ('Existing clock', 2, 2))
        scoped = ProgressClock.objects.get(campaign=target, name=self.scene_clock.name)
        self.assertNotEqual(scoped.pk, self.scene_clock.pk)
        self.assertNotEqual(scoped.scene_id, self.scene.pk)
        self.assertEqual(scoped.scene.campaign_id, target.pk)
        self.assertEqual(scoped.value, self.scene_clock.value)
