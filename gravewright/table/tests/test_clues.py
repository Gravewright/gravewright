"""Clue discoveries filter private data and preserve native command guarantees."""

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from api import cards, clocks, clues, events, resources
from api.errors import JournalError, MapError
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership, StreamerLink
from gravewright.maps.models import Broadcast, Receipt as SharedReceipt, Scene
from gravewright.table import clues as service
from gravewright.table.models import ClueReceipt, ClockReceipt, DocumentAccess, ProgressClue, ProgressClock


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class ProgressClueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gm = User.objects.create(email='clue-gm@example.test', name='GM', role='owner')
        cls.player = User.objects.create(email='clue-player@example.test', name='Player')
        cls.streamer = User.objects.create(email='clue-stream@example.test', name='Streamer')
        cls.outsider = User.objects.create(email='clue-outsider@example.test', name='Outsider')
        cls.campaign = Campaign.objects.create(owner=cls.gm, name='Clue campaign')
        cls.foreign = Campaign.objects.create(owner=cls.gm, name='Other clue campaign')
        for campaign in (cls.campaign, cls.foreign):
            Membership.objects.create(campaign=campaign, user=cls.gm, role='gm')
        Membership.objects.create(campaign=cls.campaign, user=cls.player, role='player')
        Membership.objects.create(campaign=cls.campaign, user=cls.streamer, role='streamer')
        StreamerLink.objects.create(campaign=cls.campaign, guest=cls.streamer, digest='synthetic-clue-stream-link',
                                    expires_at=timezone.now() + timedelta(hours=1))
        cls.scene = Scene.objects.create(campaign=cls.campaign, name='Broadcast scene', width=500, height=500)
        cls.hidden_scene = Scene.objects.create(campaign=cls.campaign, name='GM scene', visibility='gm', width=500, height=500)
        cls.other_scene = Scene.objects.create(campaign=cls.campaign, name='Other scene', width=500, height=500)
        cls.foreign_scene = Scene.objects.create(campaign=cls.foreign, name='Foreign scene', width=500, height=500)
        Broadcast.objects.create(campaign=cls.campaign, scene=cls.scene)

    def command(self, action, payload, user=None, request_id=None):
        return clues.command(self.campaign.pk, (user or self.gm).pk, action, payload, request_id or uuid4())

    def create(self, **fields):
        return self.command('create', {'name': 'Discovery', **fields})['clue']

    def state(self, user=None, target=None):
        return clues.state(self.campaign.pk, (user or self.gm).pk, target.pk if target else None)

    def test_public_projection_requires_completion_and_visibility_and_never_contains_gm_notes(self):
        partial = self.create(name='UNDISCOVERED_SECRET', content='UNREVEALED_CONTENT', value=3, gmNotes='GM_NOTE_A')
        hidden = self.create(name='HIDDEN_COMPLETE_SECRET', visibility='gm', value=4, gmNotes='GM_NOTE_B')
        public = self.create(content='Revealed clue', gmNotes='NEVER_PUBLIC_NOTES', value=4, pinned=True)
        local = self.create(name='Scene discovery', scopeSceneId=str(self.scene.pk), value=4, gmNotes='LOCAL_GM_NOTES')
        self.create(name='Other scene discovery', scopeSceneId=str(self.other_scene.pk), value=4)
        ProgressClue.objects.create(campaign=self.foreign, name='FOREIGN_SECRET', value=4)
        self.assertEqual({row['id'] for row in self.state()['clues']}, {partial['id'], hidden['id'], public['id']})
        for user in (self.player, self.streamer):
            state = self.state(user, self.scene)
            self.assertEqual({row['id'] for row in state['clues']}, {public['id'], local['id']})
            self.assertFalse(state['is_gm'])
            self.assertEqual(state['sceneId'], str(self.scene.pk))
            for row in state['clues']:
                self.assertTrue(row['discovered'])
                self.assertFalse(row['canEdit'] or row['canConfigure'])
                self.assertNotIn('gmNotes', row)
                self.assertNotIn('gm_notes', row)
            for secret in ('UNDISCOVERED_SECRET', 'UNREVEALED_CONTENT', 'HIDDEN_COMPLETE_SECRET', 'GM_NOTE', 'FOREIGN_SECRET'):
                self.assertNotIn(secret, str(state))
        gm = self.state(target=self.scene)
        self.assertTrue(all(row['canEdit'] and row['canConfigure'] and 'gmNotes' in row for row in gm['clues']))

    def test_scene_access_still_requires_broadcast_visibility_and_document_grants(self):
        self.create(value=4)
        for user, target in ((self.player, self.hidden_scene), (self.player, self.other_scene),
                             (self.gm, self.foreign_scene), (self.streamer, self.other_scene)):
            with self.subTest(user=user.name, scene=target.name), self.assertRaises(MapError):
                self.state(user, target)
        DocumentAccess.objects.create(campaign=self.campaign, kind='scenes', resource_id=str(self.scene.pk),
                                      grants={'default': 'none'})
        with self.assertRaises(MapError):
            self.state(self.player, self.scene)
        with self.assertRaises(JournalError):
            self.state(self.outsider)

    def test_defaults_authored_content_and_context_are_preserved_without_implicit_scope_moves(self):
        clue = self.create(sceneId=str(self.scene.pk), mapId=str(self.scene.pk))
        self.assertEqual({key: clue[key] for key in service.CONFIG_FIELDS}, {**service.DEFAULT_FIELDS, 'name': 'Discovery'})
        self.assertFalse(clue['discovered'])
        self.assertIsNone(clue['sceneId'])
        clue = self.command('update', {'id': clue['id'], 'version': 1, 'name': '  Renamed  ',
                                      'sceneId': str(self.scene.pk), 'content': '  Authored\ntext  ',
                                      'gmNotes': '  Exact private notes  '})['clue']
        self.assertIsNone(clue['sceneId'])
        self.assertEqual((clue['name'], clue['content'], clue['gmNotes']), ('Renamed', '  Authored\ntext  ', '  Exact private notes  '))
        one = self.create(segments=1, value=1, content='x' * 4000, gmNotes='y' * 4000)
        self.assertTrue(one['discovered'])

    def test_strict_configuration_validation_rejects_bad_types_limits_unknown_fields_and_foreign_scopes(self):
        invalid = [{'segments': value} for value in (True, 2.0, '4', 0, 25, None)]
        invalid += [{'value': value} for value in (True, 1.0, '1', -1, 5)]
        invalid += [{'pinned': value} for value in (0, 1, 'false', None)]
        invalid += [{key: value} for key in ('content', 'gmNotes') for value in (None, True, {}, 'x' * 4001)]
        invalid += [{'name': ''}, {'name': ' '}, {'name': None}, {'name': 'x' * 121}, {'color': 'red'},
                    {'visibility': []}, {'visibility': 'streamers'}, {'gm_notes': 'unknown'}, {'playersCanEdit': True},
                    {'scopeSceneId': str(self.foreign_scene.pk)}, {'scopeSceneId': True}, {'scopeSceneId': ''},
                    {'sceneId': str(self.foreign_scene.pk)}, {'sceneId': str(self.scene.pk), 'mapId': None},
                    {'id': str(uuid4())}, {'version': 1}]
        for fields in invalid:
            with self.subTest(fields=fields), self.assertRaises(MapError):
                self.create(**fields)
        self.assertFalse(ProgressClue.objects.exists())
        self.assertFalse(ClueReceipt.objects.exists())

    def test_limit_counts_all_clue_scopes_but_is_independent_from_clocks_and_other_campaigns(self):
        ProgressClue.objects.bulk_create([
            ProgressClue(campaign=self.campaign, scene=self.hidden_scene if index % 2 else None, name=f'Clue {index}')
            for index in range(127)
        ] + [ProgressClue(campaign=self.foreign, name=f'Other clue {index}') for index in range(128)])
        ProgressClock.objects.bulk_create([ProgressClock(campaign=self.campaign, name=f'Clock {index}') for index in range(128)])
        last = self.create(scopeSceneId=str(self.scene.pk))
        with self.assertRaises(MapError):
            self.create(scopeSceneId=str(self.other_scene.pk))
        self.assertEqual(self.command('update', {'id': last['id'], 'version': 1, 'name': 'Still editable'})['version'], 2)

    def test_reveal_hide_reset_and_bounded_advancement_preserve_separate_visibility_and_progress(self):
        clue = self.create(value=2, visibility='gm')
        for action, extra, expected in (
            ('advance', {'delta': 24}, (4, 'gm', True)), ('advance', {'delta': -24}, (0, 'gm', False)),
            ('reveal', {}, (4, 'players', True)), ('hide', {}, (4, 'gm', True)),
            ('reset', {}, (0, 'gm', False)), ('reveal', {}, (4, 'players', True)),
            ('reset', {}, (0, 'players', False)),
        ):
            clue = self.command(action, {'id': clue['id'], 'version': clue['version'], **extra})['clue']
            self.assertEqual((clue['value'], clue['visibility'], clue['discovered']), expected)
            self.assertEqual(len(self.state(self.player)['clues']), int(expected == (4, 'players', True)))
        for delta in (True, 1.0, '1', -25, 25, None):
            with self.subTest(delta=delta), self.assertRaises(MapError):
                self.command('advance', {'id': clue['id'], 'version': clue['version'], 'delta': delta})

    def test_segment_reduction_clamps_only_when_value_is_omitted_and_invalid_updates_are_atomic(self):
        clue = self.create(segments=12, value=10)
        clue = self.command('update', {'id': clue['id'], 'version': 1, 'segments': 1})['clue']
        self.assertEqual((clue['segments'], clue['value'], clue['discovered']), (1, 1, True))
        for changes in ({'segments': 2, 'value': 3}, {'name': 'Partial mutation', 'gmNotes': True}, {'segments': True}):
            with self.subTest(changes=changes), self.assertRaises(MapError):
                self.command('update', {'id': clue['id'], 'version': 2, **changes})
        row = ProgressClue.objects.get(pk=clue['id'])
        self.assertEqual((row.name, row.segments, row.value, row.version), ('Discovery', 1, 1, 2))

    def test_players_and_streamers_cannot_write_even_discovered_public_clues(self):
        clue = self.create(value=4)
        for user, error in ((self.player, MapError), (self.streamer, JournalError)):
            for action in ('create', 'update', 'advance', 'reset', 'delete', 'reveal', 'hide'):
                fields = {'name': 'Unauthorized'} if action == 'create' else {
                    'id': clue['id'], 'version': 1, **({'delta': 1} if action == 'advance' else {})}
                with self.subTest(user=user.name, action=action), self.assertRaises(error):
                    self.command(action, fields, user)
        self.assertEqual(ProgressClue.objects.get(pk=clue['id']).version, 1)
        self.assertEqual(ClueReceipt.objects.count(), 1)

    def test_scope_moves_are_explicit_and_commands_reject_wrong_scene_contexts_and_foreign_ids(self):
        clue = self.create(scopeSceneId=str(self.scene.pk))
        clue = self.command('update', {'id': clue['id'], 'version': 1, 'sceneId': str(self.scene.pk),
                                      'scopeSceneId': str(self.other_scene.pk)})['clue']
        self.assertEqual(clue['sceneId'], str(self.other_scene.pk))
        for action in ('update', 'advance', 'reset', 'delete', 'reveal', 'hide'):
            with self.subTest(action=action), self.assertRaises(MapError):
                self.command(action, {'id': clue['id'], 'version': 2, 'sceneId': str(self.scene.pk),
                                      **({'delta': 1} if action == 'advance' else {})})
        foreign = ProgressClue.objects.create(campaign=self.foreign, name='FOREIGN_SECRET')
        for clue_id in (str(foreign.pk), str(uuid4()), 'bad', True):
            with self.subTest(clue_id=clue_id), self.assertRaises(MapError) as rejected:
                self.command('hide', {'id': clue_id, 'version': 1})
            self.assertEqual(rejected.exception.code, 'not_found')
            self.assertNotIn(foreign.name, str(rejected.exception))
        clue = self.command('update', {'id': clue['id'], 'version': 2,
                                      'sceneId': str(self.other_scene.pk), 'scopeSceneId': None})['clue']
        self.assertIsNone(clue['sceneId'])

    def test_explicit_strict_revisions_reject_stale_concurrent_edits(self):
        clue = self.create()
        for version in (None, True, 1.0, '1', 0, 2):
            with self.subTest(version=version), self.assertRaises(MapError) as rejected:
                self.command('reveal', {'id': clue['id'], 'version': version})
            self.assertEqual(rejected.exception.code, 'conflict')
        self.command('reveal', {'id': clue['id'], 'version': 1})
        with self.assertRaises(MapError) as rejected:
            self.command('hide', {'id': clue['id'], 'version': 1})
        self.assertEqual(rejected.exception.code, 'conflict')
        self.assertEqual(ProgressClue.objects.get(pk=clue['id']).visibility, 'players')

    def test_unknown_actions_fields_and_malformed_receipts_are_rejected_without_writing(self):
        clue = self.create()
        for action, payload in (('unknown', {}), ('advance', {'id': clue['id'], 'version': 1}),
                                ('reveal', {'id': clue['id'], 'version': 1, 'value': 4}),
                                ('hide', {'id': clue['id'], 'version': 1, 'gmNotes': 'unexpected'}),
                                ('delete', {'id': clue['id'], 'version': 1, 'force': True})):
            with self.subTest(action=action), self.assertRaises(MapError):
                self.command(action, payload)
        with self.assertRaises(JournalError):
            self.command('reset', {'id': clue['id'], 'version': 1}, request_id='bad')
        self.assertEqual(ClueReceipt.objects.count(), 1)

    def test_receipt_retry_executes_once_and_notifications_wait_for_commit_without_private_payload(self):
        request_id, changes = uuid4(), []
        def changed(sender, change, **kwargs):
            changes.append((sender, change))
        events.resource_changed.connect(changed, weak=False, dispatch_uid='clues-once')
        self.addCleanup(events.resource_changed.disconnect, dispatch_uid='clues-once')
        with patch('gravewright.realtime.dispatch.send') as send:
            with self.captureOnCommitCallbacks(execute=True):
                created = self.command('create', {'name': 'PRIVATE_CLUE', 'gmNotes': 'PRIVATE_NOTES'}, request_id=request_id)
                self.assertFalse(send.called or changes)
            self.assertEqual(send.call_count, 1)
            self.assertEqual(send.call_args.args[1], {'type': 'room.resources', 'module': 'clues'})
            self.assertNotIn('PRIVATE', str(send.call_args))
            self.assertEqual((len(changes), changes[0][0], changes[0][1].request_id), (1, 'clues', request_id))
            send.reset_mock()
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.command('create', {'name': 'PRIVATE_CLUE', 'gmNotes': 'PRIVATE_NOTES'},
                                              request_id=request_id), created)
            send.assert_not_called()
        self.assertEqual((ProgressClue.objects.count(), ClueReceipt.objects.count()), (1, 1))
        self.assertFalse(SharedReceipt.objects.exists() or ClockReceipt.objects.exists())

    def test_outer_rollback_discards_progress_private_receipt_and_notifications(self):
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError), transaction.atomic():
                self.create(gmNotes='Rolled back private notes')
                raise RuntimeError('Synthetic rollback')
            send.assert_not_called()
        self.assertFalse(ProgressClue.objects.exists() or ClueReceipt.objects.exists())

    def test_downgraded_removed_or_inactive_gm_cannot_replay_private_notes(self):
        request_id, payload = uuid4(), {'name': 'Private', 'gmNotes': 'SECRET_RECEIPT_NOTES'}
        self.command('create', payload, request_id=request_id)
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role='player')
        with self.assertRaises(MapError):
            self.command('create', payload, request_id=request_id)
        Membership.objects.filter(campaign=self.campaign, user=self.gm).delete()
        with self.assertRaises(JournalError):
            self.command('create', payload, request_id=request_id)
        Membership.objects.create(campaign=self.campaign, user=self.gm, role='gm')
        User.objects.filter(pk=self.gm.pk).update(is_active=False)
        with self.assertRaises(JournalError):
            self.command('create', payload, request_id=request_id)

    def test_clue_clock_and_shared_receipts_are_isolated_in_both_collision_orders(self):
        for clue_first in (True, False):
            with self.subTest(clue_first=clue_first):
                request_id = uuid4()
                def clue():
                    return self.command('create', {'name': 'Private clue', 'gmNotes': 'SECRET_CLUE_CACHE'}, request_id=request_id)
                def clock():
                    return clocks.command(self.campaign.pk, self.gm.pk, 'create', {'name': 'Private clock'}, request_id)
                def deck():
                    return cards.command(self.campaign.pk, self.gm.pk, 'create', {'name': 'Deck', 'cards': ['Synthetic ace']}, request_id)
                if clue_first:
                    clue_result, clock_result, deck_result = clue(), clock(), deck()
                else:
                    deck_result, clock_result, clue_result = deck(), clock(), clue()
                self.assertEqual((clue(), clock(), deck()), (clue_result, clock_result, deck_result))
                self.assertEqual(len({clue_result['id'], clock_result['id'], deck_result['id']}), 3)
                self.assertEqual(ClueReceipt.objects.get(request_id=request_id).result, clue_result)
                self.assertNotIn('SECRET_CLUE_CACHE', str(clock_result) + str(deck_result))

    def test_other_resource_receipts_cannot_bypass_validation_and_clue_receipts_cannot_replay_elsewhere(self):
        request_id = uuid4()
        SharedReceipt.objects.create(campaign=self.campaign, user=self.gm, request_id=request_id, result={'unrelated': True})
        ClockReceipt.objects.create(campaign=self.campaign, user=self.gm, request_id=request_id, result={'unrelated': True})
        with self.assertRaises(MapError):
            self.command('create', {'name': 'Invalid', 'segments': True}, request_id=request_id)
        self.assertFalse(ClueReceipt.objects.exists())
        request_id = uuid4()
        self.command('create', {'name': 'Private', 'gmNotes': 'SECRET_CLUE_CACHE'}, request_id=request_id)
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role='player')
        with self.assertRaises(MapError):
            resources.command(self.campaign.pk, self.gm.pk, 'items', 'create', {'name': 'Different domain', 'type': 'unused'}, request_id)
        self.assertFalse(SharedReceipt.objects.filter(request_id=request_id).exists())

    def test_portable_validation_has_no_queries_and_database_constraints_reject_invalid_progress(self):
        fields = {**service.DEFAULT_FIELDS, 'name': 'Portable clue', 'gmNotes': 'Exact notes'}
        with self.assertNumQueries(0):
            self.assertEqual(service.validate_clue_fields(fields), fields)
        for invalid in ({'segments': 0}, {'segments': 25}, {'segments': 4, 'value': 5}, {'value': -1}, {'visibility': 'unknown'}):
            with self.subTest(invalid=invalid), self.assertRaises(IntegrityError), transaction.atomic():
                ProgressClue.objects.create(campaign=self.campaign, name='Invalid persisted clue', **invalid)

    def test_scene_deletion_removes_local_clues_and_preserves_campaign_clues(self):
        global_clue = self.create()
        scene_clue = self.create(scopeSceneId=str(self.scene.pk))
        self.scene.delete()
        self.assertTrue(ProgressClue.objects.filter(pk=global_clue['id']).exists())
        self.assertFalse(ProgressClue.objects.filter(pk=scene_clue['id']).exists())
