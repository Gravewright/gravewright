from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]


def test_shader_icon_opens_semantic_catalog_and_preserves_tool_state() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(
            """
            <body data-current-user-id="gm">
              <article class="room-workspace is-active" data-is-gm="true">
                <canvas data-map-canvas data-room-id="campaign"></canvas>
                <aside data-tool-dock><div class="tool-dock-groups">
                  <button data-tool="select">Select</button>
                  <button data-tool="particles">Particles</button>
                  <button data-tool="shader">Shader</button>
                  <button data-active-layer="effects">Effects</button>
                </div></aside>
              </article>
              <div data-tool-sub-panel="particles" hidden>
                <button data-subtool="smoke">Smoke</button><button data-subtool="ember">Ember</button>
              </div>
              <div data-tool-sub-panel="shader" data-loading="Loading" data-error="Error" hidden>
                <div data-shader-tool-presets role="listbox"></div>
                <div class="tool-sub-sep"></div>
                <button data-shader-tool-custom>Custom</button>
              </div>
            </body>
            """
        )
        page.evaluate(
            """
            () => {
                window.GravewrightMap = {
                    activeCanvas: () => document.querySelector("[data-map-canvas]"),
                    sceneDataFor: () => ({id: "scene"}),
                };
                window.GravewrightShaderPresets = Array.from({length: 50}, (_, index) => ({
                    id: `preset-${index + 1}`, name: `Preset ${index + 1}`,
                    description: `Description ${index + 1}`, category: "Test", color: "#8fb6ff",
                    source: `raw-source-${index + 1}`,
                }));
                window.__pickerRequests = [];
                window.__shaderPreviews = [];
                document.addEventListener("tool:shader-preview", event => {
                    window.__shaderPreviews.push(event.detail.presetId);
                });
                window.fetch = async (url, options = {}) => {
                  window.__pickerRequests.push({url, method: options.method || "GET"});
                  return ({
                    ok: true,
                    json: async () => ({presets: Array.from({length: 50}, (_, index) => ({
                        id: `preset-${index + 1}`, schemaVersion: 1,
                        labelKey: `preset.${index + 1}.name`,
                        descriptionKey: `preset.${index + 1}.description`,
                        parameters: {},
                    }))}),
                  });
                };
            }
            """
        )
        page.add_script_tag(path=str(ROOT / "static/js/tools/tools-registry.js"))
        page.add_script_tag(path=str(ROOT / "static/js/tools/tools-toolbar.js"))
        page.click('[data-active-layer="effects"]')
        page.click('[data-tool="particles"]')
        assert page.locator('[data-tool-sub-panel="particles"]').is_visible()
        assert page.evaluate("window.GravewrightTools.activeTool") == "particles"
        page.click('[data-tool-sub-panel="particles"] [data-subtool="ember"]')
        assert page.evaluate("window.GravewrightTools.activeSubTool") == "ember"
        page.evaluate("document.body.dispatchEvent(new MouseEvent('click', {bubbles: true}))")

        page.click('[data-tool="shader"]')
        assert page.evaluate("window.GravewrightTools.activeTool") == "shader"
        page.wait_for_selector('[data-shader-tool-preset="preset-50"]')

        first = page.locator('[data-shader-tool-preset="preset-1"]')
        assert page.locator("[data-shader-tool-preset]").count() == 50
        assert page.locator("[data-shader-tool-custom]").is_visible()
        assert "raw-source" not in page.locator('[data-tool-sub-panel="shader"]').inner_text()
        preview_count = page.evaluate("window.__shaderPreviews.filter(Boolean).length")
        page.locator('[data-shader-tool-preset="preset-2"]').hover()
        assert page.evaluate("window.__shaderPreviews.at(-1)") == "preset-2"
        first.hover()
        assert page.evaluate("window.__shaderPreviews.at(-1)") == "preset-1"
        assert page.evaluate("window.__shaderPreviews.filter(Boolean).length") == preview_count + 2
        first.click()
        assert page.evaluate("window.GravewrightTools.activeTool") == "shader"
        assert page.evaluate("window.GravewrightTools.selectedShaderPreset") == "preset-1"
        assert page.locator('[data-tool-sub-panel="shader"]').is_hidden()

        page.click('[data-tool="shader"]')
        assert page.locator('[data-shader-tool-preset="preset-1"]').get_attribute("aria-selected") == "true"
        page.locator('[data-shader-tool-preset="preset-2"]').click()
        assert page.evaluate("window.GravewrightTools.selectedShaderPreset") == "preset-2"
        assert page.evaluate("window.__pickerRequests.every(request => request.method === 'GET')")

        page.click('[data-tool="shader"]')
        page.keyboard.press("Escape")
        assert page.locator('[data-tool-sub-panel="shader"]').is_hidden()
        assert page.evaluate("window.GravewrightTools.activeTool") == "shader"

        page.click('[data-tool="shader"]')
        page.locator("[data-shader-tool-custom]").click()
        assert page.evaluate("window.GravewrightTools.selectedShaderPreset") is None
        assert page.evaluate("window.GravewrightTools.activeTool") == "shader"
        browser.close()


def test_shader_editor_previews_locally_and_commits_once_on_change() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(
            """
            <canvas data-map-canvas data-room-id="campaign"></canvas>
            <section data-shader-editor-panel data-room-id="campaign">
              <input type="range" min="0" max="1" step="0.01"
                data-shader-field="intensity" value="0.8">
              <output data-shader-output="intensity"></output>
              <span data-shader-status></span>
            </section>
            """
        )
        page.evaluate(
            """
            () => {
              window.__shader = {id: "s1", scene_id: "scene", intensity: 0.8};
              window.__previews = [];
              window.__commits = [];
              window.GravewrightLighting = {
                shadersFor: () => [window.__shader],
                previewShader: (_canvas, id, patch) => {
                  window.__previews.push({id, patch}); Object.assign(window.__shader, patch);
                },
                commitShaderPreview: async (_canvas, id, patch) => {
                  window.__commits.push({id, patch}); return window.__shader;
                },
                restoreShaderPreview: () => { window.__shader.intensity = 0.8; },
              };
              window.GravewrightModals = {open: () => {}, close: () => {}};
            }
            """
        )
        page.add_script_tag(path=str(ROOT / "static/js/lighting/shader-editor.js"))
        page.evaluate("window.GravewrightShaderEditor.open('campaign', 's1')")
        slider = page.locator('[data-shader-field="intensity"]')
        slider.evaluate("node => { node.value = '0.3'; node.dispatchEvent(new Event('input', {bubbles: true})); }")
        slider.evaluate("node => { node.value = '0.4'; node.dispatchEvent(new Event('input', {bubbles: true})); }")
        assert page.evaluate("window.__previews.length") == 2
        assert page.evaluate("window.__commits.length") == 0
        slider.evaluate("node => node.dispatchEvent(new Event('change', {bubbles: true}))")
        page.wait_for_function("window.__commits.length === 1")
        assert page.evaluate("window.__commits[0].patch.intensity") == 0.4

        slider.evaluate("node => { node.value = '0.6'; node.dispatchEvent(new Event('input', {bubbles: true})); }")
        page.keyboard.press("Escape")
        assert page.evaluate("window.__shader.intensity") == 0.8
        assert page.evaluate("window.__commits.length") == 1
        browser.close()
