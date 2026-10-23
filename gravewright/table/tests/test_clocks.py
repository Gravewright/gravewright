"""Progress clocks preserve campaign privacy, scoped edits and native retries."""

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from api import clocks, events
from api.errors import JournalError, MapError
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership, StreamerLink
from gravewright.maps.models import Broadcast, Receipt as SharedReceipt, Scene
from gravewright.journals.services import JournalError
from gravewright.table import clocks as service
from gravewright.table.models import ClockReceipt, DocumentAccess, ProgressClock


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class ProgressClockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gm = User.objects.create(email='clock-gm@example.test', name='GM', role='owner')
        cls.player = User.objects.create(email='clock-player@example.test', name='Player')
        cls.streamer = User.objects.create(email='clock-stream@example.test', name='Streamer')
        cls.outsider = User.objects.create(email='clock-outsider@example.test', name='Outsider')
        cls.campaign = Campaign.objects.create(owner=cls.gm, name='Clock campaign')
        cls.foreign = Campaign.objects.create(owner=cls.gm, name='Other clock campaign')
        for campaign in (cls.campaign, cls.foreign):
            Membership.objects.create(campaign=campaign, user=cls.gm, role='gm')
        Membership.objects.create(campaign=cls.campaign, user=cls.player, role='player')
        Membership.objects.create(campaign=cls.campaign, user=cls.streamer, role='streamer')
        StreamerLink.objects.create(campaign=cls.campaign, guest=cls.streamer, digest='synthetic-clock-stream-link',
                                    expires_at=timezone.now() + timedelta(hours=1))
        cls.scene = Scene.objects.create(campaign=cls.campaign, name='Broadcast scene', width=500, height=500)
        cls.hidden_scene = Scene.objects.create(campaign=cls.campaign, name='GM scene', visibility='gm', width=500, height=500)
        cls.other_scene = Scene.objects.create(campaign=cls.campaign, name='Other scene', width=500, height=500)
        cls.foreign_scene = Scene.objects.create(campaign=cls.foreign, name='Foreign scene', width=500, height=500)
        Broadcast.objects.create(campaign=cls.campaign, scene=cls.scene)

    def command(self, action, payload, user=None, request_id=None):
        return clocks.command(self.campaign.pk, (user or self.gm).pk, action, payload, request_id or uuid4())

    def create(self, **fields):
        return self.command('create', {'name': 'Progress', **fields})['clock']

    def state(self, user=None, scene=None):
        return clocks.state(self.campaign.pk, (user or self.gm).pk, scene.pk if scene else None)

    def test_projection_filters_private_and_other_scene_clocks_and_disables_streamer_editing(self):
        private = self.create(name='PRIVATE_GM_PLAN', pinned=True)
        campaign = self.create(name='Campaign public', visibility='players', playersCanEdit=True)
        scoped = self.create(name='Scene public', scopeSceneId=str(self.scene.pk), visibility='players', playersCanEdit=True)
        hidden = self.create(name='Hidden scene plan', scopeSceneId=str(self.hidden_scene.pk), visibility='players')
        ProgressClock.objects.create(campaign=self.foreign, name='FOREIGN_PLAN', visibility='players')
        self.assertEqual({row['id'] for row in self.state()['clocks']}, {private['id'], campaign['id']})
        gm_view = self.state(scene=self.scene)
        self.assertEqual({row['id'] for row in gm_view['clocks']}, {private['id'], campaign['id'], scoped['id']})
        self.assertTrue(all(row['canEdit'] and row['canConfigure'] for row in gm_view['clocks']))
        player_view = self.state(self.player, self.scene)
        self.assertEqual({row['id'] for row in player_view['clocks']}, {campaign['id'], scoped['id']})
        self.assertTrue(all(row['canEdit'] and not row['canConfigure'] for row in player_view['clocks']))
        self.assertFalse(player_view['is_gm'])
        self.assertEqual(player_view['sceneId'], str(self.scene.pk))
        stream_view = self.state(self.streamer, self.scene)
        self.assertEqual({row['id'] for row in stream_view['clocks']}, {campaign['id'], scoped['id']})
        self.assertTrue(all(not row['canEdit'] and not row['canConfigure'] for row in stream_view['clocks']))
        self.assertNotIn(hidden['id'], str(player_view))
        self.assertNotIn('PRIVATE_GM_PLAN', str(player_view))
        self.assertNotIn('FOREIGN_PLAN', str(gm_view))

    def test_scene_reads_use_native_broadcast_visibility_and_document_grants(self):
        self.create(visibility='players')
        for user, target in ((self.player, self.hidden_scene), (self.player, self.other_scene),
                             (self.gm, self.foreign_scene), (self.streamer, self.other_scene)):
            with self.subTest(user=user.name, scene=target.name), self.assertRaises(MapError):
                self.state(user, target)
        DocumentAccess.objects.create(campaign=self.campaign, kind='scenes', resource_id=str(self.scene.pk),
                                      grants={'default': 'none'})
        with self.assertRaises(MapError):
            self.state(self.player, self.scene)
        self.assertEqual(len(self.state(self.gm, self.scene)['clocks']), 1)

    def test_defaults_and_explicit_configuration_are_persisted_without_scene_context_retargeting(self):
        clock = self.create(sceneId=str(self.scene.pk), mapId=str(self.scene.pk))
        self.assertEqual({key: clock[key] for key in service.CONFIG_FIELDS}, {
            'name': 'Progress', 'description': '', 'segments': 4, 'value': 0, 'color': '#c9a44c',
            'visibility': 'gm', 'playersCanEdit': False, 'pinned': False,
        })
        self.assertIsNone(clock['sceneId'])
        clock = self.command('update', {'id': clock['id'], 'version': 1, 'name': 'Renamed',
                                      'sceneId': str(self.scene.pk), 'mapId': str(self.scene.pk)})['clock']
        self.assertIsNone(clock['sceneId'])
        configured = self.create(name='  A long operation  ', segments=24, value=24, color='#ABCDEF',
                                 visibility='players', playersCanEdit=True, pinned=True,
                                 scopeSceneId=str(self.scene.pk))
        self.assertEqual(configured['name'], 'A long operation')
        self.assertEqual(configured['value'], 24)
        row = ProgressClock.objects.get(pk=configured['id'])
        self.assertTrue(row.pinned and row.players_can_edit)
        self.assertEqual(row.scene_id, self.scene.pk)

    def test_strict_create_validation_rejects_ambiguous_types_unknown_keys_and_foreign_scope(self):
        invalid = [
            {'segments': value} for value in (True, 2.0, '4', 1, 25, None)
        ] + [{'value': value} for value in (True, 1.0, '1', -1, 5)] + [
            {'playersCanEdit': value} for value in (0, 1, 'false', None)
        ] + [{'pinned': value} for value in (0, 1, 'true', None)] + [
            {'name': ''}, {'name': '   '}, {'name': 'x' * 121}, {'name': None},
            {'color': '#fff'}, {'color': 'red'}, {'visibility': 'streamers'}, {'visibility': []},
            {'scopeSceneId': str(self.foreign_scene.pk)}, {'scopeSceneId': True}, {'scopeSceneId': ''},
            {'sceneId': str(self.foreign_scene.pk)}, {'sceneId': str(self.scene.pk), 'mapId': str(self.other_scene.pk)},
            {'unknown': True}, {'id': str(uuid4())}, {'version': 1},
        ]
        for fields in invalid:
            with self.subTest(fields=fields), self.assertRaises(MapError):
                self.create(**fields)
        self.assertEqual(ProgressClock.objects.count(), 0)
        self.assertEqual(ClockReceipt.objects.count(), 0)

    def test_campaign_limit_counts_all_scopes_and_does_not_block_existing_edits(self):
        ProgressClock.objects.bulk_create([
            ProgressClock(campaign=self.campaign, scene=self.hidden_scene if index % 2 else None, name=f'Clock {index}')
            for index in range(127)
        ] + [ProgressClock(campaign=self.foreign, name=f'Foreign clock {index}') for index in range(128)])
        last = self.create(name='Last allowed', scopeSceneId=str(self.scene.pk))
        with self.assertRaises(MapError):
            self.create(name='Too many', scopeSceneId=str(self.other_scene.pk))
        self.assertEqual(ProgressClock.objects.filter(campaign=self.campaign).count(), 128)
        updated = self.command('update', {'id': last['id'], 'version': 1, 'name': 'Still editable'})
        self.assertEqual(updated['clock']['name'], 'Still editable')

    def test_gm_configuration_clamps_only_omitted_values_and_rejects_partial_bad_updates(self):
        clock = self.create(segments=12, value=10)
        reduced = self.command('update', {'id': clock['id'], 'version': 1, 'segments': 4})['clock']
        self.assertEqual((reduced['segments'], reduced['value'], reduced['version']), (4, 4, 2))
        increased = self.command('update', {'id': clock['id'], 'version': 2, 'segments': 8})['clock']
        self.assertEqual((increased['segments'], increased['value']), (8, 4))
        for changes in ({'segments': 2, 'value': 3}, {'name': 'Partial mutation', 'pinned': 1},
                        {'segments': True}, {'value': 8.0}, {'players_can_edit': True}):
            with self.subTest(changes=changes), self.assertRaises(MapError):
                self.command('update', {'id': clock['id'], 'version': 3, **changes})
        row = ProgressClock.objects.get(pk=clock['id'])
        self.assertEqual((row.name, row.segments, row.value, row.version), ('Progress', 8, 4, 3))
        self.assertEqual(self.command('reset', {'id': clock['id'], 'version': 3})['clock']['value'], 0)

    def test_scope_changes_are_explicit_and_context_cannot_edit_a_different_scoped_clock(self):
        clock = self.create(scopeSceneId=str(self.scene.pk), visibility='players', playersCanEdit=True)
        moved = self.command('update', {'id': clock['id'], 'version': 1, 'sceneId': str(self.scene.pk),
                                      'scopeSceneId': str(self.other_scene.pk)})['clock']
        self.assertEqual(moved['sceneId'], str(self.other_scene.pk))
        for action, payload in (
            ('update', {'name': 'Wrong context'}), ('advance', {'delta': 1}), ('reset', {}), ('delete', {}),
        ):
            with self.subTest(action=action), self.assertRaises(MapError):
                self.command(action, {'id': clock['id'], 'version': 2, 'sceneId': str(self.scene.pk), **payload})
        with self.assertRaises(MapError):
            self.command('update', {'id': clock['id'], 'version': 2, 'scopeSceneId': str(self.foreign_scene.pk)})
        global_clock = self.command('update', {'id': clock['id'], 'version': 2,
                                             'sceneId': str(self.other_scene.pk), 'scopeSceneId': None})['clock']
        self.assertIsNone(global_clock['sceneId'])
        self.assertEqual(self.command('advance', {'id': clock['id'], 'version': 3, 'delta': 1,
                                                'sceneId': str(self.scene.pk)}, self.player)['clock']['value'], 1)

    def test_players_advance_only_editable_public_clocks_with_bounded_integer_intents(self):
        clock = self.create(segments=6, value=2, visibility='players', playersCanEdit=True,
                            scopeSceneId=str(self.scene.pk))
        advanced = self.command('advance', {'id': clock['id'], 'version': 1, 'delta': 24}, self.player)['clock']
        self.assertEqual(advanced['value'], 6)
        self.assertTrue(advanced['canEdit'])
        self.assertFalse(advanced['canConfigure'])
        decreased = self.command('advance', {'id': clock['id'], 'version': 2, 'delta': -24}, self.player)['clock']
        self.assertEqual(decreased['value'], 0)
        for delta in (True, 1.0, '1', -25, 25, None):
            with self.subTest(delta=delta), self.assertRaises(MapError):
                self.command('advance', {'id': clock['id'], 'version': 3, 'delta': delta}, self.player)
        for action, fields in (('create', {'name': 'Unauthorized'}), ('update', {'name': 'Unauthorized'}),
                               ('reset', {}), ('delete', {}), ('advance', {'delta': 1, 'value': 6})):
            with self.subTest(action=action, fields=fields), self.assertRaises(MapError):
                self.command(action, {'id': clock['id'], 'version': 3, **fields} if action != 'create' else fields, self.player)
        self.assertEqual(ProgressClock.objects.get(pk=clock['id']).version, 3)

    def test_private_read_only_and_inaccessible_scene_clocks_cannot_be_advanced_by_id(self):
        definitions = [
            self.create(name='Private clock', playersCanEdit=True),
            self.create(name='Public read only', visibility='players'),
            self.create(name='Hidden scene clock', visibility='players', playersCanEdit=True, scopeSceneId=str(self.hidden_scene.pk)),
            self.create(name='Other scene clock', visibility='players', playersCanEdit=True, scopeSceneId=str(self.other_scene.pk)),
        ]
        foreign = ProgressClock.objects.create(campaign=self.foreign, name='Foreign secret clock', visibility='players', players_can_edit=True)
        for clock_id in [clock['id'] for clock in definitions] + [str(foreign.pk), str(uuid4()), 'malformed', True]:
            with self.subTest(clock_id=clock_id), self.assertRaises(MapError):
                self.command('advance', {'id': clock_id, 'version': 1, 'delta': 1}, self.player)
        for action in ('update', 'advance', 'reset', 'delete'):
            with self.subTest(action=action), self.assertRaises(MapError) as caught:
                self.command(action, {'id': str(foreign.pk), 'version': 1, **({'delta': 1} if action == 'advance' else {})})
            self.assertEqual(caught.exception.code, 'not_found')
            self.assertNotIn(foreign.name, str(caught.exception))

    def test_streamers_and_removed_members_cannot_mutate_or_replay(self):
        clock = self.create(visibility='players', playersCanEdit=True)
        for action in ('create', 'update', 'advance', 'reset', 'delete'):
            with self.subTest(action=action), self.assertRaises(JournalError):
                self.command(action, {'name': 'Read only'} if action == 'create' else {
                    'id': clock['id'], 'version': 1, **({'delta': 1} if action == 'advance' else {}),
                }, self.streamer)
        with self.assertRaises(JournalError):
            self.state(self.outsider)
        request_id = uuid4()
        self.command('advance', {'id': clock['id'], 'version': 1, 'delta': 1}, self.player, request_id)
        Membership.objects.filter(campaign=self.campaign, user=self.player).delete()
        with self.assertRaises(JournalError):
            self.command('advance', {'id': clock['id'], 'version': 1, 'delta': 1}, self.player, request_id)

    def test_revisions_are_explicit_strict_and_concurrent_edits_cannot_overwrite(self):
        clock = self.create()
        for version in (None, True, 1.0, '1', 0, 2):
            with self.subTest(version=version), self.assertRaises(MapError) as caught:
                self.command('advance', {'id': clock['id'], 'version': version, 'delta': 1})
            self.assertEqual(caught.exception.code, 'conflict')
        first = self.command('advance', {'id': clock['id'], 'version': 1, 'delta': 1})
        with self.assertRaises(MapError) as caught:
            self.command('update', {'id': clock['id'], 'version': 1, 'name': 'Lost update'})
        self.assertEqual(caught.exception.code, 'conflict')
        self.assertEqual(ProgressClock.objects.get(pk=clock['id']).value, first['clock']['value'])

    def test_unknown_actions_fields_and_malformed_identifiers_do_not_create_receipts(self):
        clock = self.create()
        before = ClockReceipt.objects.count()
        for action, payload in (
            ('unknown', {}), ('advance', {'id': clock['id'], 'version': 1}),
            ('delete', {'id': clock['id'], 'version': 1, 'force': True}),
            ('reset', {'id': clock['id'], 'version': 1, 'value': 0}),
            ('update', {'id': 'not-a-uuid', 'version': 1}),
        ):
            with self.subTest(action=action, payload=payload), self.assertRaises(MapError):
                self.command(action, payload)
        self.assertEqual(ClockReceipt.objects.count(), before)
        with self.assertRaises(JournalError):
            self.command('advance', {'id': clock['id'], 'version': 1, 'delta': 1}, request_id='not-a-uuid')

    def test_native_receipts_replay_once_and_publish_only_after_commit_without_private_data(self):
        request_id, changes = uuid4(), []
        def changed(sender, change, **kwargs):
            changes.append((sender, change))
        events.resource_changed.connect(changed, weak=False, dispatch_uid='clocks-once')
        self.addCleanup(events.resource_changed.disconnect, dispatch_uid='clocks-once')
        with patch('gravewright.realtime.dispatch.send') as send:
            with self.captureOnCommitCallbacks(execute=True):
                created = self.command('create', {'name': 'GM_ONLY_SECRET'}, request_id=request_id)
                self.assertFalse(send.called)
                self.assertEqual(changes, [])
            self.assertEqual(send.call_count, 1)
            self.assertEqual(send.call_args.args[1], {'type': 'room.resources', 'module': 'clocks'})
            self.assertNotIn('GM_ONLY_SECRET', str(send.call_args))
            self.assertEqual(len(changes), 1)
            self.assertEqual(changes[0][0], 'clocks')
            self.assertEqual(changes[0][1].request_id, request_id)
            send.reset_mock()
            with self.captureOnCommitCallbacks(execute=True):
                replay = self.command('create', {'name': 'GM_ONLY_SECRET'}, request_id=request_id)
            self.assertEqual(created, replay)
            self.assertFalse(send.called)
            self.assertEqual(len(changes), 1)
        self.assertEqual(ProgressClock.objects.count(), 1)
        self.assertEqual(ClockReceipt.objects.count(), 1)
        self.assertFalse(SharedReceipt.objects.exists())

    def test_outer_rollback_discards_clock_receipt_and_notifications(self):
        with patch('gravewright.realtime.dispatch.send') as send:
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError), transaction.atomic():
                    self.create(name='Rolled back')
                    raise RuntimeError('Synthetic rollback')
            self.assertFalse(send.called)
        self.assertFalse(ProgressClock.objects.exists())
        self.assertFalse(ClockReceipt.objects.exists())

    def test_receipts_do_not_return_private_gm_snapshots_after_role_downgrade(self):
        request_id = uuid4()
        payload = {'name': 'PRIVATE_RECEIPT'}
        self.command('create', payload, request_id=request_id)
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role='player')
        with self.assertRaises(MapError):
            self.command('create', payload, request_id=request_id)
        self.assertEqual(self.state()['clocks'], [])

    def test_clock_and_native_receipts_use_separate_namespaces_in_both_collision_orders(self):
        from api import cards
        for clock_first in (False, True):
            with self.subTest(clock_first=clock_first):
                request_id = uuid4()
                native_payload = {'name': 'Native deck', 'cards': ['Synthetic ace']}
                clock_payload = {'name': 'PRIVATE_CLOCK_CACHE'}
                def native():
                    return cards.command(self.campaign.pk, self.gm.pk, 'create', native_payload, request_id)
                def progress():
                    return self.command('create', clock_payload, request_id=request_id)
                if clock_first:
                    clock_result, native_result = progress(), native()
                else:
                    native_result, clock_result = native(), progress()
                self.assertEqual(progress(), clock_result)
                self.assertEqual(native(), native_result)
                self.assertNotEqual(clock_result['id'], native_result['id'])
                self.assertEqual(ClockReceipt.objects.filter(request_id=request_id).get().result, clock_result)
                self.assertEqual(SharedReceipt.objects.filter(request_id=request_id).get().result, native_result)
                self.assertNotIn('PRIVATE_CLOCK_CACHE', str(native_result))

    def test_shared_receipts_cannot_skip_clock_validation_and_private_clock_receipts_cannot_replay_elsewhere(self):
        from api import resources
        request_id = uuid4()
        SharedReceipt.objects.create(campaign=self.campaign, user=self.gm, request_id=request_id,
                                     result={'id': 'unrelated-resource', 'unrelated': True})
        with self.assertRaises(MapError):
            self.command('create', {'name': 'Invalid', 'segments': True}, request_id=request_id)
        self.assertFalse(ClockReceipt.objects.exists())
        private_request = uuid4()
        self.command('create', {'name': 'PRIVATE_CLOCK_CACHE'}, request_id=private_request)
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role='player')
        with self.assertRaises(MapError):
            resources.command(self.campaign.pk, self.gm.pk, 'items', 'create',
                              {'name': 'Different domain', 'type': 'unused'}, private_request)
        self.assertFalse(SharedReceipt.objects.filter(request_id=private_request).exists())

    def test_player_retry_rechecks_current_visibility_editability_and_scene_access(self):
        for changed in ('hidden', 'read_only', 'different_broadcast', 'deleted'):
            with self.subTest(changed=changed):
                Broadcast.objects.filter(campaign=self.campaign).update(scene=self.scene)
                clock = self.create(visibility='players', playersCanEdit=True, scopeSceneId=str(self.scene.pk))
                request_id = uuid4()
                payload = {'id': clock['id'], 'version': 1, 'delta': 1}
                advanced = self.command('advance', payload, self.player, request_id)
                self.assertEqual(self.command('advance', payload, self.player, request_id), advanced)
                if changed == 'hidden':
                    self.command('update', {'id': clock['id'], 'version': 2, 'visibility': 'gm'})
                elif changed == 'read_only':
                    self.command('update', {'id': clock['id'], 'version': 2, 'playersCanEdit': False})
                elif changed == 'different_broadcast':
                    Broadcast.objects.filter(campaign=self.campaign).update(scene=self.other_scene)
                else:
                    self.command('delete', {'id': clock['id'], 'version': 2})
                with self.assertRaises(MapError):
                    self.command('advance', payload, self.player, request_id)

    def test_portable_validation_is_pure_and_database_constraints_reject_invalid_counters(self):
        fields = {**service.DEFAULT_FIELDS, 'name': 'Portable clock'}
        with self.assertNumQueries(0):
            self.assertEqual(service.validate_clock_fields(fields), fields)
        for invalid in ({**fields, 'value': True}, {**fields, 'segments': 1}, {**fields, 'value': 5},
                        {**fields, 'players_can_edit': True}, {**fields, 'pinned': 'yes'}):
            with self.subTest(invalid=invalid), self.assertRaises(MapError):
                service.validate_clock_fields(invalid)
        for invalid in ({'segments': 1}, {'segments': 25}, {'segments': 4, 'value': 5}, {'visibility': 'unknown'}):
            with self.subTest(invalid=invalid), self.assertRaises(IntegrityError), transaction.atomic():
                ProgressClock.objects.create(campaign=self.campaign, name='Bad persisted clock', **invalid)

    def test_descriptions_preserve_authored_text_and_follow_clock_visibility_and_gm_configuration(self):
        authored = '  Expedition notes: ' + str(self.scene.pk) + '\n<script>Authored text, not markup</script> á  '
        private = self.create(name='Private description', description='PRIVATE_CLOCK_DESCRIPTION')
        public = self.create(name='Public description', description=authored, visibility='players', playersCanEdit=True)
        self.assertEqual(self.create(name='Older client without description')['description'], '')
        for user in (self.player, self.streamer):
            state = self.state(user)
            self.assertEqual(next(row for row in state['clocks'] if row['id'] == public['id'])['description'], authored)
            self.assertNotIn('PRIVATE_CLOCK_DESCRIPTION', str(state))
            self.assertNotIn(private['id'], str(state))
            with self.assertRaises(JournalError if user == self.streamer else MapError):
                self.command('update', {'id': public['id'], 'version': 1, 'description': 'Unauthorized'}, user)
        updated = self.command('update', {'id': public['id'], 'version': 1, 'name': 'Rename only'})['clock']
        self.assertEqual(updated['description'], authored)
        advanced = self.command('advance', {'id': public['id'], 'version': 2, 'delta': 1}, self.player)['clock']
        self.assertEqual(advanced['description'], authored)
        self.assertEqual(ProgressClock.objects.get(pk=public['id']).description, authored)

    def test_description_validation_rejects_invalid_candidates_atomically_and_accepts_exact_limit(self):
        public = self.create(description='x' * 4000)
        before = ClockReceipt.objects.count()
        for invalid in (None, True, 4, [], {}, 'x' * 4001):
            with self.subTest(invalid=type(invalid).__name__):
                with self.assertRaises(MapError):
                    self.create(description=invalid)
                with self.assertRaises(MapError):
                    self.command('update', {'id': public['id'], 'version': 1,
                                            'name': 'Partial rejected change', 'description': invalid})
        row = ProgressClock.objects.get(pk=public['id'])
        self.assertEqual((row.name, row.description, row.version), ('Progress', 'x' * 4000, 1))
        self.assertEqual(ClockReceipt.objects.count(), before)

    def test_scene_deletion_removes_its_clocks_and_preserves_campaign_clocks(self):
        campaign_clock = self.create()
        scene_clock = self.create(scopeSceneId=str(self.scene.pk))
        self.scene.delete()
        self.assertTrue(ProgressClock.objects.filter(pk=campaign_clock['id']).exists())
        self.assertFalse(ProgressClock.objects.filter(pk=scene_clock['id']).exists())
