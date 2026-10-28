"""Inactive systems stay out of the table's extension controls."""
from playwright.sync_api import expect
from migration_closure import main


def check(gm, player, data, output):
    packages = [
        {'id': 'review.dice', 'version': '1.0.0', 'name': 'Dice'},
        {'id': 'review.system', 'version': '1.0.0', 'name': 'Inactive system', 'system': {'actorTypes': []}},
        {'id': 'review.translator', 'version': '1.0.0', 'name': 'Translator', 'locales': {}},
    ]
    for page in (gm, player):
        page.route('**/api/module-packages', lambda route: route.fulfill(json=packages))
        page.reload()
        rows = page.locator('[data-table-modules] [data-package-id]')
        expect(rows).to_have_count(2)
        assert rows.evaluate_all('(rows)=>rows.map(row=>row.dataset.packageId)') == ['review.dice', 'review.translator']
        expect(page.locator('[data-table-modules] [data-package-id="review.system"]')).to_have_count(0)
    expect(gm.locator('[data-table-modules] [data-package-id="review.dice"] button')).to_have_text('Activate')
    print('Table packages: inactive systems hidden for GM/player, ordinary modules preserved', flush=True)


if __name__ == '__main__':
    main(check)
