from migration_closure import main
from playwright.sync_api import expect

def check(gm,player,data,output):
    for page in (gm,player):
        page.evaluate('window.gravewrightRealtime.toggleChat()')
    field=gm.locator('#chat-form textarea')
    field.fill('/')
    expect(gm.locator('.chat-command-menu')).to_be_visible()
    expect(gm.locator('.chat-command-menu [role=option]')).to_have_count(5)
    field.press('Enter')
    expect(field).to_have_value('/roll ')
    field.fill('/roll 1d1')
    field.press('Enter')
    expect(gm.locator('#chat-log article')).to_have_count(1)
    expect(player.locator('#chat-log article')).to_have_count(1)
    expect(player.locator('[data-chat-clear]')).to_have_count(0)
    expect(player.locator('.chat-message-delete')).to_have_count(0)
    gm.on('dialog',lambda dialog:dialog.accept())
    gm.get_by_role('button',name='Delete message',exact=True).click()
    expect(gm.locator('#chat-log article')).to_have_count(0)
    expect(player.locator('#chat-log article')).to_have_count(0)
    field.fill('/me raises a torch');field.press('Enter')
    expect(player.locator('#chat-log em')).to_have_text('raises a torch')
    gm.get_by_role('button',name='Clear chat history',exact=True).click()
    expect(player.locator('#chat-log article')).to_have_count(0)
    print('Slash menu, roll, emote, GM-only deletion and live clear verified',flush=True)
if __name__ == '__main__':
    main(check)
