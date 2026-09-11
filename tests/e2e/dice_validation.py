"""Preset drafts and submitted rolls validate independently in the browser."""
from migration_closure import main
from playwright.sync_api import expect


def check(gm, player, data, output):
    gm.get_by_role('button', name='Chat', exact=True).click()
    gm.evaluate("""() => {
        const roll = window.gravewrightRealtime.roll;
        window.diceValidationCalls = [];
        window.gravewrightRealtime.roll = function(payload) {
            window.diceValidationCalls.push(payload);
            return roll.call(this, payload);
        };
    }""")
    tray = gm.locator('#dice-tray')
    for index, (button, visibility) in enumerate([('Roll', 'public'), ('To GM', 'gm'), ('Enter', 'public')]):
        gm.get_by_role('button', name='Dice tray', exact=True).click()
        tray.get_by_role('button', name='RPG presets', exact=True).click()
        expression = tray.locator('[name=expression]')
        repeat = tray.locator('[name=repeat]')
        # Applying a valid preset must work even if the roll draft is invalid.
        repeat.fill('0')
        tray.get_by_role('button', name='Use preset', exact=True).click()
        expect(expression).to_have_value('4d6dl1')
        expect(repeat).to_have_value('6')
        tray.locator('[data-preset-field=attributes]').fill('0')
        expect(tray.get_by_role('button', name='Use preset', exact=True)).to_be_disabled()
        expression.fill('1d1')
        repeat.fill('0')

        def submit():
            if button == 'Enter':
                expression.press('Enter')
            else:
                tray.get_by_role('button', name=button, exact=True).click()

        submit()
        assert gm.evaluate('window.diceValidationCalls.length') == index
        expect(repeat).to_be_focused()
        repeat.fill('1')
        submit()
        expect(tray).to_be_hidden(timeout=15000)
        calls = gm.evaluate('window.diceValidationCalls')
        assert len(calls) == index + 1
        assert calls[-1]['expression'] == '1d1'
        assert calls[-1]['visibility'] == visibility

    gm.get_by_role('button', name='Dice tray', exact=True).click()
    tray.get_by_role('button', name='RPG presets', exact=True).click()
    tray.get_by_role('button', name='d20 check', exact=True).click()
    tray.locator('[data-preset-field=bonus]').fill('')
    expect(tray.get_by_role('button', name='Use preset', exact=True)).to_be_disabled()
    print('Independent preset/roll validation passed: Roll, To GM, Enter, invalid repeat and empty modifier.', flush=True)


if __name__ == '__main__':
    main(check)
