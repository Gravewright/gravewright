"""Exercise door blueprints with synthetic artwork and isolated campaign state.

The real editor modal, graph connections, simulation, persistence and generated
table transitions run in Chromium. No operator database or media is reused.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
import os
import re
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen
from uuid import uuid4
import wave

from map_builder import (ROOT, MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale,
                         fixture_environment, serve as serve_builder)
from map_builder_reference import close_panel, set_name, upload_asset, wait_ready


AUDIO_PROBE = """(() => {
  window.__blueprintAudio = {requested:[], playing:[], rejected:[]};
  const play = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function (...args) {
    const src = this.currentSrc || this.src;
    window.__blueprintAudio.requested.push(src);
    return play.apply(this, args).then(value => {
      window.__blueprintAudio.playing.push(src); return value;
    }, error => {window.__blueprintAudio.rejected.push({src,message:error.message}); throw error;});
  };
})();"""


def serve(fixture, port):
    """Extend the common disposable fixture with a generated, silent WAV."""
    from django.core import management

    original = management.call_command

    def command(name, *args, **kwargs):
        if name == 'runserver':
            from django.core.files.base import ContentFile
            from gravewright.audio.models import Track

            seed_file = fixture / 'seed.json'
            seed = json.loads(seed_file.read_text(encoding='utf-8'))
            source = BytesIO()
            with wave.open(source, 'wb') as sound:
                sound.setnchannels(1)
                sound.setsampwidth(2)
                sound.setframerate(8000)
                sound.writeframes(bytes(16000))
            track = Track(campaign_id=seed['campaign'], name='Synthetic door click',
                          content_type='audio/wav', duration=1, kind='effect', loop=False)
            track.file.save('synthetic-door.wav', ContentFile(source.getvalue()), save=True)
            seed['track'] = str(track.pk)
            seed_file.write_text(json.dumps(seed, indent=2), encoding='utf-8')
        return original(name, *args, **kwargs)

    management.call_command = command
    try:
        serve_builder(fixture, port)
    finally:
        management.call_command = original


def artwork(color):
    from PIL import Image

    source = BytesIO()
    with Image.new('RGBA', (128, 32), color) as image:
        image.save(source, 'PNG')
    return source.getvalue()


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    builder = f'{base}/game/{campaign}/map-builder'
    api = f'{base}/api/containers/{campaign}/map-builder'
    records, errors, failed, dialogs = [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_init_script(AUDIO_PROBE)
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()

        def observe(target):
            target.on('pageerror', lambda error: errors.append(str(error)))
            target.on('requestfailed', lambda request: failed.append({'url': request.url, 'error': request.failure}))

            def native_dialog(dialog):
                dialogs.append({'type': dialog.type, 'message': dialog.message})
                dialog.dismiss()

            target.on('dialog', native_dialog)

        observe(page)
        player_context = player_page = None
        try:
            page.goto(builder)
            wait_ready(page)
            set_name(page, 'Synthetic intelligent door')
            closed_asset = upload_asset(page, 'door', 'Synthetic closed door.png', artwork('#d44628'))['id']
            open_asset = upload_asset(page, 'door', 'Synthetic open door.png', artwork('#2974d9'))['id']

            def position(x, y):
                return page.locator('[data-builder-canvas]').evaluate("""(canvas, point) => {
                  const result = new DOMPoint(point.x, point.y).matrixTransform(canvas.getScreenCTM());
                  return {x: result.x, y: result.y};
                }""", {'x': x, 'y': y})

            def stroke(start, end):
                first, last = position(*start), position(*end)
                page.mouse.move(first['x'], first['y'])
                page.mouse.down()
                page.mouse.move(last['x'], last['y'], steps=4)
                page.mouse.up()

            def save():
                if page.locator('[data-map-builder]').get_attribute('data-save-state') == 'saved':
                    project_id = page.evaluate("new URL(location.href).searchParams.get('project')")
                    response = page.request.get(api + '/projects/' + project_id)
                else:
                    with page.expect_response(lambda response: response.request.method == 'POST'
                                              and '/map-builder/projects/' in response.url
                                              and not response.url.endswith(('/generate', '/update'))) as saved:
                        page.locator('[data-builder-save]').click()
                    response = saved.value
                assert response.ok, response.text()
                return response.json()['project']

            builder_tool(page, 'wall')
            page.locator('[data-builder-brush-material]').select_option('')
            stroke((3, 6), (18, 6))
            builder_tool(page, 'door')
            page.locator('[data-builder-brush-material]').select_option(closed_asset)
            stroke((8, 6), (10, 6))
            builder_tool(page, 'light')
            stroke((12, 9), (12, 9))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=enabled]').uncheck()
            close_panel(page)
            initial = save()
            assert len(initial['document']['doors']) == len(initial['document']['lights']) == 1, initial
            door_id = initial['document']['doors'][0]['id']
            light_id = initial['document']['lights'][0]['id']

            def open_editor(tool='select'):
                builder_tool(page, tool)
                builder_workspace(page)
                door = page.locator(f'[data-builder-doors] [data-object-id="{door_id}"]')
                door.dblclick()
                modal = page.locator('[data-smart-object-modal]')
                expect(modal).to_be_visible()
                assert modal.evaluate('element => !!element.closest("[role=dialog]")')
                expect(modal.locator('[data-blueprint-event-port="change"]')).to_be_visible()
                expect(modal.locator('[data-blueprint-event-port="interact"]')).to_be_visible()
                expect(modal.locator('[data-blueprint-appearance-state] option')).to_have_count(3)
                return modal

            def choose_event(modal, key):
                target = modal.locator(f'[data-blueprint-event="{key}"]')
                if not target.is_visible():
                    modal.locator('[data-blueprint-state-events] summary').click()
                target.click()

            # Editing operates on a detached draft. Escape, cancel and close
            # restore focus without changing geometry or creating new doors.
            modal = open_editor('door')
            modal.locator('[data-blueprint-appearance-state]').select_option('open')
            modal.locator('[data-blueprint-appearance]').select_option('hidden')
            page.keyboard.press('Escape')
            expect(modal).to_have_count(0)
            expect(page.locator('[data-builder-viewport]')).to_be_focused()
            assert save()['document'] == initial['document']
            records.append({'case': 'double-click-door-opens-standard-modal-and-escape-discards-draft',
                            'activeTool': 'door', 'geometryUnchanged': True})
            modal = open_editor()
            modal.locator('[data-blueprint-appearance-state]').select_option('locked')
            modal.locator('[data-blueprint-appearance]').select_option('hidden')
            modal.locator('[data-blueprint-cancel]').click()
            assert save()['document'] == initial['document']
            records.append({'case': 'cancel-discards-blueprint-and-preserves-project'})

            modal = open_editor()
            modal.locator('[data-blueprint-appearance-state]').select_option('open')
            modal.locator('[data-blueprint-appearance]').select_option('asset')
            modal.locator('[data-blueprint-asset]').select_option(open_asset)
            choose_event(modal, 'enter:open')
            expect(modal.locator('[data-blueprint-event="enter:open"]')).to_have_attribute('aria-pressed', 'true')
            event_id = modal.locator('[data-blueprint-node]').first.get_attribute('data-blueprint-node')

            def add_node(kind, **params):
                before = set(modal.locator('[data-blueprint-node]').evaluate_all(
                    'nodes => nodes.map(node => node.dataset.blueprintNode)'))
                modal.locator('[data-blueprint-add]').click()
                picker = modal.locator('[data-blueprint-node-picker]')
                expect(picker.locator('[data-blueprint-picker-search]')).to_be_focused()
                picker.locator(f'[data-blueprint-pick-type={kind}]').click()
                expect(picker).to_have_count(0)
                after = set(modal.locator('[data-blueprint-node]').evaluate_all(
                    'nodes => nodes.map(node => node.dataset.blueprintNode)'))
                created, = after - before
                for name, value in params.items():
                    control = modal.locator(f'[data-blueprint-node="{created}"] [data-blueprint-param="{name}"]')
                    tag = control.evaluate('element => element.tagName')
                    if control.get_attribute('type') == 'checkbox':
                        control.set_checked(value)
                    elif tag == 'SELECT':
                        control.select_option(str(value).lower() if isinstance(value, bool) else str(value))
                    else:
                        control.fill(str(value))
                        control.dispatch_event('change')
                return created

            def connect(source, target, port='next'):
                modal.locator(f'[data-blueprint-node="{source}"] [data-blueprint-output="{port}"]').click()
                modal.locator(f'[data-blueprint-input="{target}"]').click()

            condition = add_node('condition', state='open')
            sound = add_node('sound', trackId=seed['track'], volume=.6)
            light = add_node('light', targetId=light_id, enabled=True)
            # A light can also be chosen by clicking it on the builder map.
            modal.locator(f'[data-blueprint-node="{light}"] [data-blueprint-pick-map=lights]').click()
            expect(modal).to_be_hidden()
            lamp = position(12, 9)
            page.mouse.click(lamp['x'], lamp['y'])
            expect(modal).to_be_visible()
            expect(modal.locator(f'[data-blueprint-node="{light}"] [data-blueprint-param=targetId]')).to_have_value(light_id)
            unused = add_node('state', targetState='closed')
            connect(condition, unused, 'false')
            modal.locator(f'[data-blueprint-delete="{unused}"]').click()
            expect(modal.locator(f'[data-blueprint-input="{unused}"]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(0)
            event_header = modal.locator(f'[data-blueprint-drag="{event_id}"]')
            event_header.focus()
            event_card = modal.locator(f'[data-blueprint-node="{event_id}"]')
            original_position = event_card.evaluate('element => ({left:element.style.left, top:element.style.top})')
            for _ in range(6):
                event_header.press('Shift+ArrowLeft')
                event_header.press('Shift+ArrowUp')
            boundary = event_card.evaluate('element => ({left:element.style.left, top:element.style.top})')
            assert boundary != original_position, (boundary, original_position)
            # Past the saved origin the moved node stays on the edge and the rest of
            # the graph shifts away from it, keeping the camera on the same view.
            sound_card = modal.locator(f'[data-blueprint-node="{sound}"]')
            sound_before = sound_card.evaluate('element => ({x:element.offsetLeft, y:element.offsetTop})')
            sound_screen = sound_card.bounding_box()
            event_header.press('Shift+ArrowLeft')
            event_header.press('Shift+ArrowUp')
            assert event_card.evaluate('element => ({left:element.style.left, top:element.style.top})') == boundary
            sound_after = sound_card.evaluate('element => ({x:element.offsetLeft, y:element.offsetTop})')
            assert (sound_after['x'] - sound_before['x'], sound_after['y'] - sound_before['y']) == (50, 50), (sound_before, sound_after)
            moved_screen = sound_card.bounding_box()
            assert abs(moved_screen['x'] - sound_screen['x']) <= 1 and abs(moved_screen['y'] - sound_screen['y']) <= 1, (sound_screen, moved_screen)
            records.append({'case': 'state-actions-delete-their-connections-and-edge-movement-shifts-the-graph'})
            connect(event_id, condition)
            connect(condition, sound, 'true')
            connect(sound, light)
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(3)
            connect(light, condition)
            expect(modal.locator('[role=alert]')).to_be_visible()
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(3)
            page.keyboard.press('Escape')
            expect(modal).to_be_visible()
            expect(modal.locator('[role=alert]')).to_be_hidden()
            records.append({'case': 'graph-rejects-cycle-without-changing-previous-connections'})
            # Click the middle of the drawn cable rather than its bounding box.
            modal.locator('[data-blueprint-fit]').click()
            middle = modal.locator(f'[data-blueprint-edge="{sound}:next:{light}"] .smart-object__wire').evaluate("""path => {
              const point = path.getPointAtLength(path.getTotalLength() / 2).matrixTransform(path.getScreenCTM());
              return {x: point.x, y: point.y};
            }""")
            page.mouse.click(middle['x'], middle['y'])
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
            expect(modal.locator('[data-blueprint-canvas]')).to_be_focused()
            page.keyboard.press('Control+z')
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(3)
            page.keyboard.press('Control+Shift+z')
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
            modal.locator('[data-blueprint-undo]').click()
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(3)
            expect(modal.locator('[data-blueprint-redo]')).to_be_enabled()
            records.append({'case': 'removed-connection-restores-with-modal-undo-redo-before-saving'})
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace]')).not_to_be_empty()
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text('Synthetic door click')
            assert page.request.get(api + '/projects/' + initial['id']).json()['project']['document'] == initial['document']
            page.screenshot(path=str(output / 'blueprint-connected-simulation.png'))
            records.append({'case': 'connected-condition-sound-light-graph-simulates-without-server-writes'})
            modal.locator('[data-blueprint-save]').click()
            expect(modal).to_have_count(0)
            edited = save()
            blueprint = edited['document']['doors'][0]['blueprint']
            assert blueprint['states']['open'] == {'appearance': 'asset', 'assetId': open_asset}, blueprint
            graph = blueprint['graphs']['enter:open']
            assert len(graph['nodes']) == 4 and len(graph['edges']) == 3, graph
            saved_event = next(node for node in graph['nodes'] if node['type'] == 'event')
            assert (saved_event['x'], saved_event['y']) == (0, 0), saved_event
            assert [row['id'] for row in edited['document']['doors']] == [door_id]

            page.locator('[data-builder-undo]').click()
            assert save()['document'] == initial['document']
            page.locator('[data-builder-redo]').click()
            assert save()['document'] == edited['document']
            records.append({'case': 'saving-blueprint-is-one-undo-step-and-redo-restores-graph'})
            page.reload()
            wait_ready(page)
            assert save()['document'] == edited['document']
            modal = open_editor()
            modal.locator('[data-blueprint-appearance-state]').select_option('open')
            expect(modal.locator('[data-blueprint-appearance]')).to_have_value('asset')
            expect(modal.locator('[data-blueprint-asset]')).to_have_value(open_asset)
            choose_event(modal, 'enter:open')
            expect(modal.locator('[data-blueprint-node]')).to_have_count(4)
            expect(modal.locator('[data-blueprint-event="enter:open"] .smart-object__badge')).to_have_text('3')
            modal.locator('[data-blueprint-close]').click()
            records.append({'case': 'saved-blueprint-and-appearance-survive-reload'})

            for locale, title in (('en', 'Smart object'), ('pt-BR', 'Objeto Inteligente'), ('es', 'Objeto inteligente')):
                change_locale(page, locale, campaign)
                for width, height in ((390, 844), (320, 700)):
                    page.set_viewport_size({'width': width, 'height': height})
                    page.goto(builder + '?project=' + initial['id'])
                    wait_ready(page)
                    modal = open_editor()
                    expect(modal).to_contain_text(title)
                    modal.locator('[data-blueprint-appearance-state]').select_option('open')
                    choose_event(modal, 'enter:open')
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    for _ in range(30):
                        page.keyboard.press('Tab')
                        assert modal.evaluate('element => !!element.closest("[role=dialog]")?.contains(document.activeElement)')
                    page.screenshot(path=str(output / f'blueprint-{locale}-{width}.png'))
                    page.keyboard.press('Escape')
                    expect(modal).to_have_count(0)
                    records.append({'case': 'responsive-localized-editor-with-keyboard-focus',
                                    'locale': locale, 'width': width, 'metrics': metrics})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(builder + '?project=' + initial['id'])
            wait_ready(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            project = page.request.get(api + '/projects/' + initial['id']).json()['project']
            scene_id = project['sceneId']

            def native_command(area, action, data, target=page):
                return target.evaluate("""args => gravewrightRealtime.mapCommand('objects', {
                  mapId: args.scene, area: args.area, action: args.action, data: args.data})""",
                                       {'scene': scene_id, 'area': area, 'action': action, 'data': data})

            native = page.request.get(f'/api/maps/{scene_id}/state').json()
            door = next(wall for wall in native['walls'] if wall['kind'] == 'door')
            native_light = native['lights'][0]
            assert door['blueprint']['graphs']['enter:open'], door
            assert door['blueprintAppearance'] == {'visible': True, 'assetId': closed_asset}, door
            assert native_light['enabled'] is False, native_light
            native_command('lighting', 'update', {'mode': 'none', 'darkness': 0, 'lights_out': False})
            page.evaluate("""args => gravewrightRealtime.mapCommand('update', {
              mapId: args.scene, version: args.version, settings: {visibility:'players'}})""",
                          {'scene': scene_id, 'version': project['sceneVersion']})
            page.evaluate("scene => gravewrightRealtime.mapCommand('activate', {mapId: scene})", scene_id)
            player_context = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800})
            player_context.add_init_script(AUDIO_PROBE)
            player_context.add_cookies([{**seed['sessions']['player'], 'url': base}])
            player_page = player_context.new_page()
            observe(player_page)
            player_page.goto(f'{base}/game/{campaign}')
            player_page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(player_page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            page.locator('.individual-audio__toggle').first.click()
            player_page.locator('.individual-audio__toggle').first.click()
            expect(page.locator('.individual-audio__toggle').first).to_have_attribute('aria-pressed', 'true')
            expect(player_page.locator('.individual-audio__toggle').first).to_have_attribute('aria-pressed', 'true')
            player_state = player_page.request.get(f'/api/maps/{scene_id}/state').json()
            public_door = next(wall for wall in player_state['walls'] if wall['id'] == door['id'])
            assert 'blueprint' not in public_door and public_door['blueprintAppearance']['assetId'] == closed_asset, public_door
            assert player_page.request.get(f'/game/map-assets/{closed_asset}').ok
            assert player_page.request.get(f'/game/map-assets/{open_asset}').status == 404
            records.append({'case': 'generation-preserves-private-blueprint-and-exposes-only-active-appearance'})

            def receipt_command(request_id):
                return page.evaluate("""args => new Promise((resolve, reject) => {
                  const stop = () => {clearTimeout(timer); removeEventListener('gravewright:api-event', receive);};
                  const receive = ({detail}) => {
                    if (detail.payload.requestId !== args.id || !['maps.ack', 'maps.error'].includes(detail.type)) return;
                    stop(); detail.type === 'maps.ack' ? resolve(detail.payload.result) : reject(new Error(detail.payload.message));
                  };
                  const timer = setTimeout(() => {stop(); reject(new Error('Door receipt timed out'));}, 15000);
                  addEventListener('gravewright:api-event', receive);
                  if (!gravewrightRealtime.tableTool('maps.command', {action:'objects', requestId:args.id,
                      data:{mapId:args.scene, area:'walls', action:'door', data:{wall_id:args.door, door_state:'open'}}})) {
                    stop(); reject(new Error('The table is disconnected'));
                  }
                })""", {'id': request_id, 'scene': scene_id, 'door': door['id']})

            request_id = str(uuid4())
            result = receipt_command(request_id)
            assert result['wall']['door_state'] == 'open', result
            deadline = time.monotonic() + 10
            opened = {}
            while time.monotonic() < deadline:
                opened = player_page.request.get(f'/api/maps/{scene_id}/state').json()
                if (next(wall for wall in opened['walls'] if wall['id'] == door['id'])['door_state'] == 'open'
                        and opened['lights'][0]['enabled']):
                    break
                page.wait_for_timeout(100)
            open_door = next(wall for wall in opened['walls'] if wall['id'] == door['id'])
            assert open_door['door_state'] == 'open' and opened['lights'][0]['enabled'], opened
            assert open_door['blueprintAppearance'] == {'visible': True, 'assetId': open_asset}, open_door
            assert 'blueprint' not in open_door
            audio = page.request.get(f'/api/containers/{campaign}/modules-native/audio?sceneId={scene_id}').json()
            voice, = [voice for voice in audio['playback']['ambient'] if voice['trackId'] == seed['track']]
            assert voice['volume'] == .6 and voice['loop'] is False and voice['playId'], voice
            opened_light = opened['lights'][0]
            assert receipt_command(request_id) == result, 'retry must return the original operation receipt'
            repeated_audio = page.request.get(f'/api/containers/{campaign}/modules-native/audio?sceneId={scene_id}').json()
            repeated_voice, = [voice for voice in repeated_audio['playback']['ambient'] if voice['trackId'] == seed['track']]
            assert (repeated_audio['version'], repeated_voice['playId']) == (audio['version'], voice['playId'])
            assert page.request.get(f'/api/maps/{scene_id}/state').json()['lights'][0]['version'] == opened_light['version']
            assert player_page.request.get(f'/game/map-assets/{open_asset}').ok
            assert player_page.request.get(f'/game/map-assets/{closed_asset}').status == 404
            for target in (page, player_page):
                target.wait_for_function("id => __blueprintAudio.playing.some(src => src.endsWith('/' + id))", arg=seed['track'])
                actual_audio = target.evaluate('window.__blueprintAudio')
                assert len([src for src in actual_audio['requested'] if src.endswith('/' + seed['track'])]) == 1, actual_audio
                assert not actual_audio['rejected'], actual_audio
            records.append({'case': 'native-transition-updates-player-door-art-and-target-light',
                            'door': open_door, 'audio': audio})
            records.append({'case': 'retry-reuses-receipt-without-restarting-sound-or-reapplying-light',
                            'playId': voice['playId'], 'playbackVersion': audio['version']})
            records.append({'case': 'native-audio-transport-plays-one-effect-on-gm-and-player-devices'})

            from PIL import Image
            samples = []
            for target, name in ((page, 'gm'), (player_page, 'player')):
                deadline = time.monotonic() + 10
                color = (0, 0, 0)
                while time.monotonic() < deadline:
                    point = target.evaluate("""cell => {
                      const surface = document.querySelector('.game-board__surface').getBoundingClientRect();
                      const view = gravewrightMaps.board.viewport();
                      // Stay clear of the native interaction handle at the
                      // middle of the door while sampling the actual artwork.
                      return {x:surface.x+view.x+9.7*cell*view.scale,y:surface.y+view.y+6.025*cell*view.scale};
                    }""", initial['document']['cellSize'])
                    with Image.open(BytesIO(target.screenshot())) as screenshot:
                        color = screenshot.getpixel((round(point['x']), round(point['y'])))[:3]
                    if color[2] > color[0] + 70 and color[2] > color[1] + 35:
                        break
                    target.wait_for_timeout(150)
                assert color[2] > color[0] + 70 and color[2] > color[1] + 35, {'device': name, 'rgb': color, 'point': point}
                samples.append({'device': name, 'rgb': color})
            records.append({'case': 'alternate-open-state-art-renders-on-native-gm-and-player-canvases', 'samples': samples})
            page.screenshot(path=str(output / 'blueprint-generated-open-door.png'))

            closed = native_command('walls', 'door', {'wall_id': door['id'], 'door_state': 'closed'}, player_page)
            assert closed['wall']['door_state'] == 'closed' and 'blueprint' not in closed, closed
            assert 'blueprint' not in closed['wall']
            locked = native_command('walls', 'door', {'wall_id': door['id'], 'door_state': 'locked'})
            assert locked['wall']['door_state'] == 'locked', locked
            denied = player_page.evaluate("""args => gravewrightRealtime.mapCommand('objects', {
              mapId: args.scene, area:'walls', action:'door', data:{wall_id:args.door, door_state:'open'}})
                .then(() => ({allowed:true})).catch(error => ({allowed:false, message:error.message}))""",
                                          {'scene': scene_id, 'door': door['id']})
            assert denied['allowed'] is False, denied
            unlocked = native_command('walls', 'door', {'wall_id': door['id'], 'door_state': 'closed'})
            assert unlocked['wall']['door_state'] == 'closed', 'unlocking must leave the door closed'
            records.append({'case': 'player-may-close-but-cannot-open-locked-door-and-unlock-leaves-it-closed'})

            # The GM's automation window lists those runs, filters problems and
            # updates live; players never receive the window or its data.
            expect(player_page.locator('#automation-log-window')).to_have_count(0)
            assert player_page.request.get(f'/api/maps/{scene_id}/automation').status == 404
            page.locator('.game-menubar__layer').nth(5).click()
            page.locator('[data-dock-tool=automation]').click()
            log = page.locator('.automation-log')
            expect(log).to_be_visible()
            expect(page.locator('[data-dock-tool=automation]')).to_have_attribute('aria-pressed', 'true')
            runs = log.locator('[data-automation-run]')
            expect(runs).to_have_count(5)
            expect(log.locator('.automation-log__run--failed')).to_contain_text('This door cannot be operated.')
            expect(log.locator('.automation-log__run--completed').last).to_contain_text('Synthetic door click')
            log.locator('[data-automation-filter=problems]').click()
            expect(runs).to_have_count(1)
            metrics = log.evaluate(MEASURE)
            assert not metrics['tiny'] and not metrics['overflow'], metrics
            page.screenshot(path=str(output / 'automation-log.png'))
            log.locator('[data-automation-filter=all]').click()
            native_command('walls', 'door', {'wall_id': door['id'], 'door_state': 'open'}, player_page)
            expect(runs).to_have_count(6)
            expect(runs.first).to_contain_text('Player')
            log.locator('[data-automation-view=doors]').click()
            log.locator('[data-scene-controls-type]').select_option('door')
            door_rows = log.locator('[data-scene-controls-element]')
            expect(door_rows).to_have_count(1)
            door_rows.first.click()
            expect(log.locator('[data-scene-controls-inspector] [data-scene-controls-action=interact]')).to_be_disabled()
            log.locator('[data-automation-pause]').click()
            expect(log.locator('[data-automation-pause]')).to_have_attribute('aria-pressed', 'true')
            expect(log.locator('[data-automation-paused-note]')).to_be_visible()
            page.screenshot(path=str(output / 'automation-doors-paused.png'))
            native_command('walls', 'door', {'wall_id': door['id'], 'door_state': 'closed'}, player_page)
            log.locator('[data-automation-view=runs]').click()
            expect(runs).to_have_count(7)
            expect(runs.first).to_have_class(re.compile('automation-log__run--paused'))
            log.locator('[data-automation-pause]').click()
            expect(log.locator('[data-automation-pause]')).to_have_attribute('aria-pressed', 'false')
            expect(log.locator('[data-automation-paused-note]')).to_be_hidden()
            runs.first.locator('[data-automation-locate]').click()
            page.keyboard.press('Escape')
            expect(log).to_have_count(0)
            expect(page.locator('[data-dock-tool=automation]')).to_have_attribute('aria-pressed', 'false')
            native_command('walls', 'door', {'wall_id': door['id'], 'door_state': 'closed'})
            records.append({'case': 'gm-automation-window-lists-filters-and-live-updates-door-runs-privately'})

            # Runtime effects acknowledge only their owned state changes; a
            # scene update still preserves unrelated manually created walls.
            manual = native_command('walls', 'create', {'x1': 1500, 'y1': 1000, 'x2': 1750, 'y2': 1000})['wall']
            page.goto(builder + '?project=' + initial['id'])
            wait_ready(page)
            builder_sidebar(page, 'review')
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-review-update]').click()
            assert updated.value.ok, updated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            updated_project = page.request.get(api + '/projects/' + initial['id']).json()['project']
            assert updated_project['sceneId'] == scene_id
            updated_native = page.request.get(f'/api/maps/{scene_id}/state').json()
            assert next(wall for wall in updated_native['walls'] if wall['id'] == manual['id']) == manual
            updated_door = next(wall for wall in updated_native['walls'] if wall['kind'] == 'door')
            assert updated_door['id'] == door['id'] and updated_door['door_state'] == 'closed', updated_door
            assert len(updated_door['blueprint']['graphs']['enter:open']['nodes']) == 4
            assert updated_native['lights'][0]['id'] == native_light['id']
            assert updated_native['lights'][0]['enabled'] is True, 'unchanged authored defaults preserve runtime light state'
            assert next(node for node in updated_door['blueprint']['graphs']['enter:open']['nodes']
                        if node['type'] == 'light')['targetId'] == native_light['id']
            records.append({'case': 'scene-update-keeps-blueprint-live-state-and-unrelated-manual-wall'})

            # Deleting an alternate state image removes its references but
            # keeps the native door, collision state and execution graph.
            deleted = page.evaluate("""async args => {
              const csrf = await (await fetch('/__gravewright/csrf')).json();
              const response = await fetch(args.url, {method:'POST',
                headers:{'Content-Type':'application/json', [csrf.header]:csrf.token},
                body:JSON.stringify({asset_id:args.id})});
              return {status:response.status, body:await response.json()};
            }""", {'url': f'/api/containers/{campaign}/library/assets/delete', 'id': open_asset})
            assert deleted['status'] == 200, deleted
            clean_project = page.request.get(api + '/projects/' + initial['id']).json()['project']
            clean_door = clean_project['document']['doors'][0]
            assert clean_door['blueprint']['states']['open'] == {'appearance': 'inherit'}, clean_door
            assert all(row['assetId'] != open_asset for row in clean_project['document']['assets'])
            clean_native = page.request.get(f'/api/maps/{scene_id}/state').json()
            clean_native_door = next(wall for wall in clean_native['walls'] if wall['id'] == door['id'])
            assert clean_native_door['door_state'] == 'closed'
            assert clean_native_door['blueprint']['states']['open'] == {'appearance': 'inherit'}
            assert len(clean_native_door['blueprint']['graphs']['enter:open']['edges']) == 3
            records.append({'case': 'deleting-state-art-cleans-source-and-native-references-without-losing-door-graph'})
        except Exception:
            (output / 'audio-diagnostics.json').write_text(json.dumps({
                'gm': page.evaluate('window.__blueprintAudio'),
                'player': player_page.evaluate('window.__blueprintAudio') if player_page else None,
            }, indent=2), encoding='utf-8')
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            if player_context:
                player_context.close()
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
    return {'passed': True, 'cases': records, 'pageErrors': errors,
            'nativeDialogs': dialogs, 'failedRequests': failed,
            'assets': 'Generated solid-color PNGs and a silent one-second WAV.'}


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
    output = (args.output or ROOT / 'data/map-builder-blueprints' /
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
    command = [executable, '-B', '-X', 'utf8', str(Path(__file__).resolve())]
    base = f'http://127.0.0.1:{port}'
    with (output / 'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen([*command, '--serve', '--fixture', str(fixture), '--port', str(port)],
                                  cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=log)
        try:
            for _ in range(300):
                if server.poll() is not None:
                    raise RuntimeError(f'Fixture exited; inspect {output / "server.log"}')
                try:
                    with urlopen(base, timeout=1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Fixture did not become ready.')
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
            report = check_browser(base, seed, output, args.browser_executable)
            (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
            print(json.dumps({'passed': True, 'cases': len(report['cases']), 'report': str(output / 'report.json')}))
        except Exception:
            (output / 'failure.txt').write_text(traceback.format_exc(), encoding='utf-8')
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            (output / 'server-exit.json').write_text(json.dumps({'pid': server.pid, 'exitCode': server.returncode}), encoding='utf-8')


if __name__ == '__main__':
    main()
