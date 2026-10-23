"""Rename a journal page from its native header without replacing rich text."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen

from journal_chapters import serve as serve_chapters
from journal_resource_links import control_state, stored_journal
from map_builder import ROOT, MEASURE, change_locale, fixture_environment


LONG_TITLE = 'Synthetic northern observatory expedition notes with a deliberately long authored page name for narrow screens'
PAGE_ID = 'unfiled'


def serve(fixture, port):
    from django.core import management
    original = management.call_command

    def command(name, *args, **kwargs):
        if name == 'runserver':
            from gravewright.table.models import DocumentAccess
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
            DocumentAccess.objects.create(campaign_id=seed['campaign'], kind='pages',
                resource_id=f'{seed["chapterJournal"]}:second', grants={'default': 'read'})
        return original(name, *args, **kwargs)

    management.call_command = command
    try: serve_chapters(fixture, port)
    finally: management.call_command = original


def check_browser(base, seed, output, executable, fixture):
    from playwright.sync_api import expect, sync_playwright
    cases, errors, dialogs, failed, contexts, pages, sockets = [], [], [], [], [], {}, {}
    campaign, identifier = seed['campaign'], seed['chapterJournal']
    before = control_state(fixture)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))

        def ready(page, *, manager=False):
            if manager: expect(page.locator('[data-manager-ready=true]')).to_be_attached(timeout=30000)
            else:
                page.wait_for_function('!!gravewrightJournals && !!gravewrightMaps?.current')
                expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def client(name, role, *, manager=False):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 1000})
            contexts.append(context); context.add_cookies([{**seed['sessions'][role], 'url': base}])
            context.add_init_script('''(()=>{
              const nodes=new WeakMap();let serial=0;window.__titleEvents=[];
              const identity=node=>{if(!node)return null;if(!nodes.has(node))nodes.set(node,++serial);return nodes.get(node)};
              const box=node=>{if(!node)return null;const r=node.getBoundingClientRect();return {top:r.top,height:r.height}};
              for(const type of ['pointerdown','blur','pointerup','click'])addEventListener(type,event=>{
                const first=document.querySelector('[data-page-id="first"]'),unfiled=document.querySelector('[data-page-id="unfiled"]');
                window.__titleEvents.push({type,at:performance.now(),tag:event.target.tagName,
                  page:event.target.closest?.('[data-page-id]')?.dataset.pageId,
                  relatedPage:event.relatedTarget?.closest?.('[data-page-id]')?.dataset.pageId,
                  firstNode:identity(first),firstBox:box(first),unfiledBox:box(unfiled),
                  selected:document.querySelector('[data-page-id][aria-current=page]')?.dataset.pageId});
                if(window.__titleEvents.length>80)window.__titleEvents.shift();
              },true);
            })();''')
            page = context.new_page(); pages[name], sockets[name] = page, []
            page.on('pageerror', lambda error: errors.append({'client': name, 'message': error.stack or str(error)}))
            page.on('dialog', lambda dialog: (dialogs.append({'client': name, 'message': dialog.message}), dialog.dismiss()))
            page.on('requestfailed', lambda request: failed.append({'client': name, 'url': request.url, 'error': request.failure}))
            page.on('websocket', lambda stream: sockets[name].append(stream.url))
            page.goto(f'/campaigns/{campaign}/manage?section=journals' if manager else f'/game/{campaign}')
            ready(page, manager=manager); return page

        def open_journal(page, journal_id=identifier, *, source_read=True):
            if source_read:
                with page.expect_response(lambda response: response.url.split('?')[0].endswith(
                        f'/api/containers/{campaign}/journals') and response.request.method == 'GET') as source:
                    page.evaluate('id=>gravewrightJournals.open(id)', journal_id)
                assert source.value.ok, source.value.text()
                source.value.json()
            else: page.evaluate('id=>gravewrightJournals.open(id)', journal_id)
            window = page.locator(f'.journal-window[data-journal-id="{journal_id}"]')
            expect(window).to_be_visible(); return window

        def close_journal(window):
            window.locator('[data-action=close]').click(); expect(window).to_have_count(0)

        def flush(page, window):
            assert page.evaluate('id=>gravewrightJournals.flush(id)', identifier)
            expect(window.locator('.journal-window__error')).to_be_hidden()

        def button(window): return window.locator('[data-journal-page-title]')
        def field(window): return window.locator('[data-journal-page-title-input]')
        def saved_page(): return next(row for row in stored_journal(fixture, identifier)['sections'] if row['id'] == PAGE_ID)
        def revision():
            database = (fixture / 'review.sqlite3').resolve()
            with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
                return connection.execute('SELECT version FROM gravewright_journals_journal WHERE id = ?',
                                          (identifier.replace('-', ''),)).fetchone()[0]

        def remember_editor(window):
            window.locator('.ProseMirror').evaluate('node=>window.__titleEditor=node')

        def same_editor(window):
            assert window.locator('.ProseMirror').evaluate('node=>window.__titleEditor===node')

        def edit(window, *, key=None):
            if key: button(window).focus(); button(window).press(key)
            else: button(window).click()
            expect(field(window)).to_be_focused()
            expect(field(window)).to_have_attribute('maxlength', '120')
            expect(field(window)).to_have_attribute('required', '')
            expect(field(window)).to_have_attribute('translate', 'no')
            return field(window)

        try:
            manager = client('manager', 'gm', manager=True); journal = open_journal(manager)
            baseline = saved_page()
            remember_editor(journal)
            edit(journal).fill('  Save  '); manager.keyboard.press('Enter')
            expect(field(journal)).to_have_count(0); expect(button(journal)).to_have_text('Save')
            assert button(journal).evaluate('node=>node.translate') is False
            flush(manager, journal); same_editor(journal)
            assert saved_page() == {**baseline, 'title': 'Save'}
            assert control_state(fixture) == before and not sockets['manager']
            manager.screenshot(path=str(output / 'journal-page-title-manager-1440.png'), full_page=True)
            cases.append({'case': 'manager-click-enter-trims-and-autosaves-only-the-page-title-without-replacing-rich-text-or-joining-table'})

            version = stored_journal(fixture, identifier)
            original_revision = revision()
            edit(journal, key='Enter').fill('Synthetic cancelled title'); manager.keyboard.press('Escape')
            expect(field(journal)).to_have_count(0); expect(button(journal)).to_be_focused()
            assert stored_journal(fixture, identifier) == version
            assert revision() == original_revision
            edit(journal, key='Space').fill('   '); manager.keyboard.press('Enter')
            if field(journal).count(): manager.keyboard.press('Escape')
            expect(button(journal)).to_have_text('Save')
            flush(manager, journal); same_editor(journal)
            assert stored_journal(fixture, identifier) == version
            assert revision() == original_revision
            cases.append({'case': 'enter-and-space-open-editing-while-escape-and-blank-input-preserve-the-stored-title'})

            edit(journal, key='Space').fill('  ' + LONG_TITLE + '  ')
            journal.locator('.ProseMirror').focus()
            expect(button(journal)).to_have_text(LONG_TITLE)
            expect(journal.locator('.ProseMirror')).to_be_focused()
            flush(manager, journal); same_editor(journal)
            assert saved_page() == {**baseline, 'title': LONG_TITLE}
            close_journal(journal); manager.reload(); ready(manager, manager=True); journal = open_journal(manager)
            expect(button(journal)).to_have_text(LONG_TITLE)
            cases.append({'case': 'blur-confirms-a-long-authored-title-and-reopening-preserves-page-content-and-references'})

            click_title = 'Synthetic title confirmed by navigating with one pointer click'
            edit(journal).fill(click_title)
            journal.locator('[data-page-id=first]').click()
            expect(journal.locator('[data-page-id=first]')).to_have_attribute('aria-current', 'page')
            flush(manager, journal)
            assert saved_page() == {**baseline, 'title': click_title}
            journal.locator('[data-page-id=unfiled]').click()
            before_navigation, before_revision = stored_journal(fixture, identifier), revision()
            edit(journal).fill('Synthetic transient navigation title')
            journal.locator('.ProseMirror').evaluate('node=>window.__staleTitleField=document.querySelector("[data-journal-page-title-input]")')
            manager.evaluate('id=>gravewrightJournals.open(id,"first")', identifier)
            expect(field(journal)).to_have_count(0)
            manager.evaluate('window.__staleTitleField.dispatchEvent(new Event("blur"))')
            flush(manager, journal)
            assert stored_journal(fixture, identifier) == before_navigation
            assert revision() == before_revision
            journal.locator('[data-page-id=unfiled]').click()
            edit(journal).fill('Synthetic transient closing title')
            field(journal).evaluate('node=>window.__staleTitleField=node')
            journal.locator('[data-action=close]').dispatch_event('click'); expect(journal).to_have_count(0)
            manager.evaluate('window.__staleTitleField.dispatchEvent(new Event("blur"))')
            journal = open_journal(manager)
            expect(button(journal)).to_have_text(click_title)
            assert stored_journal(fixture, identifier) == before_navigation
            assert revision() == before_revision
            cases.append({'case': 'pointer-navigation-confirms-and-navigates-once-while-programmatic-navigation-close-and-late-blur-cannot-save-a-draft'})

            journal.locator('[data-action=edit]').click()
            expect(button(journal)).to_have_count(0); expect(field(journal)).to_have_count(0)
            journal.locator('[data-action=edit]').click(); expect(button(journal)).to_be_visible()
            gm = client('table-gm', 'gm'); gm_window = open_journal(gm)
            edit(gm_window).fill('Save'); gm.keyboard.press('Enter'); flush(gm, gm_window)
            assert saved_page() == {**baseline, 'title': 'Save'}
            player = client('player', 'player'); player_window = open_journal(player)
            expect(button(player_window)).to_be_visible()
            player_window.locator('[data-page-id=second]').click()
            expect(button(player_window)).to_have_count(0); expect(field(player_window)).to_have_count(0)
            read_only = open_journal(player, seed['legacyJournal'], source_read=False)
            expect(button(read_only)).to_have_count(0); expect(field(read_only)).to_have_count(0)
            close_journal(read_only)
            streamer = client('streamer', 'streamer'); stream_window = open_journal(streamer)
            expect(button(stream_window)).to_have_count(0); expect(field(stream_window)).to_have_count(0)
            cases.append({'case': 'table-gm-can-rename-while-reading-mode-reader-player-streamer-and-readonly-page-have-no-title-control'})

            player_window.locator('[data-page-id=unfiled]').click()
            edit(player_window).fill('Synthetic uncommitted title during ownership revocation')
            field(player_window).evaluate('node=>window.__staleTitleField=node')
            manager.evaluate('''async ([campaign,id])=>{
              const api=gravewright.forTable(campaign),view=await api.ownership.read({kind:'journals',id});
              await api.ownership.update({kind:'journals',id,version:view.version,permissions:{default:'read'}});
            }''', [campaign, identifier])
            expect(field(player_window)).to_have_count(0, timeout=15000)
            expect(button(player_window)).to_have_count(0)
            player.evaluate('window.__staleTitleField.dispatchEvent(new Event("blur"))')
            assert saved_page() == {**baseline, 'title': 'Save'}
            cases.append({'case': 'live-ownership-revocation-cancels-uncommitted-title-and-blocks-late-blur-save'})

            for window in (player_window, stream_window, gm_window): close_journal(window)
            close_journal(journal)
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(manager, locale, campaign); manager.set_viewport_size({'width': 320, 'height': 844})
                manager.goto(f'/campaigns/{campaign}/manage?section=journals'); ready(manager, manager=True)
                narrow = open_journal(manager)
                expect(button(narrow)).to_have_text('Save')
                edit(narrow).fill(LONG_TITLE); manager.keyboard.press('Enter'); flush(manager, narrow)
                expect(button(narrow)).to_have_text(LONG_TITLE)
                metrics = narrow.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                manager.screenshot(path=str(output / f'journal-page-title-{locale}-320.png'), full_page=True)
                edit(narrow).fill('Synthetic translated interface with an unchanged authored page title')
                metrics = narrow.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                manager.screenshot(path=str(output / f'journal-page-title-input-{locale}-320.png'), full_page=True)
                manager.keyboard.press('Escape'); expect(button(narrow)).to_have_text(LONG_TITLE)
                edit(narrow).fill('Save'); manager.keyboard.press('Enter'); flush(manager, narrow)
                expect(button(narrow)).to_have_text('Save')
                close_journal(narrow)
                cases.append({'case': f'{locale}-320px-title-display-and-inline-input-preserve-authored-text-and-fit-the-header'})

            assert saved_page() == {**baseline, 'title': 'Save'}
            assert not errors, errors
            assert not dialogs, dialogs
            assert not [row for row in failed if row['error'] != 'net::ERR_ABORTED'], failed
        except Exception:
            (output / 'browser-diagnostics.json').write_text(json.dumps({'completedCases': cases,
                'pageErrors': errors, 'nativeDialogs': dialogs, 'failedRequests': failed,
                'titleEvents': {name: page.evaluate('window.__titleEvents')
                    for name, page in pages.items() if not page.is_closed()}}, indent=2), encoding='utf-8')
            for name, page in pages.items():
                if not page.is_closed(): page.screenshot(path=str(output / f'failure-{name}.png'), full_page=True)
            raise
        finally:
            for context in contexts: context.close()
            browser.close()
    return {'passed': True, 'cases': cases, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'assets': 'Generated synthetic campaign files and authored page/chapter text only.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path); parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve: serve(args.fixture, args.port); return
    output = (args.output or ROOT / 'data/journal-page-titles' /
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
