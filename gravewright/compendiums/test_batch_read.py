"""Batch reads preserve custom-pack visibility and single-document envelopes."""
import uuid
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.table import domain
from gravewright.table.models import DocumentAccess
from gravewright.maps.models import Receipt
from .models import Pack, Entry


@override_settings(
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
)
class BatchReadTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.enterContext(override_settings(MEDIA_ROOT=root / 'media', GRAVEWRIGHT_CONTENT_ROOT=root / 'content', GRAVEWRIGHT_MODULES_ROOT=root / 'modules'))
        self.gm = User.objects.create_user(email='batch-gm@example.test', name='GM', password='password', role='owner')
        self.player = User.objects.create_user(email='batch-player@example.test', name='Player', password='password')
        self.campaign = Campaign.objects.create(owner=self.gm, name='Batch compendiums')
        for user, role in ((self.gm, 'gm'), (self.player, 'player')):
            Membership.objects.create(campaign=self.campaign, user=user, role=role)
        self.pack = Pack.objects.create(campaign=self.campaign, name='Private')
        self.entries = [Entry.objects.create(pack=self.pack, name='Item ' + str(n), kind='item', data={'type': 'gear', 'data': {'nested': {'number': n}}}) for n in range(2)]

    def read(self, ids=None, user=None, **extra):
        return domain.command(self.campaign.pk, (user or self.gm).pk, 'compendiums', 'read',
                              {'packId': str(self.pack.pk), **({'ids': ids} if ids is not None else {}), **extra}, uuid.uuid4())

    def test_batch_documents_equal_single_reads_and_preserve_requested_order(self):
        ids = [str(entry.pk) for entry in reversed(self.entries)]
        expected = [self.read(id=value) for value in ids]
        result = self.read(ids)
        self.assertEqual(result, {'entries': expected})
        result['entries'][0]['data']['data']['nested']['number'] = 999
        self.assertEqual(self.read(id=ids[0])['data']['data']['nested']['number'], 1)

    def test_private_shared_and_explicit_denial_use_the_same_read_permissions(self):
        ids = [str(self.entries[0].pk)]
        with self.assertRaises(domain.MapError) as denied:
            self.read(ids, self.player)
        self.assertEqual(denied.exception.code, 'not_found')
        self.pack.shared = True
        self.pack.save(update_fields=['shared'])
        self.assertEqual(self.read(ids, self.player)['entries'][0]['id'], ids[0])
        DocumentAccess.objects.create(campaign=self.campaign, kind='compendiums', resource_id=str(self.pack.pk), grants={'default': 'read', 'player': 'none'})
        with self.assertRaises(domain.MapError) as denied:
            self.read(ids, self.player)
        self.assertEqual(denied.exception.code, 'not_found')

    def test_invalid_duplicate_missing_and_other_pack_ids_never_return_partial_results(self):
        valid = str(self.entries[0].pk)
        for ids in ([], 'wrong', {}, [True], [''], ['not-a-uuid'], [valid, valid], [valid, valid.upper()], [str(uuid.uuid4()) for _ in range(101)]):
            with self.subTest(ids=ids), self.assertRaises(domain.MapError) as invalid:
                self.read(ids)
            self.assertEqual(invalid.exception.code, 'invalid_data')
        other_pack = Pack.objects.create(campaign=self.campaign, name='Other')
        other = Entry.objects.create(pack=other_pack, name='Other item', kind='item')
        for absent in (str(uuid.uuid4()), str(other.pk)):
            with self.assertRaises(domain.MapError) as missing:
                self.read([valid, absent])
            self.assertEqual(missing.exception.code, 'not_found')
        with self.assertRaises(domain.MapError) as invalid:
            self.read([valid], id=valid)
        self.assertEqual(invalid.exception.code, 'invalid_data')

    def test_batch_limit_accepts_one_hundred_unique_ids(self):
        Entry.objects.bulk_create([Entry(pack=self.pack, name='Extra ' + str(n), kind='item', data={'number': n}) for n in range(98)])
        ids = [str(value) for value in self.pack.entries.order_by('name').values_list('pk', flat=True)]
        self.assertEqual(len(ids), 100)
        self.assertEqual([entry['id'] for entry in self.read(ids)['entries']], ids)

    def test_reads_create_no_receipts_or_notifications_and_recheck_revoked_access_on_retry(self):
        self.pack.shared = True
        self.pack.save(update_fields=['shared'])
        request_id = uuid.uuid4()
        payload = {'packId': str(self.pack.pk), 'ids': [str(self.entries[0].pk)]}
        with patch('gravewright.realtime.dispatch.changed') as changed:
            result = domain.command(self.campaign.pk, self.player.pk, 'compendiums', 'read', payload, request_id)
            self.assertEqual(result['entries'][0]['id'], payload['ids'][0])
            changed.assert_not_called()
        self.assertEqual(Receipt.objects.count(), 0)
        # Legacy read receipts must not authorize a later read after revocation.
        Receipt.objects.create(campaign=self.campaign, user=self.player, request_id=request_id, result=result)
        self.pack.shared = False
        self.pack.save(update_fields=['shared'])
        with self.assertRaises(domain.MapError) as denied:
            domain.command(self.campaign.pk, self.player.pk, 'compendiums', 'read', payload, request_id)
        self.assertEqual(denied.exception.code, 'not_found')

    def test_other_campaign_pack_is_not_readable(self):
        other = Campaign.objects.create(owner=self.gm, name='Other campaign')
        foreign = Pack.objects.create(campaign=other, name='Foreign', shared=True)
        with self.assertRaises(domain.MapError) as denied:
            self.read([str(self.entries[0].pk)], packId=str(foreign.pk))
        self.assertEqual(denied.exception.code, 'not_found')

    def test_metadata_index_rechecks_database_pack_permissions_and_omits_bodies(self):
        def index():
            return domain.state(self.campaign.pk,self.player.pk,'compendiums')['packs']

        self.assertEqual(index(), [])
        access = DocumentAccess.objects.create(campaign=self.campaign, kind='compendiums',
            resource_id=str(self.pack.pk), grants={'player':'read'})
        packs = index()
        self.assertEqual(len(packs), 1)
        self.assertEqual({entry['type'] for entry in packs[0]['entries']}, {'gear'})
        for entry in packs[0]['entries']:
            self.assertEqual(set(entry), {'id','name','kind','type','version'})
        access.grants = {'player':'none'}
        access.save(update_fields=['grants'])
        self.assertEqual(index(), [])
        with self.assertRaises(domain.MapError):
            self.read([str(self.entries[0].pk)],self.player)
