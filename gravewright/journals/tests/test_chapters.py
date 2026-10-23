"""Independent chapter trees retain legacy pages and native journal privacy."""

from copy import deepcopy
from uuid import uuid4

from django.test import TestCase, override_settings

from gravewright.journals import data, history, services
from gravewright.journals.models import Access, Journal, Receipt, Revision
from gravewright.table.models import DocumentAccess
from gravewright.table.tests import test_clocks as fixtures


def chapter(identifier, name=None, parent=None, order=10):
    return {'id': identifier, 'name': name or identifier, 'parentId': parent, 'sortOrder': order}


def page(identifier, chapter_id=None, **fields):
    return {'id': identifier, 'title': identifier, 'chapterId': chapter_id, **fields}


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class ChapterTests(TestCase):
    setUpTestData = fixtures.ProgressClockTests.__dict__['setUpTestData']

    def setUp(self):
        self.journal = Journal.objects.create(campaign=self.campaign, creator=self.gm,
                                              title='Chapter journal', visibility='shared')
        Access.objects.create(journal=self.journal, user=self.player, level='owner')

    def who(self, user=None):
        return services.member(self.campaign.pk, (user or self.gm).pk)

    def save(self, value, user=None, *, version=None):
        self.journal.refresh_from_db()
        return services.command(self.campaign.pk, (user or self.gm).pk, 'update', {
            'journal_id': str(self.journal.pk), 'title': self.journal.title,
            'version': self.journal.version if version is None else version, 'data': value}, uuid4())

    def view(self, user=None):
        self.journal.refresh_from_db()
        return services.projection(self.journal, self.who(user))

    def test_empty_chapters_and_subchapters_persist_without_any_page(self):
        tree = [chapter('root', 'Empty root'), chapter('child', 'Empty child', 'root')]
        self.save({'chapters': tree, 'sections': []})
        stored = Journal.objects.get(pk=self.journal.pk).data
        self.assertEqual(stored['chapters'], tree)
        self.assertEqual(stored['sections'], [])
        for user in (self.gm, self.player, self.streamer):
            self.assertEqual(self.view(user)['chapters'], tree)
        self.assertIn('## Chapter: Empty root / Empty child', history.readable(self.journal.title, 'diary', stored))

    def test_each_page_has_one_chapter_or_none_and_category_is_only_a_mirror(self):
        self.save({'chapters': [chapter('root', 'First'), chapter('child', 'Second', 'root')],
                   'sections': [page('one', 'child', category='Stale different name'),
                                page('two', None, category='Must not reassign')]})
        stored = Journal.objects.get(pk=self.journal.pk).data
        self.assertEqual([(row['chapterId'], row['category']) for row in stored['sections']], [('child', 'Second'), (None, '')])
        self.assertEqual(len(stored['chapters']), 2)
        stored['sections'][0]['chapterId'] = 'root'
        self.save(stored)
        self.assertEqual(self.view()['sections'][0]['category'], 'First')

    def test_legacy_categories_gain_deterministic_chapters_without_writing_on_read(self):
        legacy = {'sections': [{'id': 'a', 'category': 'Old chapter'}, {'id': 'b', 'category': 'Old chapter'},
                               {'id': 'c', 'category': ''}]}
        self.journal.data = legacy; self.journal.save()
        first, second = self.view(), self.view()
        self.assertEqual(first['chapters'], second['chapters'])
        self.assertEqual(first['chapters'][0]['id'], data.legacy_chapter_id('Old chapter'))
        self.assertEqual([row['chapterId'] for row in first['sections']],
                         [first['chapters'][0]['id'], first['chapters'][0]['id'], None])
        self.assertEqual(Journal.objects.get(pk=self.journal.pk).data, legacy)
        self.save(legacy)
        self.assertEqual(Journal.objects.get(pk=self.journal.pk).data['chapters'], first['chapters'])

    def test_legacy_client_omission_keeps_empty_chapters_and_adds_new_categories(self):
        self.save({'chapters': [chapter('empty', 'Independent empty')], 'sections': []})
        for user in (self.gm, self.player):
            self.save({'sections': [{'id': 'old-page', 'category': 'Legacy added chapter'}]}, user)
            names = {row['name'] for row in self.view(user)['chapters']}
            self.assertEqual(names, {'Independent empty', 'Legacy added chapter'})
        self.save({'sections': []}, self.player)
        self.assertEqual(len(self.view(self.player)['chapters']), 2)

    def test_names_of_chapters_containing_only_hidden_pages_are_filtered(self):
        self.save({'chapters': [chapter('visible-root', 'Visible root'), chapter('visible-child', 'Visible child', 'visible-root'),
                               chapter('hidden-root', 'SECRET_ROOT'), chapter('hidden-child', 'SECRET_CHILD', 'hidden-root'),
                               chapter('empty', 'Public empty')],
                   'sections': [page('visible-page', 'visible-child'), page('private-page', 'hidden-child', audience='gm')]})
        expected = {'visible-root', 'visible-child', 'empty'}
        for user in (self.player, self.streamer):
            view = self.view(user)
            self.assertEqual({row['id'] for row in view['chapters']}, expected)
            self.assertNotIn('SECRET_', str(view))
        self.assertEqual(len(self.view()['chapters']), 5)

    def test_explicit_page_denials_filter_chapter_paths_without_hiding_empty_chapters(self):
        self.save({'chapters': [chapter('denied', 'DENIED_CHAPTER'), chapter('empty', 'Empty')],
                   'sections': [page('denied-page', 'denied')]})
        DocumentAccess.objects.create(campaign=self.campaign, kind='pages', resource_id=f'{self.journal.pk}:denied-page',
                                       grants={'default': 'none'})
        self.assertEqual([row['id'] for row in self.view(self.player)['chapters']], ['empty'])

    def test_player_save_preserves_private_and_readonly_pages_and_required_chapter_paths(self):
        tree = [chapter('root', 'Root'), chapter('secret', 'SECRET_BRANCH', 'root'),
                chapter('readonly', 'Read branch', 'root'), chapter('editable', 'Own branch')]
        self.save({'chapters': tree, 'sections': [page('hidden', 'secret', audience='gm'),
                                                page('read', 'readonly'), page('own', 'editable')]})
        DocumentAccess.objects.create(campaign=self.campaign, kind='pages', resource_id=f'{self.journal.pk}:read',
                                       grants={'default': 'read'})
        # Omitted uneditable pages and their organizational paths are retained.
        self.save({'chapters': [chapter('root', 'Root'), chapter('readonly', 'Read branch', 'root'),
                               chapter('editable', 'Renamed own branch')],
                   'sections': [page('own', 'editable')]}, self.player)
        stored = Journal.objects.get(pk=self.journal.pk).data
        self.assertEqual({row['id'] for row in stored['chapters']}, {'root', 'secret', 'readonly', 'editable'})
        self.assertEqual({row['id']: row['chapterId'] for row in stored['sections']},
                         {'hidden': 'secret', 'read': 'readonly', 'own': 'editable'})
        self.assertEqual(next(row for row in stored['chapters'] if row['id'] == 'secret')['name'], 'SECRET_BRANCH')
        self.assertNotIn('SECRET_BRANCH', str(self.view(self.player)))

    def test_required_ancestors_follow_submitted_reparenting_and_protected_deletion_is_explicit(self):
        self.save({'chapters': [chapter('parent'), chapter('child', parent='parent')],
                   'sections': [page('readonly', 'child')]})
        DocumentAccess.objects.create(campaign=self.campaign, kind='pages', resource_id=f'{self.journal.pk}:readonly',
                                       grants={'default': 'read'})
        self.save({'chapters': [chapter('child')], 'sections': []}, self.player)
        self.assertEqual([row['id'] for row in self.view()['chapters']], ['child'])
        self.assertEqual(self.view()['sections'][0]['chapterId'], 'child')
        version = self.journal.version
        with self.assertRaisesMessage(services.JournalError, 'A chapter with protected pages cannot be removed.'):
            self.save({'chapters': [], 'sections': []}, self.player)
        self.assertEqual(Journal.objects.get(pk=self.journal.pk).version, version)
        self.assertEqual([row['id'] for row in self.view()['chapters']], ['child'])

    def test_player_cannot_inject_or_attach_to_an_unseen_chapter(self):
        self.save({'chapters': [chapter('secret', 'SECRET')], 'sections': [page('hidden', 'secret', audience='gm')]})
        for value in ({'chapters': [chapter('secret', 'Forged')], 'sections': []},
                      {'chapters': [chapter('secret', 'Guessed')], 'sections': [page('own', 'secret')]},
                      {'sections': [page('own', 'secret')]}):
            with self.subTest(value=value), self.assertRaises(services.JournalError):
                self.save(value, self.player)
        self.assertEqual(Journal.objects.get(pk=self.journal.pk).data['chapters'][0]['name'], 'SECRET')

    def test_readonly_page_identity_and_content_survive_chapter_organization_changes(self):
        self.save({'chapters': [chapter('read', 'Original heading'), chapter('new-root', 'New root')],
                   'sections': [page('readonly', 'read', title='Original page')]})
        DocumentAccess.objects.create(campaign=self.campaign, kind='pages', resource_id=f'{self.journal.pk}:readonly',
                                       grants={'default': 'read'})
        view = self.view(self.player)
        original = deepcopy(view['sections'][0])
        submitted = deepcopy(original); submitted.update(chapterId='new-root', title='Forged page')
        self.save({'chapters': [chapter('read', 'Renamed public heading', 'new-root'), chapter('new-root', 'New root')],
                   'sections': [submitted]}, self.player)
        stored = Journal.objects.get(pk=self.journal.pk).data
        self.assertEqual(stored['sections'][0]['chapterId'], 'read')
        self.assertEqual(stored['sections'][0]['title'], original['title'])
        self.assertEqual(stored['sections'][0]['content'], original['content'])
        self.assertEqual(stored['sections'][0]['category'], 'Renamed public heading')

    def test_invalid_explicit_chapter_payloads_are_atomic(self):
        self.save({'chapters': [chapter('saved')], 'sections': []})
        previous = Journal.objects.get(pk=self.journal.pk)
        malformed = [None, {}, [chapter('a'), chapter('a')], [chapter('a', parent='a')],
                     [chapter('a', parent='b'), chapter('b', parent='a')], [chapter('a', parent='missing')],
                     [{**chapter('a'), 'name': ''}], [{**chapter('a'), 'name': 'n' * 81}],
                     [{**chapter('a'), 'parentId': []}], [{**chapter('a'), 'id': 'bad/id'}],
                     [{**chapter('a'), 'sortOrder': True}], [{**chapter('a'), 'sortOrder': 2**31}],
                     [chapter(f'chapter{i}') for i in range(129)],
                     [chapter(f'level{i}', parent=f'level{i-1}' if i else None) for i in range(9)]]
        receipts = Receipt.objects.count()
        for chapters in malformed:
            with self.subTest(chapters=chapters), self.assertRaises(services.JournalError):
                self.save({'chapters': chapters, 'sections': []})
        for chapter_id in ('missing', ['saved'], 3, ''):
            with self.subTest(chapter_id=chapter_id), self.assertRaises(services.JournalError):
                self.save({'chapters': [chapter('saved')], 'sections': [page('page', chapter_id)]})
        current = Journal.objects.get(pk=self.journal.pk)
        self.assertEqual((current.version, current.data), (previous.version, previous.data))
        self.assertEqual(Receipt.objects.count(), receipts)

    def test_maximum_tree_limits_and_valid_reparenting(self):
        tree = [chapter(f'level{i}', parent=f'level{i-1}' if i else None) for i in range(8)]
        tree += [chapter(f'empty{i}') for i in range(120)]
        self.save({'chapters': tree, 'sections': [page('leaf', 'level7')]})
        self.assertEqual(len(self.view()['chapters']), 128)
        tree[7]['parentId'] = None
        self.save({'chapters': tree, 'sections': [page('leaf', 'level7')]})
        self.assertIsNone(next(row for row in self.view()['chapters'] if row['id'] == 'level7')['parentId'])
        with self.assertRaises(services.JournalError):
            self.save({'chapters': tree, 'sections': [{'id': 'legacy-extra', 'category': 'One extra legacy chapter'}]})

    def test_history_restore_and_trash_keep_empty_hierarchies(self):
        tree = [chapter('root', 'Retained root'), chapter('child', 'Retained empty child', 'root')]
        self.save({'chapters': tree, 'sections': []})
        self.journal.refresh_from_db(); history.snapshot(self.journal, self.who(), force=True)
        revision = Revision.objects.filter(journal_id=self.journal.pk, data__chapters__isnull=False).first()
        self.save({'chapters': [], 'sections': []})
        history.restore_revision(self.journal, revision.pk, self.who()); self.journal.save()
        self.assertEqual(self.view()['chapters'], tree)
        identifier = self.journal.pk
        history.trash(self.journal, self.who())
        deleted = Revision.objects.get(journal_id=identifier, reason='delete')
        restored = history.restore_deleted(deleted.pk, self.who())
        self.assertEqual(restored.data['chapters'], tree)

    def test_restoring_legacy_revision_does_not_inherit_current_empty_chapters(self):
        revision = Revision.objects.create(campaign=self.campaign, journal_id=self.journal.pk, author=self.gm,
            reason='update', title=self.journal.title, type='diary', visibility='shared', version=1,
            data={'sections': [{'id': 'legacy-page', 'category': 'Historical legacy chapter'}]})
        self.save({'chapters': [chapter('current', 'Current empty chapter')], 'sections': []})
        self.journal.refresh_from_db()
        history.restore_revision(self.journal, revision.pk, self.who()); self.journal.save()
        self.assertEqual([row['name'] for row in self.view()['chapters']], ['Historical legacy chapter'])

    def test_history_page_headings_show_assignments_and_changes_between_existing_chapters(self):
        value = {'chapters': [chapter('root', 'Root'), chapter('child', 'Child', 'root'), chapter('other', 'Other')],
                 'sections': [page('page', 'child', title='Page title')]}
        original = history.readable('Journal', 'diary', value)
        self.assertIn('## Root / Child / Page title', original)
        value['sections'][0]['chapterId'] = 'other'
        moved = history.readable('Journal', 'diary', value)
        self.assertNotEqual(original, moved)
        self.assertIn('## Other / Page title', moved)
        value['sections'][0]['chapterId'] = None
        self.assertIn('## Page title', history.readable('Journal', 'diary', value))

    def test_page_presentation_projects_only_the_page_chapter_path(self):
        from gravewright.journals import presentations
        self.save({'chapters': [chapter('root'), chapter('child', parent='root'), chapter('empty', 'UNRELATED_EMPTY')],
                   'sections': [page('shown', 'child')]})
        event = presentations.present(self.who(), {'journal_id': str(self.journal.pk), 'page_id': 'shown'})['presentation']
        _, view = presentations.resolve(presentations.ticket(event, self.player.pk), self.player.pk)
        self.assertEqual([row['id'] for row in view['chapters']], ['root', 'child'])
        self.assertNotIn('UNRELATED_EMPTY', str(view))

    def test_streamers_cannot_change_chapter_structure(self):
        self.save({'chapters': [chapter('root')], 'sections': []})
        with self.assertRaises(services.JournalError):
            self.save({'chapters': [], 'sections': []}, self.streamer)
        self.assertEqual(len(self.view(self.streamer)['chapters']), 1)
