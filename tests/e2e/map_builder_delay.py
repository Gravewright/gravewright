"""Exercise authored Delay continuations and recovery in an isolated server.

The real Blueprint editor creates the graph, a player activates its lever and
the production server resumes it without a browser polling the scene. A restart
reuses only this scenario's disposable database, sessions and synthetic assets.
"""
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
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import (MEASURE, ROOT, builder_sidebar, builder_tool,
                         builder_workspace, change_locale, fixture_environment)
from map_builder_asset_removal import BuilderReview
from map_builder_reference import close_panel, set_name, upload_asset, wait_ready


def check_browser(base, seed, output, executable, restart):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    builder = f'/game/{campaign}/map-builder'
    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = player_context = None
        page = player = None

        def observe(target):
            target.on('pageerror', lambda error: errors.append(str(error)))
            target.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))

        def create_context(role, viewport=None):
            result = browser.new_context(base_url=base, viewport=viewport or {'width': 1440, 'height': 900})
            result.add_cookies([{**seed['sessions'][role], 'url': base}])
            return result

        context = create_context('gm')
        page = context.new_page()
        observe(page)
        review = BuilderReview(page, campaign)

        def open_editor(identifier, group='decorations'):
            builder_tool(page, 'select')
            builder_workspace(page)
            target = page.locator(f'[data-builder-{group}] [data-object-id="{identifier}"]')
            if group == 'doors':
                target.dblclick()
            else:
                box = target.bounding_box()
                page.mouse.click(box['x'] + box['width'] * .25, box['y'] + box['height'] * .25)
                builder_sidebar(page, 'selection')
                page.locator('[data-builder-edit-behavior]').click()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            return modal

        def card(modal, identifier):
            return modal.locator(f'[data-blueprint-node="{identifier}"]')

        def parameter(modal, identifier, name, value):
            control = card(modal, identifier).locator(f'[data-blueprint-param="{name}"]')
            if control.get_attribute('type') == 'checkbox':
                control.set_checked(value)
            elif control.evaluate('element=>element.tagName') == 'SELECT':
                control.select_option(str(value).lower() if isinstance(value, bool) else str(value))
            else:
                control.fill(str(value))
                control.dispatch_event('change')

        def add_node(modal, kind, **params):
            before = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            modal.locator('[data-blueprint-add]').click()
            modal.locator(f'[data-blueprint-pick-type="{kind}"]').click()
            after = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            identifier, = after - before
            for name, value in params.items():
                parameter(modal, identifier, name, value)
            return identifier

        def connect(modal, source, target):
            modal.locator('[data-blueprint-fit]').click()
            source.click()
            target.click()

        def execution_wire(modal, source, target):
            connect(modal, card(modal, source).locator('[data-blueprint-output=next]'),
                    card(modal, target).locator('[data-blueprint-input]'))

        def data_wire(modal, source, target):
            connect(modal, card(modal, source).locator('[data-blueprint-data-output=door]'),
                    card(modal, target).locator('[data-blueprint-data-input=target]'))

        def wait_game(target=None):
            target = target or page
            target.wait_for_url(f'{base}/game/{campaign}')
            target.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        try:
            page.goto(builder)
            wait_ready(page)
            set_name(page, 'Synthetic persistent delayed door')
            door_asset = upload_asset(page, 'door', 'Synthetic delayed door.png',
                                      harness.artwork('#426f95'))['id']
            lever_asset = upload_asset(page, 'decoration', 'Synthetic delayed lever.png',
                                       harness.artwork('#b47d32'))['id']
            builder_tool(page, 'door')
            page.locator('[data-builder-brush-material]').select_option(door_asset)
            review.stroke((8, 6), (10, 6))
            review.stroke((20, 6), (22, 6))
            builder_tool(page, 'light')
            review.stroke((12, 9), (12, 9))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=enabled]').uncheck()
            close_panel(page)
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(lever_asset)
            review.stroke((12, 12), (14, 14))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=behavior]').select_option('lever')
            close_panel(page)
            initial = review.save()
            door, protected_door = initial['document']['doors']
            light, = initial['document']['lights']
            lever, = initial['document']['decorations']

            modal = open_editor(lever['id'])
            modal.locator('[data-blueprint-state-port=on]').click()
            recipient = add_node(modal, 'reference', targetId=door['id'])
            opened = add_node(modal, 'state')
            data_wire(modal, recipient, opened)
            parameter(modal, opened, 'targetState', 'open')
            lit = add_node(modal, 'light', targetId=light['id'], enabled=True)
            delay = add_node(modal, 'delay')
            expect(card(modal, delay).locator('[data-blueprint-param=seconds]')).to_have_value('3')
            closed = add_node(modal, 'state')
            data_wire(modal, recipient, closed)
            parameter(modal, closed, 'targetState', 'closed')
            dark = add_node(modal, 'light', targetId=light['id'], enabled=False)
            connect(modal, modal.locator('[data-blueprint-state-port=on]'),
                    card(modal, opened).locator('[data-blueprint-input]'))
            for first, second in ((opened, lit), (lit, delay), (delay, closed), (closed, dark)):
                execution_wire(modal, first, second)
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator(f'[data-blueprint-trace-node="{delay}"]')).to_be_visible()
            expect(modal.locator(f'[data-blueprint-trace-node="{closed}"]')).to_have_count(0)
            expect(modal.locator(f'[data-blueprint-trace-node="{dark}"]')).to_have_count(0)
            assert review.project(initial['id'])['document'] == initial['document']
            records.append({'case': 'actual-editor-authors-open-light-delay-close-chain-and-preview-stops-at-wait-without-persistence'})
            parameter(modal, delay, 'seconds', 5)
            modal.locator('[data-blueprint-undo]').click()
            expect(card(modal, delay).locator('[data-blueprint-param=seconds]')).to_have_value('3')
            modal.locator('[data-blueprint-fit]').click()
            page.screenshot(path=str(output / 'delay-authoring.png'))
            modal.locator('[data-blueprint-save]').click()
            authored = review.save()
            records.append({'case': 'delay-duration-participates-in-blueprint-undo-and-source-save'})

            modal = open_editor(protected_door['id'], 'doors')
            modal.locator('[data-blueprint-state-port=open]').click()
            root_lit = add_node(modal, 'light', targetId=light['id'], enabled=True)
            root_delay = add_node(modal, 'delay', seconds=3)
            root_closed = add_node(modal, 'state', targetState='closed')
            root_dark = add_node(modal, 'light', targetId=light['id'], enabled=False)
            connect(modal, modal.locator('[data-blueprint-state-port=open]'),
                    card(modal, root_lit).locator('[data-blueprint-input]'))
            for first, second in ((root_lit, root_delay), (root_delay, root_closed), (root_closed, root_dark)):
                execution_wire(modal, first, second)
            modal.locator('[data-blueprint-save]').click()
            authored = review.save()
            records.append({'case': 'actual-editor-authors-independent-own-door-delayed-close-for-original-player-permission-check'})

            modal = open_editor(lever['id'])
            modal.locator('[data-blueprint-state-port=on]').click()
            parameter(modal, delay, 'seconds', 12)
            card(modal, delay).locator('[data-blueprint-delete]').click()
            modal.locator('[data-blueprint-cancel]').click()
            assert review.save()['document'] == authored['document']
            records.append({'case': 'cancelling-duration-and-delay-node-deletion-keeps-saved-graph'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    page.goto(builder + '?project=' + authored['id'])
                    wait_ready(page)
                    modal = open_editor(lever['id'])
                    modal.locator('[data-blueprint-state-port=on]').click()
                    expect(card(modal, delay).locator('[data-blueprint-param=seconds]')).to_have_value('3')
                    modal.locator('[data-blueprint-add]').click()
                    modal.locator('[data-blueprint-picker-search]').fill('delay')
                    expect(modal.locator('[data-blueprint-pick-type=delay]')).to_be_visible()
                    modal.locator('[data-blueprint-picker-cancel]').click()
                    modal.locator('[data-blueprint-fit]').click()
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'delay-editor-{locale}-{width}.png'))
                    for _ in range(8):
                        page.keyboard.press('Tab')
                        assert modal.evaluate('element=>element.closest("[role=dialog]").contains(document.activeElement)')
                    page.keyboard.press('Escape')
                    expect(modal).to_have_count(0)
                    records.append({'case': 'localized-responsive-delay-controls-preserve-duration-and-modal-focus',
                                    'locale': locale, 'width': width, 'metrics': metrics})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(builder + '?project=' + authored['id'])
            wait_ready(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            wait_game()
            project = review.project(authored['id'])
            scene = project['sceneId']

            def command(area, action, data, target=None):
                return (target or page).evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
                  mapId:a.scene,area:a.area,action:a.action,data:a.data})""",
                                                {'scene': scene, 'area': area, 'action': action, 'data': data})

            def state(target=None):
                response = (target or page).request.get(f'/api/maps/{scene}/state')
                assert response.ok, response.text()
                return response.json()

            def automation():
                response = page.request.get(f'/api/maps/{scene}/automation')
                assert response.ok, response.text()
                return response.json()

            command('lighting', 'update', {'mode': 'none', 'darkness': 0, 'lights_out': False})
            page.evaluate("""a=>gravewrightRealtime.mapCommand('update',{
              mapId:a.scene,version:a.version,settings:{visibility:'players'}})""",
                          {'scene': scene, 'version': project['sceneVersion']})
            page.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)
            native = state()
            native_light, = native['lights']
            native_lever, = [row for row in native['images'] if row.get('lever')]
            native_door_id = next(node['targetId'] for node in native_lever['blueprint']['graphs']['enter:on']['nodes']
                                  if node['id'] == recipient)
            native_door = next(row for row in native['walls'] if row['id'] == native_door_id)
            native_protected = next(row for row in native['walls'] if row['kind'] == 'door' and row['id'] != native_door_id)
            assert not automation()['delays'], automation()

            def create_player():
                nonlocal player_context, player
                player_context = create_context('player', {'width': 1200, 'height': 800})
                player = player_context.new_page()
                observe(player)
                player.goto(f'{base}/game/{campaign}')
                wait_game(player)

            def interact(pressed):
                control = player.locator(f'[data-smart-image-id="{native_lever["id"]}"][data-smart-image-action=interact]')
                expect(control).to_have_attribute('aria-pressed', str(not pressed).lower())
                control.focus()
                control.press('Enter')
                expect(control).to_have_attribute('aria-pressed', str(pressed).lower())

            def wall_state():
                return next(row for row in state()['walls'] if row['id'] == native_door['id'])['door_state']

            def light_enabled():
                return next(row for row in state()['lights'] if row['id'] == native_light['id'])['enabled']

            def pending():
                return automation()['delays']

            def reset_effects():
                command('walls', 'door', {'wall_id': native_door['id'], 'door_state': 'closed'})
                command('lights', 'update', {'light_id': native_light['id'], 'enabled': False})

            def receipt(identifier):
                return player.evaluate("""a=>new Promise((resolve,reject)=>{
                  const stop=()=>{clearTimeout(timer);removeEventListener('gravewright:api-event',receive);};
                  const receive=({detail})=>{
                    if(detail.payload.requestId!==a.id||!['maps.ack','maps.error'].includes(detail.type))return;
                    stop();detail.type==='maps.ack'?resolve(detail.payload.result):reject(Error(detail.payload.message));};
                  const timer=setTimeout(()=>{stop();reject(Error('Delay receipt timed out'));},15000);
                  addEventListener('gravewright:api-event',receive);
                  gravewrightRealtime.tableTool('maps.command',{action:'objects',requestId:a.id,
                    data:{mapId:a.scene,area:'images',action:'interact',data:{image_id:a.image}}});
                })""", {'scene': scene, 'id': identifier, 'image': native_lever['id']})

            create_player()
            request_id = str(uuid4())
            original_receipt = receipt(request_id)
            first_pending = pending()
            assert len(first_pending) == 1 and first_pending[0]['nodeId'] == delay, first_pending
            assert wall_state() == 'open' and light_enabled() is True
            assert receipt(request_id) == original_receipt
            assert pending() == first_pending
            records.append({'case': 'real-player-opens-door-lights-it-and-duplicate-receipt-keeps-exactly-one-persistent-wait'})
            assert 'automationDelays' not in json.dumps(state(player))
            assert '"blueprint":' not in json.dumps(state(player))
            assert player.request.get(f'/api/maps/{scene}/automation').status == 404
            records.append({'case': 'player-cannot-read-private-pending-waits-or-authoring-graphs'})

            player_context.close()
            player_context = None
            context.close()
            context = None
            # Every page and socket is gone. There are no state or automation
            # requests while the server reaches and executes the due deadline.
            time.sleep(3.6)
            context = create_context('gm')
            response = context.request.get(f'/api/maps/{scene}/state')
            assert response.ok, response.text()
            resumed = response.json()
            assert next(row for row in resumed['walls'] if row['id'] == native_door['id'])['door_state'] == 'closed'
            assert next(row for row in resumed['lights'] if row['id'] == native_light['id'])['enabled'] is False
            page = context.new_page()
            observe(page)
            page.goto(f'{base}/game/{campaign}')
            wait_game()
            review = BuilderReview(page, campaign)
            assert not pending()
            records.append({'case': 'production-worker-resumes-delayed-door-and-light-with-all-browser-pages-and-sockets-closed',
                            'pollingRequestsDuringWait': 0})

            def edit_duration(seconds):
                page.goto(builder + '?project=' + authored['id'])
                wait_ready(page)
                modal = open_editor(lever['id'])
                modal.locator('[data-blueprint-state-port=on]').click()
                parameter(modal, delay, 'seconds', seconds)
                modal.locator('[data-blueprint-save]').click()
                review.save()
                builder_sidebar(page, 'review')
                with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                    page.locator('[data-builder-review-update]').click()
                assert updated.value.ok, updated.value.text()
                wait_game()

            edit_duration(180)
            create_player()
            interact(False)
            interact(True)
            cancelled, = pending()

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': 1440, 'height': 900})
                    page.goto(f'/game/{campaign}')
                    wait_game()
                    page.locator('.game-menubar__layer').nth(5).click()
                    page.locator('[data-dock-tool=automation]').click()
                    log = page.locator('.automation-log')
                    log.locator('[data-automation-view=delays]').click()
                    row = log.locator(f'[data-automation-delay-id="{cancelled["id"]}"]')
                    expect(row).to_be_visible()
                    expect(row.locator('[data-automation-cancel-delay]')).to_be_enabled()
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    metrics = log.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'delay-pending-{locale}-{width}.png'))
                    log.locator('[data-automation-close]').click()
                    records.append({'case': 'localized-responsive-gm-pending-waits-show-deadline-and-cancel-control',
                                    'locale': locale, 'width': width, 'metrics': metrics})

            # The inspection loop must not outlive the deliberately long wait.
            assert pending() == [cancelled], pending()
            page.goto(builder + '?project=' + authored['id'])
            wait_ready(page)
            set_name(page, 'Synthetic persistent delayed door renamed while waiting')
            review.save()
            builder_sidebar(page, 'review')
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-review-update]').click()
            assert updated.value.ok, updated.value.text()
            wait_game()
            assert pending() == [cancelled], pending()
            records.append({'case': 'unrelated-source-name-update-keeps-pending-job-identity-and-original-deadline'})
            before_runs = automation()['runs']
            stale = page.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
              mapId:a.scene,area:'automation',action:'cancel-delay',
              data:{delayId:a.id,expectedDueAt:'2000-01-01T00:00:00Z'}})
              .then(result=>({accepted:true,result}),error=>({accepted:false,message:error.message}))""",
                                  {'scene': scene, 'id': cancelled['id']})
            assert stale['accepted'] is False and pending() == [cancelled], stale
            records.append({'case': 'stale-gm-delay-cancel-refuses-to-overwrite-the-current-wait'})
            refused = player.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
              mapId:a.scene,area:'automation',action:'cancel-delay',data:{delayId:a.job.id,expectedDueAt:a.job.dueAt}})
              .then(result=>({accepted:true,result}),error=>({accepted:false,message:error.message}))""",
                                      {'scene': scene, 'job': cancelled})
            assert refused['accepted'] is False and pending() == [cancelled], refused
            records.append({'case': 'player-cannot-cancel-persistent-waits-through-a-forged-command'})

            page.set_viewport_size({'width': 1440, 'height': 900})
            page.locator('.game-menubar__layer').nth(5).click()
            page.locator('[data-dock-tool=automation]').click()
            log = page.locator('.automation-log')
            log.locator('[data-automation-view=delays]').click()
            log.locator(f'[data-automation-delay-id="{cancelled["id"]}"] [data-automation-cancel-delay]').click()
            expect(log.locator(f'[data-automation-delay-id="{cancelled["id"]}"]')).to_have_count(0)
            assert not pending() and wall_state() == 'open' and light_enabled() is True
            cancelled_runs = automation()['runs']
            assert cancelled_runs[1:] == before_runs
            assert cancelled_runs[0]['outcome'] == 'cancelled' and cancelled_runs[0]['delayId'] == cancelled['id']
            assert not cancelled_runs[0]['events']
            log.locator('[data-automation-close]').click()
            records.append({'case': 'gm-cancel-clears-only-the-selected-wait-without-running-its-continuation'})

            edit_duration(3)
            reset_effects()
            interact(False)
            interact(True)
            paused_job, = pending()
            command('automation', 'pause', {'paused': True})
            player.wait_for_timeout(3600)
            assert pending() == [paused_job] and wall_state() == 'open' and light_enabled() is True
            command('automation', 'pause', {'paused': False})
            player.wait_for_timeout(800)
            assert not pending() and wall_state() == 'closed' and light_enabled() is False
            records.append({'case': 'scene-pause-keeps-overdue-wait-pending-and-resume-releases-it-without-a-new-interaction'})

            reset_effects()
            command('walls', 'door', {'wall_id': native_protected['id'], 'door_state': 'open'}, player)
            locked_job, = pending()
            assert locked_job['nodeId'] == root_delay, locked_job
            command('walls', 'door', {'wall_id': native_protected['id'], 'door_state': 'locked'})
            player.wait_for_timeout(3600)
            protected_state = next(row for row in state()['walls'] if row['id'] == native_protected['id'])['door_state']
            assert not pending() and protected_state == 'locked' and wall_state() == 'closed' and light_enabled() is True
            failure_run, = [run for run in automation()['runs'] if run.get('delayId') == locked_job['id']]
            assert failure_run['outcome'] in ('blocked', 'failed', 'cancelled'), failure_run
            assert failure_run.get('message'), failure_run
            records.append({'case': 'delayed-player-continuation-rechecks-lock-permission-and-rolls-back-later-light-effect'})
            command('walls', 'door', {'wall_id': native_protected['id'], 'door_state': 'closed'})

            reset_effects()
            interact(False)
            interact(True)
            targeted_lock_job, = pending()
            command('walls', 'door', {'wall_id': native_door['id'], 'door_state': 'locked'})
            player.wait_for_timeout(3600)
            assert not pending() and wall_state() == 'locked' and light_enabled() is False
            targeted_run, = [run for run in automation()['runs'] if run.get('delayId') == targeted_lock_job['id']]
            assert any(event['event'].startswith('refused:') for event in targeted_run['events']), targeted_run
            records.append({'case': 'delayed-player-operation-of-another-locked-door-is-skipped-and-logged-without-unlocking-it'})

            # A restart happens after the server is stopped and the deadline
            # passes, so only persisted state can cause this continuation.
            command('walls', 'door', {'wall_id': native_door['id'], 'door_state': 'closed'})
            command('lights', 'update', {'light_id': native_light['id'], 'enabled': False})
            interact(False)
            interact(True)
            restart_job, = pending()
            player_context.close()
            player_context = None
            context.close()
            context = None
            restart(3.6)
            context = create_context('gm')
            # Let the automatic worker settle with no open page or socket.
            time.sleep(1.2)
            resumed = context.request.get(f'/api/maps/{scene}/state').json()
            assert next(row for row in resumed['walls'] if row['id'] == native_door['id'])['door_state'] == 'closed'
            assert next(row for row in resumed['lights'] if row['id'] == native_light['id'])['enabled'] is False
            page = context.new_page()
            observe(page)
            page.goto(f'{base}/game/{campaign}')
            wait_game()
            review = BuilderReview(page, campaign)
            assert not pending()
            records.append({'case': 'real-server-restart-recovers-overdue-wait-from-the-same-isolated-database-without-open-clients',
                            'jobId': restart_job['id'], 'deadlinePassedWhileStopped': True})

            edit_duration(180)
            create_player()
            interact(False)
            interact(True)
            changed_job, = pending()
            edit_duration(181)
            assert not pending(), pending()
            assert wall_state() == 'open' and light_enabled() is True
            records.append({'case': 'editing-authored-delay-definition-cancels-its-pending-continuation-on-linked-update',
                            'jobId': changed_job['id']})

            interact(False)
            interact(True)
            removed_job, = pending()
            page.goto(builder + '?project=' + authored['id'])
            wait_ready(page)
            modal = open_editor(lever['id'])
            modal.locator('[data-blueprint-state-port=on]').click()
            card(modal, delay).locator('[data-blueprint-delete]').click()
            modal.locator('[data-blueprint-save]').click()
            review.save()
            builder_sidebar(page, 'review')
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-review-update]').click()
            assert updated.value.ok, updated.value.text()
            wait_game()
            assert not pending() and wall_state() == 'open' and light_enabled() is True
            records.append({'case': 'deleting-delay-node-cancels-pending-work-without-running-the-disconnected-continuation',
                            'jobId': removed_job['id']})

            page.goto(builder + '?project=' + authored['id'])
            wait_ready(page)
            modal = open_editor(lever['id'])
            modal.locator('[data-blueprint-state-port=on]').click()
            replacement_delay = add_node(modal, 'delay', seconds=3)
            execution_wire(modal, lit, replacement_delay)
            execution_wire(modal, replacement_delay, closed)
            modal.locator('[data-blueprint-save]').click()
            review.save()
            builder_sidebar(page, 'review')
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-review-update]').click()
            assert updated.value.ok, updated.value.text()
            wait_game()
            interact(False)
            interact(True)
            deleted_target_job, = pending()
            command('walls', 'delete', {'wall_id': native_door['id']})
            player.wait_for_timeout(3600)
            assert not pending() and light_enabled() is True
            assert not any(row['id'] == native_door['id'] for row in state()['walls'])
            records.append({'case': 'deleting-required-target-cancels-wait-and-keeps-later-light-effect-unexecuted',
                            'jobId': deleted_target_job['id']})

        except Exception:
            if page and not page.is_closed():
                page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors,
                                                             'nativeDialogs': dialogs}, indent=2,
                                                            ensure_ascii=False), encoding='utf-8')
            raise
        finally:
            if player_context:
                player_context.close()
            if context:
                context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Generated solid-color PNGs and isolated campaign state; no operator data.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--resume', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        if args.resume:
            import django
            django.setup()
            from django.core.management import call_command
            call_command('runserver', f'127.0.0.1:{args.port}', use_reloader=False, verbosity=0)
        else:
            harness.serve(args.fixture, args.port)
        return

    output = (args.output or ROOT / 'data/map-builder-delay' /
              datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError('Use a fresh, empty output directory.')
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / 'fixture'
    fixture.mkdir()
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        port = connection.getsockname()[1]
    fixture_environment(fixture, port)
    executable = sys._base_executable if os.name == 'nt' else sys.executable
    command = [executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()),
               '--serve', '--fixture', str(fixture), '--port', str(port)]
    base = f'http://127.0.0.1:{port}'
    processes = []
    server = None
    with (output / 'server.log').open('w', encoding='utf-8') as log:
        def start(resume=False):
            nonlocal server
            server = subprocess.Popen([*command, *(['--resume'] if resume else [])],
                                      cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=log)
            processes.append(server)
            for _ in range(300):
                if server.poll() is not None:
                    raise RuntimeError(f'Fixture exited; inspect {output / "server.log"}')
                try:
                    with urlopen(base, timeout=1):
                        return
                except OSError:
                    time.sleep(.1)
            raise RuntimeError('Fixture did not become ready.')

        def stop():
            if server is None or server.poll() is not None:
                return
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()

        def restart(pause):
            stop()
            time.sleep(pause)
            start(resume=True)

        try:
            start()
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
            report = check_browser(base, seed, output, args.browser_executable, restart)
            (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
            print(json.dumps({'passed': True, 'cases': len(report['cases']), 'report': str(output / 'report.json')}))
        except Exception:
            (output / 'failure.txt').write_text(traceback.format_exc(), encoding='utf-8')
            raise
        finally:
            stop()
            (output / 'server-exit.json').write_text(json.dumps([
                {'pid': process.pid, 'exitCode': process.poll()} for process in processes
            ]), encoding='utf-8')


if __name__ == '__main__':
    main()
