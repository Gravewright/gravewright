"""Exercise independent nested journal chapters in isolated native clients."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen

from campaign_management import serve as serve_campaign
from journal_resource_links import document, control_state, stored_journal, typed_references
from map_builder import ROOT, MEASURE, change_locale, fixture_environment


TITLE = 'Synthetic independent chapters of the northern observatory expedition'
ROOT_NAME = 'Synthetic expedition records and their deliberately long chapter name'
NESTED_NAME = 'Synthetic nested observations'
EMPTY_NAME = 'Synthetic empty independent chapter'
CHILD_NAME = 'Synthetic empty subchapter of the expedition records'
RENAMED_NAME = 'Synthetic renamed independent chapter of northern discoveries'
PRIVATE_NAME = 'SYNTHETIC_PRIVATE_CHAPTER: Keeper records'
PRIVATE_TEXT = 'SYNTHETIC_PRIVATE_PAGE: The keeper concealed the northern lens.'
PLAYER_TEXT = 'Synthetic player notes preserved with hidden chapter structure.'
COLLISION_TEXT = 'Synthetic authored page whose identifier resembles a chapter overview identity.'
ROOT_ID, NESTED_ID, PRIVATE_ID = 'synthetic-root', 'synthetic-nested', 'synthetic-private'


def serve(fixture, port):
    from django.core import management
    original = management.call_command

    def command(name, *args, **kwargs):
        if name == 'runserver':
            from gravewright.actors.models import Actor
            from gravewright.campaigns.models import Campaign
            from gravewright.journals.data import normalize_data_for
            from gravewright.journals.models import Journal
            from gravewright.table.models import DocumentAccess, ProgressClock

            seed_path = fixture / 'seed.json'
            seed = json.loads(seed_path.read_text(encoding='utf-8'))
            campaign = Campaign.objects.get(pk=seed['campaign'])
            player = campaign.memberships.get(role='player').user_id
            actor = Actor.objects.get(pk=seed['actor'])
            actor.permissions = {'default': 'read'}; actor.save(update_fields=['permissions'])
            private_clock = ProgressClock.objects.create(campaign=campaign, name='SYNTHETIC_PRIVATE_CLOCK',
                visibility='gm', description='Synthetic private resource description.')
            legacy = Journal.objects.create(campaign=campaign, creator=campaign.owner, visibility='shared',
                title='Synthetic legacy categorized pages', data={'content': document('Synthetic legacy introduction.'),
                    'sections': [{'id': 'legacy-a', 'title': 'Synthetic legacy first page', 'kind': 'text',
                        'category': 'Synthetic legacy group', 'content': document('Synthetic legacy page content.')},
                        {'id': 'legacy-b', 'title': 'Synthetic legacy second page', 'kind': 'text',
                        'category': 'Synthetic legacy group', 'content': document('Synthetic second legacy page content.')} ]})
            linked = document('Synthetic unfiled page with retained references. ')
            linked['doc']['content'][0]['content'].extend([
                {'type': 'gwResourceLink', 'attrs': {'reference': {'kind': 'actor', 'id': str(actor.pk)}}},
                {'type': 'text', 'text': ' '},
                {'type': 'gwResourceLink', 'attrs': {'reference': {'kind': 'clock', 'id': str(private_clock.pk)}}},
                {'type': 'text', 'text': ' Synthetic legacy page destination', 'marks': [{'type': 'link', 'attrs': {
                    'href': f'/game/{campaign.pk}?document=journal:{legacy.pk}&page=legacy-a'}}]}])
            journal = Journal.objects.create(campaign=campaign, creator=campaign.owner, visibility='shared',
                title=TITLE, data=normalize_data_for('diary', {'content': document('Synthetic chapter introduction.'),
                    'chapters': [{'id': ROOT_ID, 'name': ROOT_NAME, 'parentId': None, 'sortOrder': 10},
                        {'id': NESTED_ID, 'name': NESTED_NAME, 'parentId': ROOT_ID, 'sortOrder': 10},
                        {'id': PRIVATE_ID, 'name': PRIVATE_NAME, 'parentId': None, 'sortOrder': 20},
                        *[{'id': f'depth-{level}', 'name': f'Synthetic nested level {level}: observation records of the northern lens',
                            'parentId': f'depth-{level - 1}' if level > 1 else None, 'sortOrder': 30}
                            for level in range(1, 9)]],
                    'sections': [{'id': 'unfiled', 'title': 'Synthetic page without a chapter', 'kind': 'text',
                        'chapterId': None, 'content': linked},
                        {'id': 'first', 'title': 'Synthetic first expedition page', 'kind': 'text',
                            'chapterId': ROOT_ID, 'content': document('Synthetic first authored expedition notes.')},
                        {'id': 'second', 'title': 'Synthetic second expedition page', 'kind': 'text',
                            'chapterId': ROOT_ID, 'content': document('Synthetic second authored expedition notes.')},
                        {'id': 'nested-page', 'title': 'Synthetic nested expedition page', 'kind': 'text',
                            'chapterId': NESTED_ID, 'content': document('Synthetic authored nested observations.')},
                        {'id': 'private-page', 'title': 'SYNTHETIC_PRIVATE_PAGE', 'kind': 'text', 'audience': 'gm',
                            'chapterId': PRIVATE_ID, 'content': document(PRIVATE_TEXT)},
                        {'id': 'deep-page', 'title': 'Synthetic eighth-level page', 'kind': 'text',
                            'chapterId': 'depth-8', 'content': document('Synthetic observations nested eight levels deep.')},
                        {'id': 'chapter:synthetic-root', 'title': 'Synthetic page with a chapter-shaped identity',
                            'kind': 'text', 'chapterId': None, 'content': document(COLLISION_TEXT)}]}))
            DocumentAccess.objects.create(campaign=campaign, kind='journals', resource_id=str(journal.pk),
                grants={'default': 'read', str(player): 'owner'})
            seed.update(chapterJournal=str(journal.pk), legacyJournal=str(legacy.pk), player=str(player),
                        privateClock=str(private_clock.pk))
            seed_path.write_text(json.dumps(seed, indent=2), encoding='utf-8')
        return original(name, *args, **kwargs)

    management.call_command = command
    try: serve_campaign(fixture, port)
    finally: management.call_command = original


def check_browser(base, seed, output, executable, fixture):
    from playwright.sync_api import expect, sync_playwright

    cases, errors, dialogs, failed, contexts, pages, sockets = [], [], [], [], [], {}, {}
    campaign, identifier = seed['campaign'], seed['chapterJournal']
    before = control_state(fixture)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))

        def client(name, role, *, manager=False):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 1000})
            context.add_cookies([{**seed['sessions'][role], 'url': base}]); contexts.append(context)
            page = context.new_page(); pages[name], sockets[name] = page, []
            page.on('pageerror', lambda error: errors.append({'client': name, 'message': error.stack or str(error)}))
            page.on('dialog', lambda dialog: (dialogs.append({'client': name, 'message': dialog.message}), dialog.dismiss()))
            page.on('requestfailed', lambda request: failed.append({'client': name, 'url': request.url, 'error': request.failure}))
            page.on('websocket', lambda stream: sockets[name].append(stream.url))
            page.goto(f'/campaigns/{campaign}/manage?section=journals' if manager else f'/game/{campaign}')
            ready(page, manager=manager)
            return page

        def ready(page, *, manager=False):
            if manager: expect(page.locator('[data-manager-ready=true]')).to_be_attached(timeout=30000)
            else:
                page.wait_for_function('!!gravewrightJournals && !!gravewrightMaps?.current')
                expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def read(page, journal_id=identifier):
            response = page.request.get(f'/api/containers/{campaign}/journals')
            assert response.ok, response.text()
            return next(row for row in response.json()['journals'] if row['id'] == journal_id)

        def open_journal(page, journal_id=identifier):
            with page.expect_response(lambda response: response.url.split('?')[0].endswith(
                    f'/api/containers/{campaign}/journals') and response.request.method == 'GET') as source:
                page.evaluate('id=>gravewrightJournals.open(id)', journal_id)
            assert source.value.ok, source.value.text()
            source.value.json()
            window = page.locator(f'.journal-window[data-journal-id="{journal_id}"]')
            expect(window).to_be_visible()
            return window

        def close_journal(window):
            window.locator('[data-action=close]').click(); expect(window).to_have_count(0)

        def flush(page, window, journal_id=identifier):
            assert page.evaluate('id=>gravewrightJournals.flush(id)', journal_id)
            expect(window.locator('.journal-window__error')).to_be_hidden()

        def chapter(window, chapter_id):
            return window.locator(f'[data-chapter-id="{chapter_id}"]')

        def actions(page, window, chapter_id, label):
            chapter(window, chapter_id).locator('[data-chapter-actions]').first.click()
            menu = page.locator('.journal-context')
            expect(menu).to_be_visible(); menu.get_by_role('button', name=label, exact=True).click()

        def chapter_form(page, window, name, *, parent='', existing=None):
            if existing: actions(page, window, existing, 'Edit chapter')
            else: window.locator('[data-action=chapter]').click()
            modal = page.locator(f'[data-journal-chapter-editor="{existing or "new"}"]')
            expect(modal).to_be_visible()
            if existing:
                expect(modal.locator(f'[name=parentId] option[value="{existing}"]')).to_have_count(0)
            modal.locator('[name=name]').fill(name)
            modal.locator('[name=parentId]').select_option(parent)
            modal.locator('[type=submit]').click(); expect(modal).to_have_count(0)
            flush(page, window)
            return next(row['id'] for row in read(page)['chapters'] if row['name'] == name)

        def move_page(page, window, page_id, chapter_id):
            window.locator(f'[data-page-id="{page_id}"]').click(button='right')
            page.locator('.journal-context').get_by_role('button', name='Move to chapter', exact=True).click()
            modal = page.locator(f'[data-journal-page-chapter="{page_id}"]')
            expect(modal).to_be_visible(); modal.locator('[name=chapterId]').select_option(chapter_id or '')
            modal.locator('[type=submit]').click(); expect(modal).to_have_count(0)
            flush(page, window)

        try:
            manager = client('manager', 'gm', manager=True)
            journal = open_journal(manager)
            initial = stored_journal(fixture, identifier)
            original_pages = {page['id'] for page in initial['sections']}
            original_refs = typed_references(initial)
            expect(chapter(journal, ROOT_ID)).to_be_visible()
            assert read(manager)['sections'][0]['chapterId'] is None
            empty_id = chapter_form(manager, journal, EMPTY_NAME)
            expect(journal.locator(f'[data-chapter-overview="{empty_id}"]')).to_be_visible()
            assert {page['id'] for page in read(manager)['sections']} == original_pages
            close_journal(journal); manager.reload(); ready(manager, manager=True); journal = open_journal(manager)
            expect(chapter(journal, empty_id)).to_be_visible()
            assert not [page for page in read(manager)['sections'] if page['chapterId'] == empty_id]
            cases.append({'case': 'empty-independent-chapter-autosaves-and-reopens-without-creating-a-page'})

            for reopen in (False, True):
                if reopen:
                    close_journal(journal); journal = open_journal(manager)
                journal.locator('[data-page-id="chapter:synthetic-root"]').click()
                expect(journal.locator('.ProseMirror')).to_contain_text(COLLISION_TEXT)
                expect(journal.locator('[data-chapter-overview]')).to_have_count(0)
                chapter(journal, ROOT_ID).locator('[data-chapter-toggle]').first.click()
                expect(journal.locator(f'[data-chapter-overview="{ROOT_ID}"]')).to_be_visible()
                expect(journal.locator('.diary-workspace__identity strong')).to_have_text(ROOT_NAME)
                expect(journal.locator('.ProseMirror')).to_have_count(0)
                chapter(journal, ROOT_ID).locator('[data-chapter-toggle]').first.click()
            cases.append({'case': 'page-identities-resembling-chapter-overviews-stay-distinct-after-close-and-reopen'})

            actions(manager, journal, ROOT_ID, 'New subchapter')
            modal = manager.locator('[data-journal-chapter-editor=new]')
            expect(modal.locator('[name=parentId]')).to_have_value(ROOT_ID)
            modal.locator('[name=name]').fill(CHILD_NAME); modal.locator('[type=submit]').click()
            expect(modal).to_have_count(0); flush(manager, journal)
            child_id = next(row['id'] for row in read(manager)['chapters'] if row['name'] == CHILD_NAME)
            assert chapter(journal, ROOT_ID).locator(f'[data-chapter-id="{child_id}"]').count() == 1
            move_page(manager, journal, 'unfiled', child_id)
            move_page(manager, journal, 'second', child_id)
            saved = read(manager)
            assert {page['id'] for page in saved['sections'] if page['chapterId'] == child_id} == {'unfiled', 'second'}
            assert len(saved['sections']) == len(original_pages)
            cases.append({'case': 'subchapter-and-multiple-page-memberships-use-single-explicit-chapter-identities'})

            renamed_id = chapter_form(manager, journal, RENAMED_NAME, parent=NESTED_ID, existing=child_id)
            assert renamed_id == child_id
            saved = read(manager)
            assert next(row for row in saved['chapters'] if row['id'] == child_id)['parentId'] == NESTED_ID
            assert all(page['category'] == RENAMED_NAME for page in saved['sections'] if page['chapterId'] == child_id)
            expect(chapter(journal, NESTED_ID).locator(f'[data-chapter-id="{child_id}"]')).to_be_visible()
            manager.screenshot(path=str(output / 'journal-chapters-nested-manager-1440.png'), full_page=True)
            cases.append({'case': 'renaming-and-reparenting-a-chapter-preserves-its-identity-pages-and-legacy-category-mirror'})

            actions(manager, journal, NESTED_ID, 'Delete chapter')
            confirmation = manager.locator(f'[data-journal-chapter-delete="{NESTED_ID}"]')
            expect(confirmation).to_be_visible(); confirmation.locator('[type=submit]').click()
            expect(confirmation).to_have_count(0); flush(manager, journal)
            saved = read(manager)
            assert not any(row['id'] == NESTED_ID for row in saved['chapters'])
            assert next(row for row in saved['chapters'] if row['id'] == child_id)['parentId'] == ROOT_ID
            assert next(page for page in saved['sections'] if page['id'] == 'nested-page')['chapterId'] is None
            move_page(manager, journal, 'unfiled', None)
            assert next(page for page in read(manager)['sections'] if page['id'] == 'unfiled')['chapterId'] is None
            assert {page['id'] for page in saved['sections']} == original_pages
            assert typed_references(stored_journal(fixture, identifier)) == original_refs
            cases.append({'case': 'deleting-a-parent-keeps-pages-and-children-and-moving-a-page-out-does-not-delete-it'})

            journal.locator('[data-page-id=unfiled]').click()
            link = journal.locator('[data-gw-resource-link][data-resource-state=available]').filter(has_text='Synthetic mapped hero')
            expect(link).to_be_visible(); link.focus(); manager.keyboard.press('Enter')
            expect(manager.locator('.actor-directory__sheet')).to_be_visible()
            manager.locator('.actor-directory__sheet [data-window=close]').click()
            journal.locator('a').filter(has_text='Synthetic legacy page destination').click()
            legacy = manager.locator(f'.journal-window[data-journal-id="{seed["legacyJournal"]}"]')
            expect(legacy).to_be_visible(); expect(legacy).to_contain_text('Synthetic legacy page content.')
            legacy_data = read(manager, seed['legacyJournal'])
            assert len(legacy_data['chapters']) == 1
            legacy_id = legacy_data['chapters'][0]['id']
            assert {page['chapterId'] for page in legacy_data['sections']} == {legacy_id}
            assert read(manager, seed['legacyJournal'])['chapters'][0]['id'] == legacy_id
            close_journal(legacy)
            assert control_state(fixture) == before and not sockets['manager']
            cases.append({'case': 'legacy-categories-normalize-stably-and-existing-typed-and-page-hyperlinks-still-open-without-game-presence'})

            gm = client('table-gm', 'gm'); table_journal = open_journal(gm)
            player = client('player', 'player'); player_journal = open_journal(player)
            streamer = client('streamer', 'streamer'); stream_journal = open_journal(streamer)
            expect(chapter(table_journal, empty_id)).to_be_visible()
            for target, window in ((player, player_journal), (streamer, stream_journal)):
                projected = read(target)
                assert PRIVATE_NAME not in json.dumps(projected) and PRIVATE_TEXT not in json.dumps(projected)
                assert PRIVATE_ID not in json.dumps(projected)
                expect(window).not_to_contain_text(PRIVATE_NAME)
                expect(chapter(window, empty_id)).to_be_visible()
                expect(chapter(window, ROOT_ID)).to_be_visible()
            expect(stream_journal.locator('[data-chapter-actions]')).to_have_count(0)
            expect(stream_journal.locator('[data-action=chapter]')).to_be_hidden()
            cases.append({'case': 'table-and-manager-share-the-tree-while-player-projections-hide-private-only-branches-and-keep-empty-chapters'})

            player_journal.locator('[data-page-id=unfiled]').click()
            surface = player_journal.locator('.ProseMirror[contenteditable=true]').first
            surface.focus(); player.keyboard.press('Control+End'); player.keyboard.type(' ' + PLAYER_TEXT)
            flush(player, player_journal)
            raw = stored_journal(fixture, identifier)
            assert PLAYER_TEXT in json.dumps(raw) and PRIVATE_TEXT in json.dumps(raw)
            assert any(row['id'] == PRIVATE_ID for row in raw['chapters'])
            assert typed_references(raw) == original_refs
            cases.append({'case': 'player-owner-autosave-preserves-omitted-private-chapters-pages-and-resource-references'})

            for window in (player_journal, stream_journal, table_journal): close_journal(window)
            close_journal(journal)
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(manager, locale, campaign); manager.set_viewport_size({'width': 320, 'height': 844})
                manager.goto(f'/campaigns/{campaign}/manage?section=journals'); ready(manager, manager=True)
                narrow = open_journal(manager)
                metrics = narrow.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                assert narrow.locator('.diary-workspace__identity').bounding_box()['width'] >= 100
                expect(chapter(narrow, empty_id)).to_be_visible()
                manager.screenshot(path=str(output / f'journal-chapters-tree-{locale}-320.png'), full_page=True)
                deepest = chapter(narrow, 'depth-8').locator('[data-chapter-toggle]').first
                deepest.scroll_into_view_if_needed(); expect(deepest).to_be_visible()
                assert deepest.locator('strong').bounding_box()['width'] >= 24
                metrics = narrow.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                manager.screenshot(path=str(output / f'journal-chapters-depth-{locale}-320.png'), full_page=True)
                narrow.locator('[data-action=chapter]').click()
                modal = manager.locator('[data-journal-chapter-editor=new]')
                expect(modal).to_be_visible(); modal.locator('[name=name]').fill(RENAMED_NAME)
                metrics = modal.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                assert modal.locator('[name=parentId] option').count() >= 9
                manager.screenshot(path=str(output / f'journal-chapters-form-{locale}-320.png'), full_page=True)
                manager.keyboard.press('Escape'); expect(modal).to_have_count(0)
                expect(narrow.locator('[data-action=chapter]')).to_be_focused()
                close_journal(narrow)
                cases.append({'case': f'{locale}-320px-long-nested-chapter-tree-and-native-form-remain-usable'})

            assert not errors, errors
            assert not dialogs, dialogs
            assert not [row for row in failed if row['error'] != 'net::ERR_ABORTED'], failed
        except Exception:
            (output / 'browser-diagnostics.json').write_text(json.dumps({'completedCases': cases,
                'pageErrors': errors, 'nativeDialogs': dialogs, 'failedRequests': failed}, indent=2), encoding='utf-8')
            for name, page in pages.items():
                if not page.is_closed(): page.screenshot(path=str(output / f'failure-{name}.png'), full_page=True)
            raise
        finally:
            for context in contexts: context.close()
            browser.close()
    return {'passed': True, 'cases': cases, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'assets': 'Generated synthetic campaign files and authored chapter/page text only.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path); parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve: serve(args.fixture, args.port); return
    output = (args.output or ROOT / 'data/journal-chapters' /
              datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if output.exists() and any(output.iterdir()): raise RuntimeError('Use a fresh, empty output directory.')
    output.mkdir(parents=True, exist_ok=True); fixture = output / 'fixture'; fixture.mkdir()
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0)); port = connection.getsockname()[1]
    fixture_environment(fixture, port)
    executable = sys._base_executable if os.name == 'nt' else sys.executable
    command = [executable, '-B', '-X', 'utf8', str(Path(__file__).resolve())]
    base = f'http://127.0.0.1:{port}'
    with (output / 'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen([*command, '--serve', '--fixture', str(fixture), '--port', str(port)],
                                  cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=log)
        try:
            for _ in range(300):
                if server.poll() is not None: raise RuntimeError(f"Fixture exited; inspect {output / 'server.log'}")
                try:
                    with urlopen(base, timeout=1): break
                except OSError: time.sleep(.1)
            else: raise RuntimeError('Fixture did not become ready.')
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
            report = check_browser(base, seed, output, args.browser_executable, fixture)
            (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps({'passed': True, 'cases': len(report['cases']), 'report': str(output / 'report.json')}))
        except Exception:
            (output / 'failure.txt').write_text(traceback.format_exc(), encoding='utf-8'); raise
        finally:
            server.terminate()
            try: server.wait(timeout=10)
            except subprocess.TimeoutExpired: server.kill(); server.wait()
            (output / 'server-exit.json').write_text(json.dumps({'pid': server.pid, 'exitCode': server.returncode}), encoding='utf-8')


if __name__ == '__main__': main()
