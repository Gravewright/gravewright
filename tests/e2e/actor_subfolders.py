"""Actor folder actions must not be shadowed by the rendered Templates folder."""
from playwright.sync_api import expect
from migration_closure import main


def check(gm, player, data, output):
    gm.evaluate("()=>gravewrightRealtime.resourceCommand('actors','folder.create',{name:'Parent actor',color:'#c9a44c'})")
    gm.evaluate('gravewrightActors.toggle()')
    panel=gm.locator('#actors-panel')
    parent=panel.locator('.gw-folder').filter(has=gm.locator('.gw-folder__label',has_text='Parent actor')).first
    expect(parent).to_be_visible()
    parent.locator(':scope > header .gw-folder__toggle').click(button='right')
    gm.locator('.directory-context-menu').get_by_role('menuitem',name='Create folder',exact=True).click()
    form=gm.locator('.directory-dialog:visible');expect(form).to_be_visible()
    form.locator('[name=label]').fill('Child actor')
    form.locator('button[type=submit]').click()
    expect(panel.locator('.gw-folder__label',has_text='Child actor')).to_have_count(1)
    expect(parent.locator(':scope > header .gw-folder__toggle')).to_have_attribute('aria-expanded','true')
    child=panel.locator('.gw-folder').filter(has=gm.locator('.gw-folder__label',has_text='Child actor')).last
    expect(child).to_be_visible()
    child.locator(':scope > header .gw-folder__toggle').click(button='right')
    gm.locator('.directory-context-menu').get_by_role('menuitem',name='Edit folder',exact=True).click()
    form=gm.locator('.directory-dialog:visible')
    expect(form.locator('[name=label]')).to_have_value('Child actor')
    form.locator('[name=label]').fill('Renamed child')
    form.locator('button[type=submit]').click()
    expect(parent.locator('.gw-folder__label',has_text='Renamed child')).to_be_visible()
    # The quick subfolder button routes through the same menu as right-click.
    parent.locator(':scope > header .gw-folder__actions button').nth(1).click()
    gm.locator('.directory-context-menu').get_by_role('menuitem',name='Create folder',exact=True).click()
    form=gm.locator('.directory-dialog:visible')
    form.locator('[name=label]').fill('Second child')
    form.locator('button[type=submit]').click()
    expect(parent.locator('.gw-folder__label',has_text='Second child')).to_be_visible()
    expect(panel.locator('[role=alert]')).to_be_hidden()
    gm.reload();gm.wait_for_function('!!gravewrightMaps.board?.viewport()')
    gm.evaluate('gravewrightActors.toggle()')
    expect(parent.locator('.gw-folder__label',has_text='Renamed child')).to_be_visible()
    expect(parent.locator('.gw-folder__label',has_text='Second child')).to_be_visible()
    expect(panel.locator('.gw-folder__label',has_text='Templates')).to_have_count(1)
    print('Actor subfolders: context menu, quick action, rename, nested placement and persistence passed',flush=True)


if __name__=='__main__':main(check)
