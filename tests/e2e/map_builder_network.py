"""Browse existing behavior relationships and edit their original source/native owner.

Uses the isolated Builder harness and synthetic rule graphs. The native scenario
also observes real, committed message/camera presentations and the local camera
preference; no operator data or globally running server is used.
"""
from __future__ import annotations

from copy import deepcopy
import json
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import close_panel, set_name, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        context.add_init_script('''window.__networkPresentations=[];
          addEventListener('gravewright:api-event',event=>{if(event.detail?.type==='automation.presentation')
            window.__networkPresentations.push(event.detail);});''')
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        review = BuilderReview(page, campaign)

        def network():
            return page.locator('[data-scene-network]')

        def source_network():
            builder_sidebar(page, 'tools'); page.locator('[data-builder-network]').click()
            expect(network()).to_be_visible()

        def open_rule(owner_id):
            network().locator(f'[data-network-open="{owner_id}"]').click()
            editor = page.locator('[data-smart-object-modal]')
            expect(editor).to_be_visible()
            editor.locator('[data-blueprint-event="enter:open"]').click()
            return editor

        def value(editor, state):
            editor.locator('[data-blueprint-node=change] [data-blueprint-param=targetState]').select_option(state)

        def wait_game():
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        try:
            page.goto(review.builder); wait_ready(page)
            set_name(page, 'Synthetic existing behavior network')
            for x in (12, 23):
                builder_tool(page, 'door'); review.stroke((x, 8), (x + 2, 8))
            for x in (8, 25):
                builder_tool(page, 'light'); review.stroke((x, 15), (x, 15))
            project = review.save()
            document = deepcopy(project['document'])
            owners = [row['id'] for row in document['doors']]
            lights = [row['id'] for row in document['lights']]
            missing = str(uuid4())
            definitions = page.evaluate('''args=>{
              const states=Object.fromEntries(['closed','open','locked'].map(state=>[state,{appearance:'inherit'}]));
              const n=(id,type,fields={})=>({id,type,x:200,y:100,...fields});
              const ex=(from,to)=>({from,to,output:'next',kind:'execution'});
              const data=(from,to,output='door')=>({from,to,output,kind:'data',input:'target'});
              const first={version:2,kind:'door',states,graphs:{'enter:open':{nodes:[
                n('event','event',{event:'enter:open'}), n('ref','reference',{targetId:args.owners[1]}),
                n('change','state',{targetState:'open'}),
                n('lights','elementGroup',{name:'Authored lamps '+args.owners[0],memberType:'light',targetIds:args.lights}),
                n('on','light',{targetId:args.lights[0],enabled:true}),
                n('missing','reference',{targetId:args.missing}),n('move','move',{dx:1,dy:0}),
                n('emit','emitEvent',{scope:'scene',name:'NetworkLinked'})
              ],edges:[ex('event','change'),ex('change','on'),ex('on','move'),ex('move','emit'),
                data('ref','change'),data('lights','on','targets'),data('missing','move')]}}};
              const second={version:2,kind:'door',states:structuredClone(states),graphs:{'signal:NetworkLinked':{nodes:[
                n('event','event',{event:'signal:NetworkLinked'}),
                n('message','showMessage',{text:'Synthetic authored <b>network message</b>',audience:{scope:'trigger'}}),
                n('camera','cameraFocus',{focusX:4,focusY:5,audience:{scope:'trigger'}})
              ],edges:[ex('event','message'),ex('message','camera')]}}};
              return [first,second];
            }''', {'owners': owners, 'lights': lights, 'missing': missing})
            for row, blueprint in zip(document['doors'], definitions):
                row['blueprint'] = blueprint
            project = review.store(project['id'], project['version'], project['folderId'], document)
            page.goto(review.builder + '?project=' + project['id']); wait_ready(page)

            source_network()
            expect(network().locator('[data-network-element]')).to_have_count(5)
            expect(network().locator('[data-network-edge=group]')).to_have_count(2)
            expect(network().locator('[data-network-edge=signal]')).to_have_count(1)
            network().locator('[data-network-search]').fill('NetworkLinked')
            expect(network().locator('[data-network-element]')).to_have_count(1)
            network().locator('[data-network-search]').fill('')
            network().locator('[data-network-problems]').check()
            expect(network().locator('[data-network-element]')).to_have_count(2)
            expect(network().locator(f'[data-network-element="{missing}"]')).to_be_visible()
            network().locator('[data-network-problems]').uncheck()
            assert review.project(project['id'])['document'] == project['document']
            records.append({'case': 'source-network-derives-existing-targets-groups-signals-and-searchable-missing-bindings-without-writing'})

            editor = open_rule(owners[0]); value(editor, 'locked')
            editor.locator('[data-blueprint-cancel]').click()
            expect(editor).to_have_count(0); expect(network()).to_be_visible()
            assert review.project(project['id'])['document'] == project['document']
            records.append({'case': 'nested-source-editor-cancel-restores-network-and-preserves-owner-source'})
            editor = open_rule(owners[0]); value(editor, 'locked')
            editor.locator('[data-blueprint-save]').click()
            expect(editor).to_have_count(0); expect(network()).to_be_visible()
            network().locator('[data-network-close]').click()
            changed = review.save()
            assert changed['document']['doors'][0]['blueprint']['graphs']['enter:open']['nodes'][2]['targetState'] == 'locked'
            assert changed['document']['doors'][1]['blueprint'] == definitions[1]
            records.append({'case': 'source-network-edit-updates-original-owner-in-one-project-draft-with-no-duplicate-rule'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    page.goto(review.builder + '?project=' + changed['id']); wait_ready(page); source_network()
                    metrics = network().evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'network-{locale}-{width}.png'))
                    records.append({'case': 'localized-network-at-desktop-and-phone-width', 'locale': locale, 'width': width, 'metrics': metrics})
                    page.keyboard.press('Escape'); expect(network()).to_have_count(0)

            change_locale(page, 'en', campaign); page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(review.builder + '?project=' + changed['id']); wait_ready(page); close_panel(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            wait_game()
            project = review.project(changed['id']); scene = project['sceneId']
            endpoint = f'/api/maps/{scene}/automation/network'
            catalog = page.request.get(endpoint).json()
            native_owner = next(row for row in catalog['elements'] if 'enter:open' in (row.get('blueprint') or {}).get('graphs', {}))
            native_recipient = next(row for row in catalog['elements'] if 'signal:NetworkLinked' in (row.get('blueprint') or {}).get('graphs', {}))
            page.locator('.game-menubar__layer').nth(5).click(); page.locator('[data-dock-tool=automation]').click()
            page.locator('[data-automation-network]').click(); expect(network()).to_be_visible()
            editor = open_rule(native_owner['id']); value(editor, 'open')
            with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith(native_owner['id'])) as native_saved:
                editor.locator('[data-blueprint-save]').click()
            assert native_saved.value.ok, native_saved.value.text()
            expect(editor).to_have_count(0); expect(network()).to_be_visible()
            source = review.project(changed['id'])
            authored_nodes = source['document']['doors'][0]['blueprint']['graphs']['enter:open']['nodes']
            assert authored_nodes[1]['targetId'] == owners[1]
            assert authored_nodes[2]['targetState'] == 'open'
            assert authored_nodes[3]['targetIds'] == lights
            assert source['version'] == project['version'] + 1
            fresh = page.request.get(endpoint).json()
            assert next(row for row in fresh['elements'] if row['id'] == native_owner['id'])['blueprint']['graphs']['enter:open']['nodes'][2]['targetState'] == 'open'
            network().locator('[data-network-close]').click(); page.locator('[data-automation-close]').click()
            records.append({'case': 'native-gm-network-save-updates-original-native-owner-and-remaps-back-to-authored-source-with-cas'})

            def command(state):
                return page.evaluate("args=>gravewrightRealtime.mapCommand('objects',{mapId:args.scene,area:'walls',action:'door',data:{wall_id:args.owner,door_state:args.state}})",
                                     {'scene': scene, 'owner': native_owner['id'], 'state': state})

            page.evaluate('''()=>{window.__networkCamera=[]; const board=gravewrightMaps.board, original=board.ping;
              board.ping=function(...args){window.__networkCamera.push(args);return original.apply(this,args);};}''')
            command('open')
            message = page.locator('[data-automation-presentation]')
            expect(message).to_be_visible(); expect(message).to_contain_text('Synthetic authored <b>network message</b>')
            assert message.locator('b').count() == 0
            page.wait_for_function("window.__networkPresentations.some(event=>event.payload.type==='camera')")
            assert page.evaluate('window.__networkCamera.length') == 0
            original_message = page.evaluate("window.__networkPresentations.find(event=>event.payload.type==='message')")
            page.evaluate("detail=>dispatchEvent(new CustomEvent('gravewright:api-event',{detail}))", original_message)
            expect(message.locator('p')).to_have_count(1)
            message.locator('[data-presentation-close]').click()
            records.append({'case': 'committed-message-presentation-is-plain-text-deduplicated-and-camera-is-off-by-default'})

            page.locator('.game-menubar__logo').click(); page.locator('.house-menu__section').nth(2).click()
            preference = page.locator('[data-automation-camera-preference]'); expect(preference).not_to_be_checked(); preference.check()
            page.locator('.house-menu__close').click()
            command('closed'); command('open')
            expect(message).to_be_visible()
            page.wait_for_function('window.__networkCamera.length===1')
            camera = page.evaluate("window.__networkPresentations.filter(event=>event.payload.type==='camera').at(-1)")
            page.evaluate("detail=>dispatchEvent(new CustomEvent('gravewright:api-event',{detail}))", camera)
            assert page.evaluate('window.__networkCamera.length') == 1
            message.locator('[data-presentation-close]').click()
            records.append({'case': 'local-camera-opt-in-allows-one-focus-per-real-committed-event-and-repeated-delivery-is-inert'})

            for role in ('player', 'streamer'):
                guest = browser.new_context(base_url=base)
                guest.add_cookies([{**seed['sessions'][role], 'url': base}])
                response = guest.request.get(endpoint)
                assert response.status in (403, 404), (role, response.status)
                guest.close()
            records.append({'case': 'player-and-streamer-cannot-read-private-native-network'})

        except Exception:
            if not page.is_closed(): page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs}, indent=2), encoding='utf-8')
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Disposable map with native doors/lights and plain authored messages.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
