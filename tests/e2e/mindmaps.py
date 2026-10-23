"""Exercise native mind-map authoring, live permissions and recipient link privacy.

Uses generated campaign assets, disposable accounts and installation-local
storage. It never opens or modifies the operator's campaign or running server.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
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


MAP_NAME = 'Synthetic relationships around the abandoned northern observatory and the lost expedition'
ROOT_LABEL = 'Synthetic expedition and its deliberately long central topic'
CHILD_LABEL = 'Synthetic eastern valley investigation'
SIBLING_LABEL = 'Synthetic keeper and the missing instruments'
NOTES = 'Synthetic authored notes: interview the keeper and inspect the northern lens. ' * 12
PLAYER_NOTES = 'Synthetic player findings: the western bridge is safe.'
DRAFT_ONE = 'Synthetic unsaved investigation notes: inspect the eastern gate.'
DRAFT_TWO = 'Synthetic unsaved investigation notes: inspect the eastern gate and preserve this draft.'
CLOCK_LABEL = 'SYNTHETIC_LINK_CLOCK: Observatory keeper preparations'
FRESH_CLOCK_LABEL = 'SYNTHETIC_DRAFT_LINK: Unpublished expedition route'


def serve(fixture, port):
    from django.core import management

    original = management.call_command

    def command(name, *args, **kwargs):
        if name == 'runserver':
            from django.conf import settings
            from django.test import Client
            from gravewright.accounts.models import User
            from gravewright.campaigns.models import Membership, Onboarding
            from gravewright.table.models import MindMap, ProgressClock

            seed_file = fixture / 'seed.json'
            seed = json.loads(seed_file.read_text(encoding='utf-8'))
            membership = Membership.objects.get(campaign_id=seed['campaign'], role='player')
            reader = User.objects.create_user('reader@mindmaps.test', 'synthetic-browser-pass', name='Synthetic reader')
            reader_member = Membership.objects.create(campaign_id=seed['campaign'], user=reader, role='player')
            Onboarding.objects.create(membership=reader_member, dismissed=True)
            client = Client(); client.force_login(reader)
            seed['sessions']['reader'] = {'name': settings.SESSION_COOKIE_NAME,
                                         'value': client.cookies[settings.SESSION_COOKIE_NAME].value}
            seed['player'] = str(membership.user_id)
            clock = ProgressClock.objects.create(campaign_id=seed['campaign'], name=CLOCK_LABEL,
                                                  segments=6, value=2, visibility='players')
            fresh = ProgressClock.objects.create(campaign_id=seed['campaign'], name=FRESH_CLOCK_LABEL,
                                                  segments=4, value=1, visibility='players')
            foreign = MindMap.objects.create(campaign_id=seed['otherCampaign'], name='Foreign synthetic mind map',
                document={'nodes': [{'id': str(uuid4()), 'label': 'Foreign private synthetic topic'}], 'edges': []})
            seed.update(clock=str(clock.pk), freshClock=str(fresh.pk), foreignMindmap=str(foreign.pk))
            seed_file.write_text(json.dumps(seed, indent=2), encoding='utf-8')
        return original(name, *args, **kwargs)

    management.call_command = command
    try:
        serve_campaign(fixture, port)
    finally:
        management.call_command = original


def stored_maps(fixture):
    database = (fixture / 'review.sqlite3').resolve()
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
        return {table: sorted(connection.execute('SELECT * FROM "' + table + '"').fetchall(), key=repr)
                for table in ('gravewright_table_mindmap', 'gravewright_table_mindmapreceipt')}


def check_browser(base, seed, output, executable, fixture):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs, failed, contexts = [], [], [], [], []
    pages, sockets, responses = {}, {}, {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))

        def client(name, role, *, manager=False):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 1000})
            contexts.append(context)
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            page = context.new_page()
            pages[name], sockets[name], responses[name] = page, [], []
            page.on('pageerror', lambda error: errors.append({'client': name, 'message': error.stack or str(error)}))
            page.on('requestfailed', lambda request: failed.append({'client': name, 'url': request.url, 'error': request.failure}))
            page.on('dialog', lambda dialog: (dialogs.append({'client': name, 'message': dialog.message}), dialog.dismiss()))
            page.on('websocket', lambda stream: sockets[name].append(stream.url))
            response = page.goto(f'/campaigns/{campaign}/manage?section=mindmaps' if manager else f'/game/{campaign}')
            assert response.ok, (name, response.status)
            ready(page, manager=manager)
            return page

        def ready(page, *, manager=False):
            if manager:
                expect(page.locator('[data-manager-ready=true]')).to_be_attached(timeout=30000)
                expect(page.locator('[data-manager-view=mindmaps]')).to_be_visible()
            else:
                page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime && !!window.gravewrightMindMaps')
                expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def api(page, action, payload=None):
            return page.evaluate('''async ([campaign,action,payload])=>{
              try{return {ok:true,value:await gravewright.forTable(campaign).mindmaps[action](payload||{})};}
              catch(error){return {ok:false,code:error.code,status:error.status,message:error.message};}
            }''', [campaign, action, payload])

        def read(page, identifier):
            result = api(page, 'read', {'id': identifier})
            assert result['ok'], result
            return result['value'].get('mindmap', result['value'])

        def state(page):
            result = api(page, 'state')
            assert result['ok'], result
            return result['value']

        def editor(page, identifier):
            return page.locator(f'[data-mindmap-editor="{identifier}"]')

        def open_map(page, identifier, node_id=None):
            page.evaluate('([id,node])=>gravewrightMindMaps.open(id,node)', [identifier, node_id])
            modal = editor(page, identifier)
            expect(modal).to_be_visible()
            return modal

        def topic(modal, identifier):
            return modal.locator(f'[data-mindmap-node-id="{identifier}"]')

        def selected(modal):
            return modal.locator('.mindmap-editor__topic--selected').get_attribute('data-mindmap-node-id')

        def field(modal, name, value):
            control = modal.locator(f'.mindmap-editor__inspector [name="{name}"]')
            control.fill(value)
            control.dispatch_event('change')

        def save(page, modal, identifier):
            modal.locator('[data-mindmap-save]').click()
            expect(modal.locator('.mindmap-editor__status')).to_have_text('Saved')
            expect(modal.locator('[data-mindmap-save]')).to_be_disabled()
            return read(page, identifier)

        def close(modal):
            modal.locator('.mindmap-editor__header > button').click()
            expect(modal).to_have_count(0)

        def permissions(page, identifier):
            with page.expect_response(lambda response: response.request.method == 'GET'
                                      and response.url.endswith('/modules-native/mindmaps')) as refreshed:
                page.locator('[data-manager-view=mindmaps]').get_by_role('button', name='Refresh mind maps', exact=True).click()
            assert refreshed.value.ok, refreshed.value.text()
            card = page.locator(f'[data-manager-view=mindmaps] [data-mindmap-id="{identifier}"]')
            card.get_by_role('button', name='Permissions', exact=True).click()
            modal = page.locator('.mindmap-form')
            expect(modal).to_be_visible()
            return modal

        def choose_clock(page, modal, label):
            modal.get_by_role('button', name='Link campaign resource', exact=True).click()
            picker = page.locator('.mindmap-resource-picker')
            expect(picker).to_be_visible()
            expect(picker.locator('select:not([size]) option')).to_have_count(38)
            picker.locator('input[type=search]').fill(label)
            picker.locator('select:not([size])').select_option('clock')
            expect(picker.locator('select[size] option')).to_have_count(1)
            expect(picker.locator('select[size] option')).to_have_text(label)
            picker.locator('select[size]').select_option('0')
            picker.locator('[type=submit]').click()
            expect(picker).to_have_count(0)

        def clock_visibility(page, identifier, visibility):
            return page.evaluate('''async ({campaign,id,visibility})=>{
              const api=gravewright.forTable(campaign),state=await api.clocks.state();
              const row=state.clocks.find(row=>row.id===id);
              return api.clocks.update({id,version:row.version,visibility});
            }''', {'campaign': campaign, 'id': identifier, 'visibility': visibility})

        def native_form(page, title):
            return page.locator('.mindmap-form').filter(has=page.locator('header strong', has_text=title))

        try:
            manager = client('manager', 'gm', manager=True)
            directory = manager.locator('[data-manager-view=mindmaps]')
            expect(directory).to_contain_text('No mind maps are available.')
            assert not sockets['manager']
            manager.screenshot(path=str(output / 'mindmaps-empty-manager-1440.png'), full_page=True)
            directory.get_by_role('button', name='New mind map', exact=True).click()
            creation = manager.locator('.mindmap-form')
            expect(creation.locator('[name=visibility]')).to_have_value('gm')
            creation.locator('[name=name]').fill(MAP_NAME)
            creation.locator('[type=submit]').click()
            modal = manager.locator('[data-mindmap-editor]')
            expect(modal).to_be_visible()
            identifier = modal.get_attribute('data-mindmap-editor')
            row = read(manager, identifier)
            assert row['visibility'] == 'gm' and row['editorIds'] == []
            root = row['document']['nodes'][0]['id']
            records.append({'case': 'gm-creates-a-private-map-from-empty-campaign-manager-without-a-game-socket'})

            for key in ('Enter', 'F2'):
                topic(modal, root).focus()
                manager.keyboard.press(key)
                expect(modal.locator('[name=label]')).to_be_focused()
            field(modal, 'label', ROOT_LABEL)
            field(modal, 'notes', NOTES)
            topic(modal, root).focus()
            manager.keyboard.press('Tab')
            expect(modal.locator('[data-mindmap-node-id]')).to_have_count(2)
            child = selected(modal); field(modal, 'label', CHILD_LABEL)
            field(modal, 'notes', 'Synthetic child notes: inspect the eastern lens.')
            modal.locator('[name=color]').evaluate("input=>{input.value='#438fc2';input.dispatchEvent(new Event('change',{bubbles:true}));}")
            topic(modal, child).focus()
            manager.keyboard.press('Shift+Tab')
            sibling = selected(modal); field(modal, 'label', SIBLING_LABEL)
            modal.get_by_role('button', name='Add root topic', exact=True).click()
            second_root = selected(modal); field(modal, 'label', 'Synthetic independent faction')
            modal.get_by_role('button', name='Fit map', exact=True).click()
            topic(modal, root).click()
            modal.get_by_role('button', name='Connect topics', exact=True).click()
            connection = native_form(manager, 'Connect topics')
            connection.locator('[name=to]').select_option(second_root)
            connection.locator('[name=label]').fill('Synthetic uncertain alliance')
            connection.locator('[type=submit]').click()
            expect(connection).to_have_count(0)
            catalog = api(manager, 'resources', {'limit': 200})
            assert catalog['ok'] and len(catalog['value']['kinds']) == 37, catalog
            choose_clock(manager, modal, CLOCK_LABEL)
            saved = save(manager, modal, identifier)
            by_id = {node['id']: node for node in saved['document']['nodes']}
            assert len({(node['x'], node['y']) for node in by_id.values()}) == len(by_id), 'New topics must not occupy another topic position.'
            assert by_id[child]['parentId'] == root and by_id[sibling]['parentId'] == root
            assert by_id[child]['color'] == '#438fc2' and by_id[root]['notes'] == NOTES
            assert len(saved['document']['edges']) == 1 and by_id[root]['links'][0]['id'] == seed['clock']
            manager.screenshot(path=str(output / 'mindmap-authored-editor-1440.png'), full_page=True)
            records.append({'case': 'author-roots-children-siblings-notes-colors-cross-connections-and-typed-links-from-37-kind-catalog'})

            # Resource previews perform a fresh native read and return focus.
            modal.get_by_role('button', name=CLOCK_LABEL, exact=True).click()
            preview = manager.locator('.mindmap-resource')
            expect(preview).to_be_visible()
            expect(preview).to_contain_text('2/6')
            manager.keyboard.press('Escape')
            expect(preview).to_have_count(0)
            expect(modal.get_by_role('button', name=CLOCK_LABEL, exact=True)).to_be_focused()
            records.append({'case': 'linked-clock-opens-native-progress-preview-and-escape-restores-focus'})

            modal.get_by_role('button', name='Fit map', exact=True).click()
            old = deepcopy(by_id[child])
            shape = topic(modal, child); box = shape.bounding_box()
            manager.mouse.move(box['x'] + 30, box['y'] + 25); manager.mouse.down()
            manager.mouse.move(box['x'] + 100, box['y'] + 75, steps=8); manager.mouse.up()
            expect(modal.locator('.mindmap-editor__status')).to_have_text('Unsaved changes')
            modal.get_by_role('button', name='Undo', exact=True).click()
            assert float(topic(modal, child).evaluate('el=>parseFloat(el.style.left)')) == old['x']
            modal.get_by_role('button', name='Redo', exact=True).click()
            moved = save(manager, modal, identifier)
            moved_child = next(node for node in moved['document']['nodes'] if node['id'] == child)
            assert moved_child['x'] != old['x'] and moved_child['y'] != old['y']
            current_left = float(topic(modal, child).evaluate('el=>parseFloat(el.style.left)'))
            box = topic(modal, child).bounding_box()
            manager.mouse.move(box['x'] + 30, box['y'] + 15); manager.mouse.down()
            manager.mouse.move(box['x'] + 85, box['y'] + 45, steps=5)
            manager.keyboard.press('Escape'); manager.mouse.up()
            expect(modal).to_be_visible()
            expect(manager.locator('.mindmap-form')).to_have_count(0)
            assert abs(float(topic(modal, child).evaluate('el=>parseFloat(el.style.left)')) - current_left) < .001
            expect(modal.locator('.mindmap-editor__status')).to_have_text('Saved')
            before_pan = stored_maps(fixture)
            world = modal.locator('.mindmap-editor__world')
            transform = world.evaluate('el=>el.style.transform')
            canvas = modal.locator('[data-mindmap-canvas]').bounding_box()
            manager.mouse.move(canvas['x'] + 10, canvas['y'] + 10); manager.mouse.down()
            manager.mouse.move(canvas['x'] + 70, canvas['y'] + 45, steps=8)
            manager.keyboard.press('Escape'); manager.mouse.up()
            assert world.evaluate('el=>el.style.transform') == transform
            expect(modal).to_be_visible()
            expect(manager.locator('.mindmap-form')).to_have_count(0)
            manager.mouse.move(canvas['x'] + 10, canvas['y'] + 10); manager.mouse.down()
            manager.mouse.move(canvas['x'] + 70, canvas['y'] + 45, steps=8); manager.mouse.up()
            assert world.evaluate('el=>el.style.transform') != transform
            transform = world.evaluate('el=>el.style.transform')
            modal.get_by_role('button', name='Zoom in', exact=True).click()
            assert world.evaluate('el=>el.style.transform') != transform
            assert stored_maps(fixture) == before_pan
            close(modal)
            manager.reload(); ready(manager, manager=True)
            modal = open_map(manager, identifier, child)
            assert abs(float(topic(modal, child).evaluate('el=>parseFloat(el.style.left)')) - moved_child['x']) < .001
            close(modal)
            records.append({'case': 'real-topic-drag-undo-redo-save-and-reload-persist-while-pan-and-zoom-remain-local'})

            access = permissions(manager, identifier)
            access.locator(f'[name=editor][value="{seed["player"]}"]').check()
            expect(access.locator('[name=visibility]')).to_have_value('gm')
            access.locator('[type=submit]').click(); expect(access).to_have_count(0)
            player = client('player', 'player')
            reader = client('reader', 'reader')
            streamer = client('streamer', 'streamer')
            assert identifier in {row['id'] for row in state(player)['mindmaps']}
            assert identifier not in {row['id'] for row in state(reader)['mindmaps']}
            assert identifier not in {row['id'] for row in state(streamer)['mindmaps']}
            expect(player.locator('[data-mindmaps-open]')).to_be_visible()
            player.locator('[data-mindmaps-open]').click()
            table_directory = player.locator('[data-mindmap-directory]')
            expect(table_directory).to_be_visible()
            table_directory.locator(f'[data-mindmap-id="{identifier}"] .mindmaps__open').click()
            player_map = open_map(player, identifier, root)
            player_map.locator('[name=notes]').fill(PLAYER_NOTES)
            with player.expect_response(lambda response: response.request.method == 'GET'
                                        and response.url.endswith('/modules-native/mindmaps')) as refreshed:
                clock_visibility(manager, seed['clock'], 'players')
            assert refreshed.value.ok, refreshed.value.text()
            expect(player_map.locator('[name=notes]')).to_have_value(PLAYER_NOTES)
            expect(player_map.locator('.mindmap-editor__status')).to_have_text('Unsaved changes')
            player_map.locator('[name=notes]').dispatch_event('change')
            player_saved = save(player, player_map, identifier)
            assert next(node['notes'] for node in player_saved['document']['nodes'] if node['id'] == root) == PLAYER_NOTES
            records.append({'case': 'explicitly-authorized-player-can-read-and-edit-a-gm-only-map-with-other-players-and-streamers-excluded'})

            access = permissions(manager, identifier)
            access.locator('[name=visibility]').select_option('players')
            access.locator('[type=submit]').click(); expect(access).to_have_count(0)
            for target in (reader, streamer):
                readonly = open_map(target, identifier, root)
                expect(readonly.locator('[data-edit-action]:enabled')).to_have_count(0)
                expect(readonly.locator('[name=notes]')).to_be_disabled()
                for key in ('Enter', 'F2'):
                    topic(readonly, root).focus()
                    target.keyboard.press(key)
                    expect(readonly.get_by_role('button', name=CLOCK_LABEL, exact=True)).to_be_focused()
                open_map(target, identifier, child)
                for key in ('Enter', 'F2'):
                    topic(readonly, child).focus()
                    target.keyboard.press(key)
                    expect(readonly.locator('.mindmap-editor__inspector')).to_be_focused()
            denied_before = stored_maps(fixture)
            for target in (reader, streamer):
                current = read(target, identifier)
                result = api(target, 'update', {'id': identifier, 'version': current['version'], 'name': 'Unauthorized overwrite'})
                assert not result['ok'] and result['status'] == 403, result
            for action, payload in (('read', {'id': seed['foreignMindmap']}),
                                    ('resolve', {'reference': {'kind': 'journal', 'id': seed['foreignJournal']}})):
                denied = api(player, action, payload)
                if action == 'read':
                    assert not denied['ok'] and denied['status'] == 404, denied
                else:
                    assert not denied['ok'] or denied['value'] is None or (
                        isinstance(denied['value'], dict) and 'resource' in denied['value'] and denied['value']['resource'] is None), denied
            assert stored_maps(fixture) == denied_before
            records.append({'case': 'public-readers-and-streamers-cannot-mutate-and-foreign-campaign-references-do-not-resolve'})

            # A newer canonical revision must not replace this browser's draft.
            field(player_map, 'notes', DRAFT_ONE)
            remote = read(manager, identifier)
            remote_graph = deepcopy(remote['document'])
            next(node for node in remote_graph['nodes'] if node['id'] == root)['notes'] = 'Synthetic concurrent GM revision.'
            changed = api(manager, 'update', {'id': identifier, 'version': remote['version'], 'document': remote_graph})
            assert changed['ok'], changed
            expect(player_map.locator('.mindmap-editor__status')).to_have_text('Saved version changed', timeout=15000)
            expect(player_map.locator('[name=notes]')).to_have_value(DRAFT_ONE)
            expect(player_map.locator('[data-mindmap-save]')).to_be_disabled()
            player_map.get_by_role('button', name='Reload saved map', exact=True).click()
            reload_prompt = native_form(player, 'Reload saved mind map')
            reload_prompt.get_by_role('button', name='Cancel', exact=True).click()
            expect(player_map.locator('[name=notes]')).to_have_value(DRAFT_ONE)
            player_map.get_by_role('button', name='Reload saved map', exact=True).click()
            reload_prompt = native_form(player, 'Reload saved mind map')
            reload_prompt.locator('[type=submit]').click(); expect(reload_prompt).to_have_count(0)
            expect(player_map.locator('[name=notes]')).to_have_value('Synthetic concurrent GM revision.')
            records.append({'case': 'concurrent-gm-revision-preserves-player-draft-until-an-explicit-confirmed-reload'})

            # Revoke a saved link while local text/history remain unsaved.
            field(player_map, 'notes', DRAFT_ONE); field(player_map, 'notes', DRAFT_TWO)
            expect(player_map).to_contain_text(CLOCK_LABEL)
            clock_visibility(manager, seed['clock'], 'gm')
            expect(player_map).not_to_contain_text(CLOCK_LABEL, timeout=15000)
            expect(player_map).to_contain_text('Unavailable resource')
            expect(player_map.locator('[name=notes]')).to_have_value(DRAFT_TWO)
            player_map.get_by_role('button', name='Undo', exact=True).click()
            expect(player_map.locator('[name=notes]')).to_have_value(DRAFT_ONE)
            expect(player_map).not_to_contain_text(CLOCK_LABEL)
            player_map.get_by_role('button', name='Redo', exact=True).click()
            expect(player_map.locator('[name=notes]')).to_have_value(DRAFT_TWO)
            hidden = read(player, identifier)
            hidden_link = next(node for node in hidden['document']['nodes'] if node['id'] == root)['links'][0]
            assert hidden_link['unavailable'] and 'id' not in hidden_link and 'kind' not in hidden_link and 'label' not in hidden_link
            player.screenshot(path=str(output / 'mindmap-player-hidden-link-draft-1440.png'), full_page=True)
            save(player, player_map, identifier)
            gm_link = next(node for node in read(manager, identifier)['document']['nodes'] if node['id'] == root)['links'][0]
            assert gm_link['id'] == seed['clock']
            clock_visibility(manager, seed['clock'], 'players')
            expect(player_map).to_contain_text(CLOCK_LABEL, timeout=15000)
            records.append({'case': 'live-resource-revocation-redacts-label-and-target-through-undo-redo-and-save-without-losing-draft-or-reference'})

            choose_clock(player, player_map, FRESH_CLOCK_LABEL)
            field(player_map, 'notes', 'Synthetic draft with a newly linked resource.')
            clock_visibility(manager, seed['freshClock'], 'gm')
            expect(player_map).not_to_contain_text(FRESH_CLOCK_LABEL, timeout=15000)
            expect(player_map.locator('[name=notes]')).to_have_value('Synthetic draft with a newly linked resource.')
            player_map.get_by_role('button', name='Undo', exact=True).click()
            expect(player_map).not_to_contain_text(FRESH_CLOCK_LABEL)
            clock_visibility(manager, seed['freshClock'], 'players')
            expect(player_map).to_contain_text(FRESH_CLOCK_LABEL, timeout=15000)
            save(player, player_map, identifier)
            assert len(next(node for node in read(manager, identifier)['document']['nodes'] if node['id'] == root)['links']) == 2
            records.append({'case': 'new-unsaved-resource-links-are-rechecked-live-with-history-and-authored-text-preserved'})

            field(player_map, 'notes', 'Synthetic close-cancellation draft.')
            player.keyboard.press('Escape')
            discard = native_form(player, 'Unsaved mind map')
            expect(discard).to_be_visible()
            discard.get_by_role('button', name='Cancel', exact=True).click()
            expect(player_map.locator('[name=notes]')).to_have_value('Synthetic close-cancellation draft.')
            player_map.locator('.mindmap-editor__header > button').click()
            discard = native_form(player, 'Unsaved mind map')
            discard.locator('[type=submit]').click()
            expect(player_map).to_have_count(0)
            records.append({'case': 'escape-and-close-ask-through-native-modal-and-cancel-preserves-unsaved-text'})

            # Long authored labels and empty states remain usable with each
            # installed locale; authored text never passes through translation.
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(manager, locale, campaign)
                manager.set_viewport_size({'width': 320, 'height': 844})
                manager.goto(f'/campaigns/{campaign}/manage?section=mindmaps'); ready(manager, manager=True)
                narrow = open_map(manager, identifier, root)
                expect(narrow.locator('[name=label]')).to_have_value(ROOT_LABEL)
                zoom_label = {'en': 'Zoom in', 'pt-BR': 'Aumentar zoom', 'es': 'Acercar'}[locale]
                scale_before = narrow.locator('.mindmap-editor__world').evaluate('el=>new DOMMatrix(getComputedStyle(el).transform).a')
                for _ in range(6):
                    narrow.get_by_role('button', name=zoom_label, exact=True).click()
                scale_after = narrow.locator('.mindmap-editor__world').evaluate('el=>new DOMMatrix(getComputedStyle(el).transform).a')
                assert scale_after > scale_before and scale_after >= 1, (locale, scale_before, scale_after)
                expect(topic(narrow, root)).to_be_in_viewport()
                metrics = narrow.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                manager.screenshot(path=str(output / f'mindmap-editor-{locale}-320.png'), full_page=True)
                narrow.locator('.mindmap-editor__header > button').click(); expect(narrow).to_have_count(0)
                directory_metrics = manager.locator('[data-manager-view=mindmaps]').evaluate(MEASURE)
                assert not directory_metrics['tiny'] and not directory_metrics['overflow'], (locale, directory_metrics)
                records.append({'case': f'{locale}-320px-editor-and-directory-preserve-authored-content-and-minimum-text-size'})

            assert not errors, errors
            assert not dialogs, dialogs
            assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
        except Exception:
            (output / 'browser-diagnostics.json').write_text(json.dumps({'completedCases': records,
                'pageErrors': errors, 'nativeDialogs': dialogs, 'failedRequests': failed}, indent=2), encoding='utf-8')
            for name, page in pages.items():
                if not page.is_closed():
                    page.screenshot(path=str(output / f'failure-{name}.png'), full_page=True)
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'assets': 'Synthetic PDFs, images, silent WAV and authored mind-map content only.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(args.fixture, args.port)
        return
    output = (args.output or ROOT / 'data/mindmaps' /
              datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError('Use a fresh, empty output directory.')
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / 'fixture'; fixture.mkdir()
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
                if server.poll() is not None:
                    raise RuntimeError(f"Fixture exited; inspect {output / 'server.log'}")
                try:
                    with urlopen(base, timeout=1): break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Fixture did not become ready.')
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
            report = check_browser(base, seed, output, args.browser_executable, fixture)
            (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps({'passed': True, 'cases': len(report['cases']), 'report': str(output / 'report.json')}))
        except Exception:
            (output / 'failure.txt').write_text(traceback.format_exc(), encoding='utf-8'); raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill(); server.wait()
            (output / 'server-exit.json').write_text(json.dumps({'pid': server.pid, 'exitCode': server.returncode}), encoding='utf-8')


if __name__ == '__main__':
    main()
