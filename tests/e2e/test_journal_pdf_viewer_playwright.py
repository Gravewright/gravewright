from __future__ import annotations

from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]


def test_journal_pdf_renders_inline_inside_diary_page() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content("""
          <main id="journal" data-journal-modal>
            <h1>Field Notes</h1>
            <section class="journal-notebook-section" id="pdf-page">
              <div class="journal-page-pdf" data-journal-pdf-inline
                   data-document-id="document-42"></div>
            </section>
          </main>
        """)
        page.evaluate("""
          () => {
            window.__opened = [];
            window.__pages = [];
            window.GravewrightPdfViewer = {
              open: async options => {
                window.__opened.push(options.url);
                options.host.innerHTML = '<canvas data-pdf-page="1"></canvas>';
                options.onPageChange({page: 1, pages: 3});
              },
              nextPage: async () => window.__pages.push(2),
              prevPage: async () => window.__pages.push(1),
              zoomBy: async factor => window.__zoom = factor,
              search: async query => query === 'dragon' ? [{page: 3}] : [],
              goToPage: async number => window.__pages.push(number),
            };
            window.fetch = async () => ({
              ok: true,
              json: async () => ({document: {
                id: 'document-42', filename: 'handout.pdf',
                url: '/game/journal/asset/document-42',
              }}),
            });
          }
        """)
        page.add_script_tag(path=str(ROOT / "static/js/journals/journal-pdf-viewer.js"))

        inline = page.locator("#pdf-page [data-journal-pdf-inline]")
        expect(inline.locator("[data-journal-pdf-host] canvas")).to_be_visible()
        expect(inline.locator("[data-journal-pdf-title]")).to_have_text("handout.pdf")
        expect(inline.locator("[data-journal-pdf-page]")).to_have_text("1 / 3")
        expect(page.locator("dialog.journal-pdf-viewer")).to_have_count(0)
        assert page.evaluate("window.__opened") == ["/game/journal/asset/document-42"]

        inline.locator("[data-journal-pdf-next]").click()
        inline.locator("[data-journal-pdf-search]").fill("dragon")
        inline.locator("[data-journal-pdf-search]").press("Enter")
        inline.locator("[data-journal-pdf-zoom-in]").click()
        assert page.evaluate("window.__pages") == [2, 3]
        assert page.evaluate("window.__zoom") == 1.25
        browser.close()


def test_uploaded_pdf_is_mounted_immediately_in_editor_page() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content("""
          <article data-journal-section data-section-id="pdf-page">
            <div class="journal-page-asset">
              <button type="button" data-page-asset-upload>Enviar arquivo</button>
              <div data-journal-pdf-inline data-page-pdf-inline hidden></div>
            </div>
          </article>
        """)
        page.evaluate("""
          () => {
            window.GravewrightPdfViewer = {
              open: async options => {
                options.host.innerHTML = '<canvas data-pdf-page="1"></canvas>';
                options.onPageChange({page: 1, pages: 1});
              },
            };
            window.fetch = async () => ({
              ok: true,
              json: async () => ({document: {
                id: 'uploaded-pdf', filename: 'uploaded.pdf',
                url: '/game/journal/asset/uploaded-pdf',
              }}),
            });
          }
        """)
        page.add_script_tag(path=str(ROOT / "static/js/journals/journal-pdf-viewer.js"))
        page.evaluate("""
          async () => {
            const host = document.querySelector('[data-page-pdf-inline]');
            host.hidden = false;
            await window.GravewrightJournalPdfViewer.mount(host, 'uploaded-pdf');
            document.querySelector('[data-page-asset-upload]').hidden = true;
          }
        """)

        inline = page.locator("[data-page-pdf-inline]")
        expect(inline).to_be_visible()
        expect(inline.locator("canvas")).to_be_visible()
        expect(inline.locator("[data-journal-pdf-title]")).to_have_text("uploaded.pdf")
        expect(page.locator("[data-page-asset-upload]")).to_be_hidden()
        expect(page.locator("dialog")).to_have_count(0)
        browser.close()
