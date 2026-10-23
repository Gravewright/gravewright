"""Protect preparation drafts, concurrent restores, private history and pickers.

Uses the native preparation fixture and public browser API. All accounts,
attachments, mutations and deliberately missing files belong to a new fixture.
"""
from __future__ import annotations

from copy import deepcopy
import json
import sqlite3
import time

import campaign_preparation as harness
from map_builder import MEASURE, change_locale
from map_builder_blueprints import artwork


PLAN_TITLE = 'Synthetic regression plan with a deliberately long authored title'
BASELINE = 'Synthetic saved notes: prepare the northern observatory.'
DRAFT = 'Synthetic unsaved notes: the western entrance is flooded.'
LATER_DRAFT = 'Synthetic notes entered while saving: keep the eastern entrance available.'
PRIVATE_TITLE = 'Synthetic private historical journal'
PRIVATE_TEXT = 'PREPARATION_REGRESSION_SECRET: The observatory keeper concealed the northern passage.'


def document(text):
    return {'format': 'gw-journal-doc-v1', 'version': 1,
            'doc': {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': text}]}]}}


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    cases, errors, dialogs, failed, contexts = [], [], [], [], []
    pages = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))

        def client(name, role, *, table=False):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 1000})
            contexts.append(context)
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            context.add_init_script("window.__prepWire=[];addEventListener('gravewright:api-event',event=>__prepWire.push(event.detail));")
            page = context.new_page()
            pages[name] = page
            page.on('pageerror', lambda error: errors.append(error.stack or str(error)))
            page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
            page.on('requestfailed', lambda request: failed.append({'url': request.url, 'error': request.failure}))
            response = page.goto(f'/game/{campaign}' if table else f'/campaigns/{campaign}/manage')
            assert response.ok, (name, response.status)
            if table:
                page.wait_for_function('!!window.gravewrightRealtime && !!window.gravewrightMaps?.current')
            else:
                expect(page.locator('[data-manager-ready=true]')).to_be_attached(timeout=30000)
            return page

        def section(page, name):
            page.locator(f'[data-manager-section="{name}"]').click()
            expect(page.locator(f'[data-manager-view="{name}"]')).to_be_visible()

        def command(page, action, payload):
            return page.evaluate('''([action,payload])=>gravewrightRealtime.journalCommand(action,payload,{requestId:crypto.randomUUID()})''', [action, payload])

        def journal(page, identifier):
            return page.evaluate("id=>gravewrightRealtime.states.get('journals').journals.find(doc=>doc.id===id)", identifier)

        def plans():
            response = gm.request.get(f'/api/containers/{campaign}/preparation')
            assert response.ok, response.text()
            return response.json()

        def plan():
            return next(row for row in plans()['sessions'] if row['title'] == PLAN_TITLE)

        def history(identifier):
            response = gm.request.get(f'/api/containers/{campaign}/journal-history/{identifier}')
            assert response.ok, response.text()
            return response.json()['revisions']

        def compare(identifier, revision, *, label='Compare'):
            section(gm, 'history')
            with gm.expect_response(lambda response: response.request.method == 'GET' and response.url.endswith('/journal-history/' + identifier)) as loaded:
                gm.locator('[data-history-journal]').select_option(identifier)
            assert loaded.value.ok, loaded.value.text()
            rows = history(identifier)
            index = next(index for index, row in enumerate(rows) if row['id'] == revision['id'])
            article = gm.locator('[data-history-versions] article').nth(index)
            expect(article).to_contain_text(revision['title'])
            button = article.get_by_role('button', name=label, exact=True)
            expect(button).to_be_visible()
            with gm.expect_response(lambda response: response.request.method == 'GET' and response.url.endswith('/journal-revisions/' + revision['id'])) as compared:
                button.click()
            assert compared.value.ok, compared.value.text()
            modal = gm.locator('[data-window-key=manager-compare]')
            expect(modal).to_be_visible()
            return modal, compared.value.json()

        def restore_request(request):
            return request.method == 'POST' and any(action in (request.post_data or '') for action in ('restoreRevision', 'restore-revision'))

        def journal_rows():
            path = (output / 'fixture/review.sqlite3').resolve()
            with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as connection:
                names = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                         if row[0].startswith('gravewright_journals_') or row[0] == 'gravewright_table_documentaccess']
                return {name: sorted(connection.execute('SELECT * FROM "' + name.replace('"', '""') + '"').fetchall(), key=repr)
                        for name in names}

        try:
            gm = client('gm', 'gm')
            section(gm, 'sessions')
            gm.locator('[data-session-create]').click()
            modal = gm.locator('[data-window-key=manager-session-create]')
            modal.locator('[name=title]').fill(PLAN_TITLE)
            modal.locator('[type=submit]').click()
            editor = gm.locator('[data-session-editor]')
            expect(editor.locator('textarea')).to_be_visible()
            editor.locator('textarea').fill(BASELINE)
            editor.get_by_role('button', name='Save changes', exact=True).click()
            expect(editor.get_by_role('button', name='Saved', exact=True)).to_be_visible()
            stored = plan()
            editor.locator('textarea').fill(DRAFT)
            gm.locator('[data-session-list] button').filter(has_text=PLAN_TITLE).click()
            expect(editor.locator('textarea')).to_have_value(DRAFT)
            expect(editor.get_by_role('button', name='Save changes', exact=True)).to_be_enabled()
            assert plan() == stored
            gm.screenshot(path=str(output / 'same-session-draft-preserved-1440.png'), full_page=True)
            cases.append({'case': 'clicking-the-selected-session-preserves-unsaved-notes-and-does-not-write'})

            held = []
            preparation_url = f'**/api/containers/{campaign}/preparation'
            def hold_save(route):
                body = route.request.post_data_json if route.request.method == 'POST' else {}
                if body.get('action') == 'session-update' and not held:
                    held.append((route, route.fetch(), deepcopy(body)))
                else:
                    route.continue_()
            gm.route(preparation_url, hold_save)
            try:
                editor.get_by_role('button', name='Save changes', exact=True).click()
                deadline = time.monotonic() + 10
                while not held and time.monotonic() < deadline:
                    gm.wait_for_timeout(20)
                assert held, 'The actual session save must be awaiting its response.'
                editable = editor.locator('textarea').is_editable()
                if editable:
                    editor.locator('textarea').fill(LATER_DRAFT)
                held[0][0].fulfill(response=held[0][1])
                gm.unroute(preparation_url, hold_save)
                if editable:
                    expect(editor.locator('textarea')).to_have_value(LATER_DRAFT)
                    expect(editor.get_by_role('button', name='Save changes', exact=True)).to_be_enabled()
                    assert plan()['notes'] == DRAFT
                    editor.get_by_role('button', name='Save changes', exact=True).click()
                    expect(editor.get_by_role('button', name='Saved', exact=True)).to_be_visible()
                    assert plan()['notes'] == LATER_DRAFT
                else:
                    expect(editor.locator('textarea')).to_have_value(DRAFT)
                    expect(editor.get_by_role('button', name='Saved', exact=True)).to_be_visible()
                    assert plan()['notes'] == DRAFT
                cases.append({'case': 'pending-save-preserves-later-typing-or-locks-input-until-acknowledged', 'inputsWereEditable': editable})
            finally:
                gm.unroute(preparation_url, hold_save)

            section(gm, 'overview')
            unavailable = 'Synthetic reference insertion service is temporarily unavailable.'
            rejected = []
            def reject_pin(route):
                body = route.request.post_data_json if route.request.method == 'POST' else {}
                if body.get('action') == 'board-update' and not rejected:
                    rejected.append(body)
                    route.fulfill(status=503, content_type='application/json', body=json.dumps({'error': unavailable}))
                else:
                    route.continue_()
            gm.route(preparation_url, reject_pin)
            try:
                gm.locator('[data-widget=pins]').get_by_role('button', name='Pin document', exact=True).click()
                picker = gm.locator('[data-window-key=reference-picker]')
                picker.locator('input').fill('Synthetic mapped hero')
                candidate = picker.locator('.document-reference-results button').first
                expect(candidate).to_be_visible()
                selected_title = candidate.inner_text()
                candidate.click()
                picker.locator('[type=submit]').click()
                expect(picker).to_be_visible()
                expect(picker.locator('[role=alert]')).to_contain_text(unavailable)
                expect(picker.locator('.document-reference-results button[aria-pressed=true]')).to_have_text(selected_title)
                gm.screenshot(path=str(output / 'reference-picker-retry-preserves-selection-1440.png'), full_page=True)
                picker.locator('[type=submit]').click()
                expect(picker).to_have_count(0)
                assert len(plans()['board']['pins']) == 1
                cases.append({'case': 'failed-async-reference-insertion-keeps-modal-selection-and-can-retry'})
            finally:
                gm.unroute(preparation_url, reject_pin)

            quest = command(gm, 'create', {'title': 'Synthetic concurrent restoration quest', 'journal_type': 'quest'})['journal_id']
            command(gm, 'status', {'journal_id': quest, 'version': journal(gm, quest)['version'], 'status': 'active'})
            revision = history(quest)[0]
            modal, compared = compare(quest, revision)
            original_diff = modal.locator('.campaign-prep__diff').inner_text()
            cogm = client('cogm', 'cogm')
            changed = command(cogm, 'status', {'journal_id': quest, 'version': compared['current']['version'], 'status': 'completed'})
            gm.wait_for_function("({id,version})=>gravewrightRealtime.states.get('journals').journals.find(doc=>doc.id===id)?.version===version",
                                 arg={'id': quest, 'version': changed['version']}, timeout=25000)
            assert modal.locator('.campaign-prep__diff').inner_text() == original_diff
            with gm.expect_request(restore_request) as attempted, gm.expect_response(lambda response: restore_request(response.request)) as response:
                modal.locator('[type=submit]').click()
            assert response.value.status == 409, response.value.text()
            assert attempted.value.post_data_json['payload']['version'] == compared['current']['version']
            expect(modal).to_be_visible()
            expect(modal.locator('[role=alert]')).to_be_visible()
            latest = journal(gm, quest)
            assert latest['version'] == changed['version'] and latest['quest']['status'] == 'completed', latest
            gm.screenshot(path=str(output / 'stale-comparison-conflict-preserves-newer-quest-1440.png'), full_page=True)
            gm.keyboard.press('Escape')
            expect(modal).to_have_count(0)
            modal, reviewed = compare(quest, revision)
            assert reviewed['current']['version'] == changed['version']
            with gm.expect_response(lambda response: restore_request(response.request)) as response:
                modal.locator('[type=submit]').click()
            assert response.value.ok, response.value.text()
            expect(modal).to_have_count(0)
            assert journal(gm, quest)['quest']['status'] == 'available'
            cases.append({'case': 'stale-comparison-conflicts-without-overwrite-and-restores-only-after-recompare'})

            identifier = command(gm, 'create', {'title': PRIVATE_TITLE, 'journal_type': 'diary'})['journal_id']
            # A different GM makes a distinct historical checkpoint instead of
            # the native five-minute coalescing of one author's rapid saves.
            private_saved = command(cogm, 'update', {'journal_id': identifier, 'version': journal(gm, identifier)['version'],
                'title': PRIVATE_TITLE, 'visibility': 'private', 'data': {'content': document(PRIVATE_TEXT)}})
            command(gm, 'update', {'journal_id': identifier, 'version': private_saved['version'],
                'title': 'Synthetic harmless public journal', 'visibility': 'shared', 'data': {'content': document('Synthetic publicly shared information.')}})
            gm.evaluate('''async ({campaign,id})=>{
              const api=gravewright.forTable(campaign),snapshot=await api.ownership.read({kind:'journals',id});
              await api.ownership.update({kind:'journals',id,version:snapshot.version,permissions:{default:'read'}});
            }''', {'campaign': campaign, 'id': identifier})
            player = client('player', 'player', table=True)
            def player_state():
                return player.evaluate('campaign=>gravewright.forTable(campaign).journals.state()', campaign)
            assert any(row['id'] == identifier for row in player_state()['journals'])
            private_revision = next(row for row in history(identifier) if row['title'] == PRIVATE_TITLE and row['version'] > 1)
            modal, _ = compare(identifier, private_revision)
            with gm.expect_response(lambda response: restore_request(response.request)) as response:
                modal.locator('[type=submit]').click()
            assert response.value.ok, response.value.text()
            expect(modal).to_have_count(0)
            projection = player_state()
            assert not any(row['id'] == identifier for row in projection['journals']), projection
            assert PRIVATE_TEXT not in json.dumps(projection) and PRIVATE_TEXT not in player.content()
            assert PRIVATE_TEXT not in json.dumps(player.evaluate('window.__prepWire'))
            restored = journal(gm, identifier)
            assert restored['visibility'] == 'private' and PRIVATE_TEXT in json.dumps(restored), restored
            cases.append({'case': 'restoring-private-history-removes-public-default-grant-and-never-sends-secret-to-player'})

            asset_journal = command(gm, 'create', {'title': 'Synthetic missing attachment regression', 'journal_type': 'diary'})['journal_id']
            uploaded = gm.evaluate('''async ({campaign,id,bytes})=>{
              const csrf=await(await fetch('/__gravewright/csrf')).json(),data=new FormData();
              data.append('campaign_id',campaign);data.append('journal_id',id);
              data.append('file',new Blob([new Uint8Array(bytes)],{type:'image/png'}),'synthetic-history.png');
              const response=await fetch('/game/journal/asset',{method:'POST',headers:{[csrf.header]:csrf.token},body:data});
              return {status:response.status,body:await response.json()};
            }''', {'campaign': campaign, 'id': asset_journal, 'bytes': list(artwork('#397ca5'))})
            assert uploaded['status'] == 200, uploaded
            asset = uploaded['body']
            asset_data = {'content': document('Synthetic attachment before editing.'), 'sections': [
                {'id': 'synthetic-image', 'title': 'Synthetic authorized image', 'kind': 'image',
                 'assetId': asset['asset_id'], 'src': asset['src'], 'audience': 'public'}]}
            asset_saved = command(cogm, 'update', {'journal_id': asset_journal, 'version': journal(gm, asset_journal)['version'],
                'title': 'Synthetic attachment before editing', 'data': asset_data})
            asset_data['content'] = document('Synthetic current content must survive the rejected restore.')
            command(gm, 'update', {'journal_id': asset_journal, 'version': asset_saved['version'],
                'title': 'Synthetic attachment current title', 'data': asset_data})
            with sqlite3.connect((output / 'fixture/review.sqlite3').resolve().as_uri() + '?mode=ro', uri=True) as connection:
                storage_name, = connection.execute('SELECT file FROM gravewright_journals_asset WHERE id=?', (asset['asset_id'].replace('-', ''),)).fetchone()
            media_root = (output / 'fixture/media').resolve()
            missing_file = (media_root / storage_name).resolve()
            assert missing_file.is_relative_to(media_root) and missing_file.is_file(), missing_file
            missing_file.unlink()
            asset_revision = next(row for row in history(asset_journal) if row['version'] == 2)
            modal, _ = compare(asset_journal, asset_revision)
            before = journal_rows()
            with gm.expect_response(lambda response: restore_request(response.request)) as response:
                modal.locator('[type=submit]').click()
            assert response.value.status == 400, response.value.text()
            expect(modal).to_be_visible()
            expect(modal.locator('[role=alert]')).to_have_text(
                'That version uses files that were removed from this document.')
            assert journal_rows() == before
            gm.screenshot(path=str(output / 'missing-attachment-restore-rejected-atomically-1440.png'), full_page=True)
            gm.keyboard.press('Escape')
            expect(modal).to_have_count(0)
            cases.append({'case': 'missing-historical-attachment-rejects-restore-without-changing-journal-revision-grants-or-assets'})

            expected = {
                'pt-BR': {'nav': 'Planejador de sessões', 'customize': 'Personalizar painel', 'notes': 'Notas privadas',
                          'error': 'Essa versão usa arquivos que foram removidos deste documento.'},
                'es': {'nav': 'Planificador de sesiones', 'customize': 'Personalizar panel', 'notes': 'Notas privadas',
                       'error': 'Esa versión usa archivos que se eliminaron de este documento.'},
            }
            for locale in ('pt-BR', 'es'):
                change_locale(gm, locale, campaign)
                gm.set_viewport_size({'width': 320, 'height': 844})
                gm.goto(f'/campaigns/{campaign}/manage')
                expect(gm.locator('[data-manager-ready=true]')).to_be_attached(timeout=30000)
                expect(gm.locator('[data-manager-section=sessions]')).to_have_text(expected[locale]['nav'])
                expect(gm.locator('[data-manager-dashboard] .campaign-prep__heading button')).to_have_text(expected[locale]['customize'])
                gm.screenshot(path=str(output / f'dashboard-{locale}-320.png'), full_page=True)
                section(gm, 'sessions')
                gm.locator('[data-session-list] button').filter(has_text=PLAN_TITLE).click()
                expect(editor.locator('textarea')).to_have_value(LATER_DRAFT if editable else DRAFT)
                expect(editor.get_by_label(expected[locale]['notes'], exact=False)).to_be_visible()
                assert PLAN_TITLE in editor.inner_text() or editor.locator('input').first.input_value() == PLAN_TITLE
                metrics = gm.locator('[data-manager-view=sessions]').evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                assert gm.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                gm.screenshot(path=str(output / f'planner-{locale}-320.png'), full_page=True)
                modal, _ = compare(asset_journal, asset_revision, label='Comparar')
                with gm.expect_response(lambda response: restore_request(response.request)) as response:
                    modal.locator('[type=submit]').click()
                assert response.value.status == 400, response.value.text()
                expect(modal.locator('[role=alert]')).to_have_text(expected[locale]['error'])
                assert journal_rows() == before
                metrics = modal.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                gm.screenshot(path=str(output / f'missing-attachment-error-{locale}-320.png'), full_page=True)
                gm.keyboard.press('Escape')
                expect(modal).to_have_count(0)
                cases.append({'case': f'translated-dashboard-planner-and-native-error-{locale}-320-preserve-authored-content'})
            assert not errors, errors
            assert not dialogs, dialogs
            assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
        except Exception:
            (output / 'progress.json').write_text(json.dumps({'cases': cases, 'pageErrors': errors,
                'nativeDialogs': dialogs, 'failedRequests': failed}, indent=2), encoding='utf-8')
            for name, page in pages.items():
                page.screenshot(path=str(output / f'failure-{name}.png'), full_page=True)
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()
    return {'passed': True, 'cases': cases, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'assets': 'Only fixture-generated PNG and synthetic authored text.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
