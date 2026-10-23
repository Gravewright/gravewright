"""Author typed journal links and preserve native resource permissions in real clients.

Uses generated campaign data, files and installation-local storage on a fresh
port. No operator campaign, configuration or running application is reused.
"""
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
from uuid import uuid4

from campaign_management import serve as serve_campaign
from map_builder import ROOT, MEASURE, change_locale, fixture_environment


SOURCE_NAME = 'Synthetic resource index for the northern observatory with a deliberately long journal title'
TARGET_NAME = 'Synthetic expedition archive and its deliberately long linked journal title'
PAGE_NAME = 'Synthetic public page about the northern lens'
PAGE_TEXT = 'Synthetic authored page: the northern lens points toward the river.'
QUEST_NAME = 'Synthetic quest to recover the observatory instruments'
CLOCK_NAME = 'Synthetic public expedition progress'
PRIVATE_CLOCK_NAME = 'SYNTHETIC_PRIVATE_RESOURCE: Observatory keeper preparations'
PRIVATE_CLOCK_TEXT = 'SYNTHETIC_PRIVATE_DESCRIPTION: The keeper concealed the northern lens.'
CLUE_NAME = 'Synthetic discovered route to the observatory'
CLUE_TEXT = 'Synthetic public finding: the western bridge remains intact.'
PRIVATE_NOTES = 'SYNTHETIC_JOURNAL_GM_NOTES: The keeper concealed the eastern passage.'
PLAYER_NOTES = 'Synthetic player-authored notes retained while resource access changes.'
LEGACY_LABEL = 'Synthetic legacy page link'


def document(text):
    return {'format': 'gw-journal-doc-v1', 'version': 1,
            'doc': {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': text}]}]}}


def serve(fixture, port):
    from django.core import management

    original = management.call_command

    def command(name, *args, **kwargs):
        if name == 'runserver':
            from gravewright.actors.models import Actor
            from gravewright.campaigns.models import Campaign, SessionPlan, CampaignEvent
            from gravewright.items.models import Item, Folder as ItemFolder
            from gravewright.journals.data import normalize_data_for
            from gravewright.journals.models import Journal, Folder
            from gravewright.table.models import DocumentAccess, MindMap, ProgressClock, ProgressClue

            seed_file = fixture / 'seed.json'
            seed = json.loads(seed_file.read_text(encoding='utf-8'))
            campaign = Campaign.objects.get(pk=seed['campaign'])
            player = campaign.memberships.get(role='player').user_id
            actor = Actor.objects.get(pk=seed['actor'])
            actor.permissions = {'default': 'read', str(player): 'owner'}
            actor.save(update_fields=['permissions'])
            folder = Folder.objects.create(campaign=campaign, creator=campaign.owner, name='Synthetic journal archive folder')
            target = Journal.objects.create(campaign=campaign, creator=campaign.owner, folder=folder,
                title=TARGET_NAME, visibility='shared', data=normalize_data_for('diary', {
                    'content': document('Synthetic public archive opening.'),
                    'sections': [{'id': 'public-page', 'title': PAGE_NAME, 'kind': 'text', 'audience': 'public', 'content': document(PAGE_TEXT)},
                                 {'id': 'gm-page', 'title': 'SYNTHETIC_PRIVATE_PAGE', 'kind': 'text', 'audience': 'gm', 'content': document(PRIVATE_NOTES)}],
                    'gm': {'notes': document(PRIVATE_NOTES)}}))
            quest = Journal.objects.create(campaign=campaign, creator=campaign.owner, title=QUEST_NAME,
                type='quest', visibility='shared', data=normalize_data_for('quest', {'status': 'available',
                    'public': {'description': document('Synthetic public quest description: recover the northern lens.')}}))
            legacy_href = f'/game/{campaign.pk}?document=journal:{target.pk}&page=public-page'
            opening = document('Synthetic resource index. ')
            opening['doc']['content'][0]['content'].extend([
                {'type': 'text', 'text': LEGACY_LABEL, 'marks': [{'type': 'link', 'attrs': {'href': legacy_href}}]},
                {'type': 'text', 'text': ' Synthetic authored text remains separate from linked resource metadata. '}])
            source = Journal.objects.create(campaign=campaign, creator=campaign.owner, title=SOURCE_NAME,
                visibility='shared', data=normalize_data_for('diary', {'content': opening, 'gm': {'notes': document(PRIVATE_NOTES)}}))
            scratch = Journal.objects.create(campaign=campaign, creator=campaign.owner,
                title='Synthetic empty page for reference keyboard input', visibility='shared',
                data=normalize_data_for('diary', {'sections': [{'id': 'scratch', 'title': 'Synthetic reference input page',
                    'kind': 'text', 'content': {'format': 'gw-journal-doc-v1', 'version': 1,
                        'doc': {'type': 'doc', 'content': [{'type': 'paragraph'}]}}}]}))
            DocumentAccess.objects.create(campaign=campaign, kind='journals', resource_id=str(source.pk),
                                          grants={'default': 'read', str(player): 'owner'})
            item_folder = ItemFolder.objects.create(campaign=campaign, name='Synthetic expedition equipment folder')
            item = Item.objects.create(campaign=campaign, folder=item_folder, name='Synthetic brass observatory lens',
                system_id=campaign.system, type='synthetic-item', permissions={'default': 'read'},
                data={'description': 'Synthetic public item description: a brass observation lens.'})
            clock = ProgressClock.objects.create(campaign=campaign, name=CLOCK_NAME, segments=6, value=2,
                visibility='players', description='Synthetic public clock description.')
            private_clock = ProgressClock.objects.create(campaign=campaign, name=PRIVATE_CLOCK_NAME,
                segments=4, value=1, visibility='gm', description=PRIVATE_CLOCK_TEXT)
            clue = ProgressClue.objects.create(campaign=campaign, name=CLUE_NAME, segments=3, value=3,
                visibility='players', content=CLUE_TEXT, gm_notes=PRIVATE_NOTES)
            mindmap = MindMap.objects.create(campaign=campaign, name='Synthetic expedition relationships', visibility='players',
                document={'nodes': [{'id': str(uuid4()), 'parentId': None, 'label': 'Synthetic expedition root',
                    'notes': 'Synthetic public mind-map notes.', 'color': '#c9a44c', 'x': 0, 'y': 0,
                    'collapsed': False, 'completed': False, 'links': []}], 'edges': []})
            plan = SessionPlan.objects.create(campaign=campaign, title='Synthetic expedition session plan', notes='Synthetic GM session notes.')
            event = CampaignEvent.objects.create(campaign=campaign, title='Synthetic observatory timeline event',
                world_date='Synthetic day 12', description='Synthetic GM timeline description.')
            seed.update(sourceJournal=str(source.pk), scratchJournal=str(scratch.pk), targetJournal=str(target.pk), quest=str(quest.pk),
                item=str(item.pk), itemFolder=str(item_folder.pk), journalFolder=str(folder.pk), clock=str(clock.pk),
                privateClock=str(private_clock.pk), clue=str(clue.pk), mindmap=str(mindmap.pk),
                sessionPlan=str(plan.pk), campaignEvent=str(event.pk), player=str(player))
            seed_file.write_text(json.dumps(seed, indent=2), encoding='utf-8')
        return original(name, *args, **kwargs)

    management.call_command = command
    try:
        serve_campaign(fixture, port)
    finally:
        management.call_command = original


def control_state(fixture):
    database = (fixture / 'review.sqlite3').resolve()
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
        return {table: sorted(connection.execute('SELECT * FROM "' + table + '"').fetchall(), key=repr)
                for table in ('gravewright_maps_broadcast', 'gravewright_maps_scenenavigation', 'gravewright_realtime_presenceconnection')}


def stored_journal(fixture, identifier):
    database = (fixture / 'review.sqlite3').resolve()
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
        row = connection.execute('SELECT data FROM gravewright_journals_journal WHERE id = ?',
                                 (identifier.replace('-', ''),)).fetchone()
        return json.loads(row[0])


def typed_references(value):
    if isinstance(value, dict):
        result = [value['attrs']['reference']] if value.get('type') == 'gwResourceLink' else []
        return result + [reference for child in value.values() for reference in typed_references(child)]
    if isinstance(value, list):
        return [reference for child in value for reference in typed_references(child)]
    return []


def check_browser(base, seed, output, executable, fixture):
    from playwright.sync_api import expect, sync_playwright

    campaign, source_id = seed['campaign'], seed['sourceJournal']
    cases, errors, dialogs, failed, contexts = [], [], [], [], []
    pages, sockets = {}, {}
    before_manager = control_state(fixture)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))

        def client(name, role, *, manager=False):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 1000})
            contexts.append(context); context.add_cookies([{**seed['sessions'][role], 'url': base}])
            context.add_init_script('''(()=>{
              const Native=window.WebSocket;window.__heldJournalWrites=[];
              window.__resourceEvents=[];
              window.__resourcePointerEvents=[];
              for(const type of ['pointerdown','pointerup','click'])addEventListener(type,event=>{
                const link=event.target.closest?.('[data-gw-resource-link]');
                window.__resourcePointerEvents.push({type,at:performance.now(),x:event.clientX,y:event.clientY,
                  tag:event.target.tagName,link:link?.textContent,state:link?.dataset.resourceState,
                  expected:window.__expectedResourceClick});
                if(window.__resourcePointerEvents.length>60)window.__resourcePointerEvents.shift();
              },true);
              for(const type of ['gravewright:resources','gravewright:api-event','gravewright:journals',
                'gravewright:maps','gravewright:map-layers','gravewright:actors.state','gravewright:access-revoked'])
                addEventListener(type,event=>{const text=JSON.stringify(event.detail)||'';
                  window.__resourceEvents.push({type,at:performance.now(),module:event.detail?.module,
                    apiType:event.detail?.type,length:text.length,
                    hash:Array.from(text).reduce((hash,char)=>(Math.imul(hash,31)+char.charCodeAt(0))|0,0)});
                  if(window.__resourceEvents.length>120)window.__resourceEvents.shift();});
              window.__releaseJournalWrites=()=>{window.__holdJournalId=null;
                for(const row of window.__heldJournalWrites.splice(0))Native.prototype.send.call(row.socket,row.data);};
              window.WebSocket=class extends Native{send(data){let message;try{message=JSON.parse(data)}catch{}
                if(window.__holdJournalId&&message?.type==='journals.command'&&message.payload?.action==='update'
                  &&message.payload.data?.journal_id===window.__holdJournalId){window.__heldJournalWrites.push({socket:this,data});return;}
                return super.send(data);}};
            })();''')
            page = context.new_page(); pages[name], sockets[name] = page, []
            page.on('pageerror', lambda error: errors.append({'client': name, 'message': error.stack or str(error)}))
            page.on('requestfailed', lambda request: failed.append({'client': name, 'url': request.url, 'error': request.failure}))
            page.on('dialog', lambda dialog: (dialogs.append({'client': name, 'message': dialog.message}), dialog.dismiss()))
            page.on('websocket', lambda stream: sockets[name].append(stream.url))
            response = page.goto(f'/campaigns/{campaign}/manage?section=journals' if manager else f'/game/{campaign}')
            assert response.ok, (name, response.status)
            ready(page, manager=manager)
            return page

        def ready(page, *, manager=False):
            if manager:
                expect(page.locator('[data-manager-ready=true]')).to_be_attached(timeout=30000)
            else:
                page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime && !!window.gravewrightJournals')
                expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def open_journal(page, identifier=source_id, page_id=None):
            # The link helper neutralizes cached names while its first source
            # read checks access. Wait for that actual read, then interact.
            if typed_references(read_journal(page, identifier)):
                with page.expect_response(lambda response: response.url.split('?')[0].endswith(
                        f'/api/containers/{campaign}/journals') and response.request.method == 'GET') as source:
                    page.evaluate('([id,page])=>gravewrightJournals.open(id,page)', [identifier, page_id])
                assert source.value.ok, source.value.text()
                source.value.json()
            else:
                page.evaluate('([id,page])=>gravewrightJournals.open(id,page)', [identifier, page_id])
            window = page.locator(f'.journal-window[data-journal-id="{identifier}"]')
            expect(window).to_be_visible()
            return window

        def close_journal(window):
            window.locator('[data-action=close]').click(); expect(window).to_have_count(0)

        def read_journal(page, identifier=source_id):
            response = page.request.get(f'/api/containers/{campaign}/journals')
            assert response.ok, response.text()
            return next(row for row in response.json()['journals'] if row['id'] == identifier)

        def flush(page, window, identifier=source_id):
            assert page.evaluate('id=>gravewrightJournals.flush(id)', identifier)
            expect(window.locator('.journal-window__error')).to_be_hidden()

        def insert(page, window, kind, label):
            surface = window.locator('.ProseMirror[contenteditable=true]').first
            surface.focus(); page.keyboard.press('Control+End'); page.keyboard.type(' @')
            choose_reference(page, kind, label)
            expect(window.locator('[data-gw-resource-link][data-resource-state=available]').filter(has_text=label)).to_have_count(1)

        def choose_reference(page, kind, label):
            picker = page.locator('[data-resource-picker]')
            expect(picker).to_be_visible()
            picker.locator('input[type=search]').fill(label)
            picker.locator('select:not([size])').select_option(kind)
            expect(picker.locator('select[size] option')).to_have_count(1)
            expect(picker.locator('select[size] option')).to_have_text(label)
            picker.locator('select[size]').select_option('0'); picker.locator('[type=submit]').click()
            expect(picker).to_have_count(0)

        def clear_surface(page, window):
            surface = window.locator('.ProseMirror[contenteditable=true]').first
            surface.focus(); page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
            return surface

        def atom(window, label):
            return window.locator('[data-gw-resource-link][data-resource-state=available]').filter(has_text=label)

        def click_atom(window, label):
            for _ in range(5):
                link = atom(window, label)
                expect(link).to_be_visible()
                link.scroll_into_view_if_needed()
                # Inline fragments need an actual text point; the union's centre
                # can fall between lines. Only retry when captured input proves
                # the source became disabled during an authorization refresh.
                point = link.evaluate('''element=>{
                  const box=Array.from(element.getClientRects()).find(box=>box.width&&box.height);
                  return {x:box.x+Math.min(8,box.width/2),y:box.y+box.height/2};
                }''')
                token = str(uuid4())
                window.page.evaluate('value=>window.__expectedResourceClick=value',
                                     {'label': label, 'point': point, 'token': token})
                window.page.mouse.click(point['x'], point['y'])
                clicks = window.page.evaluate('''token=>window.__resourcePointerEvents.filter(
                  row=>row.type==='click'&&row.expected?.token===token)''', token)
                assert len(clicks) == 1, clicks
                if clicks[0].get('state') == 'unavailable': continue
                assert clicks[0].get('link') == label and clicks[0].get('state') == 'available', clicks
                return
            raise AssertionError(f'Resource did not remain available for a click: {label}')

        def preview(page, window, label):
            click_atom(window, label)
            modal = page.locator('[data-resource-preview]')
            expect(modal).to_be_visible()
            expect(modal.locator('header strong')).to_have_text(label)
            return modal

        def close_preview(modal):
            modal.locator('header button').click(); expect(modal).to_have_count(0)

        def clock_visibility(page, identifier, visibility):
            return page.evaluate('''async ([campaign,id,visibility])=>{
              const api=gravewright.forTable(campaign),row=(await api.clocks.state()).clocks.find(row=>row.id===id);
              return api.clocks.update({id,version:row.version,visibility});
            }''', [campaign, identifier, visibility])

        try:
            manager = client('manager', 'gm', manager=True)
            journal = open_journal(manager)
            catalog = manager.evaluate('campaign=>gravewright.forTable(campaign).journals.resources({limit:200})', campaign)
            assert len(catalog['kinds']) >= 37
            candidates = [
                ('actor', 'Synthetic mapped hero', seed['actor']),
                ('journal', TARGET_NAME, seed['targetJournal']),
                ('journal-page', PAGE_NAME, seed['targetJournal']),
                ('journal', QUEST_NAME, seed['quest']),
                ('item', 'Synthetic brass observatory lens', seed['item']),
                ('scene', 'Players remain here', seed['broadcastScene']),
                ('clock', CLOCK_NAME, seed['clock']),
                ('clue', CLUE_NAME, seed['clue']),
                ('mindmap', 'Synthetic expedition relationships', seed['mindmap']),
                ('track', 'Synthetic local preview', seed['previewTrack']),
                ('journal-folder', 'Synthetic journal archive folder', seed['journalFolder']),
                ('item-folder', 'Synthetic expedition equipment folder', seed['itemFolder']),
                ('session-plan', 'Synthetic expedition session plan', seed['sessionPlan']),
                ('campaign-event', 'Synthetic observatory timeline event', seed['campaignEvent']),
                ('clock', PRIVATE_CLOCK_NAME, seed['privateClock']),
            ]
            for kind, label, identifier in candidates:
                insert(manager, journal, kind, label)
            flush(manager, journal)
            saved = read_journal(manager)
            references = typed_references(saved['content_doc'])
            assert len(references) == len(candidates), references
            assert any(ref.get('pageId') == 'public-page' for ref in references)
            assert LEGACY_LABEL in json.dumps(saved) and '&page=public-page' in json.dumps(saved)
            assert not sockets['manager'] and control_state(fixture) == before_manager
            expect(journal.locator('[data-gw-resource-link][data-resource-state=available]')).to_have_count(len(candidates))
            for _, label, _ in candidates:
                expect(atom(journal, label)).to_be_visible()
            manager.screenshot(path=str(output / 'journal-resource-index-manager-1440.png'), full_page=True)
            cases.append({'case': 'manager-inserts-native-campaign-resource-kinds-and-page-destinations-without-game-socket-or-presence', 'insertedKinds': sorted({row[0] for row in candidates})})

            scratch = open_journal(manager, seed['scratchJournal'])
            expect(scratch.locator('[data-journal-resource-insert]')).to_have_count(0)
            surface = scratch.locator('.ProseMirror[contenteditable=true]').first
            expect(surface.locator('.is-empty[data-placeholder]')).to_have_attribute(
                'data-placeholder', 'Type / to insert blocks or @ to insert references')
            surface.focus(); manager.keyboard.type('@')
            picker = manager.locator('[data-resource-picker]'); expect(picker).to_be_visible()
            manager.keyboard.press('Escape'); expect(picker).to_have_count(0)
            expect(surface).to_have_text('@')
            clear_surface(manager, scratch); manager.keyboard.type('name@example.com')
            expect(manager.locator('[data-resource-picker]')).to_have_count(0)
            expect(surface).to_have_text('name@example.com')
            manager.keyboard.type(' @'); expect(picker).to_be_visible()
            picker.locator('header button').click(); expect(picker).to_have_count(0)
            expect(surface).to_have_text('name@example.com @')
            surface.focus(); manager.keyboard.press('Control+End'); manager.keyboard.press('Enter'); manager.keyboard.type('/')
            slash = manager.locator('.journal-rich-text__commands'); expect(slash).to_be_visible()
            slash.get_by_role('option', name='Text', exact=True).click(); expect(slash).to_have_count(0)
            expect(surface).to_contain_text('name@example.com @')
            flush(manager, scratch, seed['scratchJournal'])
            assert not typed_references(read_journal(manager, seed['scratchJournal']))
            cases.append({'case': 'at-sign-cancel-keeps-literal-text-emails-do-not-trigger-and-slash-blocks-still-insert'})

            surface = clear_surface(manager, scratch)
            prefix, suffix = 'Synthetic left ', ' Synthetic right'
            manager.keyboard.type(prefix + suffix); manager.keyboard.press('Control+Home')
            for _ in prefix: manager.keyboard.press('ArrowRight')
            manager.keyboard.type('@'); expect(picker).to_be_visible()
            # Tiptap exposes its instance on its native contenteditable node.
            # Move the editor selection while the modal is open: confirmation
            # must still replace only the original typed @ range.
            surface.evaluate('''node=>{
              const editor=node.editor;
              if(!editor?.commands?.setTextSelection)throw Error('Native editor instance missing.');
              editor.commands.setTextSelection({from:1,to:editor.state.doc.content.size-1});
            }''')
            choose_reference(manager, 'actor', 'Synthetic mapped hero')
            flush(manager, scratch, seed['scratchJournal'])
            saved_scratch = stored_journal(fixture, seed['scratchJournal'])['sections'][0]['content']['doc']['content'][0]['content']
            assert saved_scratch[0]['type'] == 'text' and saved_scratch[0]['text'] == prefix, saved_scratch
            assert saved_scratch[-1]['type'] == 'text' and saved_scratch[-1]['text'].endswith(suffix), saved_scratch
            assert '@' not in ''.join(row.get('text', '') for row in saved_scratch)
            projected_scratch = read_journal(manager, seed['scratchJournal'])['sections'][0]['content']
            assert [ref['id'] for ref in typed_references(projected_scratch)] == [seed['actor']]
            close_journal(scratch)
            cases.append({'case': 'at-confirmation-replaces-only-the-captured-trigger-range-after-editor-selection-changes'})

            close_journal(journal)
            manager.reload(); ready(manager, manager=True); journal = open_journal(manager)
            expect(journal.locator('[data-gw-resource-link]')).to_have_count(len(candidates))
            for label, expected in ((CLOCK_NAME, '2/6'), (CLUE_NAME, CLUE_TEXT),
                                    ('Synthetic journal archive folder', TARGET_NAME),
                                    ('Synthetic expedition session plan', 'Synthetic GM session notes.')):
                modal = preview(manager, journal, label)
                expect(modal).to_contain_text(expected)
                close_preview(modal)
            click_atom(journal, PAGE_NAME)
            linked = manager.locator(f'.journal-window[data-journal-id="{seed["targetJournal"]}"]')
            expect(linked).to_be_visible()
            expect(linked).to_contain_text(PAGE_TEXT)
            linked.locator('.ProseMirror').first.focus()
            expect(linked.locator('.ProseMirror').first).to_be_focused()
            close_journal(linked)
            click_atom(journal, 'Synthetic mapped hero')
            actor = manager.locator('.actor-directory__sheet')
            expect(actor).to_be_visible()
            actor.locator('[data-window=close]').click(); expect(actor).to_have_count(0)
            click_atom(journal, 'Synthetic brass observatory lens')
            item = manager.locator('.item-sheet'); expect(item).to_be_visible()
            item.locator('[data-close]').click(); expect(item).to_have_count(0)
            click_atom(journal, 'Synthetic expedition relationships')
            mindmap = manager.locator(f'[data-mindmap-editor="{seed["mindmap"]}"]')
            expect(mindmap).to_be_visible(); expect(mindmap).to_contain_text('Synthetic expedition root')
            mindmap.locator('.mindmap-editor__header > button').click(); expect(mindmap).to_have_count(0)
            click_atom(journal, 'Players remain here')
            expect(manager.locator('[data-manager-view=maps]')).to_be_visible()
            expect(manager.locator('[data-manager-scene]')).to_have_value(seed['broadcastScene'])
            click_atom(journal, QUEST_NAME)
            quest = manager.locator(f'.journal-window[data-journal-id="{seed["quest"]}"]')
            expect(quest).to_be_visible(); expect(quest.locator('.quest-sheet')).to_be_visible()
            close_journal(quest)
            assert control_state(fixture) == before_manager and not sockets['manager']
            cases.append({'case': 'saved-inline-links-reopen-and-read-native-previews-character-sheet-and-an-exact-journal-page'})

            # Legacy anchors retain their native page navigation alongside atoms.
            journal.get_by_role('link', name=LEGACY_LABEL, exact=True).click()
            legacy = manager.locator(f'.journal-window[data-journal-id="{seed["targetJournal"]}"]')
            expect(legacy).to_be_visible(); expect(legacy).to_contain_text(PAGE_TEXT)
            close_journal(legacy)
            cases.append({'case': 'existing-journal-page-hyperlinks-remain-actionable-after-typed-reference-edits'})

            player = client('player', 'player'); streamer = client('streamer', 'streamer')
            player_journal = open_journal(player); stream_journal = open_journal(streamer)
            for target, window in ((player, player_journal), (streamer, stream_journal)):
                projection = read_journal(target)
                encoded = json.dumps(projection)
                assert PRIVATE_CLOCK_NAME not in encoded and seed['privateClock'] not in encoded and PRIVATE_CLOCK_TEXT not in encoded
                assert seed['sessionPlan'] not in encoded and seed['campaignEvent'] not in encoded
                assert PRIVATE_NOTES not in encoded and PRIVATE_NOTES not in window.inner_text()
                expect(window).not_to_contain_text(PRIVATE_CLOCK_NAME)
                expect(window).to_contain_text('Unavailable resource')
            expect(player_journal.locator('.ProseMirror[contenteditable=true]')).to_have_count(1)
            expect(player_journal.locator('[data-journal-resource-insert]')).to_have_count(0)
            expect(stream_journal.locator('[data-journal-resource-insert]')).to_have_count(0)
            expect(stream_journal.locator('.ProseMirror[contenteditable=true]')).to_have_count(0)
            cases.append({'case': 'player-owner-can-edit-while-streamer-is-readonly-and-private-target-names-identities-and-gm-notes-are-redacted'})

            surface = player_journal.locator('.ProseMirror[contenteditable=true]').first
            surface.focus(); player.keyboard.press('Control+End'); player.keyboard.type(' ' + PLAYER_NOTES)
            flush(player, player_journal)
            assert PLAYER_NOTES in json.dumps(read_journal(player))
            hidden_refs = typed_references(read_journal(player)['content_doc'])
            assert any(ref.get('unavailable') is True and ref.get('key') for ref in hidden_refs)
            gm_refs = typed_references(read_journal(manager)['content_doc'])
            assert any(ref.get('id') == seed['privateClock'] for ref in gm_refs)
            cases.append({'case': 'player-owner-resave-preserves-authorized-text-and-opaque-existing-private-references'})

            player.evaluate('id=>window.__holdJournalId=id', source_id)
            surface = player_journal.locator('.ProseMirror[contenteditable=true]').first
            surface.focus(); player.keyboard.press('Control+End')
            pending_notes = ' Synthetic draft typed before revoking a linked clock.'
            player.keyboard.type(pending_notes)
            player.wait_for_function('window.__heldJournalWrites.length===1')
            clock_visibility(manager, seed['clock'], 'gm')
            expect(player_journal).not_to_contain_text(CLOCK_NAME, timeout=15000)
            expect(player_journal).to_contain_text(pending_notes.strip())
            player.evaluate('window.__releaseJournalWrites()')
            flush(player, player_journal)
            assert pending_notes.strip() in json.dumps(read_journal(player))
            assert any(ref.get('id') == seed['clock'] for ref in typed_references(read_journal(manager)['content_doc']))
            clock_visibility(manager, seed['clock'], 'players')
            expect(atom(player_journal, CLOCK_NAME)).to_be_visible(timeout=15000)
            cases.append({'case': 'live-revocation-during-pending-player-autosave-preserves-typed-draft-and-hidden-target-on-acknowledgement'})

            # Capture an authorized resolve response, revoke the target while
            # it is delayed, then release it. The old response must not open a
            # late preview containing the former resource's metadata.
            authorized = player.request.get(f'/api/containers/{campaign}/journals/resolve',
                params={'reference': json.dumps({'kind': 'clock', 'id': seed['clock']})})
            assert authorized.ok and CLOCK_NAME in authorized.text()
            held_resolve = {}
            def delay_resolve(route):
                if held_resolve or seed['clock'] not in route.request.url:
                    route.continue_(); return
                held_resolve['route'] = route
            resolve_pattern = '**/journals/resolve?*'
            player.route(resolve_pattern, delay_resolve)
            try:
                with player.expect_request(lambda request: '/resolve' in request.url and seed['clock'] in request.url):
                    click_atom(player_journal, CLOCK_NAME)
                deadline = time.monotonic() + 5
                while not held_resolve and time.monotonic() < deadline: player.wait_for_timeout(20)
                assert held_resolve
                clock_visibility(manager, seed['clock'], 'gm')
                expect(player_journal).not_to_contain_text(CLOCK_NAME, timeout=15000)
                held_resolve['route'].fulfill(status=200, content_type='application/json', body=authorized.text())
                player.wait_for_timeout(150)
                expect(player.locator('[data-resource-preview]')).to_have_count(0)
            finally:
                if held_resolve:
                    try: held_resolve['route'].abort()
                    except Exception: pass  # Already fulfilled or cancelled by the browser.
                player.unroute(resolve_pattern, delay_resolve)
            clock_visibility(manager, seed['clock'], 'players')
            expect(atom(player_journal, CLOCK_NAME)).to_be_visible(timeout=15000)
            cases.append({'case': 'delayed-authorized-resolve-cannot-open-a-stale-preview-after-resource-revocation'})

            live = preview(streamer, stream_journal, CLOCK_NAME)
            clock_visibility(manager, seed['clock'], 'gm')
            expect(live).to_have_count(0)
            expect(player_journal).not_to_contain_text(CLOCK_NAME, timeout=15000)
            expect(stream_journal).not_to_contain_text(CLOCK_NAME, timeout=15000)
            hidden = read_journal(player)
            assert seed['clock'] not in json.dumps(hidden) and CLOCK_NAME not in json.dumps(hidden)
            clock_visibility(manager, seed['clock'], 'players')
            expect(atom(player_journal, CLOCK_NAME)).to_be_visible(timeout=15000)
            cases.append({'case': 'live-target-revocation-removes-public-metadata-and-closes-an-open-resource-preview'})

            # A deleted discovered clue becomes neutral without invalidating
            # the surrounding journal or the remaining resource references.
            manager.evaluate('''async ([campaign,id])=>{
              const api=gravewright.forTable(campaign),row=(await api.clues.state()).clues.find(row=>row.id===id);
              return api.clues.delete({id,version:row.version});
            }''', [campaign, seed['clue']])
            expect(player_journal).not_to_contain_text(CLUE_NAME, timeout=15000)
            expect(player_journal).to_contain_text(PLAYER_NOTES)
            flush(player, player_journal)
            assert seed['clue'] not in json.dumps(read_journal(manager)['content_doc'])
            assert any(ref.get('id') == seed['clue'] for ref in typed_references(stored_journal(fixture, source_id)))
            cases.append({'case': 'deleted-resource-leaves-a-neutral-reference-and-does-not-remove-authored-journal-notes'})

            # Source ownership does not broaden resource authorization.
            invalid = player.evaluate('''async ([campaign,id])=>{
              try{return {ok:true,value:await gravewright.forTable(campaign).journals.resolve({reference:{kind:'journal',id}})};}
              catch(error){return {ok:false,status:error.status};}
            }''', [campaign, seed['foreignJournal']])
            assert not invalid['ok'] or invalid['value'] is None or (
                isinstance(invalid['value'], dict) and 'resource' in invalid['value'] and invalid['value']['resource'] is None), invalid
            cases.append({'case': 'source-journal-ownership-does-not-resolve-a-foreign-campaign-target'})

            close_journal(player_journal); close_journal(stream_journal); close_journal(journal)
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(manager, locale, campaign); manager.set_viewport_size({'width': 320, 'height': 844})
                manager.goto(f'/campaigns/{campaign}/manage?section=journals'); ready(manager, manager=True)
                narrow = open_journal(manager)
                metrics = narrow.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                manager.screenshot(path=str(output / f'journal-resource-sidebar-{locale}-320.png'), full_page=True)
                narrow.locator('[data-action=collapse]').click()
                expect(narrow.locator('.diary-workspace--collapsed')).to_be_visible()
                assert narrow.locator('.ProseMirror').first.bounding_box()['width'] >= 200
                expect(narrow.locator('[data-journal-resource-insert]')).to_have_count(0)
                surface = narrow.locator('.ProseMirror[contenteditable=true]').first
                surface.focus(); manager.keyboard.press('Control+End'); manager.keyboard.type(' @')
                picker = manager.locator('[data-resource-picker]'); expect(picker).to_be_visible()
                with manager.expect_response(lambda response: 'SYNTHETIC_NO_MATCH_739104' in response.url
                                             and response.request.method == 'GET') as empty_search:
                    picker.locator('input[type=search]').fill('SYNTHETIC_NO_MATCH_739104')
                assert empty_search.value.ok, empty_search.value.text()
                expect(picker.locator('select[size] option')).to_have_count(0)
                metrics = picker.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                manager.screenshot(path=str(output / f'journal-resource-search-{locale}-320.png'), full_page=True)
                picker.locator('header button').click(); expect(picker).to_have_count(0)
                surface.focus(); manager.keyboard.press('Control+End'); manager.keyboard.press('Backspace'); manager.keyboard.press('Backspace')
                manager.screenshot(path=str(output / f'journal-resource-links-{locale}-320.png'), full_page=True)
                close_journal(narrow)
                scratch = open_journal(manager, seed['scratchJournal'])
                scratch.locator('[data-action=collapse]').click()
                surface = clear_surface(manager, scratch)
                placeholder = {'en': 'Type / to insert blocks or @ to insert references',
                    'pt-BR': 'Digite / para inserir blocos ou @ para inserir referências',
                    'es': 'Escribe / para insertar bloques o @ para insertar referencias'}[locale]
                expect(surface.locator('.is-empty[data-placeholder]')).to_have_attribute('data-placeholder', placeholder)
                expect(scratch.locator('[data-journal-resource-insert]')).to_have_count(0)
                metrics = scratch.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                manager.screenshot(path=str(output / f'journal-resource-placeholder-{locale}-320.png'), full_page=True)
                manager.keyboard.type('@'); expect(picker).to_be_visible()
                manager.keyboard.press('Escape'); expect(picker).to_have_count(0)
                expect(surface).to_have_text('@')
                close_journal(scratch)
                cases.append({'case': f'{locale}-320px-long-linked-names-empty-search-and-translated-at-placeholder-remain-usable'})

            assert not errors, errors
            assert not dialogs, dialogs
            assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
        except Exception:
            (output / 'browser-diagnostics.json').write_text(json.dumps({'completedCases': cases,
                'pageErrors': errors, 'nativeDialogs': dialogs, 'failedRequests': failed,
                'resourceEvents': {name: page.evaluate('window.__resourceEvents')
                    for name, page in pages.items() if not page.is_closed()},
                'pointerEvents': {name: page.evaluate('window.__resourcePointerEvents')
                    for name, page in pages.items() if not page.is_closed()}}, indent=2), encoding='utf-8')
            for name, page in pages.items():
                if not page.is_closed(): page.screenshot(path=str(output / f'failure-{name}.png'), full_page=True)
            raise
        finally:
            for context in contexts: context.close()
            browser.close()
    return {'passed': True, 'cases': cases, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'assets': 'Synthetic PDFs, silent WAV, generated map images and authored journal/resource text only.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path); parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve: serve(args.fixture, args.port); return
    output = (args.output or ROOT / 'data/journal-resource-links' /
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
