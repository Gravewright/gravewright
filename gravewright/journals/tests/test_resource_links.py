"""Inline links preserve journal drafts without granting target access."""

from copy import deepcopy
import json
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase, override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext

from api import journals as api
from gravewright.actors.models import Actor
from gravewright.campaigns.models import Membership
from gravewright.journals import documents, history, links, presentations, services
from gravewright.journals.models import Access, Journal, Receipt, Revision
from gravewright.table.models import DocumentAccess, ProgressClock
from gravewright.table.tests import test_clocks as fixtures


def document(*references, secret=False):
    return {'format': documents.DOC_FORMAT, 'version': 1, 'doc': {'type': 'doc', 'content': [
        {'type': 'paragraph', 'attrs': {'visibility': 'gm' if secret else 'public'}, 'content': [
            {'type': 'gwResourceLink', 'attrs': {'reference': deepcopy(ref)}} for ref in references]}]}}


def references(value):
    return [node['attrs']['reference'] for node in links.nodes(value)]


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
                   ALLOWED_HOSTS=['testserver'])
class JournalResourceTests(TestCase):
    setUpTestData = fixtures.ProgressClockTests.__dict__['setUpTestData']

    def setUp(self):
        self.source = Journal.objects.create(campaign=self.campaign, creator=self.gm,
                                             title='Shared source', visibility='shared')
        Access.objects.create(journal=self.source, user=self.player, level='owner')
        self.actor = Actor.objects.create(campaign=self.campaign, name='Readable actor', permissions={'default': 'read'})
        self.ref = {'kind': 'actor', 'id': str(self.actor.pk)}

    def who(self, user=None):
        return services.member(self.campaign.pk, (user or self.gm).pk)

    def save(self, data, user=None, *, version=None, request_id=None):
        self.source.refresh_from_db()
        return api.command(self.campaign.pk, (user or self.gm).pk, 'update', {
            'journal_id': str(self.source.pk), 'version': version if version is not None else self.source.version,
            'title': self.source.title, 'data': data}, request_id or uuid4())

    def view(self, user=None):
        self.source.refresh_from_db()
        return services.projection(self.source, self.who(user))

    def test_canonical_atom_roundtrip_projects_live_metadata_and_is_renderable(self):
        self.save({'content': document({**self.ref, 'label': 'Forged display', 'key': 'untrusted'})}, self.player)
        stored = references(Journal.objects.get(pk=self.source.pk).data)
        self.assertEqual(stored, [self.ref])
        visible = references(self.view(self.player)['content_doc'])[0]
        self.assertEqual(visible['label'], self.actor.name)
        self.assertEqual(len(visible['key']), 64)
        self.assertTrue(documents.has_renderable_content(document(self.ref)))
        self.actor.name = 'Changed live title'; self.actor.save()
        self.assertEqual(references(self.view(self.player)['content_doc'])[0]['label'], 'Changed live title')
        self.assertNotIn('Changed live title', str(Journal.objects.get(pk=self.source.pk).data))

    def test_private_and_foreign_new_targets_are_rejected_without_receipt_or_revision(self):
        private = Actor.objects.create(campaign=self.campaign, name='PRIVATE', permissions={'default': 'none'})
        foreign = Actor.objects.create(campaign=self.foreign, name='FOREIGN', permissions={'default': 'read'})
        for target in (private, foreign):
            with self.subTest(target=target.name), self.assertRaises(services.JournalError):
                self.save({'content': document({'kind': 'actor', 'id': str(target.pk)})}, self.player)
        self.assertEqual(Receipt.objects.count(), 0)
        self.assertEqual(Revision.objects.count(), 0)

    def test_revoked_and_deleted_links_have_only_opaque_keys_and_resave(self):
        self.save({'content': document(self.ref)}, self.player)
        key = references(self.view(self.player)['content_doc'])[0]['key']
        self.actor.permissions = {'default': 'none'}; self.actor.save()
        ref = references(self.view(self.player)['content_doc'])[0]
        self.assertEqual(ref, {'unavailable': True, 'key': key})
        self.save({'content': document(ref)}, self.player)
        self.assertEqual(references(self.source.data), [self.ref])
        self.actor.delete()
        ref = references(self.view(self.player)['content_doc'])[0]
        self.assertEqual(ref, {'unavailable': True, 'key': key})
        self.save({'content': document(ref)}, self.player)
        self.assertEqual(references(self.source.data), [self.ref])

    def test_placeholder_forgery_and_cross_journal_replay_are_rejected(self):
        self.save({'content': document(self.ref)})
        key = references(self.view(self.player)['content_doc'])[0]['key']
        for ref in ({'unavailable': True, 'key': '0' * 64},
                    {'unavailable': True, 'key': key, 'id': str(self.actor.pk)},
                    {'unavailable': 'true', 'key': key}):
            with self.subTest(ref=ref), self.assertRaises(services.JournalError):
                self.save({'content': document(ref)}, self.player)
        other = Journal.objects.create(campaign=self.campaign, creator=self.player, title='Other source')
        Access.objects.create(journal=other, user=self.player, level='owner')
        with self.assertRaises(services.JournalError):
            services.clean_data({'content': document({'unavailable': True, 'key': key})}, other, self.who(self.player))

    def test_secret_pages_and_blocks_are_filtered_before_resolution_and_survive_player_save(self):
        secret = Actor.objects.create(campaign=self.campaign, name='SECRET_TARGET', permissions={'default': 'none'})
        secret_ref = {'kind': 'actor', 'id': str(secret.pk)}
        body = document(self.ref)
        body['doc']['content'] += document(secret_ref, secret=True)['doc']['content']
        self.save({'content': body, 'sections': [{'id': 'secret-page', 'title': 'SECRET_PAGE', 'audience': 'gm',
                                                'content': document(secret_ref)}],
                   'gm': {'notes': document(secret_ref)}})
        with patch('gravewright.table.resource_links.Resolver.resolve', wraps=None) as resolve:
            resolve.return_value = {'kind': 'actor', 'id': str(self.actor.pk), 'label': 'Readable actor'}
            visible = self.view(self.player)
            self.assertEqual(resolve.call_args_list[0].args[0], self.ref)
            self.assertEqual(resolve.call_count, 1)
        self.assertNotIn(str(secret.pk), json.dumps(visible))
        self.save({'content': visible['content_doc'], 'sections': visible['editable_sections']}, self.player)
        self.assertEqual(references(self.source.data).count(secret_ref), 3)
        # Knowledge of an unseen GM-block identity cannot authorize its insertion.
        with self.assertRaises(services.JournalError):
            self.save({'content': document(secret_ref)}, self.player)

    def test_journal_self_and_cross_links_do_not_recurse_and_share_page_keys(self):
        other = Journal.objects.create(campaign=self.campaign, creator=self.gm, title='Other linked journal', visibility='shared')
        source_ref = {'kind': 'journal', 'id': str(self.source.pk)}
        other_ref = {'kind': 'journal', 'id': str(other.pk)}
        other.data = {'content': document(source_ref)}; other.save()
        self.save({'content': document(source_ref, other_ref), 'sections': [
            {'id': 'page', 'title': 'Page', 'content': document(other_ref)}]})
        state = api.state(self.campaign.pk, self.player.pk)
        source = next(row for row in state['journals'] if row['id'] == str(self.source.pk))
        self.assertEqual([row['label'] for row in references(source['content_doc'])], ['Shared source', 'Other linked journal'])
        self.assertEqual(references(source['sections']), references(source['editable_sections']))
        self.assertEqual(references(source['content_doc'])[1]['key'], references(source['sections'])[0]['key'])
        self.assertTrue(api.resources(self.campaign.pk, self.player.pk, kinds=['journal'])['resources'])

    def test_crosslinked_journal_query_cost_remains_batched_as_directory_grows(self):
        rows = [self.source]
        counts = []
        for target_count in (5, 20):
            while len(rows) < target_count:
                rows.append(Journal.objects.create(campaign=self.campaign, title=f'Linked {len(rows)}', visibility='shared'))
            for index, row in enumerate(rows):
                row.data = {'content': document({'kind': 'journal', 'id': str(rows[(index + 1) % len(rows)].pk)})}
                row.save()
            with patch.object(services, 'metadata_state', wraps=services.metadata_state) as metadata:
                with CaptureQueriesContext(connection) as queries:
                    result = api.state(self.campaign.pk, self.player.pk)
            self.assertEqual(metadata.call_count, 1)
            self.assertEqual(len(result['journals']), target_count)
            counts.append(len(queries))
        self.assertLessEqual(counts[1], counts[0] + 1)

    def test_readonly_and_denied_pages_are_preserved_without_new_target_permission(self):
        private = Actor.objects.create(campaign=self.campaign, name='PRIVATE_PAGE_TARGET', permissions={'default': 'none'})
        ref = {'kind': 'actor', 'id': str(private.pk)}
        self.save({'sections': [
            {'id': 'readonly', 'title': 'Read page', 'content': document(ref)},
            {'id': 'denied', 'title': 'Denied page', 'content': document(ref)}]})
        for page, permission in (('readonly', 'read'), ('denied', 'none')):
            DocumentAccess.objects.create(campaign=self.campaign, kind='pages', resource_id=f'{self.source.pk}:{page}',
                                           grants={'default': permission})
        view = self.view(self.player)
        self.assertEqual([page['id'] for page in view['sections']], ['readonly'])
        self.save({'content': document(self.ref), 'sections': view['editable_sections']}, self.player)
        self.assertEqual(references(self.source.data).count(ref), 2)

    def test_quest_description_and_gm_notes_use_same_permission_boundary(self):
        quest = Journal.objects.create(campaign=self.campaign, creator=self.gm, title='Quest', type='quest', visibility='shared')
        Access.objects.create(journal=quest, user=self.player, level='owner')
        data = services.clean_data({'status': 'active', 'public': {'description': document(self.ref)},
                                    'gm': {'notes': document(self.ref)}}, quest, self.who())
        quest.data = data; quest.save()
        view = services.projection(quest, self.who(self.player))
        self.assertEqual(len(references(view)), 1)
        self.assertEqual(references(view)[0]['label'], self.actor.name)

    def test_streamer_reads_and_denied_writes_and_membership_revocation(self):
        self.save({'content': document(self.ref)})
        self.assertEqual(references(self.view(self.streamer)['content_doc'])[0]['label'], self.actor.name)
        with self.assertRaises(services.JournalError):
            self.save({'content': document(self.ref)}, self.streamer)
        Membership.objects.filter(campaign=self.campaign, user=self.player).delete()
        with self.assertRaises(services.JournalError):
            api.resources(self.campaign.pk, self.player.pk)

    def test_invalid_atoms_are_rejected_and_limit_enforced(self):
        invalid = [None, [], {'kind': 'actor', 'id': '../private'}, {**self.ref, 'html': '<script>'},
                   {'kind': 'journal-page', 'id': str(self.source.pk)},
                   {'kind': ['actor'], 'id': str(self.actor.pk)}]
        for ref in invalid:
            with self.subTest(ref=ref), self.assertRaises(services.JournalError):
                self.save({'content': document(ref)})
        with self.assertRaises(services.JournalError):
            self.save({'content': document(*([self.ref] * 513))})

    def test_final_link_limit_includes_preserved_secrets_and_rejects_atomically(self):
        hidden = Actor.objects.create(campaign=self.campaign, name='PRIVATE_PRESERVED', permissions={'default': 'none'})
        hidden_ref = {'kind': 'actor', 'id': str(hidden.pk)}
        self.save({'gm': {'notes': document(hidden_ref)}})
        before = Journal.objects.get(pk=self.source.pk)
        receipts, revisions = Receipt.objects.count(), Revision.objects.count()
        with self.assertRaisesMessage(services.JournalError, 'Use up to 512 resource references per document.'):
            self.save({'content': document(*([self.ref] * 512))}, self.player)
        stored = Journal.objects.get(pk=self.source.pk)
        self.assertEqual(stored.data, before.data)
        self.assertEqual(stored.version, before.version)
        self.assertEqual(Receipt.objects.count(), receipts)
        self.assertEqual(Revision.objects.count(), revisions)
        # The valid boundary includes the single retained secret reference.
        self.save({'content': document(*([self.ref] * 511))}, self.player)
        self.assertEqual(len(references(Journal.objects.get(pk=self.source.pk).data)), 512)

    def test_receipts_and_conflicts_preserve_canonical_links(self):
        rid, version = uuid4(), self.source.version
        result = self.save({'content': document(self.ref)}, request_id=rid, version=version)
        self.assertEqual(self.save({'content': document(self.ref)}, request_id=rid, version=version), result)
        with self.assertRaises(services.JournalError) as error:
            self.save({'content': document(self.ref)}, version=version)
        self.assertEqual(error.exception.code, 'conflict')
        self.assertEqual(Receipt.objects.count(), 1)
        self.assertEqual(references(Journal.objects.get(pk=self.source.pk).data), [self.ref])

    def test_restore_history_and_trash_retain_deleted_references_without_display_metadata(self):
        self.save({'content': document(self.ref)})
        self.source.refresh_from_db()
        history.snapshot(self.source, self.who(), force=True)
        revision = Revision.objects.filter(journal_id=self.source.pk, data__content__isnull=False).first()
        self.save({'content': document()})
        self.actor.delete()
        history.restore_revision(self.source, revision.pk, self.who())
        self.source.save()
        self.assertEqual(references(self.source.data), [self.ref])
        self.assertEqual(set(references(self.view(self.player)['content_doc'])[0]), {'unavailable', 'key'})
        source_id = self.source.pk
        history.trash(self.source, self.who())
        trashed = Revision.objects.get(journal_id=source_id, reason='delete')
        restored = history.restore_deleted(trashed.pk, self.who())
        self.assertEqual(references(restored.data), [self.ref])

    def test_presentation_grants_only_source_and_never_promotes_recipient_role(self):
        private_actor = Actor.objects.create(campaign=self.campaign, name='GM_ROLE_SECRET', permissions={'default': 'none'})
        hidden = ProgressClock.objects.create(campaign=self.campaign, name='HIDDEN_CLOCK')
        private_journal = Journal.objects.create(campaign=self.campaign, title='PRIVATE_JOURNAL')
        self.source.visibility = 'private'
        self.source.data = {'content': document(self.ref, {'kind': 'actor', 'id': str(private_actor.pk)},
                                               {'kind': 'clock', 'id': str(hidden.pk)},
                                               {'kind': 'journal', 'id': str(private_journal.pk)},
                                               {'kind': 'journal', 'id': str(self.source.pk)})}
        self.source.save()
        Access.objects.filter(journal=self.source).delete()
        event = presentations.present(self.who(), {'journal_id': str(self.source.pk)})['presentation']
        for user in (self.player, self.gm):
            _, view = presentations.resolve(presentations.ticket(event, user.pk), user.pk)
            refs = references(view['content_doc'])
            self.assertEqual(refs[0]['label'], self.actor.name)
            self.assertTrue(all(ref.get('unavailable') for ref in refs[1:4]))
            self.assertEqual(refs[4]['label'], self.source.title)
            self.assertNotIn('GM_ROLE_SECRET', json.dumps(view))
            self.assertFalse(view['can_edit'])

    def test_presentation_preserves_target_explicit_denials(self):
        target = Journal.objects.create(campaign=self.campaign, title='DENIED_JOURNAL', visibility='shared')
        DocumentAccess.objects.create(campaign=self.campaign, kind='journals', resource_id=str(target.pk),
                                       grants={'default': 'none'})
        self.save({'content': document({'kind': 'journal', 'id': str(target.pk)})})
        event = presentations.present(self.who(), {'journal_id': str(self.source.pk)})['presentation']
        _, view = presentations.resolve(presentations.ticket(event, self.player.pk), self.player.pk)
        self.assertTrue(references(view['content_doc'])[0]['unavailable'])

    def test_page_presentation_limits_source_metadata_and_resolution_to_ticket_page(self):
        page_ref = {'kind': 'journal-page', 'id': str(self.source.pk), 'pageId': 'other'}
        self.source.data = {'content': document(self.ref), 'sections': [
            {'id': 'presented', 'title': 'Presented page', 'content': document(page_ref)},
            {'id': 'other', 'title': 'OUTSIDE_TICKET_PAGE', 'content': document(self.ref)}]}
        self.source.visibility = 'private'; self.source.save()
        Access.objects.filter(journal=self.source).delete()
        event = presentations.present(self.who(), {'journal_id': str(self.source.pk), 'page_id': 'presented'})['presentation']
        with patch('gravewright.table.resource_links.Resolver.resolve', return_value=None) as resolve:
            _, view = presentations.resolve(presentations.ticket(event, self.player.pk), self.player.pk)
            self.assertEqual(resolve.call_count, 2)  # The same page in reader/editable projections.
            self.assertTrue(all(call.args[0] == page_ref for call in resolve.call_args_list))
        _, view = presentations.resolve(presentations.ticket(event, self.player.pk), self.player.pk)
        self.assertEqual([page['id'] for page in view['sections']], ['presented'])
        self.assertTrue(references(view['sections'])[0]['unavailable'])
        self.assertNotIn('OUTSIDE_TICKET_PAGE', json.dumps(view))

    def test_presentations_do_not_scan_raw_sheet_secrets_for_reusable_asset_metadata(self):
        from gravewright.actors.models import Asset
        asset = Asset.objects.create(campaign=self.campaign, name='PRIVATE_REUSABLE_ASSET', kind='pdf', file='synthetic.pdf')
        self.actor.data = {'gm': {'privateAsset': str(asset.pk)}}; self.actor.save()
        self.source.data = {'content': document({'kind': 'actor-asset', 'id': str(asset.pk)})}; self.source.save()
        event = presentations.present(self.who(), {'journal_id': str(self.source.pk)})['presentation']
        with patch('gravewright.actors.services.sheet', return_value={'data': {'public': 'text'}}):
            for user in (self.player, self.gm):
                _, view = presentations.resolve(presentations.ticket(event, user.pk), user.pk)
                self.assertTrue(references(view['content_doc'])[0]['unavailable'])
                self.assertNotIn(asset.name, json.dumps(view))

    def test_http_catalog_and_resolve_validate_queries_and_private_no_store(self):
        base = f'/api/containers/{self.campaign.pk}/journals'
        self.assertEqual(self.client.get(base + '/resources').status_code, 403)
        self.client.force_login(self.player)
        for kinds in ('actor', '["actor"]'):
            response = self.client.get(base + '/resources', {'kinds': kinds, 'query': 'Readable'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['resources'][0]['id'], str(self.actor.pk))
            self.assertIn('no-store', response['Cache-Control'])
        response = self.client.get(base + '/resolve', {'reference': json.dumps(self.ref)})
        self.assertEqual(response.json()['resource']['label'], self.actor.name)
        self.assertEqual(self.client.get(base + '/resources', {'kinds': '[]'}).json()['resources'], [])
        missing = {'kind': 'actor', 'id': str(uuid4())}
        self.assertEqual(self.client.get(base + '/resolve', {'reference': json.dumps(missing)}).json(), {'resource': None})
        for query in ({'kinds': '[true]'}, {'kinds': '["invalid"]'}, {'limit': 'true'}, {'limit': '201'}):
            self.assertEqual(self.client.get(base + '/resources', query).status_code, 400)
        self.assertEqual(self.client.get(base + '/resolve', {'reference': '{bad'}).status_code, 400)
        self.assertEqual(self.client.post(base + '/resolve', {}).status_code, 405)

    def test_streamer_http_get_can_search_and_resolve_without_post(self):
        self.client.force_login(self.streamer)
        base = f'/api/containers/{self.campaign.pk}/journals'
        self.assertEqual(self.client.get(base + '/resources', {'kinds': '["actor"]'}).status_code, 200)
        self.assertEqual(self.client.get(base + '/resolve', {'reference': json.dumps(self.ref)}).status_code, 200)

    def test_http_rejects_unknown_and_ambiguous_parameters_without_defaulting_invalid_kinds(self):
        self.client.force_login(self.player)
        base = f'/api/containers/{self.campaign.pk}/journals'
        for endpoint, query in (
            ('resources', {'userId': str(self.gm.pk)}),
            ('resources', {'query': ['Readable', 'Private']}),
            ('resources', {'limit': ['1', '80']}),
            ('resources', {'sceneId': [str(self.scene.pk), str(self.hidden_scene.pk)]}),
            ('resources', {'kinds': 'null'}),
            ('resources', {'kinds': '[null]'}),
            ('resources', {'kinds': '[["actor"]]'}),
            ('resources', {'kinds': '["actor","actor"]'}),
            ('resources', {'kinds': ['actor', 'invalid']}),
            ('resolve', {'reference': json.dumps(self.ref), 'kinds': 'actor'}),
            ('resolve', {'reference': [json.dumps(self.ref), json.dumps(self.ref)]}),
            ('resolve', {'reference': json.dumps(self.ref), 'sceneId': [str(self.scene.pk), str(self.scene.pk)]}),
        ):
            with self.subTest(endpoint=endpoint, query=query):
                self.assertEqual(self.client.get(base + '/' + endpoint, query).status_code, 400)
        # Repeated kinds deliberately remain supported; singleton ambiguity does not.
        response = self.client.get(base + '/resources', {'kinds': ['actor', 'journal']})
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row['kind'] for row in response.json()['resources']}, {'actor', 'journal'})
        self.assertEqual(self.client.get(base + '/resources', {'kinds': 'actor,journal'}).status_code, 200)

    def test_http_resolve_rechecks_explicit_scene_scope(self):
        self.client.force_login(self.player)
        url = f'/api/containers/{self.campaign.pk}/journals/resolve'
        self.assertEqual(self.client.get(url, {'reference': json.dumps(self.ref), 'sceneId': str(self.scene.pk)}).status_code, 200)
        for scene_id in (str(self.hidden_scene.pk), str(self.foreign_scene.pk), '../private'):
            with self.subTest(scene_id=scene_id):
                response = self.client.get(url, {'reference': json.dumps(self.ref), 'sceneId': scene_id})
                self.assertEqual(response.status_code, 400)
                self.assertNotIn(self.actor.name, response.content.decode())
