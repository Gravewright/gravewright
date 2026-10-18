"""Author cross-object Target cables from both sockets using real mouse input.

The disposable campaign contains synthetic artwork, an Empty Object area and
three mechanisms. Connections are saved, reloaded, rehearsed and used by real
token movement; no operator campaign or media is accessed.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import builder_tool, builder_workspace
from map_builder_asset_removal import BuilderReview
from map_builder_playtest import behavior, node, persistent_snapshot
from map_builder_reference import close_panel, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, measurements, errors, dialogs = [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1920, 'height': 1080})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        review = BuilderReview(page, campaign)

        def diagnostics():
            (output / 'measurements.json').write_text(json.dumps({
                'measurements': measurements, 'cases': records,
                'pageErrors': errors, 'nativeDialogs': dialogs}, indent=2), encoding='utf-8')

        def saved():
            expect(page.locator('[data-map-builder]')).to_have_attribute(
                'data-save-state', 'saved', timeout=20_000)
            identifier = page.evaluate("new URL(location.href).searchParams.get('project')")
            assert identifier
            return review.project(identifier)

        def editor(identifier):
            builder_tool(page, 'select')
            builder_workspace(page)
            target = page.locator(f'[data-builder-decorations] [data-object-id="{identifier}"]')
            point = target.evaluate('''group=>{
              const box=group.getBBox(),point=new DOMPoint(box.x+box.width*.25,box.y+box.height*.5)
                .matrixTransform(group.getScreenCTM());return [point.x,point.y];
            }''')
            page.mouse.dblclick(*point)
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            modal.locator('[data-blueprint-event="presence:enter"]').click()
            return modal

        def card(modal, identifier):
            return modal.locator(f'[data-blueprint-node="{identifier}"]')

        def center(locator):
            locator.scroll_into_view_if_needed()
            box = locator.bounding_box()
            assert box
            return (box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)

        def drag(modal, source, target, *, required=True):
            start = center(source)
            finish = center(target) if hasattr(target, 'bounding_box') else target
            # Re-read both endpoints after any scroll needed to reveal sockets.
            start = center(source)
            finish = center(target) if hasattr(target, 'bounding_box') else target
            page.mouse.move(*start)
            page.mouse.down()
            page.mouse.move(*finish, steps=12)
            preview = modal.locator('[data-blueprint-wire-preview]')
            visible = preview.count() == 1
            measurements.append({'start': start, 'finish': finish, 'preview': visible,
                'zoom': modal.locator('[data-blueprint-zoom-reset]').inner_text()})
            diagnostics()
            if required:
                assert visible, 'Dragging a socket must display a cable preview.'
                assert 'C' in preview.get_attribute('d')
            page.mouse.up()
            return visible

        def blank(modal):
            return modal.locator('[data-blueprint-canvas]').evaluate('''canvas=>{
              const rect=canvas.getBoundingClientRect();
              for(const fy of [.85,.7,.45,.2])for(const fx of [.9,.65,.45,.2]){
                const x=rect.left+rect.width*fx,y=rect.top+rect.height*fy;
                const hit=document.elementFromPoint(x,y);
                if(hit&&canvas.contains(hit)&&!hit.closest('[data-blueprint-node],[data-blueprint-edge]'))return [x,y];
              }throw Error('No visible blank graph point');
            }''')

        def data_edges(modal):
            return modal.locator('[data-blueprint-edge].is-data')

        def zoom_to(modal, value):
            modal.locator('[data-blueprint-zoom-reset]').click()
            if value != 100:
                bounds = modal.locator('[data-blueprint-canvas]').bounding_box()
                modal.locator('[data-blueprint-canvas]').dispatch_event('wheel', {
                    'deltaY': -math.log(value / 100) / .002,
                    'clientX': bounds['x'] + bounds['width'] / 2,
                    'clientY': bounds['y'] + bounds['height'] / 2})
            expect(modal.locator('[data-blueprint-zoom-reset]')).to_have_text(f'{value}%')

        def game():
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        try:
            page.goto(review.builder)
            wait_ready(page)
            page.locator('[data-builder-quick-name]').fill('Synthetic Target socket authoring')
            page.locator('[data-builder-quick-name]').press('Tab')
            artwork = upload_asset(page, 'decoration', 'Synthetic external mechanism.png',
                                   harness.artwork('#a56632'))['id']
            project = saved()
            document = deepcopy(project['document'])
            layer = document['layers'][0]['id']
            owner, lever, torch, door, lamp = (str(uuid4()) for _ in range(5))
            graph = {'nodes': [node('event', 'event', event='presence:enter', x=40, y=60)], 'edges': []}
            for index, (name, identifier) in enumerate((('lever', lever), ('door', door), ('torch', torch))):
                graph['nodes'].extend((node(name + 'Ref', 'reference', targetId=identifier, x=350, y=60+index*250),
                    node(name + 'State', 'state', targetState='on', x=700, y=60+index*250)))
                graph['edges'].append({'kind': 'execution', 'from': 'event',
                                      'output': 'next', 'to': name + 'State'})
            document['decorations'] = [
                {'id': owner, 'layerId': layer, 'assetId': None, 'empty': True,
                 'name': 'Synthetic encounter area', 'x': 8, 'y': 8, 'width': 4, 'height': 3,
                 'rotation': 0, 'lever': {'state': 'off'},
                 'blueprint': behavior('lever', {'presence:enter': graph})},
                {'id': lever, 'layerId': layer, 'assetId': artwork, 'x': 16, 'y': 8,
                 'width': 2, 'height': 2, 'rotation': 0, 'lever': {'state': 'off'}},
                {'id': torch, 'layerId': layer, 'assetId': artwork, 'x': 22, 'y': 8,
                 'width': 2, 'height': 2, 'rotation': 0,
                 'torch': {'state': 'off', 'lit': False, 'lightId': lamp}},
            ]
            document['lights'] = [{'id': lamp, 'layerId': layer, 'x': 23, 'y': 9,
                'brightRadius': 2, 'dimRadius': 3, 'color': '#ffbb66', 'intensity': .8,
                'enabled': False, 'rotation': 0, 'angle': 360, 'animation': 'torch'}]
            document['doors'] = [{'id': door, 'layerId': layer, 'assetId': None,
                'x1': 26, 'y1': 8, 'x2': 28, 'y2': 8, 'thickness': .4, 'state': 'closed'}]
            project = review.store(project['id'], project['version'], project['folderId'], document)
            page.goto(review.builder + '?project=' + project['id'])
            wait_ready(page)
            modal = editor(owner)

            for value in (100, 74):
                zoom_to(modal, value)
                ref = card(modal, 'leverRef').locator('[data-blueprint-data-output="door"]')
                target = card(modal, 'leverState').locator('[data-blueprint-data-input="target"]')
                drag(modal, ref, target)
                expect(data_edges(modal)).to_have_count(1)
                modal.locator('[data-blueprint-undo]').click()
                expect(data_edges(modal)).to_have_count(0)
                records.append({'case': 'reference-output-to-target-input-drag', 'zoom': value})
                drag(modal, target, ref)
                expect(data_edges(modal)).to_have_count(1)
                modal.locator('[data-blueprint-undo]').click()
                expect(data_edges(modal)).to_have_count(0)
                records.append({'case': 'target-input-to-reference-output-drag', 'zoom': value})
                diagnostics()

            target = card(modal, 'leverState').locator('[data-blueprint-data-input="target"]')
            ref = card(modal, 'leverRef').locator('[data-blueprint-data-output="door"]')
            target.click()
            picker = modal.locator('[data-blueprint-node-picker]')
            expect(picker).to_be_visible()
            expect(picker.locator('[data-blueprint-pick-type="reference"]')).to_be_enabled()
            expect(picker.locator('[data-blueprint-pick-type="state"]')).to_have_count(0)
            expect(picker.locator('[data-blueprint-pick-type="sound"]')).to_have_count(0)
            expect(picker.locator('[data-blueprint-pick-type="lightReference"]')).to_have_count(0)
            page.screenshot(path=str(output / 'target-click-filtered-reference-picker.png'))
            page.keyboard.press('Escape')
            expect(picker).to_have_count(0)
            expect(target).to_be_focused()
            expect(data_edges(modal)).to_have_count(0)
            expect(modal.locator('[data-blueprint-node]')).to_have_count(7)
            records.append({'case': 'click-target-opens-compatible-producers-and-escape-restores-focus-without-mutation'})

            target.press('Enter')
            expect(picker).to_be_visible()
            picker.locator('[data-blueprint-picker-search]').fill('element reference')
            picker.locator('[data-blueprint-picker-search]').press('Enter')
            expect(data_edges(modal)).to_have_count(1)
            expect(modal.locator('[data-blueprint-node]')).to_have_count(8)
            modal.locator('[data-blueprint-undo]').click()
            expect(data_edges(modal)).to_have_count(0)
            expect(modal.locator('[data-blueprint-node]')).to_have_count(7)
            records.append({'case': 'keyboard-target-picker-creates-compatible-reference-and-wire-as-one-undo-step'})

            drag(modal, target, blank(modal))
            expect(picker).to_be_visible()
            expect(picker.locator('[data-blueprint-pick-type="reference"]')).to_be_enabled()
            page.screenshot(path=str(output / 'target-drag-blank-reference-picker.png'))
            before_nodes = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            picker.locator('[data-blueprint-pick-type="reference"]').click()
            expect(data_edges(modal)).to_have_count(1)
            new_id, = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)')) - before_nodes
            expect(card(modal, new_id).locator('[data-blueprint-param="targetId"]')).not_to_have_value('')
            modal.locator('[data-blueprint-fit]').click()
            page.screenshot(path=str(output / 'target-drag-created-reference-wire.png'))
            # The created node and wire must remain one reversible authoring
            # operation, independent of the reference's initial target.
            modal.locator('[data-blueprint-undo]').click()
            expect(data_edges(modal)).to_have_count(0)
            expect(modal.locator('[data-blueprint-node]')).to_have_count(7)
            modal.locator('[data-blueprint-redo]').click()
            expect(data_edges(modal)).to_have_count(1)
            expect(modal.locator('[data-blueprint-node]')).to_have_count(8)
            modal.locator('[data-blueprint-undo]').click()
            expect(data_edges(modal)).to_have_count(0)
            records.append({'case': 'target-drag-to-blank-creates-reference-wire-with-atomic-undo-and-redo'})

            target.press('Shift+Enter')
            ref.press('Enter')
            expect(data_edges(modal)).to_have_count(1)
            modal.locator('[data-blueprint-undo]').click()
            expect(data_edges(modal)).to_have_count(0)
            records.append({'case': 'keyboard-target-to-existing-reference-connects'})

            ref.click()
            target.click()
            expect(data_edges(modal)).to_have_count(1)
            modal.locator('[data-blueprint-undo]').click()
            expect(data_edges(modal)).to_have_count(0)
            records.append({'case': 'existing-forward-click-to-connect-is-preserved'})

            for name in ('lever', 'door', 'torch'):
                drag(modal, card(modal, name + 'State').locator('[data-blueprint-data-input="target"]'),
                     card(modal, name + 'Ref').locator('[data-blueprint-data-output="door"]'))
                if name == 'door':
                    card(modal, 'doorState').locator('[data-blueprint-param="targetState"]').select_option('open')
            expect(data_edges(modal)).to_have_count(3)
            existing = data_edges(modal).evaluate_all('edges=>edges.map(edge=>edge.dataset.blueprintEdge)')
            drag(modal, card(modal, 'leverState').locator('[data-blueprint-data-input="target"]'),
                 card(modal, 'torchRef').locator('[data-blueprint-data-output="door"]'))
            expect(modal.locator('[role="alert"]')).to_be_visible()
            assert data_edges(modal).evaluate_all('edges=>edges.map(edge=>edge.dataset.blueprintEdge)') == existing
            records.append({'case': 'occupied-target-rejects-replacement-without-changing-existing-wires'})
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text('Activated')
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text('Open')
            page.screenshot(path=str(output / 'empty-area-target-connections.png'))
            modal.locator('[data-blueprint-close]').click()
            project = saved()
            authored = next(row for row in project['document']['decorations'] if row['id'] == owner)['blueprint']
            assert len([edge for edge in authored['graphs']['presence:enter']['edges'] if edge.get('kind') == 'data']) == 3
            records.append({'case': 'reverse-target-wires-support-another-object-door-and-torch-and-simulate'})

            page.reload()
            wait_ready(page)
            modal = editor(owner)
            expect(data_edges(modal)).to_have_count(3)
            modal.locator('[data-blueprint-close]').click()
            records.append({'case': 'connections-save-automatically-and-survive-a-reload'})

            before = persistent_snapshot(output)
            page.locator('[data-builder-test]').click()
            rehearsal = page.locator('[data-playtest]')
            rehearsal.locator('[data-playtest-element]').select_option(owner)
            rehearsal.locator('[data-playtest-event]').select_option('presence:enter')
            with page.expect_response(lambda response: response.request.method == 'POST'
                                     and response.url.endswith('/map-builder/test')) as rehearsed:
                rehearsal.locator('[data-playtest-run]').click()
            assert rehearsed.value.ok, rehearsed.value.text()
            prediction = rehearsed.value.json()
            assert prediction['ok'] and prediction['dryRun'], prediction
            changes = {row['sourceId']: row['after']['data'] for row in prediction['changes']['elements']}
            assert changes[lever]['lever']['state'] == 'on', prediction
            assert changes[torch]['torch']['state'] == 'on', prediction
            assert changes[door]['door_state'] == 'open', prediction
            assert owner not in changes, prediction
            assert persistent_snapshot(output) == before
            rehearsal.locator('[data-playtest-close]').click()
            records.append({'case': 'server-rehearsal-resolves-all-external-targets-and-rolls-back'})

            close_panel(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game()
            project = review.project(project['id'])
            scene = project['sceneId']
            actor = page.evaluate('''()=>gravewrightRealtime.resourceCommand('actors','actor.create',
              {name:'Synthetic external-target traveler'})''')
            token = page.evaluate('''a=>gravewrightRealtime.resourceCommand('tokens','place',
              {mapId:a.scene,actorId:a.actor,gridX:2,gridY:3})''',
                {'scene': scene, 'actor': actor['id']})['createdIds'][0]
            page.evaluate('''async a=>{
              const response=await(await fetch(`/api/containers/${a.campaign}/maps/${a.scene}/tokens`)).json();
              const token=response.tokens.find(row=>row.id===a.token);
              return gravewrightRealtime.resourceCommand('tokens','move',{mapId:a.scene,id:a.token,
                expectedVersion:token.version,gridX:9,gridY:9});
            }''', {'campaign': campaign, 'scene': scene, 'token': token})
            response = page.request.get(f'/api/maps/{scene}/state')
            assert response.ok, response.text()
            native = response.json()
            empty = next(row for row in native['images'] if row.get('empty'))
            native_lever = next(row for row in native['images'] if row.get('lever') and not row.get('empty'))
            native_torch = next(row for row in native['images'] if row.get('torch'))
            native_door = next(row for row in native['walls'] if row.get('kind') == 'door')
            assert empty['lever']['state'] == 'off', empty
            assert native_lever['lever']['state'] == 'on', native_lever
            assert native_torch['torch']['state'] == 'on', native_torch
            assert native_door['door_state'] == 'open', native_door
            records.append({'case': 'actual-token-entry-activates-only-wired-external-targets'})
            diagnostics()
        except Exception:
            diagnostics()
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'measurements': measurements,
            'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Synthetic PNG, disposable actor and fixture silent WAV only.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
