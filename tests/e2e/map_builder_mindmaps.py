"""Author, rehearse and execute mind-map nodes in an isolated synthetic campaign."""
from __future__ import annotations

import json
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_clocks import snapshot
from map_builder_reference import close_panel, set_name, upload_asset, wait_ready


MAP_NAME = 'Synthetic connections between the northern observatory and the lost expedition'
TOPIC_NAME = 'Synthetic expedition has found the observatory entrance'


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign, topic_id = seed['campaign'], str(uuid4())
    records, errors, dialogs, failed, contexts, pages = [], [], [], [], [], {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))

        def client(name, role):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
            contexts.append(context)
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            context.add_init_script("window.__mindmapEvents=[];addEventListener('gravewright:api-event',event=>__mindmapEvents.push(event.detail));")
            page = context.new_page()
            pages[name] = page
            page.on('pageerror', lambda error: errors.append(error.stack or str(error)))
            page.on('requestfailed', lambda request: failed.append({'url': request.url, 'error': request.failure}))
            page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
            return page

        page = client('gm', 'gm')
        review = BuilderReview(page, campaign)

        def game(target):
            target.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def state(target=page):
            return target.evaluate('async campaign=>(await gravewright.forTable(campaign).mindmaps.state()).mindmaps', campaign)

        def open_editor(owner):
            builder_tool(page, 'select')
            builder_workspace(page)
            shape = page.locator(f'[data-builder-decorations] [data-object-id="{owner}"]')
            box = shape.bounding_box()
            page.mouse.click(box['x'] + box['width'] * .25, box['y'] + box['height'] * .25)
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-edit-behavior]').click()
            editor = page.locator('[data-smart-object-modal]')
            expect(editor).to_be_visible()
            editor.locator('[data-blueprint-event=interact]').click()
            return editor

        def card(editor, identifier):
            return editor.locator(f'[data-blueprint-node="{identifier}"]')

        def parameter(editor, identifier, key, value):
            card(editor, identifier).locator(f'[data-blueprint-param="{key}"]').select_option(str(value))

        def add(editor, kind, **params):
            before = set(editor.locator('[data-blueprint-node]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            editor.locator('[data-blueprint-add]').click()
            editor.locator(f'[data-blueprint-pick-type="{kind}"]').click()
            after = set(editor.locator('[data-blueprint-node]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            identifier, = after - before
            for key, value in params.items():
                parameter(editor, identifier, key, value)
            return identifier

        def wire(editor, source, target):
            editor.locator('[data-blueprint-fit]').click()
            source.click()
            target.click()

        try:
            page.goto(f'/game/{campaign}')
            game(page)
            created = page.evaluate('''async ({campaign,name,topic,topicId})=>gravewright.forTable(campaign).mindmaps.create({
              name,visibility:'players',document:{nodes:[{id:topicId,label:topic,completed:false}],edges:[]}})''',
                {'campaign': campaign, 'name': MAP_NAME, 'topic': TOPIC_NAME, 'topicId': topic_id})
            map_id = created['id']
            private = page.evaluate('''async ({campaign,topicId})=>gravewright.forTable(campaign).mindmaps.create({
              name:'PRIVATE SYNTHETIC MAP',document:{nodes:[{id:topicId,label:'PRIVATE TOPIC'}],edges:[]}})''',
                {'campaign': campaign, 'topicId': str(uuid4())})
            player = client('player', 'player')
            player.goto(f'/game/{campaign}')
            game(player)
            assert len(state(player)) == 1
            player.evaluate('window.__mindmapOpens=[];window.gravewrightMindMaps={open:(id,nodeId)=>__mindmapOpens.push({id,nodeId})}')

            page.goto(review.builder)
            wait_ready(page)
            set_name(page, 'Synthetic MapBuilder mind-map automation')
            artwork = upload_asset(page, 'decoration', 'Synthetic mind-map mechanism.png', harness.artwork('#38779a'))['id']
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(artwork)
            review.stroke((6, 6), (8, 8))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=behavior]').select_option('lever')
            close_panel(page)
            project = review.save()
            owner = project['document']['decorations'][0]['id']
            editor = open_editor(owner)
            complete = add(editor, 'mindMapNode', mindMapId=map_id, nodeId=topic_id, action='complete')
            opening = add(editor, 'openMindMap', mindMapId=map_id, nodeId=topic_id)
            assert card(editor, opening).locator('[data-blueprint-param=nodeId]').input_value() == topic_id
            wire(editor, editor.locator('[data-blueprint-instance] [data-blueprint-event-port=interact][data-blueprint-output=next]'),
                 card(editor, complete).locator('[data-blueprint-input]'))
            wire(editor, card(editor, complete).locator('[data-blueprint-output=next]'),
                 card(editor, opening).locator('[data-blueprint-input]'))
            editor.locator('[data-blueprint-simulate]').click()
            expect(editor.locator('[data-blueprint-trace]')).to_contain_text(MAP_NAME)
            expect(editor.locator('[data-blueprint-autosave]')).to_have_attribute('data-state', 'saved')
            page.screenshot(path=str(output / 'mindmap-builder-nodes-1440.png'))
            editor.locator('[data-blueprint-close]').click()
            project = review.save()
            assert state(player)[0]['document']['nodes'][0]['completed'] is False
            records.append({'case': 'native-chooser-authors-map-topic-completion-and-authorized-open-with-execution-continuation'})

            page.reload()
            wait_ready(page)
            editor = open_editor(owner)
            expect(card(editor, complete).locator('[data-blueprint-param=mindMapId]')).to_have_value(map_id)
            expect(card(editor, complete).locator('[data-blueprint-param=nodeId]')).to_have_value(topic_id)
            editor.locator('[data-blueprint-close]').click()
            records.append({'case': 'saved-mind-map-and-topic-bindings-survive-reload'})

            before = snapshot(output)
            page.locator('[data-builder-test]').click()
            rehearsal = page.locator('[data-playtest]')
            rehearsal.locator('[data-playtest-element]').select_option(owner)
            rehearsal.locator('[data-playtest-event]').select_option('interact')
            with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith('/map-builder/test')) as tested:
                rehearsal.locator('[data-playtest-run]').click()
            assert tested.value.ok, tested.value.text()
            result = tested.value.json()
            assert result['ok'] and result['dryRun'], result
            assert result['changes']['mindmaps'][0]['after']['nodes'][0]['completed'] is True
            expect(rehearsal.locator('[data-playtest-results]')).to_contain_text(MAP_NAME)
            assert snapshot(output) == before
            assert player.evaluate('window.__mindmapOpens') == []
            page.keyboard.press('Escape')
            records.append({'case': 'server-rehearsal-predicts-completion-without-persisting-rows-receipts-files-or-presentations'})

            for width in (1440, 320):
                page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                editor = open_editor(owner)
                metrics = editor.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (width, metrics)
                page.screenshot(path=str(output / f'mindmap-builder-nodes-{width}.png'))
                page.keyboard.press('Escape')
                records.append({'case': f'mind-map-node-layout-{width}'})
            page.set_viewport_size({'width': 1440, 'height': 900})
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game(page)
            project = review.project(project['id'])
            scene = project['sceneId']
            page.evaluate('args=>gravewrightRealtime.mapCommand("update",{mapId:args.scene,version:args.version,settings:{visibility:"players"}})',
                          {'scene': scene, 'version': project['sceneVersion']})
            page.evaluate('scene=>gravewrightRealtime.mapCommand("activate",{mapId:scene})', scene)
            player.wait_for_function('scene=>gravewrightMaps.current?.id===scene', arg=scene)
            native = page.request.get(f'/api/maps/{scene}/state').json()
            lever, = [image for image in native['images'] if image.get('lever')]
            control = player.locator(f'[data-smart-image-id="{lever["id"]}"][data-smart-image-action=interact]')
            control.focus()
            control.press('Enter')
            player.wait_for_function('window.__mindmapOpens.length===1')
            assert player.evaluate('window.__mindmapOpens') == [{'id': map_id, 'nodeId': topic_id}]
            assert state(player)[0]['document']['nodes'][0]['completed'] is True
            public_wire = json.dumps(player.evaluate('window.__mindmapEvents'))
            assert 'PRIVATE SYNTHETIC MAP' not in public_wire and private['id'] not in public_wire
            records.append({'case': 'player-mechanism-completes-the-gm-bound-topic-and-delivers-only-authorized-open'})
            assert not errors, errors
            assert not dialogs, dialogs
            assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
        except Exception:
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors,
                'nativeDialogs': dialogs, 'failedRequests': failed}, indent=2), encoding='utf-8')
            for name, target in pages.items():
                target.screenshot(path=str(output / f'failure-{name}.png'), full_page=True)
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'assets': 'Generated solid-color PNG and synthetic authored map/topic names only.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
