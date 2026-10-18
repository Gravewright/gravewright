"""Create reusable campaign behaviors and apply independent, rebound copies.

The fixture owns its disposable database, generated artwork, sessions and HTTP
server. No operator campaign, configuration or media is reused.
"""
from __future__ import annotations

from copy import deepcopy
import json

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_tool, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import set_name, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        review = BuilderReview(page, campaign)

        def library():
            return page.locator('.blueprint-templates')

        def open_library(owner, blueprint=None):
            page.evaluate('''async args => {
              const {openTemplateLibrary}=await import('/static/gravewright_maps/builder/blueprint-templates.js');
              const {createTranslator}=await import('/static/gravewright_modules/i18n.js');
              const translator=createTranslator(),t=(message,params)=>translator.t(message,params);
              window.__templateApplied??=[];
              await openTemplateLibrary({campaignId:args.campaign,ownerId:args.owner,
                blueprint:args.blueprint,catalog:args.catalog,t,
                onApply:result=>window.__templateApplied.push(result)});
            }''', {'campaign': campaign, 'owner': owner, 'blueprint': blueprint or authored, 'catalog': catalog})
            expect(library()).to_be_visible()

        def choose_template(name):
            library().locator('.blueprint-templates__item').filter(has_text=name).click()
            expect(library().locator('h3').first).to_have_text(name)

        try:
            page.goto(review.builder); wait_ready(page)
            set_name(page, 'Synthetic reusable mechanisms')
            for x in (12, 23):
                builder_tool(page, 'door'); review.stroke((x, 8), (x + 2, 8))
            for x in (8, 25):
                builder_tool(page, 'light'); review.stroke((x, 15), (x, 15))
            initial = review.save()
            document = deepcopy(initial['document'])
            owners = [row['id'] for row in document['doors']]
            lights = [row['id'] for row in document['lights']]
            authored = page.evaluate('''args=>{
              const states=Object.fromEntries(['closed','open','locked'].map(state=>[state,{appearance:'inherit'}]));
              return {version:2,kind:'door',states,graphs:{'interact:closed':{nodes:[
                {id:'event',type:'event',event:'interact:closed',x:40,y:60},
                {id:'self',type:'reference',targetId:args.owners[0],x:350,y:300},
                {id:'group',type:'elementGroup',name:args.owners[0],memberType:'element',targetIds:args.owners,x:650,y:300},
                {id:'light',type:'light',targetId:args.lights[0],enabled:true,x:350,y:60},
                {id:'wait',type:'delay',seconds:3,x:650,y:60},
                {id:'text',type:'setVariable',scope:'element',name:'Identity',valueType:'text',value:[args.owners[0],'Second authored line'].join(String.fromCharCode(10)),x:950,y:60}
              ],edges:[{from:'event',to:'light',output:'next',kind:'execution'},
                {from:'light',to:'wait',output:'next',kind:'execution'},
                {from:'wait',to:'text',output:'next',kind:'execution'}]}}};
            }''', {'owners': owners, 'lights': lights})
            document['doors'][0]['blueprint'] = authored
            saved = review.store(initial['id'], initial['version'], initial['folderId'], document)
            page.goto(review.builder + '?project=' + saved['id']); wait_ready(page)
            catalog = {'assets': [], 'elements': [{'id': identifier, 'name': f'Synthetic door {index}'} for index, identifier in enumerate(owners)],
                       'lights': [{'id': identifier, 'name': f'Synthetic light {index}'} for index, identifier in enumerate(lights)],
                       'sounds': [], 'users': [], 'handouts': []}

            open_library(owners[0])
            expect(library().locator('.blueprint-templates__list')).to_contain_text('No templates')
            library().get_by_role('button', name='Save current behavior as template', exact=True).click()
            name = 'Reusable mechanism with a deliberately long authored name ' + '\u96ea' * 25
            library().get_by_label('Template name', exact=True).fill(name)
            library().get_by_label('Description', exact=True).fill('Independent graph snapshot, never a shared live link.')
            library().get_by_label('Binding · Element', exact=True).fill('Other door binding')
            library().get_by_label('Binding · Light', exact=True).fill('Light binding')
            duration = library().locator('.blueprint-templates__parameter').filter(has_text='wait · seconds')
            duration.locator('input[type=checkbox]').check()
            duration.locator('input[type=text]').fill('Wait duration')
            text_parameter = library().locator('.blueprint-templates__parameter').filter(has_text='text · value')
            text_parameter.locator('input[type=checkbox]').check()
            text_parameter.locator('input[type=text]').fill('Authored text parameter')
            with page.expect_response(lambda response: response.request.method == 'POST' and '/map-builder/templates/' in response.url) as saved_template:
                library().get_by_role('button', name='Save template', exact=True).click()
            assert saved_template.value.ok, saved_template.value.text()
            template = saved_template.value.json()['template']
            expect(library().get_by_label('Other door binding', exact=True)).to_be_visible()
            nodes = template['definition']['blueprint']['graphs']['interact:closed']['nodes']
            assert nodes[1]['targetId'] == nodes[2]['targetIds'][0]
            assert nodes[2]['name'] == owners[0] and nodes[5]['value'] == owners[0] + '\nSecond authored line'
            assert nodes[3]['targetId'] == {'binding': next(row['id'] for row in template['definition']['bindings'] if row['type'] == 'light')}
            records.append({'case': 'gm-authors-id-free-typed-bindings-self-and-opt-in-scalar-parameter-through-library-modal'})

            library().get_by_label('Other door binding', exact=True).select_option(owners[1])
            library().get_by_label('Light binding', exact=True).select_option(lights[0])
            library().get_by_label('Wait duration', exact=True).fill('9')
            expect(library().get_by_label('Authored text parameter', exact=True)).to_have_value(owners[0] + '\nSecond authored line')
            library().get_by_role('button', name='Apply independent copy', exact=True).click()
            expect(library()).to_have_count(0)
            open_library(owners[1]); choose_template(name)
            library().get_by_label('Other door binding', exact=True).select_option(owners[0])
            library().get_by_label('Light binding', exact=True).select_option(lights[1])
            library().get_by_role('button', name='Apply independent copy', exact=True).click()
            expect(library()).to_have_count(0)
            copies = page.evaluate('window.__templateApplied')
            assert len(copies) == 2
            first, second = [copy['graphs']['interact:closed']['nodes'] for copy in copies]
            assert first[1]['targetId'] == owners[0] and second[1]['targetId'] == owners[1]
            assert first[2]['targetIds'] == owners and second[2]['targetIds'] == owners[::-1]
            assert first[3]['targetId'] == lights[0] and second[3]['targetId'] == lights[1]
            assert first[4]['seconds'] == 9 and second[4]['seconds'] == 3
            assert first[5]['value'] == second[5]['value'] == owners[0] + '\nSecond authored line'
            assert review.project(saved['id']) == saved
            records.append({'case': 'two-independent-copies-rebind-self-elements-and-lights-with-different-parameter-values-without-saving-owner'})

            document['doors'][0]['blueprint'], document['doors'][1]['blueprint'] = copies
            persisted = review.store(saved['id'], saved['version'], saved['folderId'], document)
            assert persisted['document']['doors'][1]['blueprint'] == copies[1]
            records.append({'case': 'normal-project-save-revalidates-and-persists-both-independent-applied-instances'})

            # Failed response after commit must retry the exact logical operation.
            open_library(owners[0]); choose_template(name)
            library().get_by_role('button', name='Edit template', exact=True).click()
            library().get_by_label('Description', exact=True).fill('Updated library metadata, independent existing copies.')
            intercepted = []
            def lose_response(route):
                intercepted.append(route.request.post_data_json)
                response = route.fetch()
                assert response.ok, response.text()
                route.fulfill(status=503, json={'error': 'Synthetic response loss after commit'})
            page.route(f'**/map-builder/templates/{template["id"]}', lose_response, times=1)
            library().get_by_role('button', name='Save template', exact=True).click()
            expect(library().locator('[role=status]')).to_contain_text('Synthetic response loss')
            with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith(template['id'])) as retry:
                library().get_by_role('button', name='Save template', exact=True).click()
            assert retry.value.ok, retry.value.text()
            updated = retry.value.json()['template']
            assert updated['version'] == 2
            assert retry.value.request.post_data_json['request_id'] == intercepted[0]['request_id']
            assert review.project(saved['id'])['document'] == persisted['document']
            records.append({'case': 'lost-write-response-retries-same-request-uuid-once-and-library-edits-do-not-propagate'})
            library().get_by_role('button', name='Close', exact=True).click()

            page.goto(review.builder + '?project=' + saved['id']); wait_ready(page)
            builder_tool(page, 'select')
            page.locator(f'[data-builder-doors] [data-object-id="{owners[0]}"]').dblclick()
            editor = page.locator('[data-smart-object-modal]')
            expect(editor).to_be_visible()
            editor.locator('[data-blueprint-templates]').click()
            choose_template(name)
            # The real editor supplies the current map catalog and owner identity.
            library().get_by_label('Other door binding', exact=True).select_option(owners[1])
            library().get_by_label('Light binding', exact=True).select_option(lights[1])
            library().get_by_label('Wait duration', exact=True).fill('7')
            library().get_by_role('button', name='Apply independent copy', exact=True).click()
            expect(library()).to_have_count(0)
            editor.locator('[data-blueprint-event="interact:closed"]').click()
            duration = editor.locator('[data-blueprint-node=wait] [data-blueprint-param=seconds]')
            expect(duration).to_have_value('7')
            editor.locator('[data-blueprint-undo]').click()
            expect(duration).to_have_value('9')
            editor.locator('[data-blueprint-redo]').click()
            expect(duration).to_have_value('7')
            editor.locator('[data-blueprint-cancel]').click()
            expect(editor).to_have_count(0)
            assert review.project(saved['id'])['document'] == persisted['document']
            records.append({'case': 'real-editor-template-button-applies-one-undoable-draft-operation-and-cancel-preserves-server-source'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    page.goto(review.builder + '?project=' + saved['id']); wait_ready(page)
                    open_library(owners[0]); choose_template(name)
                    metrics = library().evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'templates-{locale}-{width}.png'))
                    records.append({'case': 'localized-library-with-long-authored-labels-at-desktop-and-phone-width', 'locale': locale, 'width': width, 'metrics': metrics})
                    page.keyboard.press('Escape'); expect(library()).to_have_count(0)

            change_locale(page, 'en', campaign); page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(review.builder + '?project=' + saved['id']); wait_ready(page)
            open_library(owners[0]); choose_template(name)
            library().get_by_role('button', name='Delete template', exact=True).click()
            expect(library()).to_contain_text('Existing copies will remain unchanged')
            library().get_by_role('button', name='Delete template', exact=True).click()
            expect(library().locator('.blueprint-templates__list')).to_contain_text('No templates')
            assert review.project(saved['id'])['document'] == persisted['document']
            records.append({'case': 'application-modal-delete-keeps-existing-instances-unchanged-and-uses-no-native-confirmation'})

        except Exception:
            if not page.is_closed(): page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs}, indent=2), encoding='utf-8')
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Disposable empty map and generated lights; no operator data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
