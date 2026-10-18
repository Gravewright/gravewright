"""Exercise a composed torch from Map Builder through native tabletop play.

Uses synthetic artwork, an isolated campaign, database and localhost server.
Mechanism rotation, flame, Blueprint actions and native components stay separate.
"""
from __future__ import annotations

import time

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import close_panel, create_layer, set_name, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    builder = f'/game/{campaign}/map-builder'
    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        guests = []

        def observe(target):
            target.on('pageerror', lambda error: errors.append(str(error)))
            target.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))

        observe(page)
        review = BuilderReview(page, campaign)

        def point(x, y):
            return page.locator('[data-builder-canvas]').evaluate("""(svg,p)=>{
              const r=new DOMPoint(...p).matrixTransform(svg.getScreenCTM());return [r.x,r.y];
            }""", [x, y])

        def select(identifier):
            builder_tool(page, 'select')
            builder_workspace(page)
            box = page.locator(f'[data-builder-decorations] [data-object-id="{identifier}"]').bounding_box()
            page.mouse.click(box['x'] + box['width'] * .25, box['y'] + box['height'] * .25)
            builder_sidebar(page, 'selection')
            expect(page.locator('[data-builder-property=torchLit]')).to_be_visible()

        def edit_native(kind, label, value):
            page.locator(f'[data-builder-edit-torch-component={kind}]').click()
            modal = page.locator(f'[data-builder-native-editor={kind}]')
            expect(modal).to_be_visible()
            control = modal.get_by_label(label, exact=True)
            if control.get_attribute('type') in ('range', 'color'):
                control.evaluate("""(el,value)=>{el.value=String(value);
                  el.dispatchEvent(new Event('input',{bubbles:true}));
                  el.dispatchEvent(new Event('change',{bubbles:true}));}""", value)
            else:
                control.fill(str(value))
                control.dispatch_event('change')
            modal.locator('[data-native-editor-save]').click()
            expect(modal).to_have_count(0)
            expect(page.locator('[data-builder-property=torchLit]')).to_be_visible()

        def add_node(modal, kind):
            modal.locator('[data-blueprint-add]').click()
            modal.locator(f'[data-blueprint-pick-type={kind}]').click()
            modal.locator('[data-blueprint-fit]').click()
            return modal.locator(f'[data-blueprint-type={kind}]')

        def connect(modal, source, target):
            modal.locator('[data-blueprint-fit]').click()
            source.click()
            target.click()

        try:
            page.goto(builder)
            wait_ready(page)
            set_name(page, 'Synthetic torch opens a secret passage')
            artwork = upload_asset(page, 'decoration',
                                   'Synthetic torch with an intentionally long descriptive artwork label.png',
                                   harness.artwork('#b96f28'))['id']
            door_art = upload_asset(page, 'door', 'Synthetic secret passage.png', harness.artwork('#559344'))['id']
            builder_tool(page, 'door')
            page.locator('[data-builder-brush-material]').select_option(door_art)
            review.stroke((7, 6), (9, 6))
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(artwork)
            review.stroke((12, 8), (14, 10))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=behavior]').select_option('torch')
            expect(page.locator('[data-builder-property=torchState]')).to_have_value('off')
            expect(page.locator('[data-builder-property=torchLit]')).to_be_checked()
            page.locator('[data-builder-add-torch-component=particles]').click()
            page.locator('[data-builder-add-torch-component=shaders]').click()
            initial = review.save()
            torch, = initial['document']['decorations']
            door, = initial['document']['doors']
            assert torch['torch']['state'] == 'off' and torch['torch']['lit'] is True, torch
            for kind, key in (('lights', 'lightId'), ('particles', 'particleId'), ('shaders', 'shaderId')):
                component, = initial['document'][kind]
                assert component['id'] == torch['torch'][key] and component['layerId'] == torch['layerId']
            records.append({'case': 'torch-conversion-creates-one-owned-light-and-adds-native-particle-shader'})

            edit_native('lights', 'Color', '#ff8800')
            edit_native('particles', 'Quantity', .75)
            edit_native('shaders', 'Intensity', .7)
            configured = review.save()
            assert configured['document']['lights'][0]['color'] == '#ff8800'
            assert configured['document']['particles'][0]['density'] == .75
            assert configured['document']['shaders'][0]['intensity'] == .7
            records.append({'case': 'all-three-components-reuse-complete-game-editors-and-return-to-owner-selection'})

            page.locator('[data-builder-property=torchState]').select_option('on')
            page.locator('[data-builder-property=torchLit]').uncheck()
            extinguished = review.save()
            assert extinguished['document']['decorations'][0]['torch']['state'] == 'on'
            assert extinguished['document']['decorations'][0]['torch']['lit'] is False
            assert all(row['enabled'] for kind in ('lights', 'particles', 'shaders') for row in extinguished['document'][kind])
            page.locator('[data-builder-property=torchState]').select_option('off')
            page.locator('[data-builder-property=torchLit]').check()
            review.save()
            records.append({'case': 'authoring-mechanism-and-flame-are-independent-and-preserve-component-enabled-settings'})

            page.locator('[data-builder-duplicate]').click()
            duplicated = review.save()
            original, copied = duplicated['document']['decorations']
            assert original['id'] != copied['id']
            for kind, key in (('lights', 'lightId'), ('particles', 'particleId'), ('shaders', 'shaderId')):
                assert len(duplicated['document'][kind]) == 2
                assert original['torch'][key] != copied['torch'][key]
            close_panel(page)
            page.locator('[data-builder-viewport]').focus()
            page.keyboard.press('Delete')
            deleted = review.save()
            assert len(deleted['document']['decorations']) == 1
            assert all(len(deleted['document'][kind]) == 1 for kind in ('lights', 'particles', 'shaders'))
            page.locator('[data-builder-undo]').click()
            assert len(review.save()['document']['decorations']) == 2
            page.locator('[data-builder-redo]').click()
            assert len(review.save()['document']['decorations']) == 1
            records.append({'case': 'duplicate-remaps-components-and-delete-undo-redo-treat-one-composed-object'})

            select(torch['id'])
            before = review.save()['document']
            field = page.locator('[data-builder-property=x]')
            field.fill(str(torch['x'] + 2))
            field.press('Tab')
            moved = review.save()['document']
            for kind in ('lights', 'particles', 'shaders'):
                assert moved[kind][0]['x'] == before[kind][0]['x'] + 2, (kind, before[kind], moved[kind])
            layer = create_layer(page, 'Synthetic torch layer with a long descriptive label')
            select(torch['id'])
            page.locator('[data-builder-property=layerId]').select_option(layer)
            layered = review.save()['document']
            assert layered['decorations'][0]['layerId'] == layer
            assert all(row['layerId'] == layer for kind in ('lights', 'particles', 'shaders') for row in layered[kind])
            records.append({'case': 'moving-and-changing-owner-layer-carries-each-component-once'})

            page.locator('[data-builder-edit-behavior]').click()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            modal.locator('[data-blueprint-state-events] summary').click()
            modal.locator('[data-blueprint-event="enter:on"]').click()
            reference = add_node(modal, 'reference')
            reference.locator('[data-blueprint-param=targetId]').select_option(door['id'])
            action = add_node(modal, 'state')
            connect(modal, reference.locator('[data-blueprint-data-output=door]'),
                    action.locator('[data-blueprint-data-input=target]'))
            action = modal.locator('[data-blueprint-type=state]')
            action.locator('[data-blueprint-param=targetState]').select_option('open')
            modal.locator('[data-blueprint-type=state] [data-blueprint-param=players]').select_option('true')
            connect(modal, modal.locator('[data-blueprint-state-port=on]'),
                    modal.locator('[data-blueprint-type=state] [data-blueprint-input]'))
            flame = add_node(modal, 'flame')
            flame.locator('[data-blueprint-param=enabled]').select_option('false')
            connect(modal, modal.locator('[data-blueprint-type=state] [data-blueprint-output]'),
                    modal.locator('[data-blueprint-type=flame] [data-blueprint-input]'))
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text('Extinguished')
            page.screenshot(path=str(output / 'torch-blueprint-desktop.png'))
            modal.locator('[data-blueprint-save]').click()
            playable = review.save()
            assert playable['document']['decorations'][0]['blueprint']['kind'] == 'torch'
            records.append({'case': 'torch-blueprint-opens-referenced-passage-and-extinguishes-own-flame-with-dry-simulation'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                page.set_viewport_size({'width': 390, 'height': 844})
                page.goto(builder + '?project=' + playable['id'])
                wait_ready(page)
                select(torch['id'])
                expect(page.locator('[data-builder-property=torchLit]')).to_be_visible()
                page.locator('[data-builder-property=torchState]').scroll_into_view_if_needed()
                page.screenshot(path=str(output / f'torch-{locale}-390-mechanism.png'))
                page.locator('.map-builder__torch-components').scroll_into_view_if_needed()
                metrics = page.locator('#builder-editor-panels').evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], metrics
                checkbox = page.locator('[data-builder-property=torchLit]').bounding_box()
                label = page.locator('.map-builder__torch-lit:has([data-builder-property=torchLit]) > span').bounding_box()
                assert abs((checkbox['y'] + checkbox['height'] / 2) - (label['y'] + label['height'] / 2)) < 2
                assert label['x'] > checkbox['x'] + checkbox['width']
                page.screenshot(path=str(output / f'torch-{locale}-390.png'))
                records.append({'case': 'localized-mobile-composed-object-properties', 'locale': locale, 'metrics': metrics})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(builder + '?project=' + playable['id'])
            wait_ready(page)
            select(torch['id'])
            page.locator('.map-builder__torch-components').scroll_into_view_if_needed()
            page.screenshot(path=str(output / 'torch-en-1440-properties.png'))
            close_panel(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            project = review.project(playable['id'])
            scene = project['sceneId']

            def command(area, action, data):
                return page.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
                  mapId:a.scene,area:a.area,action:a.action,data:a.data})""",
                                     {'scene': scene, 'area': area, 'action': action, 'data': data})

            command('lighting', 'update', {'mode': 'none', 'darkness': 0, 'lights_out': False})
            page.evaluate("""a=>gravewrightRealtime.mapCommand('update',{
              mapId:a.scene,version:a.version,settings:{visibility:'players'}})""",
                          {'scene': scene, 'version': project['sceneVersion']})
            page.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)

            def state(target=page):
                return target.request.get(f'/api/maps/{scene}/state').json()

            native = state()
            image, = [row for row in native['images'] if row.get('torch')]
            native_door, = [row for row in native['walls'] if row['kind'] == 'door']

            def wait_state(target, mechanism, lit):
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline:
                    document = state(target)
                    current = next(row for row in document['images'] if row['id'] == image['id'])
                    if current['torch']['state'] == mechanism and current['torch']['lit'] is lit:
                        return document, current
                    target.wait_for_timeout(100)
                raise AssertionError(document)

            def guest(role):
                guest_context = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800})
                guests.append(guest_context)
                guest_context.add_cookies([{**seed['sessions'][role], 'url': base}])
                target = guest_context.new_page()
                observe(target)
                target.goto(f'{base}/game/{campaign}')
                target.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
                expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
                return target

            player = guest('player')
            public = next(row for row in state(player)['images'] if row['id'] == image['id'])
            assert public['torch'] == {'state': 'off', 'lit': True} and 'blueprint' not in public, public
            mechanism = player.locator(f'[data-smart-image-id="{image["id"]}"][data-smart-image-action=interact]')
            expect(mechanism).to_have_count(1)
            mechanism.focus()
            mechanism.press('Enter')
            opened, turned = wait_state(player, 'on', False)
            assert next(row for row in opened['walls'] if row['id'] == native_door['id'])['door_state'] == 'open'
            assert turned['rotation'] == image['rotation'] + 90
            records.append({'case': 'real-player-keyboard-turn-runs-door-and-flame-blueprint-with-private-metadata-filtered'})

            flame_control = player.locator(f'[data-smart-image-id="{image["id"]}"][data-smart-image-action=torch-light]')
            flame_control.focus()
            flame_control.press('Space')
            _, relit = wait_state(player, 'on', True)
            assert relit['rotation'] == turned['rotation']
            flame_control.focus()
            flame_control.click()
            _, dark = wait_state(player, 'on', False)
            assert dark['rotation'] == turned['rotation']
            player.screenshot(path=str(output / 'torch-player-extinguished-turned.png'))
            records.append({'case': 'player-flame-button-and-keyboard-leave-mechanism-position-and-passage-unchanged'})

            gm_native = state()
            owner = next(row for row in gm_native['images'] if row['id'] == image['id'])
            before_components = {kind: next(row for row in gm_native[kind] if row['id'] == component['id'])
                                 for kind, component in owner['torch']['components'].items()}
            command('images', 'update', {'placement_id': owner['id'], 'expected_version': owner['version'],
                                         'x': owner['x'] + 40, 'y': owner['y'] + 20, 'scale': owner['scale'] * 1.2})
            moved_native = state()
            for kind, component in owner['torch']['components'].items():
                moved_component = next(row for row in moved_native[kind] if row['id'] == component['id'])
                assert abs(moved_component['x'] - (owner['x'] + 40 + (before_components[kind]['x'] - owner['x']) * 1.2)) < .01
                assert abs(moved_component['y'] - (owner['y'] + 20 + (before_components[kind]['y'] - owner['y']) * 1.2)) < .01
                assert moved_component['enabled'] is False
            records.append({'case': 'native-game-image-transform-carries-native-components-and-keeps-flame-state'})

            streamer = guest('streamer')
            expect(streamer.locator('[data-smart-image-id]')).to_have_count(0)
            refusal = streamer.evaluate("""a=>new Promise((resolve,reject)=>{
              const table=document.querySelector('#table-workspace').dataset.tableId;
              const socket=new WebSocket(`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/ws/tables/${table}/`);
              const timer=setTimeout(()=>{socket.close();reject(Error('Read-only response timed out.'));},5000);
              socket.addEventListener('open',()=>socket.send(JSON.stringify({type:'maps.command',payload:{
                requestId:crypto.randomUUID(),action:'objects',data:{mapId:a.scene,area:'images',
                action:'torch-light',data:{image_id:a.id,lit:true}}}})));
              socket.addEventListener('message',event=>{const result=JSON.parse(event.data);
                if(result.type==='error'&&result.payload?.code==='read_only'){
                  clearTimeout(timer);socket.close();resolve(result.payload);}});
              socket.addEventListener('error',()=>{clearTimeout(timer);socket.close();reject(Error('Socket failed.'));});
            })""", {'scene': scene, 'id': image['id']})
            assert refusal['code'] == 'read_only', refusal
            _, still_dark = wait_state(player, 'on', False)
            assert still_dark['torch']['lit'] is False
            records.append({'case': 'streamer-remains-read-only-with-no-interaction-controls-or-write-permission'})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            for guest_context in guests:
                guest_context.close()
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Synthetic solid-color PNGs and silent WAV; no operator data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
