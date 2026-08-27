from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]


def test_graphics_quality_profile_is_applied_and_emits_change() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(device_scale_factor=2)
        page.set_content(
            """
            <select data-graphics-quality>
              <option value="auto">Automatic</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
            """
        )
        page.evaluate(
            """
            () => {
              window.__qualityEvents = [];
              document.addEventListener("vtt:graphics-quality-changed", event => {
                window.__qualityEvents.push(event.detail);
              });
            }
            """
        )
        page.add_script_tag(path=str(ROOT / "static/js/game/graphics-quality.js"))
        page.select_option("select[data-graphics-quality]", "low")

        assert page.evaluate("document.documentElement.dataset.graphicsQuality") == "low"
        assert page.evaluate("GravewrightGraphicsQuality.current()") == "low"
        assert page.evaluate("GravewrightGraphicsQuality.renderResolution()") == 1
        assert page.evaluate("GravewrightGraphicsQuality.config().textureCacheBytes") == 64 * 1024 * 1024
        assert page.evaluate("window.__qualityEvents.at(-1).effective") == "low"
        browser.close()
