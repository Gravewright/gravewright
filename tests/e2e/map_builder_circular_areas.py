"""Configure a circular object trigger and enter it without clicking the art."""
from copy import deepcopy

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_object_areas import behavior
from map_builder_reference import set_name, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    records, errors, dialogs = [], [], []
    campaign = seed['campaign']
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        review = BuilderReview(page, campaign)
        try:
            page.goto(review.builder)
            wait_ready(page)
            set_name(page, 'Synthetic circular object trigger')
            asset = upload_asset(page, 'decoration', 'Synthetic chest.png', harness.artwork('#ad642b'))['id']
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(asset)
            review.stroke((8, 8), (10, 10))
            project = review.save()
            original, = project['document']['decorations']
            identifier = original['id']
            obj = page.locator(f'[data-builder-decorations] [data-object-id="{identifier}"]').first

            def properties():
                builder_tool(page, 'select')
                builder_workspace(page)
                obj.click(button='right')
                page.locator('[data-builder-object-action=behavior]').click()
                modal = page.locator('[data-builder-property-modal=behavior]')
                expect(modal).to_be_visible()
                return modal

            modal = properties()
            modal.locator('[data-builder-property=presenceArea]').check()
            radius = modal.locator('[data-builder-property=presenceRadius]')
            expect(radius).to_have_value('1.5')
            radius.fill('3')
            radius.press('Tab')
            assert not modal.evaluate(MEASURE)['tiny']
            page.screenshot(path=str(output / 'circular-area-properties.png'))
            page.keyboard.press('Escape')
            builder_workspace(page)
            guide = page.locator(f'[data-builder-presence-area="{identifier}"]')
            expect(guide).to_have_attribute('r', '3')
            handle = page.locator(f'[data-builder-area-handle="{identifier}"]')
            start = handle.bounding_box()
            end = page.locator('[data-builder-canvas]').evaluate('''canvas=>{
              const p=new DOMPoint(13,9).matrixTransform(canvas.getScreenCTM());return [p.x,p.y];
            }''')
            page.mouse.move(start['x'] + start['width'] / 2, start['y'] + start['height'] / 2)
            page.mouse.down()
            page.mouse.move(*end, steps=8)
            page.mouse.up()
            expect(guide).to_have_attribute('r', '4')
            page.screenshot(path=str(output / 'circular-area-drag-handle.png'))
            project = review.save()
            source, = project['document']['decorations']
            assert source['presenceRadius'] == 4 and source['blueprint']['graphs'] == {}
            assert all(source[key] == value for key, value in original.items())
            records.append({'case': 'uploaded-image-gains-blank-smart-object-and-independent-draggable-circle'})

            page.reload()
            wait_ready(page)
            modal = properties()
            expect(modal.locator('[data-builder-property=presenceRadius]')).to_have_value('4')
            modal.locator('[data-builder-property=presenceArea]').uncheck()
            expect(modal.locator('[data-builder-property=presenceRadius]')).to_have_count(0)
            page.keyboard.press('Escape')
            project = review.save()
            assert 'presenceRadius' not in project['document']['decorations'][0]
            assert project['document']['decorations'][0]['lever']['state'] == 'off'
            records.append({'case': 'circle-persists-after-reload-and-can-be-disabled-without-removing-behavior'})

            for locale in ('pt-BR', 'es'):
                change_locale(page, locale, campaign)
                page.set_viewport_size({'width': 390, 'height': 844})
                page.goto(review.builder + '?project=' + project['id'])
                wait_ready(page)
                modal = properties()
                modal.locator('[data-builder-property=presenceArea]').check()
                metrics = modal.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], metrics
                page.screenshot(path=str(output / f'circular-area-{locale}-390.png'))
                page.keyboard.press('Escape')
                project = review.save()
                records.append({'case': 'localized-circular-area-properties-fit-narrow-viewport', 'locale': locale})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            # Author explicit effects, with click interaction disabled. A token
            # at (9,12) is outside the chest's artwork but inside its circle.
            document = deepcopy(project['document'])
            document['decorations'][0].update(presenceRadius=4, interactionEnabled=False, blueprint=behavior('lever'))
            project = review.store(project['id'], project['version'], project['folderId'], document)
            page.goto(review.builder + '?project=' + project['id'])
            wait_ready(page)
            builder_workspace(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            scene = review.project(project['id'])['sceneId']

            def image():
                response = page.request.get(f'/api/maps/{scene}/state')
                assert response.ok, response.text()
                return next(row for row in response.json()['images'] if row.get('lever'))

            native = image()
            assert native['presenceRadius'] == 4 * project['document']['cellSize']
            actor = page.evaluate('''()=>gravewrightRealtime.resourceCommand('actors','actor.create',
              {name:'Synthetic circular area traveler'})''')
            token = page.evaluate('''a=>gravewrightRealtime.resourceCommand('tokens','place',
              {mapId:a.scene,actorId:a.actor,gridX:2,gridY:12})''', {'scene': scene, 'actor': actor['id']})['createdIds'][0]

            def move(x):
                return page.evaluate('''async a=>{
                  const body=await(await fetch(`/api/containers/${a.campaign}/maps/${a.scene}/tokens`)).json();
                  const token=body.tokens.find(row=>row.id===a.id);
                  return gravewrightRealtime.resourceCommand('tokens','move',{mapId:a.scene,id:a.id,
                    expectedVersion:token.version,gridX:a.x,gridY:12});
                }''', {'campaign': campaign, 'scene': scene, 'id': token, 'x': x})

            move(9)
            assert image()['automationVariables']['AreaInside']['value'] is True
            assert image()['lever']['state'] == 'off'
            move(15)
            assert image()['automationVariables']['AreaInside']['value'] is False
            assert image()['interactionEnabled'] is False
            records.append({'case': 'committed-token-enters-and-exits-circle-outside-art-with-click-interaction-disabled'})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Generated solid-color PNG; no operator content.'}


if __name__ == '__main__':
    harness.__file__ = __file__
    harness.check_browser = check_browser
    harness.main()
