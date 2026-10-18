"""Measure real MapBuilder gameplay through native input, WebSockets and GPU pixels.

The representative scene matches a small 2800x2100 tabletop: 36 authored floors
in two native planes, two decorations, two regions, one token and no lights or
effects. Movement, sprite automation and teleport execute on the real server.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder_asset_removal import BuilderReview
from map_builder_combination_matrix import behavior
from map_builder_playtest import chain, node
from map_builder_reference import close_panel, upload_asset, wait_ready


BASELINE_ENV = 'GRAVEWRIGHT_E2E_MAPBUILDER_PERF_BASELINE'
BACKEND_ENV = 'GRAVEWRIGHT_E2E_MAPBUILDER_PERF_BACKEND'
BASE_SERVE = harness.serve


def serve(fixture, port):
    saved = os.environ.get(BACKEND_ENV)
    if saved:
        import django
        django.setup()
        from gravewright.realtime import consumers, dispatch
        for module in (dispatch, consumers):
            path = Path(saved) / (module.__name__.rsplit('.', 1)[1] + '.py')
            exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), module.__dict__)
        path = Path(saved) / 'blueprint_world.py'
        if path.exists():
            from gravewright.maps import blueprint_world
            exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), blueprint_world.__dict__)
    BASE_SERVE(fixture, port)


def percentile(values, portion):
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int((len(ordered) - 1) * portion))], 2) if ordered else None


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    cases, errors, measurements, contexts, clients, cdps = [], [], [], [], {}, {}
    scene = token = None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        baseline = os.environ.get(BASELINE_ENV)
        static = {}
        if baseline:
            saved = Path(baseline)
            if (saved / 'gravewright').exists():
                for app in (saved / 'gravewright').iterdir():
                    root = app / 'static'
                    if root.exists():
                        static.update({str(path.relative_to(root)).replace('\\', '/'): path for path in root.rglob('*.js')})
            else:
                static = {str(path.relative_to(saved)).replace('\\', '/'): path for path in saved.rglob('*.js')}

        def route(route, request):
            key = urlsplit(request.url).path.removeprefix('/static/')
            if key in static:
                route.fulfill(path=str(static[key]), content_type='text/javascript')
            else:
                route.continue_()

        def client(role):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            context.add_init_script(path=str(harness.ROOT / 'tests/fixtures/mapbuilder_ingame_perf.js'))
            if static:
                context.route('**/static/**', route)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append({'role': role, 'message': str(error), 'stack': error.stack}))
            contexts.append(context)
            clients[role] = page
            session = context.new_cdp_session(page)
            session.send('Performance.enable')
            cdps[role] = session
            return page

        gm = client('gm')
        review = BuilderReview(gm, campaign)

        def game(page):
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.board?.viewport() && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def cdp(role):
            return {row['name']: row['value'] for row in cdps[role].send('Performance.getMetrics')['metrics']}

        def diagnostics():
            (output / 'measurements.json').write_text(json.dumps({
                'cases': cases, 'measurements': measurements, 'pageErrors': errors,
                'currentProbes': {role: page.evaluate('window.__mapbuilderPerf?.finish()') for role, page in clients.items()},
                'baseline': baseline, 'scene': scene, 'token': token}, indent=2), encoding='utf-8')

        try:
            gm.goto(review.builder)
            wait_ready(gm)
            gm.locator('[data-builder-quick-name]').fill('Synthetic representative MapBuilder gameplay')
            gm.locator('[data-builder-quick-name]').press('Tab')
            floor = upload_asset(gm, 'floor', 'Synthetic gameplay floor.png', harness.artwork('#387050'))['id']
            blue = upload_asset(gm, 'decoration', 'Synthetic gameplay off.png', harness.artwork('#245dc9'))['id']
            orange = upload_asset(gm, 'decoration', 'Synthetic gameplay on.png', harness.artwork('#ed7822'))['id']
            expect(gm.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)
            project = review.project(gm.evaluate("new URL(location.href).searchParams.get('project')"))
            document = deepcopy(project['document'])
            layer = document['layers'][0]['id']
            target, private, source, destination = [str(uuid4()) for _ in range(4)]
            document.update(columns=40, rows=30, cellSize=70, background='#18222c')
            document['floors'] = [{'id': str(uuid4()), 'layerId': layer, 'assetId': floor,
                'x': 0, 'y': 0, 'width': 40, 'height': 30, 'rotation': 0, 'dynamic': True}]
            document['floors'] += [{'id': str(uuid4()), 'layerId': layer, 'assetId': floor,
                'x': index % 7 * 5, 'y': index // 7 * 5, 'width': 4, 'height': 4, 'rotation': 0}
                for index in range(35)]
            document['decorations'] = [
                {'id': target, 'layerId': layer, 'assetId': blue, 'x': 16, 'y': 8, 'width': 2, 'height': 2, 'rotation': 0},
                {'id': private, 'layerId': layer, 'assetId': blue, 'x': 20, 'y': 8, 'width': 2, 'height': 2,
                    'rotation': 0, 'lever': {'state': 'off'}, 'blueprint': behavior('lever', {})},
            ]
            enter = chain('presence:enter', [node('sprite', 'sprite', appearance='asset', assetId=orange),
                node('teleport', 'teleport', destinationId=destination)],
                [node('target', 'reference', targetId=target)], [('target', 'door', 'sprite', 'target')])
            leave = chain('presence:exit', [node('sprite', 'sprite', appearance='asset', assetId=blue)],
                [node('target', 'reference', targetId=target)], [('target', 'door', 'sprite', 'target')])
            document['regions'] = [
                {'id': source, 'layerId': layer, 'x': 8, 'y': 14, 'width': 3, 'height': 3,
                    'name': 'Synthetic source', 'enabled': True, 'blueprint': behavior('region', {'presence:enter': enter})},
                {'id': destination, 'layerId': layer, 'x': 23, 'y': 14, 'width': 3, 'height': 3,
                    'name': 'Synthetic destination', 'enabled': True, 'blueprint': behavior('region', {'presence:exit': leave})},
            ]
            project = review.store(project['id'], project['version'], project['folderId'], document)
            gm.goto(review.builder + '?project=' + project['id'])
            wait_ready(gm)
            close_panel(gm)
            with gm.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                gm.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game(gm)
            project = review.project(project['id'])
            scene = project['sceneId']
            gm.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)
            native = gm.request.get(f'/api/maps/{scene}/state').json()
            private_row = next(row for row in native['images'] if row.get('lever'))
            gm.evaluate('''a=>gravewrightRealtime.mapCommand('objects',{mapId:a.scene,area:'images',action:'update',
                data:{id:a.id,layer:'gm-image-layer'}})''', {'scene': scene, 'id': private_row['id']})
            actor = gm.evaluate("()=>gravewrightRealtime.resourceCommand('actors','actor.create',{name:'Synthetic actual gameplay traveler'})")
            gm.evaluate("id=>gravewrightRealtime.resourceCommand('actors','actor.permissions',{id,permissions:{default:'owner'}})", actor['id'])
            csrf = gm.request.get('/__gravewright/csrf').json()
            uploaded = gm.request.post(f'/api/containers/{campaign}/actor-upload', headers={csrf['header']: csrf['token']},
                multipart={'actorId': actor['id'], 'kind': 'token', 'file': {
                    'name': 'Synthetic gameplay token.png', 'mimeType': 'image/png', 'buffer': harness.artwork('#78b53a')}})
            assert uploaded.ok, uploaded.text()
            token = gm.evaluate('''a=>gravewrightRealtime.resourceCommand('tokens','place',{
                mapId:a.scene,actorId:a.actor,gridX:5,gridY:9})''', {'scene': scene, 'actor': actor['id']})['createdIds'][0]
            player = client('player')
            player.goto(f'/game/{campaign}')
            game(player)
            player.wait_for_function('id=>gravewrightMaps.current?.id===id', arg=scene)
            for page in clients.values():
                expect(page.get_by_role('button', name='Token: Synthetic actual gameplay traveler', exact=True)).to_be_visible()
                page.wait_for_timeout(500)
                page.evaluate('__mapbuilderPerf.install()')
            native = gm.request.get(f'/api/maps/{scene}/state').json()
            manifest = gm.request.get(f'/api/maps/{scene}/manifest').json()
            counts = {'width': manifest['width'], 'height': manifest['height'], 'floors': len(document['floors']),
                'images': len(native['images']), 'floorPlanes': sum('surfacePlane' in row for row in native['images']),
                'regions': len(native['zones']), 'walls': len(native['walls']), 'lights': len(native['lights']),
                'particles': len(native['particles']), 'shaders': len(native['shaders']), 'tokens': 1,
                'stateBytes': len(json.dumps(native).encode()), 'tileCount': sum(row['columns'] * row['rows'] for row in manifest['levels'])}
            assert counts['floors'] == 36 and counts['images'] == 4 and counts['floorPlanes'] == 2, counts
            floor_assets = {asset for row in native['images'] if 'surfacePlane' in row
                for asset in (row.get('asset_id'), row.get('surface', {}).get('maskId')) if asset}
            cases.append({'case': 'real-generated-representative-scene', 'counts': counts})
            diagnostics()

            def movement(label, x, y, final_x=None, final_y=None, batch=False):
                final_x, final_y = final_x if final_x is not None else x, final_y if final_y is not None else y
                before = {role: cdp(role) for role in clients}
                for page in clients.values():
                    page.evaluate('watch=>__mapbuilderPerf.start(watch)', {'token': token, 'cell': 70,
                        'x': final_x, 'y': final_y, 'minX': final_x, 'maxX': final_x, 'minY': final_y, 'maxY': final_y})
                hero = player.get_by_role('button', name='Token: Synthetic actual gameplay traveler', exact=True)
                box = hero.bounding_box()
                at = player.evaluate('''p=>{const r=document.querySelector('.game-board__surface').getBoundingClientRect(),v=gravewrightMaps.board.viewport();
                    return {x:r.x+v.x+(p.x+.5)*70*v.scale,y:r.y+v.y+(p.y+.5)*70*v.scale};}''', {'x': x, 'y': y})
                if batch:
                    hero.click()
                    player.evaluate('''()=>new Promise((resolve,reject)=>{
                      let count=0;
                      const target=document.querySelector('.token-workspace rect[role=button]');
                      const timer=setTimeout(()=>{removeEventListener('gravewright:api-event',received);reject(Error('20-move chain timed out'));},30000);
                      function received(event){
                        if(event.detail.type==='tokens.error'){clearTimeout(timer);removeEventListener('gravewright:api-event',received);reject(Error(JSON.stringify(event.detail.payload)));return;}
                        if(event.detail.type!=='tokens.ack')return;
                        if(++count===20){target.dispatchEvent(new KeyboardEvent('keyup',{key:'ArrowRight',bubbles:true}));
                          clearTimeout(timer);removeEventListener('gravewright:api-event',received);resolve();}
                        else target.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',repeat:true,bubbles:true,cancelable:true}));
                      }
                      addEventListener('gravewright:api-event',received);
                      target.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true}));
                    })''')
                else:
                    player.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                    player.mouse.down()
                    player.mouse.move(at['x'], at['y'], steps=8)
                    player.mouse.up()
                player.wait_for_function("__mapbuilderPerf.events.some(row=>row.kind==='tokens.ack')", timeout=20_000)
                for page in clients.values():
                    page.wait_for_function('!!__mapbuilderPerf.committedPixel', timeout=20_000)
                player.wait_for_timeout(100)
                result = {'case': label, 'clients': {}}
                for role, page in clients.items():
                    value = page.evaluate('__mapbuilderPerf.finish()')
                    after = cdp(role)
                    value['cpu'] = {key: round((after[key] - before[role][key]) * 1000, 2)
                        for key in ('TaskDuration', 'ScriptDuration', 'LayoutDuration', 'RecalcStyleDuration')}
                    value['frameP95Ms'] = percentile(value['gaps'], .95)
                    value['frameMaxMs'] = round(max(value['gaps'], default=0), 2)
                    value['wsSentBytes'] = sum(row['bytes'] for row in value['traffic'] if row['direction'] == 'sent')
                    value['wsReceivedBytes'] = sum(row['bytes'] for row in value['traffic'] if row['direction'] == 'received')
                    command = next((row for row in value['events'] if row['kind'] == 'command'), None)
                    ack = next((row for row in value['events'] if row['kind'] == 'tokens.ack'), None)
                    value['ackMs'] = round(ack['at'] - command['at'], 2) if ack and command else None
                    sent = {row['requestId']: row['at'] for row in value['events'] if row['kind'] == 'command'}
                    acks = [row for row in value['events'] if row['kind'] == 'tokens.ack' and row.get('requestId') in sent]
                    value['acceptedMoves'] = len(acks)
                    value['ackP95Ms'] = percentile([row['at'] - sent[row['requestId']] for row in acks], .95)
                    value['chainMs'] = round(acks[-1]['at'] - min(sent.values()), 2) if acks else None
                    value['messageCounts'] = {name: sum(row['type'] == name for row in value['traffic'])
                        for name in sorted({row['type'] for row in value['traffic']})}
                    assert not value['errors'], value['errors']
                    result['clients'][role] = value
                release = next(row['at'] for row in result['clients']['player']['events']
                    if row['kind'] == ('command' if batch else 'pointerup'))
                origin = result['clients']['player']['timeOrigin'] + release
                for value in result['clients'].values():
                    value['releaseToCommittedPixelMs'] = round(value['timeOrigin'] +
                        max(value['committedPixel']['at'], value['confirmedAt']) - origin, 2)
                measurements.append(result)
                cases.append({'case': label, 'actualServer': True, 'renderedClients': list(clients)})
                diagnostics()
                if not baseline and 'warm' in label:
                    for role, value in result['clients'].items():
                        invalidated = [row['url'] for row in value['fetches'] if
                            any(part in row['url'] for part in ('/manifest', '/state', '/tiles/')) or
                            any(asset in row['url'] for asset in floor_assets)]
                        assert not invalidated, {'role': role, 'case': label, 'unnecessarySceneReads': invalidated}
                        large = [row for row in value['decodedSizes'] + value['uploads']
                            if (row.get('width') or 0) * (row.get('height') or 0) > 512 * 512]
                        assert not large, {'role': role, 'case': label, 'rebuiltFloorArtwork': large}

            for index in range(4):
                movement(f'plain-out-{index}', 6, 9)
                movement(f'plain-back-{index}', 5, 9)
            movement('twenty-accepted-native-arrow-moves-without-idle-sleeps', 25, 9, batch=True)
            movement('enter-and-teleport-cold', 8, 14, 23, 14)
            movement('exit-destination-cold', 26, 14)
            for index in range(3):
                movement(f'enter-and-teleport-warm-{index}', 8, 14, 23, 14)
                movement(f'exit-destination-warm-{index}', 26, 14)
            for role, page in clients.items():
                page.screenshot(path=str(output / f'final-{role}.png'))
            assert not errors, {'count': len(errors), 'first': errors[0]['message'][:200] if errors else None}
        finally:
            diagnostics()
            for context in reversed(contexts):
                context.close()
            browser.close()
    summary = {}
    for kind, rows in [('plain', [row for row in measurements if row['case'].startswith('plain')]),
                       ('automation', [row for row in measurements if 'warm' in row['case']])]:
        summary[kind] = {role: {key: percentile([row['clients'][role][key] for row in rows
            if row['clients'][role][key] is not None], .5) for key in
            ('ackMs', 'releaseToCommittedPixelMs', 'frameP95Ms', 'frameMaxMs', 'wsReceivedBytes')}
            for role in clients}
    return {'passed': True, 'cases': cases, 'summary': summary, 'measurements': measurements, 'pageErrors': errors,
        'baseline': baseline, 'backendSource': os.environ.get(BACKEND_ENV),
        'measurement': 'Actual native pointer drag and held-arrow queue, authenticated WebSocket commands/automation, CDP CPU and real GPU token pixels. Settled presentation is the later of an observed matching GPU preview and authoritative confirmation; unchanged previews need no redraw. Screenshots excluded from timed intervals.',
        'scope': 'Representative native host scene with a synthetic actor; no private RPG system package or authored campaign assets are copied.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--baseline-dir', type=Path)
    parser.add_argument('--backend-source', type=Path)
    options, remaining = parser.parse_known_args()
    if options.baseline_dir:
        os.environ[BASELINE_ENV] = str(options.baseline_dir.resolve())
    if options.backend_source:
        os.environ[BACKEND_ENV] = str(options.backend_source.resolve())
    sys.argv = [sys.argv[0], *remaining]
    harness.__file__ = __file__
    harness.serve = serve
    harness.check_browser = check_browser
    harness.main()
