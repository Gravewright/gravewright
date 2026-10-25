"""Author a blank Smart Object on uploaded artwork without applying a preset."""
import map_builder_blueprints as harness
from map_builder import builder_tool, builder_workspace
from map_builder_asset_removal import BuilderReview
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
        editor = page.locator('[data-smart-object-modal]')
        try:
            page.goto(review.builder)
            wait_ready(page)
            set_name(page, 'Uploaded artwork with custom behavior')
            asset = upload_asset(page, 'decoration', 'Synthetic custom chest.png', harness.artwork('#a65b28'))['id']
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(asset)
            review.stroke((6, 6), (8, 8))
            review.stroke((12, 6), (14, 8))
            review.stroke((18, 6), (20, 8))
            initial = review.save()
            originals = initial['document']['decorations']
            assert len(originals) == 3 and all('lever' not in item for item in originals)
            first, second, third = [item['id'] for item in originals]

            def obj(identifier):
                return page.locator(f'[data-builder-decorations] [data-object-id="{identifier}"]').first

            # The Object placement tool must not create extra objects on either
            # click before the double-click opens the uploaded object's editor.
            builder_workspace(page)
            obj(third).click(button='left')
            expect(editor).to_have_count(0)
            expect(page.locator('[data-builder-decorations] [data-object-id]')).to_have_count(3)
            obj(third).dblclick(button='left')
            expect(editor).to_be_visible()
            editor.locator('[data-blueprint-close]').click()
            clicked = review.save()['document']['decorations']
            assert len(clicked) == 3
            converted = next(item for item in clicked if item['id'] == third)
            for key, value in originals[2].items():
                assert converted[key] == value, key
            assert converted['blueprint']['graphs'] == {}
            records.append({'case': 'left-double-click-with-object-tool-opens-the-existing-upload-without-duplicates-or-movement'})

            builder_tool(page, 'select')
            builder_workspace(page)
            obj(first).click(button='right')
            page.locator('[data-builder-object-action=nodes]').click()
            expect(editor).to_be_visible()
            expect(page.locator('[data-interactive-object-catalog]')).to_have_count(0)
            editor.locator('[data-blueprint-close]').click()
            blank = review.save()['document']['decorations'][0]
            assert blank['assetId'] == asset and blank['lever']['state'] == 'off'
            assert blank['blueprint']['graphs'] == {}
            assert all(state['appearance'] == 'inherit' for state in blank['blueprint']['states'].values())
            for key, value in originals[0].items():
                assert blank[key] == value, key
            records.append({'case': 'uploaded-object-context-opens-a-blank-blueprint-preserving-art-and-geometry'})

            obj(second).click(button='right')
            page.locator('[data-builder-object-action=behavior]').click()
            properties = page.locator('[data-builder-property-modal=behavior]')
            properties.get_by_role('button', name='Smart object', exact=True).click()
            expect(editor).to_be_visible()
            editor.locator('[data-blueprint-close]').click()
            expect(editor).to_have_count(0)
            records.append({'case': 'ordinary-uploaded-object-also-opens-from-the-behavior-inspector'})

            builder_workspace(page)
            obj(first).dblclick()
            expect(editor).to_be_visible()
            editor.locator('[data-blueprint-event=interact]').click()
            editor.locator('[data-blueprint-add]').click()
            editor.locator('[data-blueprint-pick-type=showMessage]').click()
            message = 'This custom chest was authored without a ready-made model.'
            card = editor.locator('[data-blueprint-type=showMessage]')
            card.locator('[data-blueprint-param=text]').fill(message)
            card.locator('[data-blueprint-param=text]').press('Tab')
            node_id = card.get_attribute('data-blueprint-node')
            editor.locator('[data-blueprint-fit]').click()
            editor.locator('[data-blueprint-instance] [data-blueprint-event-port=interact][data-blueprint-output=next]').click()
            card.locator('[data-blueprint-input]').click()
            page.screenshot(path=str(output / 'custom-smart-object-editor.png'))
            editor.locator('[data-blueprint-close]').click()
            expect(editor).to_have_count(0)
            saved = review.save()
            item = next(item for item in saved['document']['decorations'] if item['id'] == first)
            graph = item['blueprint']['graphs']['interact']
            assert any(node['id'] == node_id and node.get('text') == message for node in graph['nodes'])
            assert len(graph['nodes']) == 2 and len(graph['edges']) == 1
            page.reload()
            wait_ready(page)
            persisted = review.save()
            assert persisted['document']['decorations'] == saved['document']['decorations']
            records.append({'case': 'custom-nodes-and-uploaded-artwork-survive-autosave-and-reload'})

            builder_workspace(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.board?.viewport()')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            scene = review.project(saved['id'])['sceneId']
            response = page.request.get(f'/api/maps/{scene}/state')
            assert response.ok, response.text()
            native, = [image for image in response.json()['images'] if any(
                node.get('text') == message for graph in image.get('blueprint', {}).get('graphs', {}).values()
                for node in graph['nodes'])]
            assert native['asset_id'] == asset
            control = page.locator(f'[data-smart-image-id="{native["id"]}"][data-smart-image-action=interact]')
            expect(control).to_be_visible()
            control.focus()
            control.press('Enter')
            expect(page.locator('[data-automation-presentation]')).to_contain_text(message)
            page.screenshot(path=str(output / 'custom-smart-object-in-game.png'))
            records.append({'case': 'generated-object-keeps-its-uploaded-image-and-runs-the-custom-interaction'})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'A generated solid-color PNG; no operator content.'}


if __name__ == '__main__':
    harness.__file__ = __file__
    harness.check_browser = check_browser
    harness.main()
