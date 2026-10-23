"""GM preparation records, content usages, player previews and journal history."""

import json
import uuid

from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from gravewright.accounts.models import User
from gravewright.accounts.services import AuthError
from gravewright.actors.models import Actor
from gravewright.journals import services as journals
from gravewright.journals.models import Access, BoardEntry, Journal, Revision
from gravewright.journals.services import JournalError
from gravewright.maps.models import Scene

from . import preparation
from .models import Campaign, CampaignEvent, Membership, PreparationBoard, PreparationReceipt, SessionPlan


def doc(*nodes):
    return {'format': 'gw-journal-doc-v1', 'version': 1, 'doc': {'type': 'doc', 'content': list(nodes)}}


def paragraph(text, href=None):
    node = {'type': 'text', 'text': text}
    if href:
        node['marks'] = [{'type': 'link', 'attrs': {'href': href}}]
    return {'type': 'paragraph', 'content': [node]}


class PreparationTests(TestCase):
    def setUp(self):
        self.host = User.objects.create_user('prep-host@example.test', name='Host', role='owner')
        self.gm = User.objects.create_user('prep-gm@example.test', name='Synthetic GM')
        self.player = User.objects.create_user('prep-player@example.test', name='Synthetic player')
        self.campaign = Campaign.objects.create(owner=self.host, name='Synthetic preparation campaign')
        Membership.objects.create(campaign=self.campaign, user=self.gm, role='gm')
        Membership.objects.create(campaign=self.campaign, user=self.player, role='player')
        self.scene = Scene.objects.create(campaign=self.campaign, name='Synthetic harbor', width=100, height=100)
        self.actor = Actor.objects.create(campaign=self.campaign, name='Synthetic captain', permissions={})
        self.other = Campaign.objects.create(owner=self.host, name='Other campaign')
        Membership.objects.create(campaign=self.other, user=self.gm, role='player')
        self.foreign_scene = Scene.objects.create(campaign=self.other, name='Foreign', width=10, height=10)

    def journal(self, action, payload):
        return journals.command(self.campaign.pk, self.gm.pk, action, payload, uuid.uuid4())

    def prepare(self, action, payload, user=None, request_id=None):
        return preparation.command(user or self.gm, self.campaign.pk, action, payload, request_id or uuid.uuid4())

    def test_only_current_gms_use_preparation(self):
        for user in (self.player, self.host):
            with self.assertRaises(AuthError):
                preparation.state(user, self.campaign.pk)
            with self.assertRaises(AuthError):
                self.prepare('session-create', {'title': 'Denied'}, user=user)
        response = self.client.get(reverse('campaigns:preparation', args=[self.campaign.pk]))
        self.assertEqual(response.status_code, 401)

    def test_session_plan_lifecycle_is_idempotent_and_revisioned(self):
        request = uuid.uuid4()
        created = self.prepare('session-create', {'title': 'Session one', 'scheduledFor': '2026-11-02',
                                                  'steps': [{'kind': 'scene', 'refId': str(self.scene.pk), 'label': ''},
                                                            {'kind': 'note', 'label': 'Open with the storm'}],
                                                  'checklist': [{'text': 'Print handouts'}], 'notes': 'Private twist'},
                               request_id=request)
        self.assertEqual(self.prepare('session-create', {'title': 'Retry'}, request_id=request), created)
        self.assertEqual(SessionPlan.objects.count(), 1)
        with self.assertRaises(preparation.PreparationError):
            self.prepare('session-update', {'id': created['id'], 'revision': 1,
                                            'steps': [{'kind': 'scene', 'refId': str(self.foreign_scene.pk)}]})
        state = preparation.state(self.gm, self.campaign.pk)
        session = state['sessions'][0]
        self.assertEqual(session['steps'][0]['title'], 'Synthetic harbor')
        self.assertEqual(state['pending']['session']['checklist'][0]['text'], 'Print handouts')
        finished = self.prepare('session-finish', {'id': created['id'], 'revision': 1, 'summary': 'The ship escaped.',
                                                   'pending': [{'text': 'Name the smuggler'}]})
        with self.assertRaises(preparation.PreparationError) as conflict:
            self.prepare('session-update', {'id': created['id'], 'revision': 1, 'title': 'Stale'})
        self.assertEqual(conflict.exception.status, 409)
        state = preparation.state(self.gm, self.campaign.pk)
        self.assertEqual(state['sessions'][0]['status'], 'completed')
        self.assertEqual(state['pending']['carried'][0]['text'], 'Name the smuggler')
        self.assertIsNone(state['pending']['session'])
        self.assertEqual(finished['revision'], 2)

    def test_timeline_links_and_dashboard_pins_are_validated(self):
        quest = self.journal('create', {'title': 'Find the map', 'journal_type': 'quest'})['journal_id']
        self.prepare('event-create', {'title': 'Harbor fire', 'worldDate': '3rd of Frostfall', 'date': '2026-11-09',
                                      'upcoming': True, 'links': [{'type': 'journal', 'id': quest},
                                                                  {'type': 'actor', 'id': str(self.actor.pk)}]})
        with self.assertRaises(preparation.PreparationError):
            self.prepare('event-create', {'title': 'Bad', 'links': [{'type': 'scene', 'id': str(self.foreign_scene.pk)}]})
        with self.assertRaises(preparation.PreparationError):
            self.prepare('event-create', {'title': 'Bad date', 'date': '2026-13-40'})
        self.prepare('board-update', {'revision': 0, 'pins': [{'type': 'scene', 'id': str(self.scene.pk)}],
                                      'widgets': ['pending', 'pins']})
        with self.assertRaises(preparation.PreparationError):
            self.prepare('board-update', {'revision': 0, 'widgets': ['pins']})
        state = preparation.state(self.gm, self.campaign.pk)
        self.assertEqual(state['events'][0]['links'][0]['title'], 'Find the map')
        self.assertEqual(state['board']['pins'][0]['title'], 'Synthetic harbor')
        self.assertEqual(state['board']['widgets'], ['pending', 'pins'])
        self.assertEqual([row['title'] for row in state['pending']['unassigned']], ['Find the map'])

    def test_references_list_links_and_usages(self):
        target = self.journal('create', {'title': 'Lighthouse', 'journal_type': 'diary'})['journal_id']
        source = self.journal('create', {'title': 'Session notes', 'journal_type': 'diary'})['journal_id']
        href = f'/game/{self.campaign.pk}?document=journal:{target}'
        row = Journal.objects.get(pk=source)
        self.journal('update', {'journal_id': source, 'version': row.version, 'title': row.title,
                                'data': {'content': doc(paragraph('See ', None), paragraph('Lighthouse', href),
                                                        paragraph('Captain', f'/game/{self.campaign.pk}?document=actor:{self.actor.pk}'))}})
        quest = self.journal('create', {'title': 'Rescue', 'journal_type': 'quest'})['journal_id']
        version = Journal.objects.get(pk=quest).version
        self.journal('assign', {'journal_id': quest, 'version': version, 'assignees': [str(self.actor.pk)]})
        used = preparation.references(self.gm, self.campaign.pk, 'journal', target)['usedBy']
        self.assertEqual([(row['title'], row['via']) for row in used], [('Session notes', 'link')])
        links = preparation.references(self.gm, self.campaign.pk, 'journal', source)['links']
        self.assertEqual({row['title'] for row in links}, {'Lighthouse', 'Synthetic captain'})
        actor_uses = {(row['title'], row['via']) for row in preparation.references(self.gm, self.campaign.pk, 'actor', str(self.actor.pk))['usedBy']}
        self.assertEqual(actor_uses, {('Session notes', 'link'), ('Rescue', 'assigned')})
        with self.assertRaises(preparation.PreparationError):
            preparation.references(self.gm, self.campaign.pk, 'scene', str(self.foreign_scene.pk))

    def test_connections_include_typed_journal_resources_and_pages_without_legacy_duplicates(self):
        from gravewright.items.models import Item
        item = Item.objects.create(campaign=self.campaign, name='Synthetic key', type='equipment', system_id='synthetic')
        target = self.journal('create', {'title': 'Lighthouse pages', 'journal_type': 'diary'})['journal_id']
        row = Journal.objects.get(pk=target)
        self.journal('update', {'journal_id': target, 'version': row.version, 'title': row.title,
                                'data': {'sections': [{'id': 'page', 'title': 'Tower', 'content': doc(paragraph('Tower notes'))}]}})
        source = self.journal('create', {'title': 'Typed session notes', 'journal_type': 'diary'})['journal_id']
        refs = [{'kind': 'actor', 'id': str(self.actor.pk)}, {'kind': 'item', 'id': str(item.pk)},
                {'kind': 'scene', 'id': str(self.scene.pk)}, {'kind': 'journal', 'id': target},
                {'kind': 'journal-page', 'id': target, 'pageId': 'page'}]
        typed = {'type': 'paragraph', 'content': [{'type': 'gwResourceLink', 'attrs': {'reference': ref}} for ref in refs]}
        row = Journal.objects.get(pk=source)
        self.journal('update', {'journal_id': source, 'version': row.version, 'title': row.title,
                                'data': {'content': doc(typed,
                                    paragraph('Legacy journal', f'/game/{self.campaign.pk}?document=journal:{target}'),
                                    paragraph('Legacy actor', f'/game/{self.campaign.pk}?document=actor:{self.actor.pk}'))}})
        expected = {('actor', str(self.actor.pk)), ('item', str(item.pk)),
                    ('scene', str(self.scene.pk)), ('journal', target)}
        outgoing = preparation.references(self.gm, self.campaign.pk, 'journal', source)['links']
        self.assertEqual({(link['type'], link['id']) for link in outgoing}, expected)
        self.assertEqual(len(outgoing), 4)
        self.assertTrue(all(link['title'] and not link['missing'] for link in outgoing))
        for kind, identifier in expected:
            uses = preparation.references(self.gm, self.campaign.pk, kind, identifier)['usedBy']
            self.assertEqual([(use['id'], use['via']) for use in uses], [(source, 'link')])
        for user in (self.player, self.host):
            with self.assertRaises(AuthError):
                preparation.references(user, self.campaign.pk, 'journal', source)
        with self.assertRaises(preparation.PreparationError):
            preparation.references(self.gm, self.campaign.pk, 'scene', str(self.foreign_scene.pk))

    def test_connections_skip_malformed_atoms_and_keep_foreign_titles_private(self):
        source = self.journal('create', {'title': 'Imported missing references', 'journal_type': 'diary'})['journal_id']
        # Historical/imported missing destinations remain inert; even a valid
        # foreign UUID cannot disclose its title through the campaign index.
        row = Journal.objects.get(pk=source)
        row.data = {'content': doc({'type': 'paragraph', 'content': [
            {'type': 'gwResourceLink', 'attrs': {'reference': {'kind': 'scene', 'id': str(self.foreign_scene.pk)}}},
            {'type': 'gwResourceLink', 'attrs': {'reference': {'kind': 'actor', 'id': '../bad'}}},
            {'type': 'gwResourceLink', 'attrs': {'reference': {'unavailable': True, 'key': '0' * 64}}}]}),
            'legacy': 'document=actor:------------------------------------'}
        row.save()
        result = preparation.references(self.gm, self.campaign.pk, 'journal', source)
        self.assertEqual(result['links'], [{'type': 'scene', 'id': str(self.foreign_scene.pk),
                                           'via': 'link', 'title': '', 'missing': True}])
        self.assertNotIn('Foreign', json.dumps(result))

    def test_quest_prerequisites_reject_cycles_and_survive_editor_saves(self):
        first = self.journal('create', {'title': 'First', 'journal_type': 'quest'})['journal_id']
        second = self.journal('create', {'title': 'Second', 'journal_type': 'quest'})['journal_id']
        self.journal('prerequisites', {'journal_id': second, 'version': Journal.objects.get(pk=second).version,
                                       'prerequisites': [first]})
        with self.assertRaises(JournalError):
            self.journal('prerequisites', {'journal_id': first, 'version': Journal.objects.get(pk=first).version,
                                           'prerequisites': [second]})
        row = Journal.objects.get(pk=second)
        self.journal('update', {'journal_id': second, 'version': row.version, 'title': 'Second',
                                'data': {'status': 'active', 'objectives': []}})
        self.assertEqual(Journal.objects.get(pk=second).data['prerequisites'], [first])
        state = preparation.state(self.gm, self.campaign.pk)
        self.assertEqual(state['pending']['blocked'][0]['waitingFor'], [first])
        player_view = journals.state(self.campaign.pk, self.player.pk)
        self.assertFalse(any('prerequisites' in row.get('quest', {}) for row in player_view['journals']))

    def test_view_as_returns_the_native_player_projection(self):
        shared = self.journal('create', {'title': 'Shared handout', 'journal_type': 'diary'})['journal_id']
        self.journal('create', {'title': 'GM secret', 'journal_type': 'diary'})
        self.journal('access', {'journal_id': shared, 'target_user_id': str(self.player.pk), 'access_level': 'read'})
        view = preparation.view_as(self.gm, self.campaign.pk, str(self.player.pk))
        self.assertEqual([row['title'] for row in view['journals'] if row.get('can_open')], ['Shared handout'])
        self.assertEqual(view['scenes'], [])
        with self.assertRaises(preparation.PreparationError):
            preparation.view_as(self.gm, self.campaign.pk, str(self.gm.pk))
        with self.assertRaises(AuthError):
            preparation.view_as(self.player, self.campaign.pk, str(self.player.pk))

    def test_journal_history_restores_versions_and_trash_restores_deleted_documents(self):
        jid = self.journal('create', {'title': 'Chronicle', 'journal_type': 'diary'})['journal_id']
        row = Journal.objects.get(pk=jid)
        self.journal('update', {'journal_id': jid, 'version': row.version, 'title': 'Chronicle',
                                'data': {'content': doc(paragraph('First draft'))}})
        revision = preparation.journal_history(self.gm, self.campaign.pk, jid)['revisions'][0]
        compared = preparation.compare(self.gm, self.campaign.pk, revision['id'])
        self.assertIn('First draft', compared['current']['lines'])
        self.assertNotIn('First draft', compared['revision']['lines'])
        version = Journal.objects.get(pk=jid).version
        with self.assertRaises(JournalError):
            self.journal('restore-revision', {'journal_id': jid, 'version': version - 1, 'revision_id': revision['id']})
        self.journal('restore-revision', {'journal_id': jid, 'version': version, 'revision_id': revision['id']})
        restored = Journal.objects.get(pk=jid)
        self.assertNotIn('First draft', json.dumps(restored.data))
        self.assertEqual(restored.version, version + 1)
        # Restoring is itself undoable: the replaced draft is now the latest revision.
        latest = preparation.journal_history(self.gm, self.campaign.pk, jid)['revisions'][0]
        self.assertIn('First draft', preparation.compare(self.gm, self.campaign.pk, latest['id'])['revision']['lines'])

        board = self.journal('create', {'title': 'Board', 'journal_type': 'quest_board'})['journal_id']
        quest = self.journal('create', {'title': 'Lost quest', 'journal_type': 'quest'})['journal_id']
        self.journal('board-add', {'journal_id': board, 'quest_id': quest})
        self.journal('access', {'journal_id': quest, 'target_user_id': str(self.player.pk), 'access_level': 'read'})
        self.journal('delete', {'journal_id': quest})
        self.assertFalse(Journal.objects.filter(pk=quest).exists())
        trashed = preparation.trash(self.gm, self.campaign.pk)['journals']
        self.assertEqual([row['title'] for row in trashed], ['Lost quest'])
        with self.assertRaises(JournalError):
            journals.command(self.campaign.pk, self.player.pk, 'restore-deleted', {'revision_id': trashed[0]['id']}, uuid.uuid4())
        self.journal('restore-deleted', {'revision_id': trashed[0]['id']})
        self.assertTrue(Journal.objects.filter(pk=quest, title='Lost quest').exists())
        self.assertTrue(BoardEntry.objects.filter(board_id=board, quest_id=quest).exists())
        self.assertEqual(Access.objects.get(journal_id=quest, user=self.player).level, 'read')
        self.assertFalse(Revision.objects.filter(reason='delete').exists())
        self.journal('delete', {'journal_id': quest})
        self.journal('trash-purge', {'revision_id': Revision.objects.get(reason='delete').pk})
        self.assertEqual(preparation.trash(self.gm, self.campaign.pk)['journals'], [])

    def test_http_endpoints_return_messages_and_require_csrf_safe_post(self):
        self.client.force_login(self.gm)
        url = reverse('campaigns:preparation', args=[self.campaign.pk])
        response = self.client.post(url, json.dumps({'action': 'session-create', 'payload': {'title': ''},
                                                     'request_id': str(uuid.uuid4())}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Title', response.json()['error'])
        response = self.client.post(url, json.dumps({'action': 'session-create', 'payload': {'title': 'Ok'},
                                                     'request_id': str(uuid.uuid4())}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(url).json()['sessions'][0]['title'], 'Ok')
        self.client.force_login(self.player)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_invalid_date_types_do_not_erase_saved_session_or_event_dates(self):
        session = self.prepare('session-create', {'title': 'Planned', 'scheduledFor': '2026-11-02'})
        event = self.prepare('event-create', {'title': 'Dated event', 'date': '2026-11-03'})
        before = PreparationReceipt.objects.count()
        for value in (True, False, 0, 1, 1.5, [], {}, 'not-a-date', '2026-11-02T12:00:00'):
            for action, row, field in (('session-update', session, 'scheduledFor'), ('event-update', event, 'date')):
                with self.subTest(value=value, action=action), self.assertRaises(preparation.PreparationError):
                    self.prepare(action, {'id': row['id'], 'revision': 1, field: value})
        self.assertEqual(SessionPlan.objects.get(pk=session['id']).scheduled_for.isoformat(), '2026-11-02')
        self.assertEqual(CampaignEvent.objects.get(pk=event['id']).date.isoformat(), '2026-11-03')
        self.assertEqual(PreparationReceipt.objects.count(), before)
        self.prepare('session-update', {'id': session['id'], 'revision': 1, 'scheduledFor': None})
        self.assertIsNone(SessionPlan.objects.get(pk=session['id']).scheduled_for)

    def test_malformed_dashboard_panels_return_400_and_keep_current_board_and_receipts(self):
        self.prepare('board-update', {'revision': 0, 'widgets': ['pins']})
        before = PreparationReceipt.objects.count()
        self.client.force_login(self.gm)
        url = reverse('campaigns:preparation', args=[self.campaign.pk])
        for widgets in ([{}], [['pins']], [True], ['pins', 'pins'], ['unknown'], None, {}):
            with self.subTest(widgets=widgets):
                response = self.client.post(url, {'action': 'board-update', 'payload': {'revision': 1, 'widgets': widgets},
                                                  'request_id': str(uuid.uuid4())}, content_type='application/json')
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()['code'], 'invalid_input')
        board = PreparationBoard.objects.get()
        self.assertEqual((board.widgets, board.revision), (['pins'], 1))
        self.assertEqual(PreparationReceipt.objects.count(), before)

    def test_unknown_campaign_write_returns_404_and_revoked_gm_cannot_replay(self):
        self.client.force_login(self.gm)
        response = self.client.post(reverse('campaigns:preparation', args=[uuid.uuid4()]), {
            'action': 'session-create', 'payload': {'title': 'Unknown campaign'}, 'request_id': str(uuid.uuid4()),
        }, content_type='application/json')
        self.assertEqual(response.status_code, 404, response.content)
        self.assertEqual(response.json()['code'], 'not_found')
        request_id = uuid.uuid4()
        self.prepare('session-create', {'title': 'Private plan'}, request_id=request_id)
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role='player')
        with self.assertRaises(AuthError):
            self.prepare('session-create', {'title': 'Private plan'}, request_id=request_id)
        self.assertEqual(SessionPlan.objects.count(), 1)

    def test_preparation_write_requires_actual_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.gm)
        url = reverse('campaigns:preparation', args=[self.campaign.pk])
        payload = {'action': 'session-create', 'payload': {'title': 'Protected plan'}, 'request_id': str(uuid.uuid4())}
        self.assertEqual(client.post(url, payload, content_type='application/json').status_code, 403)
        client.get(reverse('campaigns:manage', args=[self.campaign.pk]))
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        response = client.post(url, payload, content_type='application/json', **{settings.CSRF_HEADER_NAME: token})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(SessionPlan.objects.count(), 1)
