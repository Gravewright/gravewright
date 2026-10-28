"""Compact dock disclosure, real actions, keyboard access and responsive layout."""
from playwright.sync_api import expect
from migration_closure import main
from map_pointer_preferences import SEED, environment
from map_builder import change_locale


def check(gm, player, data, output):
    dock = gm.locator('.game-dock')
    toggle = dock.locator('[data-dock-menu-toggle]')
    menu = dock.locator('[data-dock-overflow]')
    expect(menu).to_be_hidden()
    assert dock.locator('button:visible').count() == 9
    dock.screenshot(path=str(output/'dock-desktop.png'))
    toggle.click()
    expect(menu).to_be_visible()
    expect(menu.locator('[data-panel=scenes]')).to_be_focused()
    gm.keyboard.press('ArrowDown')
    expect(menu.locator('[data-panel=journals]')).to_be_focused()
    gm.keyboard.press('Escape')
    expect(menu).to_be_hidden()
    expect(toggle).to_be_focused()
    toggle.click()
    gm.mouse.click(650,300)
    expect(menu).to_be_hidden()
    # Closed disclosure must not disable existing global keyboard commands.
    gm.keyboard.press('m')
    expect(gm.locator('#maps-panel')).to_be_visible()
    gm.keyboard.press('m')
    expect(gm.locator('#maps-panel')).to_be_hidden()
    toggle.click()
    menu.locator('[data-panel=scenes]').click()
    expect(menu).to_be_hidden()
    expect(gm.locator('#maps-panel')).to_be_visible()
    gm.keyboard.press('m')
    gm.keyboard.press('Control+k')
    expect(gm.locator('[data-command-palette]')).to_be_visible()
    gm.keyboard.press('Escape')
    gm.keyboard.press('F6')
    expect(dock.locator('[data-shortcut-layer=walls]')).to_be_visible()
    gm.keyboard.press('F1')
    toggle.click()
    menu.screenshot(path=str(output/'dock-panels-desktop.png'))
    gm.keyboard.press('Escape')
    change_locale(gm,'pt-BR',data['campaign'])
    gm.reload();gm.wait_for_function('!!gravewrightMaps.board?.viewport()')
    for width in [1440,390,320]:
        gm.set_viewport_size({'width':width,'height':844})
        toggle = gm.locator('[data-dock-menu-toggle]');menu=gm.locator('[data-dock-overflow]')
        toggle.click()
        expect(menu).to_be_visible()
        metrics=gm.locator('.game-dock').evaluate('''dock=>{
            const menu=dock.querySelector('[data-dock-overflow]'),b=dock.getBoundingClientRect(),m=menu.getBoundingClientRect();
            return {width:b.width,left:b.left,right:b.right,menuLeft:m.left,menuRight:m.right,
                overflow:menu.scrollWidth>menu.clientWidth,
                tiny:[...dock.querySelectorAll('span,kbd,h2')].filter(e=>e.getClientRects().length&&e.textContent.trim()&&getComputedStyle(e).fontSize!=='0px').some(e=>parseFloat(getComputedStyle(e).fontSize)<12)};
        }''')
        assert metrics['left']>=0 and metrics['right']<=width and metrics['menuLeft']>=0 and metrics['menuRight']<=width, metrics
        assert not metrics['overflow'] and not metrics['tiny'],metrics
        gm.screenshot(path=str(output/f'dock-pt-BR-{width}.png'))
        gm.keyboard.press('Escape')
    # Players keep access to available panels without receiving GM-only actions.
    player.locator('[data-dock-menu-toggle]').click()
    expect(player.locator('[data-dock-overflow]')).to_be_visible()
    expect(player.locator('[data-menubar-shortcut]')).to_have_count(0)
    print('Dock: labeled groups, disclosure, focus, Escape, outside click, real panel actions, closed-menu shortcuts, layers, Portuguese at 1440/390/320px and player access passed',flush=True)


if __name__=='__main__':
    main(check,seed_extra=SEED,environment=environment)
