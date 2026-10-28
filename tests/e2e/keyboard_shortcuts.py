"""Remap real table controls through the house menu, including persistence."""
from playwright.sync_api import expect
from map_builder import MEASURE, change_locale
from map_pointer_preferences import SEED, environment
from migration_closure import main


def check(gm, player, data, output):
    def open_settings(page=gm):
        page.locator('.game-menubar__logo').click()
        page.locator('.house-menu__rail').get_by_role('button', name='Shortcuts', exact=True).click()
        panel = page.locator('[data-shortcut-settings]')
        expect(panel).to_be_visible()
        return panel

    def field(action):
        return gm.locator(f'[data-shortcut-record="{action}"]')

    def close():
        gm.locator('.house-menu__close').click()

    layers = ['game', 'gm', 'composition', 'audio', 'effects', 'walls', 'lighting']
    for index, layer in enumerate(layers, 1):
        button = gm.locator(f'[data-menubar-shortcut="layer-{layer}"]')
        expect(button).to_have_attribute('aria-keyshortcuts', f'F{index}')
        gm.keyboard.press(f'F{index}')
        expect(button).to_have_attribute('aria-pressed', 'true')
        expect(button).to_have_attribute('title', __import__('re').compile(f'F{index}$'))
    gm.keyboard.press('F1')
    expect(gm.locator('[data-menubar-shortcut="layer-game"]')).to_have_attribute('aria-pressed', 'true')
    expect(player.locator('[data-menubar-shortcut]')).to_have_count(0)
    gm.evaluate("() => {const input=document.createElement('input');input.id='function-key-input';document.body.append(input);input.focus()}")
    gm.locator('#function-key-input').press('F2')
    expect(gm.locator('[data-menubar-shortcut="layer-game"]')).to_have_attribute('aria-pressed', 'true')
    gm.locator('#function-key-input').evaluate('input=>input.remove()')
    panel = open_settings()
    expect(field('window:layer-effects')).to_have_value('F5')
    field('window:layer-effects').focus()
    field('window:layer-effects').press('F6')
    expect(panel.locator('[data-shortcut-error]')).to_contain_text('already assigned')
    field('window:layer-effects').press('F5')
    expect(panel.locator('[data-shortcut-error]')).to_be_hidden()
    measure = field('tool:game:measure')
    expect(measure).to_have_value('R')
    measure.focus()
    measure.press('c')
    expect(panel.locator('[data-shortcut-error]')).to_contain_text('already assigned')
    expect(gm.locator('[data-shortcut-layer=game] [data-dock-tool=measure]')).to_have_attribute('aria-keyshortcuts', 'R')
    measure.press('Control+r')
    expect(panel.locator('[data-shortcut-error]')).to_contain_text('reserved')
    measure.press('Shift+q')
    expect(measure).to_have_value('Shift+Q')
    expect(panel.locator('[data-shortcut-error]')).to_be_hidden()
    measure.focus()
    measure.press('Escape')
    expect(panel).to_be_visible()
    expect(measure).to_have_value('Shift+Q')
    gm.screenshot(path=str(output / 'keyboard-shortcuts-desktop.png'))
    close()

    gm.keyboard.press('r')
    expect(gm.locator('.measure-panel')).to_have_count(0)
    gm.keyboard.press('Shift+q')
    expect(gm.locator('.measure-panel')).to_be_visible()
    gm.get_by_role('button', name='Close measurement', exact=True).click()
    gm.evaluate('''() => {const input=document.createElement('textarea');input.id='shortcut-fixture-input';document.body.append(input);input.focus();}''')
    gm.locator('#shortcut-fixture-input').press('Shift+q')
    expect(gm.locator('#shortcut-fixture-input')).to_have_value('q')
    expect(gm.locator('.measure-panel')).to_have_count(0)
    gm.locator('#shortcut-fixture-input').evaluate('input=>input.remove()')
    gm.reload()
    gm.wait_for_function('!!gravewrightMaps.board?.viewport()')
    panel = open_settings()
    expect(field('tool:game:measure')).to_have_value('Shift+Q')
    expect(player.locator('[data-shortcut-layer=game] [data-dock-tool=measure]')).to_have_attribute('aria-keyshortcuts', 'R')

    panel.locator('[data-shortcut-clear="tool:game:measure"]').click()
    expect(field('tool:game:measure')).to_have_value('Unassigned')
    close()
    gm.keyboard.press('Shift+q')
    expect(gm.locator('.measure-panel')).to_have_count(0)
    panel = open_settings()
    panel.locator('[data-shortcut-reset]').click()
    expect(field('tool:game:measure')).to_have_value('R')

    # The palette's old hardcoded listener must honor its custom combination.
    search = field('window:search')
    search.focus()
    search.press('Control+Shift+F2')
    expect(search).to_have_value('Ctrl+Shift+F2')
    close()
    gm.keyboard.press('Control+k')
    expect(gm.locator('[data-command-palette]')).to_be_hidden()
    gm.keyboard.press('Control+Shift+F2')
    expect(gm.locator('[data-command-palette]')).to_be_visible()
    gm.keyboard.press('Escape')
    expect(gm.locator('[data-command-palette]')).to_be_hidden()
    panel = open_settings()
    panel.locator('[data-shortcut-reset]').click()
    close()
    gm.keyboard.press('r')
    expect(gm.locator('.measure-panel')).to_be_visible()
    gm.get_by_role('button', name='Close measurement', exact=True).click()

    change_locale(gm, 'pt-BR', data['campaign'])
    gm.reload()
    gm.wait_for_function('!!gravewrightMaps.board?.viewport()')
    gm.set_viewport_size({'width': 390, 'height': 844})
    gm.locator('.game-menubar__logo').click()
    gm.locator('.house-menu__rail').get_by_role('button', name='Atalhos', exact=True).click()
    panel = gm.locator('[data-shortcut-settings]')
    expect(panel).to_be_visible()
    expect(panel.get_by_role('button', name='Restaurar padrões', exact=True)).to_be_visible()
    metrics = panel.evaluate(MEASURE)
    assert not metrics['tiny'] and not metrics['overflow'], metrics
    gm.screenshot(path=str(output / 'keyboard-shortcuts-pt-BR-mobile.png'))
    close()
    gm.set_viewport_size({'width': 1440, 'height': 1000})
    expect(gm.locator('[data-scene-builder-open]')).to_be_visible()
    gm.keyboard.press('F8')
    gm.wait_for_url('**/map-builder?project=*')
    print('Keyboard shortcuts: recording, conflicts, reserved combinations, cancellation, dispatch, typing, persistence, profile isolation, unassign/reset, remapped search and Portuguese mobile layout passed', flush=True)


if __name__ == '__main__':
    main(check, seed_extra=SEED, environment=environment)
