"""Chat uses one minimize control and the shared titlebar order."""
from playwright.sync_api import expect
from migration_closure import main


def check(gm, player, data, output):
    for page in (gm,player):
        page.evaluate('window.gravewrightRealtime.toggleChat()')
        panel=page.locator('#chat-panel')
        expect(panel).to_be_visible()
        expect(panel.locator('[data-window-action=reset]')).to_have_count(1)
        expect(panel.locator('[data-window-action=minimize]')).to_have_count(1)
        order=panel.locator('header button').evaluate_all("buttons=>buttons.map(b=>b.dataset.windowAction||b.dataset.chatAction||(b.hasAttribute('data-chat-clear')?'clear':''))")
        assert order==(['clear'] if page==gm else [])+['detach','reset','minimize','close'],order
        size=panel.bounding_box()
        panel.locator('[data-chat-action=minimize]').click()
        expect(panel).to_have_class(__import__('re').compile('game-panel--minimized'))
        expect(panel.locator('[data-chat-action=minimize]')).to_have_attribute('aria-label','Restore')
        assert panel.bounding_box()['height']<60
        panel.locator('[data-chat-action=minimize]').click()
        expect(panel.locator('[data-chat-action=minimize]')).to_have_attribute('aria-label','Minimize')
        assert abs(panel.bounding_box()['height']-size['height'])<2
        panel.locator('[data-chat-action=close]').click()
        expect(panel).to_be_hidden()
        page.evaluate('window.gravewrightRealtime.toggleChat()')
        expect(panel).to_be_visible()
        assert panel.bounding_box()['height']>100
    gm.locator('#chat-panel header').screenshot(path=str(output/'chat-header.png'))
    with gm.expect_popup() as opened:
        gm.locator('[data-chat-action=detach]').click()
    popup=opened.value
    expect(popup.locator('#chat-panel')).to_be_visible()
    expect(popup.locator('[data-chat-action=detach]')).to_be_hidden()
    expect(popup.locator('[data-chat-action=minimize]')).to_be_hidden()
    expect(popup.locator('[data-window-action=reset]')).to_be_hidden()
    expect(popup.locator('[data-chat-clear]')).to_be_visible()
    expect(popup.locator('[data-chat-action=close]')).to_be_visible()
    popup.locator('[data-chat-action=close]').click()
    expect(gm.locator('#chat-panel')).to_be_visible()
    gm.set_viewport_size({'width':390,'height':844})
    gm.locator('#chat-panel [data-window-action=reset]').click()
    gm.locator('#chat-panel header').screenshot(path=str(output/'chat-header-mobile.png'))
    assert gm.locator('#chat-panel header').evaluate('e=>e.scrollWidth<=e.clientWidth')
    print('Chat header: GM/player order, one minimize, restore, close/reopen, detached controls and mobile layout passed',flush=True)


if __name__=='__main__':main(check)
