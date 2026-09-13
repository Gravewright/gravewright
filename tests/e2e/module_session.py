"""An unauthenticated table module request must stop polling and offer sign-in."""
from migration_closure import main
from playwright.sync_api import expect


def check(gm, player, data, output):
    gm.get_by_role('button', name='Settings', exact=True).click()
    gm.get_by_role('button', name='Extensions', exact=True).click()
    pane = gm.locator('[data-table-modules]')
    expect(pane.get_by_role('button', name='Refresh', exact=True)).to_be_enabled()
    # Expire only this browser's credentials; the existing table DOM remains open.
    gm.context.clear_cookies()
    requests = []
    gm.on('request', lambda r: requests.append(r.url) if r.url.endswith('/modules') else None)
    pane.get_by_role('button', name='Refresh', exact=True).click()
    expect(pane.get_by_role('alert')).to_contain_text('Your session is no longer valid')
    expect(pane.get_by_role('link', name='Sign in again')).to_have_attribute('href', '/login')
    expect(pane.get_by_role('button', name='Refresh', exact=True)).to_be_disabled()
    gm.wait_for_timeout(16000)
    assert len(requests) == 1, requests
    gm.screenshot(path=str(output / 'module-session-expired.png'))
    # The other user's authenticated access is unaffected.
    response = player.request.get(player.url.split('/game/')[0] + '/api/tables/' + data['campaign'] + '/modules')
    assert response.status == 200
    print('PASS: 401 offers sign-in, disables stale actions, stops polling and preserves other sessions.', flush=True)


if __name__ == '__main__':
    main(check)
