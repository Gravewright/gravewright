"""Check native builder wall shadows, custom shader recovery and visibility.

Only the shared disposable campaign and synthetic documents are used. Pixel
comparisons sample the actual composed native canvas against its hidden state.
"""
from __future__ import annotations

from io import BytesIO
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import builder_sidebar, builder_tool, builder_workspace
from map_builder_reference import wait_ready


def check_browser(base, seed, output, executable):
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    builder = f'/game/{campaign}/map-builder'
    api = f'/api/containers/{campaign}/map-builder'
    errors, dialogs, records = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        try:
            page.goto(builder)
            wait_ready(page)
            layer, wall, door, light = (str(uuid4()) for _ in range(4))
            document = {'schemaVersion': 3, 'name': 'Synthetic native light wall shadow',
                        'columns': 20, 'rows': 16, 'cellSize': 70, 'background': '#253038',
                        'assets': [], 'layers': [{'id': layer, 'name': 'Base', 'visible': True, 'locked': False}],
                        'floors': [], 'decorations': [], 'particles': [], 'shaders': [],
                        'walls': [{'id': wall, 'layerId': layer, 'assetId': None,
                                   'x1': 10, 'y1': 4, 'x2': 10, 'y2': 12, 'thickness': .18}],
                        'doors': [{'id': door, 'layerId': layer, 'assetId': None, 'state': 'closed',
                                   'x1': 10, 'y1': 7, 'x2': 10, 'y2': 9, 'thickness': .18}],
                        'lights': [{'id': light, 'layerId': layer, 'x': 8, 'y': 8, 'brightRadius': 2,
                                    'dimRadius': 5, 'color': '#ffe0ac', 'intensity': 1, 'angle': 360,
                                    'rotation': 0, 'animation': 'none', 'enabled': True}]}
            project_id = str(uuid4())
            created = page.evaluate("""async args => {
              const csrf = await (await fetch('/__gravewright/csrf')).json();
              const response = await fetch(args.url,{method:'POST',headers:{
                'Content-Type':'application/json',[csrf.header]:csrf.token},body:JSON.stringify(args.body)});
              return {status:response.status,body:await response.json()};
            }""", {'url': api + '/projects/' + project_id, 'body': {
                'request_id': str(uuid4()), 'expected_version': 0, 'folder_id': None, 'document': document}})
            assert created['status'] == 200, created
            page.goto(builder + '?project=' + project_id)
            wait_ready(page)
            host = page.locator('[data-builder-native-effects]')
            canvas = host.locator('canvas')

            def ready():
                expect(host).to_have_attribute('data-render-state', 'ready')
                expect(canvas).to_have_count(1)
                page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')

            def points():
                return page.locator('[data-builder-canvas]').evaluate("""svg => {
                  const at = (x,y) => {const p=new DOMPoint(x,y).matrixTransform(svg.getScreenCTM());return [Math.round(p.x),Math.round(p.y)];};
                  return {front:at(9.2,8.2),passage:at(11.2,8.2),solid:at(11.2,5.5)};
                }""")

            def native_delta():
                ready()
                locations = points()
                lit = Image.open(BytesIO(page.screenshot())).convert('RGB')
                canvas.evaluate("el=>el.style.visibility='hidden'")
                plain = Image.open(BytesIO(page.screenshot())).convert('RGB')
                canvas.evaluate("el=>el.style.visibility=''")
                samples = {}
                for name, point in locations.items():
                    a, b = lit.getpixel(tuple(point)), plain.getpixel(tuple(point))
                    samples[name] = {'lit': a, 'plain': b, 'difference': sum(abs(a[i] - b[i]) for i in range(3))}
                return samples

            builder_workspace(page)
            page.locator('[data-builder-preview]').click()
            closed = native_delta()
            assert closed['front']['difference'] > 30, closed
            assert closed['passage']['difference'] <= 3, closed
            assert closed['solid']['difference'] <= 3, closed
            page.screenshot(path=str(output / 'native-wall-shadow-door-closed.png'))
            page.locator('[data-builder-preview]').click()
            builder_tool(page, 'select')
            page.locator(f'[data-builder-doors] [data-object-id="{door}"]').click()
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-door-state=open]').click()
            builder_workspace(page)
            page.locator('[data-builder-preview]').click()
            opened = native_delta()
            assert opened['front']['difference'] > 30, opened
            assert opened['passage']['difference'] > 20, opened
            assert opened['solid']['difference'] <= 3, opened
            assert abs(opened['front']['difference'] - closed['front']['difference']) <= 3, (closed, opened)
            assert page.request.get(api + '/projects/' + project_id).json()['project']['document'] == created['body']['project']['document']
            page.screenshot(path=str(output / 'native-wall-shadow-door-open.png'))
            records.append({'case': 'actual-native-light-mask-blocks-solid-wall-and-closed-door-but-passes-open-door',
                            'closed': closed, 'opened': opened})

            # Invalid custom code remains in its authored draft, is diagnosed,
            # and never reaches a live shader. Correcting it restarts the preview.
            page.locator('[data-builder-preview]').click()
            builder_sidebar(page, 'library')
            page.locator('[data-builder-role=effect]').click()
            page.locator('[data-builder-collection-filter]').select_option('shader')
            page.locator('[data-builder-shader-preset=orb-1]').click()
            coordinate = page.locator('[data-builder-canvas]').evaluate("""svg => {
              const p=new DOMPoint(15,8).matrixTransform(svg.getScreenCTM()); return [p.x,p.y];
            }""")
            page.mouse.click(*coordinate)
            shader = page.locator('[data-builder-shaders] [data-object-id]').get_attribute('data-object-id')
            builder_tool(page, 'select')
            page.locator(f'[data-builder-shaders] [data-object-id="{shader}"]').click()
            builder_sidebar(page, 'selection')
            page.locator('.map-builder__shader-source summary').click()
            source = page.locator('[data-builder-property=source]')
            source.fill('void main() { definitely_missing(finalColor); }')
            source.dispatch_event('change')
            expect(host).to_have_attribute('data-render-state', 'failed')
            expect(canvas).to_have_count(0)
            expect(page.locator('[data-builder-notice]')).to_contain_text('definitely_missing')
            expect(source).to_have_value('void main() { definitely_missing(finalColor); }')
            page.screenshot(path=str(output / 'native-invalid-shader-diagnostic.png'))
            valid_source = 'void main() { finalColor = vec4(0.8, 0.1, 0.05, 0.65); }'
            source.fill(valid_source)
            source.dispatch_event('change')
            ready()
            expect(source).to_have_value(valid_source)
            expect(canvas).to_have_css('pointer-events', 'none')
            records.append({'case': 'invalid-custom-shader-has-visible-diagnostic-and-correction-recovers-one-native-canvas'})

            source.fill('gravewright-preset://missing/v1')
            source.dispatch_event('change')
            expect(host).to_have_attribute('data-render-state', 'failed')
            expect(canvas).to_have_count(0)
            expect(page.locator('[data-builder-notice]')).to_contain_text('Unknown shader preset.')
            source.fill(valid_source)
            source.dispatch_event('change')
            ready()
            records.append({'case': 'unknown-preset-uri-is-diagnosed-and-corrected-source-recovers-preview'})

            # Native code is allowed to ignore intensity. Only the native
            # wrapper's forced opacity can justify skipping a shader entirely.
            intensity = page.locator('[data-builder-property=intensity]')
            intensity.fill('0')
            intensity.dispatch_event('change')
            ready()
            page.locator('[data-builder-notice] button').click()
            builder_workspace(page)
            ready()
            point = page.locator('[data-builder-canvas]').evaluate("""svg => {
              const p=new DOMPoint(15.2,8.2).matrixTransform(svg.getScreenCTM());return [Math.round(p.x),Math.round(p.y)];
            }""")
            visible = Image.open(BytesIO(page.screenshot())).convert('RGB').getpixel(tuple(point))
            canvas.evaluate("el=>el.style.visibility='hidden'")
            plain = Image.open(BytesIO(page.screenshot())).convert('RGB').getpixel(tuple(point))
            canvas.evaluate("el=>el.style.visibility=''")
            difference = sum(abs(visible[i] - plain[i]) for i in range(3))
            assert difference > 60, {'visible': visible, 'plain': plain, 'difference': difference}
            page.screenshot(path=str(output / 'native-custom-shader-zero-intensity.png'))
            records.append({'case': 'custom-shader-ignoring-intensity-renders-native-pixels-at-zero-intensity',
                            'visible': visible, 'plain': plain, 'difference': difference})

            # Exercise the visibility handler in this disposable page without
            # relying on headless browser tab-visibility heuristics.
            page.evaluate("""() => {
              Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
              document.dispatchEvent(new Event('visibilitychange'));
            }""")
            expect(canvas).to_have_count(0)
            page.evaluate("""() => {
              delete document.hidden;
              document.dispatchEvent(new Event('visibilitychange'));
            }""")
            ready()
            page.screenshot(path=str(output / 'native-preview-after-visibility-restore.png'))
            records.append({'case': 'simulated-document-visibility-disposes-and-restores-exactly-one-native-canvas'})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Synthetic project geometry and native effects; no operator data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
