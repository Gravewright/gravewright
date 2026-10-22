"""Actor forms use the host modal with isolated layout and save coverage.

Start compendium_server.py with a new fixture and pass its seed.json. The
scenario creates only synthetic actors/folders inside that disposable campaign.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser-executable', type=Path)
    args = parser.parse_args()
    seed = json.loads(args.seed.read_text(encoding='utf-8'))
    if seed.get('kind') != 'compendium-layout-review':
        raise RuntimeError('Use a disposable compendium_server.py fixture.')
    if not (Path(seed['fixture']) / 'review.sqlite3').is_file():
        raise RuntimeError('The disposable review database is missing.')
    from scripts.runtime_storage import configure_runtime_storage
    configure_runtime_storage(ROOT, args.output.resolve() / 'tools')
    from playwright.sync_api import expect, sync_playwright

    args.output.mkdir(parents=True, exist_ok=True)
    records, errors = [], []
    sample = next(iter(seed['systems'].values()))
    marker = uuid.uuid4().hex[:8]
    actor_name = f'Synthetic modal actor {marker}'
    folder_name = f'Synthetic modal folder {marker}'
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**(
            {'executable_path': str(args.browser_executable)}
            if args.browser_executable else {}))
        context = browser.new_context(viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**sample['sessions']['gm'], 'url': seed['base']}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(seed['base'] + '/game/' + sample['campaign'])
        page.wait_for_function('!!window.gravewrightActors')
        page.evaluate('window.gravewrightActors.showDirectory()')
        opener = page.locator('[data-actor-panel=create]')
        panel = page.locator('#actors-panel')
        background = page.locator('#app')

        def modal():
            result = page.locator('.ownership-modal-overlay > .directory-dialog')
            expect(result).to_be_visible()
            expect(result).to_have_attribute('aria-modal', 'true')
            return result

        for width in (1440, 390, 320):
            page.set_viewport_size({'width': width, 'height': 844})
            opener.click()
            form = modal()
            expect(form.locator('[name=name]')).to_be_focused()
            form.locator('[name=name]').fill(actor_name)
            measure = form.evaluate("""form => {
              const r = form.getBoundingClientRect();
              return {left:r.left,right:r.right,width:innerWidth,
                scroll:form.scrollWidth,client:form.clientWidth,
                fields:[...form.querySelectorAll('input,select')]
                  .filter(el=>el.checkVisibility()).map(el=>{
                    const s=getComputedStyle(el);
                    return {font:parseFloat(s.fontSize),tag:el.tagName,
                      arrow:s.backgroundImage};})};
            }""")
            assert 0 <= measure['left'] < measure['right'] <= width, measure
            assert measure['scroll'] <= measure['client'] + 1, measure
            for field in measure['fields']:
                assert field['font'] >= 12, field
                if field['tag'] == 'SELECT':
                    assert 'linear-gradient' in field['arrow'], field
            close = form.locator('header button')
            submit = form.locator('[type=submit]')
            expect(submit).to_be_enabled()
            close.focus()
            page.keyboard.press('Shift+Tab')
            expect(submit).to_be_focused()
            page.keyboard.press('Tab')
            expect(close).to_be_focused()
            expect(background).to_have_attribute('inert', '')
            page.screenshot(path=str(args.output / f'actor-form-{width}.png'))
            page.keyboard.press('Escape')
            expect(form).not_to_be_visible()
            expect(opener).to_be_focused()
            expect(background).not_to_have_attribute('inert', '')
            records.append({'viewport': width, 'layout': measure,
                            'focusTrapAndEscape': True})

        page.set_viewport_size({'width': 1440, 'height': 900})
        opener.click()
        form = modal()
        form.get_by_role('button', name='Cancel', exact=True).click()
        expect(form).not_to_be_visible()
        expect(opener).to_be_focused()

        # A pending rejection exercises Escape protection and retry without
        # changing the server or weakening its authorization/validation.
        page.evaluate("""() => {
          window.originalActorSave = window.gravewrightRealtime.resourceCommand;
          window.gravewrightRealtime.resourceCommand = (...args) => {
            if (args[0] === 'actors' && args[1] === 'actor.create')
              return new Promise((resolve,reject) => {
                window.rejectActorSave = () => reject(new Error('Synthetic save failure'));
              });
            return window.originalActorSave(...args);
          };
        }""")
        opener.click()
        form = modal()
        form.locator('[name=name]').fill(actor_name)
        form.locator('[type=submit]').click()
        expect(form.locator('[name=name]')).to_be_disabled()
        page.keyboard.press('Escape')
        expect(form).to_be_visible()
        page.evaluate('window.rejectActorSave()')
        expect(form.get_by_role('alert')).to_have_text('Synthetic save failure')
        expect(form.locator('[name=name]')).to_be_enabled()
        expect(form.locator('[name=name]')).to_have_value(actor_name)
        expect(form.get_by_role('button', name='Cancel', exact=True)).to_be_enabled()
        page.evaluate("""() => {
          window.gravewrightRealtime.resourceCommand = window.originalActorSave;
          delete window.originalActorSave; delete window.rejectActorSave;
        }""")
        form.locator('[type=submit]').click()
        expect(form).not_to_be_visible()
        expect(panel.get_by_text(actor_name, exact=True)).to_be_visible()
        expect(opener).to_be_focused()

        folder_opener = page.locator('[data-actor-panel=folder]')
        folder_opener.click()
        form = modal()
        form.locator('[name=label]').fill(folder_name)
        form.locator('[name=color]').fill('#5a8bc0')
        form.locator('[type=submit]').click()
        expect(form).not_to_be_visible()
        expect(panel.get_by_text(folder_name, exact=True)).to_be_visible()
        expect(folder_opener).to_be_focused()
        assert not errors, errors
        browser.close()
    result = {'layouts': records, 'cancelAndFocusRestore': True,
              'busyEscapeAndFailureRetry': True, 'actorAndFolderCreated': True,
              'pageErrors': errors}
    (args.output / 'report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'status': 'passed'}))


if __name__ == '__main__':
    main()
