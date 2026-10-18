"""Verify token acknowledgements, recovery and saving status on a real native board.

The common disposable server provides real templates, modules and a WebGL board.
Only the token transport boundary is controlled after seeding two synthetic
actors, allowing deterministic delayed replies, conflicts and newer pushes.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import map_builder_blueprints as harness


BASELINE_ENV = 'GRAVEWRIGHT_E2E_TOKEN_SAVING_BASELINE'


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    cases, failures, errors = [], [], []
    campaign, scene, cell = seed['campaign'], seed['selectedScene'], 40
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        context.add_init_script(path=str(harness.ROOT / 'tests/fixtures/token_saving_probe.js'))
        baseline = os.environ.get(BASELINE_ENV)
        if baseline:
            for name in ('controller.js', 'workspace.js'):
                source = Path(baseline) / 'gravewright/tokens/static/gravewright_tokens' / name
                context.route(f'**/static/gravewright_tokens/{name}*',
                    lambda route, _request, source=source: route.fulfill(path=str(source), content_type='text/javascript'))
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append({'message': str(error), 'stack': error.stack}))

        def stats():
            return page.evaluate('__tokenSaving.stats()')

        def reset(options=None):
            page.evaluate('__tokenSaving.reset()')
            if options:
                page.evaluate('value=>__tokenSaving.configure(value)', options)

        def check(condition, message):
            if not condition:
                failures.append(message)

        def record(name):
            value = stats()
            cases.append({'case': name, 'result': value})
            return value

        def settled():
            page.wait_for_function('__tokenSaving.pending===0 && !__tokenSaving.held')
            page.wait_for_timeout(180)

        def selected(name, additive=False):
            if not additive:
                page.keyboard.press('Escape')
            page.get_by_role('button', name='Token: ' + name, exact=True).click(
                modifiers=['Shift'] if additive else [])

        def position(identifier):
            value = next(row for row in stats()['rows'] if row['id'] == identifier)
            return value['gridX'], value['gridY']

        def presented(value, identifier):
            piece = next(row for row in value['currentPieces'] if row['key'] == identifier)
            return piece['x'] / cell - .5, piece['y'] / cell - .5

        def no_reload(value, name):
            check(not value['reads'] and not value['refreshes'], f'{name}: successful ACK must not refetch tokens or refresh map layers')

        try:
            page.goto(f'/game/{campaign}')
            page.wait_for_function('id=>gravewrightMaps?.current?.id===id && !!gravewrightMaps.board?.viewport()', arg=scene)
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            page.evaluate('''async a=>{
              const scene=gravewrightMaps.current;
              await gravewrightRealtime.mapCommand('update',{mapId:a.scene,version:scene.version,
                settings:{gridSize:a.cell,initialView:{x:0,y:0,scale:1}}});
            }''', {'scene': scene, 'cell': cell})
            page.wait_for_function('gravewrightMaps.current.gridSize===40')
            identifiers = []
            names = ['Synthetic saving traveler A', 'Synthetic saving traveler B']
            for index, name in enumerate(names):
                actor = page.evaluate('''name=>gravewrightRealtime.resourceCommand('actors','actor.create',{name})''', name)
                placed = page.evaluate('''a=>gravewrightRealtime.resourceCommand('tokens','place',{
                  mapId:a.scene,actorId:a.actor,gridX:a.x,gridY:a.y})''',
                    {'scene': scene, 'actor': actor['id'], 'x': index, 'y': 1 + index * 2})
                identifiers.append(placed['createdIds'][0])
            for name in names:
                expect(page.get_by_role('button', name='Token: ' + name, exact=True)).to_be_visible()
            page.wait_for_timeout(250)
            rows = page.request.get(f'/api/containers/{campaign}/maps/{scene}/tokens').json()['tokens']
            page.evaluate('args=>installTokenSavingProbe(args)', {'rows': rows, 'scene': scene, 'cell': cell})
            selected(names[0])
            page.mouse.move(1, 1)
            settled()

            reset()
            for _ in range(12):
                page.evaluate("dispatchEvent(new Event('gravewright:condition-layout'))")
                page.wait_for_timeout(20)
            page.wait_for_timeout(500)
            value = record('idle-and-unchanged-repaints-preserve-token-status-DOM')
            check(value['mutations']['status'] == 0, 'idle status must not be rewritten on unchanged repaints')
            check(not value['commands'] and not value['reads'] and not value['visible'], 'idle must not write, read or display saving')

            reset()
            page.evaluate('''scene=>dispatchEvent(new CustomEvent('gravewright:token.drag',{
              detail:{scene_id:scene,stream:'synthetic-stream',connection:'synthetic-peer',phase:'end'}}))''', scene)
            settled()
            value = record('remote-drag-end-keeps-authoritative-snapshot-without-refresh')
            check(not value['reads'] and not value['refreshes'] and not value['commands'],
                'remote drag end must not force a token read or map refresh')

            reset()
            page.keyboard.press('ArrowLeft')
            settled()
            value = record('boundary-no-op-does-not-enter-save-or-refetch')
            check(not value['commands'] and not value['reads'] and not value['refreshes'] and not value['visible'],
                'clamped keyboard no-op must not enter persistence or flash Saving')

            reset()
            selected(names[0])
            settled()
            value = record('click-without-drag-does-not-save')
            check(not value['commands'] and not value['reads'] and not value['refreshes'] and not value['visible'],
                'selection click must not save or refresh')

            reset()
            hit = page.get_by_role('button', name='Token: ' + names[0], exact=True).bounding_box()
            page.keyboard.down('Control')
            page.mouse.click(hit['x'] + hit['width'] * 2.5, hit['y'] + hit['height'] / 2)
            expect(page.locator('.token-workspace__status')).to_be_visible()
            check('Ctrl+click' in page.locator('.token-workspace__status').inner_text(),
                'movement route instructions remain visible without any Saving popup')
            page.keyboard.press('Escape')
            page.keyboard.up('Control')
            settled()
            record('route-guidance-remains-visible-and-can-be-cancelled')

            reset()
            hit = page.get_by_role('button', name='Token: ' + names[0], exact=True).bounding_box()
            x, y = hit['x'] + hit['width'] / 2, hit['y'] + hit['height'] / 2
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(x + 60, y, steps=6)
            page.mouse.move(x, y, steps=6)
            page.mouse.up()
            settled()
            value = record('out-and-back-path-still-persists-area-crossing')
            check(len(value['commands']) == 1 and len(value['commands'][0]['data']['path']) > 2,
                'out-and-back movement must retain its traveled path for region effects')
            no_reload(value, 'out-and-back movement')

            reset()
            page.keyboard.press('ArrowRight')
            settled()
            value = record('fast-move-applies-ACK-without-read-refresh-or-saving-flash')
            check(position(identifiers[0]) == (1, 1), 'accepted move reaches its destination')
            check(presented(value, identifiers[0]) == (1, 1), 'accepted ACK is presented immediately')
            no_reload(value, 'fast move')
            check(not any(row['saving'] for row in value['visible']), 'fast ACK must not show Saving')

            reset()
            page.keyboard.press('Control+z')
            settled()
            value = record('undo-uses-latest-revision-and-ACK-without-reload')
            check(position(identifiers[0]) == (0, 1), 'undo restores the accepted source')
            no_reload(value, 'undo')

            reset({'other': identifiers[1]})
            page.keyboard.press('ArrowRight')
            settled()
            value = record('full-ACK-also-applies-other-token-changes')
            check(presented(value, identifiers[1]) == position(identifiers[1]), 'full ACK must refresh another token without GET')
            no_reload(value, 'full ACK')

            page.keyboard.press('Control+a')
            reset()
            page.keyboard.press('ArrowRight')
            settled()
            value = record('group-movement-accepts-both-ACKs-without-reload')
            check(len(value['commands']) == 2, 'group movement commits one operation per selected token')
            check(all(presented(value, identifier) == position(identifier) for identifier in identifiers), 'group ACKs present both final positions')
            no_reload(value, 'group movement')

            reset({'failFor': identifiers[1]})
            page.keyboard.press('ArrowDown')
            settled()
            value = record('partial-group-refusal-rereads-authoritative-state')
            check(len(value['commands']) == 2 and len(value['reads']) == 1 and len(value['refreshes']) == 1,
                'partial group failure needs one authoritative recovery read and layer refresh')
            check(all(presented(value, identifier) == position(identifier) for identifier in identifiers), 'partial failure reconciles both accepted and refused tokens')
            before_other = position(identifiers[1])
            reset()
            page.keyboard.press('Control+z')
            settled()
            value = record('undo-after-partial-failure-only-reverts-accepted-token')
            check(len(value['commands']) == 1 and position(identifiers[1]) == before_other, 'partial failure undo must leave refused token unchanged')
            no_reload(value, 'partial failure undo')

            selected(names[0])
            reset({'conflict': True})
            page.keyboard.press('ArrowRight')
            settled()
            value = record('conflict-rereads-and-presents-authoritative-position')
            check(len(value['reads']) == 1 and len(value['refreshes']) == 1, 'conflict must recover through authoritative state')
            check(presented(value, identifiers[0]) == position(identifiers[0]), 'conflict recovery presents server position')
            check(value['status']['role'] == 'alert' and not value['status']['hidden'] and value['status']['text'],
                'movement errors must remain visible after removing the Saving popup')
            reset()
            page.keyboard.press('ArrowRight')
            settled()
            value = record('movement-after-conflict-uses-recovered-version')
            no_reload(value, 'movement after conflict')

            reset({'hold': True})
            page.keyboard.press('ArrowRight')
            page.wait_for_function('!!__tokenSaving.held')
            page.wait_for_timeout(100)
            check(page.locator('.token-workspace__status').is_hidden(), 'pending movement must not display a Saving popup')
            page.wait_for_timeout(250)
            check(page.locator('.token-workspace__status').is_hidden(), 'even slow movement must not display a Saving popup')
            page.evaluate('__tokenSaving.release()')
            settled()
            value = record('slow-ACK-never-displays-saving-popup')
            check(value['status']['hidden'] and not any(row['saving'] for row in value['visible']),
                'movement Saving popup must remain absent throughout a slow ACK')
            no_reload(value, 'slow ACK')

            reset({'hold': True})
            page.keyboard.press('ArrowRight')
            page.wait_for_function('!!__tokenSaving.held')
            page.evaluate('id=>__tokenSaving.pushNewer(id,{gridX:8,gridY:4})', identifiers[0])
            page.evaluate('__tokenSaving.release()')
            settled()
            value = record('newer-pushed-token-state-survives-an-older-ACK')
            check(presented(value, identifiers[0]) == (8, 4), 'an older ACK must not roll back an already received newer token revision')

            page.keyboard.press('Control+a')
            reset({'holdFor': identifiers[1]})
            page.keyboard.press('ArrowRight')
            page.wait_for_function('!!__tokenSaving.held')
            page.evaluate('id=>__tokenSaving.pushNewer(id,{gridX:8,gridY:5})', identifiers[0])
            page.evaluate('__tokenSaving.release()')
            settled()
            value = record('newer-first-token-push-survives-second-group-ACK')
            check(len(value['commands']) == 2 and presented(value, identifiers[0]) == (8, 5),
                'second group ACK must not roll back a newer pushed revision of the first token')
            check(presented(value, identifiers[1]) == position(identifiers[1]), 'second token still reaches its accepted group destination')
            no_reload(value, 'group movement with newer push')

            selected(names[0])
            reset({'teleport': {'gridX': 9, 'gridY': 9}})
            page.keyboard.press('ArrowLeft')
            settled()
            value = record('teleport-ACK-preserves-marker-and-lands-without-read')
            check(presented(value, identifiers[0]) == (9, 9), 'teleport ACK presents the authoritative destination')
            piece = next(row for row in value['currentPieces'] if row['key'] == identifiers[0])
            check(piece.get('teleportVersion', 0) > 0, 'teleport ACK reaches the rendered piece with its marker')
            no_reload(value, 'teleport ACK')
            check(not page.evaluate('__tokenSaving.failures'), 'every subsequent write uses the current authoritative version')

            reset({'hold': True})
            page.keyboard.press('ArrowLeft')
            page.wait_for_function('!!__tokenSaving.held')
            page.evaluate('gravewrightMaps.showDirectory()')
            for identifier in (seed['parentFolder'], seed['folder']):
                toggle = page.locator(f'[data-map-folder="{identifier}"] > header > .gw-folder__toggle')
                if toggle.get_attribute('aria-expanded') != 'true':
                    toggle.click()
            page.locator(f'.game-directory__scene[data-scene-id="{seed["broadcastScene"]}"]').click()
            page.wait_for_function('id=>gravewrightMaps.current?.id===id', arg=seed['broadcastScene'])
            page.wait_for_function('!__tokenSaving.stats().status.connected')
            detached_mutations = stats()['mutations']['status']
            page.wait_for_timeout(350)
            check(page.locator('.token-workspace__status:visible').count() == 0,
                'a disposed token workspace must never leave a Saving popup')
            check(stats()['mutations']['status'] == detached_mutations,
                'disposed workspace must not mutate detached status DOM')
            page.evaluate('__tokenSaving.release()')
            settled()
            record('scene-disposal-leaves-no-saving-or-late-ACK-work')
            check(not errors, 'native board must produce no browser exceptions')
            page.screenshot(path=str(output / 'final-native-board.png'))
        finally:
            if page.evaluate('!!window.__tokenSaving'):
                probe = stats()
                page.evaluate('__tokenSaving.dispose()')
            else:
                probe = None
            (output / 'measurements.json').write_text(json.dumps({
                'cases': cases, 'failures': failures, 'pageErrors': errors, 'finalProbe': probe}, indent=2), encoding='utf-8')
            context.close()
            browser.close()
    assert not failures, failures
    return {'passed': True, 'cases': cases, 'pageErrors': errors,
        'data': 'Two synthetic actors and tokens in a disposable campaign; controlled token transport only.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--baseline-dir', type=Path)
    options, remaining = parser.parse_known_args()
    if options.baseline_dir:
        os.environ[BASELINE_ENV] = str(options.baseline_dir.resolve())
    sys.argv = [sys.argv[0], *remaining]
    harness.__file__ = __file__
    harness.check_browser = check_browser
    harness.main()
