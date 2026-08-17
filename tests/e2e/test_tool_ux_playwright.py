from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[2]


def _load_tool_world(page: Page, *, tool: str, layer: str) -> None:
    page.set_content(
        '<body data-current-user-id="gm"><div data-map-viewport data-lighting-gm="true">'
        '<canvas data-map-canvas data-room-id="campaign"></canvas></div></body>'
    )
    page.evaluate(
        """
        ({tool, layer}) => {
            window.__posts = [];
            window.__shaders = [{
                id: "shader", name: "Mist", source: "void main(){}", x: 200, y: 160,
                radius: 2, color: "#ffffff", enabled: 1, intensity: 1, opacity: 1,
                scale: 1, speed: 1, rotation: 0,
            }];
            window.__lights = [{
                id: "light", x: 200, y: 160, bright_radius: 2, dim_radius: 4,
                color: "#ffffff", intensity: 1, angle: 360, rotation: 0,
                animation: "none", enabled: 1,
            }];
            window.GravewrightTools = {activeTool: tool, activeLayer: layer, activeSubTool: "none", isLayerVisible: () => true};
            const canvas = document.querySelector("[data-map-canvas]");
            window.GravewrightMap = {
                redraw() {}, activeCanvas: () => canvas, history: {push() {}},
                sceneDataFor: () => ({id: "scene", width: 1000, height: 800, scaledTileSize: 50, darkness: 0}),
                tokenStoreFor: () => new Map(), isPlayerView: () => false,
                worldFromScreen: (_canvas, x, y) => ({worldX: x, worldY: y}),
                screenToWorldXY: (x, y) => ({worldX: x, worldY: y}),
                stateFor: () => ({zoom: 1}),
            };
            window.GravewrightVisionMode = {current: () => "cinematic", isClassic: () => false};
            window.GravewrightShaderPreference = {enabled: () => true};
            window.GravewrightShaderEffects = {invalidate() {}};
            window.GravewrightToasts = {showToast() {}};
            window.csrfToken = () => "csrf";
            window.fetch = async (url, options = {}) => {
                if ((options.method || "GET") === "GET") {
                    if (url.includes("/game/shaders/")) return {ok: true, json: async () => ({shaders: window.__shaders.map(x => ({...x}))})};
                    if (url.includes("/game/lights/")) return {ok: true, json: async () => ({lights: window.__lights.map(x => ({...x}))})};
                    if (url.includes("/game/particles/")) return {ok: true, json: async () => ({emitters: []})};
                    return {ok: true, json: async () => ({walls: []})};
                }
                const body = JSON.parse(options.body);
                window.__posts.push({url, body});
                if (url.endsWith("/game/shaders/update")) {
                    Object.assign(window.__shaders[0], body);
                    return {ok: true, json: async () => ({shader: {...window.__shaders[0]}})};
                }
                if (url.endsWith("/game/lights/update")) {
                    Object.assign(window.__lights[0], body);
                    return {ok: true, json: async () => ({light: {...window.__lights[0]}})};
                }
                if (url.endsWith("/game/shaders/delete-many")) window.__shaders = [];
                if (url.endsWith("/game/lights/delete-many")) window.__lights = [];
                return {ok: true, json: async () => ({})};
            };
        }
        """,
        {"tool": tool, "layer": layer},
    )
    page.add_script_tag(path=str(ROOT / "static/js/lighting/dynamic-lighting.js"))
    page.wait_for_timeout(50)


def _drag(page: Page, start: tuple[int, int], end: tuple[int, int]) -> None:
    page.evaluate(
        """
        ({start, end}) => {
            const surface = document.querySelector("[data-map-viewport]");
            const fire = (type, point) => surface.dispatchEvent(new PointerEvent(type, {
                bubbles: true, button: 0, pointerId: 7, clientX: point[0], clientY: point[1],
            }));
            fire("pointerdown", start); fire("pointermove", end); fire("pointerup", end);
        }
        """,
        {"start": start, "end": end},
    )
    page.wait_for_timeout(50)


def test_shader_tool_owns_overlapped_shader_workflow() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        _load_tool_world(page, tool="shader", layer="effects")
        _drag(page, (200, 160), (270, 210))
        page.keyboard.press("Delete")
        page.wait_for_timeout(50)
        result = page.evaluate("({posts: window.__posts, tool: window.GravewrightTools.activeTool})")
        browser.close()

    urls = [row["url"] for row in result["posts"]]
    assert any(url.endswith("/game/shaders/update") for url in urls)
    assert any(url.endswith("/game/shaders/delete-many") for url in urls)
    assert not any("/game/lights/update" in url or "/game/lights/delete" in url for url in urls)
    assert result["tool"] == "shader"


def test_light_tool_moves_light_without_selection_tool() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        _load_tool_world(page, tool="light", layer="lighting")
        _drag(page, (200, 160), (245, 190))
        result = page.evaluate("({posts: window.__posts, tool: window.GravewrightTools.activeTool})")
        browser.close()

    urls = [row["url"] for row in result["posts"]]
    assert any(url.endswith("/game/lights/update") for url in urls)
    assert not any("/game/shaders/update" in url for url in urls)
    assert result["tool"] == "light"
