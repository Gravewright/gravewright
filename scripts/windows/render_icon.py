"""Export the existing CSS house mark to a Windows icon; not a runtime step.

Run ``uv run --locked python scripts/windows/render_icon.py`` after installing
Playwright Chromium (``uv run --locked playwright install chromium``). Pillow
only packages/resizes the browser-rendered pixels into the ICO container.
See ICON-NOTICE.md for the inherited UI attribution and source files.
"""

from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


def main() -> None:
    """Render the canonical CSS at a larger scale, preserving its proportions."""
    root = Path(__file__).resolve().parents[2]
    css_root = root / 'gravewright/web/static/gravewright_web/css'
    tokens = (css_root / 'tokens.css').read_text(encoding='utf-8')
    mark = (css_root / 'blocks/mark.css').read_text(encoding='utf-8')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={'width': 256, 'height': 256})
        page.set_content(
            '<style>' + tokens + mark + '''
            html, body { margin: 0; background: transparent; }
            .gw-mark {
                box-sizing: border-box;
                width: 256px;
                height: 256px;
                border-width: calc(256px / 34);
            }
            </style><span class="gw-mark"></span>'''
        )
        pixels = page.locator('.gw-mark').screenshot(omit_background=True)
        browser.close()
    with Image.open(BytesIO(pixels)) as rendered:
        rendered.save(
            Path(__file__).with_name('gravewright.ico'),
            format='ICO',
            sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)],
        )


if __name__ == '__main__':
    main()
