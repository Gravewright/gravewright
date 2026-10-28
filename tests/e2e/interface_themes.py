"""Theme selection works for owners and players, survives navigation and reload."""
from playwright.sync_api import expect
from migration_closure import main


def check(gm, player, data, output):
    for page in (gm, player):
        page.goto(page.url.split('/game/')[0] + '/inside?section=theme')
        expect(page.locator('[data-theme-choice]')).to_have_count(4)
        expect(page.locator('[data-theme-choice][value=classic]')).to_be_checked()
        for theme in ('ocean', 'forest', 'amethyst', 'classic'):
            page.locator(f'[data-theme-choice][value={theme}]').check()
            expect(page.locator('html')).to_have_attribute('data-theme', theme)
            expect(page.locator(f'[data-theme-choice][value={theme}]')).to_be_checked()
        page.locator('[data-theme-choice][value=ocean]').check()
        page.reload()
        expect(page.locator('[data-theme-choice][value=ocean]')).to_be_checked()
        assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()") == '#0d1722'
    # Navigate through real Datastar controls and preserve the checked option.
    gm.get_by_role('button', name='Settings', exact=True).first.click()
    expect(gm.locator('[data-theme-choice]')).to_have_count(0)
    gm.get_by_role('button', name='Theme', exact=True).click()
    expect(gm.locator('[data-theme-choice][value=ocean]')).to_be_checked()
    gm.locator('[data-theme-choice][value=ocean]').focus()
    gm.keyboard.press('ArrowRight')
    expect(gm.locator('[data-theme-choice][value=forest]')).to_be_checked()
    gm.keyboard.press('ArrowLeft')
    expect(gm.locator('[data-theme-choice][value=ocean]')).to_be_checked()
    gm.screenshot(path=str(output/'themes-desktop.png'))
    gm.set_viewport_size({'width':390,'height':844})
    gm.screenshot(path=str(output/'themes-mobile.png'), full_page=True)
    assert gm.evaluate('document.documentElement.scrollWidth<=innerWidth')
    gm.goto(gm.url.split('/inside')[0]+'/game/'+data['campaign'])
    expect(gm.locator('html')).to_have_attribute('data-theme','ocean')
    gm.goto(gm.url.split('/game/')[0]+'/inside?section=theme')
    gm.evaluate("localStorage.setItem('gravewright.interface-theme','invalid')")
    gm.reload()
    expect(gm.locator('[data-theme-choice][value=classic]')).to_be_checked()
    print('Themes: all palettes, owner/player, persistence, table, mobile and invalid preference passed',flush=True)


if __name__=='__main__': main(check)
