from __future__ import annotations

from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]


def test_marketplace_renders_exact_catalog_and_install_status() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content("""
          <input id="section-marketplace" type="radio">
          <main data-marketplace>
            <div data-marketplace-status>Last updated</div>
            <input data-marketplace-search><select data-marketplace-kind>
              <option value="">All</option><option value="addon">Addons</option><option value="ruleset">Rulesets</option>
            </select>
            <div data-marketplace-bands>
              <section data-marketplace-band="ruleset"><h2>Rulesets</h2>
                <article data-marketplace-package data-kind="ruleset" data-search="5e srd compatible framework">
                  <h3>5e SRD Compatible Framework</h3><span>v0.3.1</span><span data-marketplace-package-status>Install</span>
                  <details><summary>Details</summary><p>Stable · SDK 1</p></details>
                  <form action="/sdk/marketplace/install" data-marketplace-install>
                    <input name="package_id" value="dnd5e"><button type="submit">Install</button>
                  </form>
                </article>
              </section>
            </div>
          </main>
        """)
        page.evaluate("""() => {
          window.marketplaceRequest = null;
          window.marketplaceDestination = null;
          window.GravewrightMarketplaceNavigate = (hash) => { window.marketplaceDestination = hash; };
          window.fetch = async (_url, options) => {
            window.marketplaceRequest = {
              bodyType: options.body.constructor.name,
              packageId: options.body.get('package_id'),
            };
            return {ok: true, json: async () => ({ok: true, package_id: 'dnd5e'})};
          };
        }""")
        page.add_script_tag(path=str(ROOT / "static/js/inside/marketplace.js"))

        expect(page.get_by_role("heading", name="Rulesets")).to_be_visible()
        expect(page.locator("[data-marketplace-package]")).to_have_count(1)
        expect(page.get_by_role("heading", name="5e SRD Compatible Framework")).to_be_visible()
        expect(page.get_by_text("v0.3.1")).to_be_visible()
        page.get_by_text("Details").click()
        expect(page.get_by_text("Stable · SDK 1")).to_be_visible()
        page.get_by_role("button", name="Install").click()
        expect(page.locator("[data-marketplace-package-status]")).to_have_text("Installing…")
        expect(page.get_by_role("button", name="Install")).to_be_disabled()
        assert page.evaluate("window.marketplaceDestination") == "rulesets"
        assert page.evaluate("window.marketplaceRequest") == {
            "bodyType": "URLSearchParams",
            "packageId": "dnd5e",
        }
        browser.close()


def test_incompatible_marketplace_package_cannot_install() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content("""
          <main data-marketplace>
            <input data-marketplace-search><select data-marketplace-kind><option value="">All</option></select>
            <section data-marketplace-band="addon"><h2>Addons</h2>
              <article data-marketplace-package data-kind="addon" data-search="future addon">
                <h3>Future Addon</h3><span data-marketplace-package-status>Incompatible</span>
                <button type="button" disabled>Incompatible</button>
              </article>
            </section>
          </main>
        """)
        page.add_script_tag(path=str(ROOT / "static/js/inside/marketplace.js"))
        expect(page.get_by_role("heading", name="Future Addon")).to_be_visible()
        expect(page.get_by_role("button", name="Incompatible")).to_be_disabled()
        expect(page.locator("[data-marketplace-install]")).to_have_count(0)
        browser.close()
