import 'pixi.js/unsafe-eval';
import { Application } from 'pixi.js';
import { createBoard } from '../../gravewright/maps/frontend/widgets/game-board/ui/board.js';
import { PixiBoardRenderer } from '../../gravewright/maps/frontend/widgets/game-board/lib/pixi-board-renderer.js';

const colors = { original: [42, 80, 112], revised: [160, 60, 95],
    superseded: [192, 98, 45], latest: [70, 110, 190], recovered: [190, 105, 42],
    stale: [212, 150, 30], other: [60, 144, 72], token: [90, 208, 230] };
const check = (value, message) => { if (!value) throw Error(message); };
const frame = () => new Promise(resolve => requestAnimationFrame(resolve));
const matches = (actual, expected) => expected.every((value, i) => Math.abs(actual[i] - value) <= 4);
const equalView = (actual, expected) => ['x', 'y', 'scale'].every(key => Math.abs(actual[key] - expected[key]) < 1e-8);
const manifest = (mapId = 'map-a', artwork = 'original', version = 1, width = 1024) => ({
    mapId, version, width, height: 1024, tileSize: 1400, maxLod: 0,
    tileUrlTemplate: `/tiles/${artwork}.png`,
    levels: [{ lod: 0, width, height: 1024, columns: 1, rows: 1 }],
});
const grid = (visible = false, width = 1024) => ({ visible, width, height: 1024,
    cellSize: 100, color: '#ffffff', opacity: 1 });

window.runBoardSceneRefresh = async () => {
    const host = document.createElement('div');
    host.style.cssText = 'width:720px;height:520px;--bg:#171816;touch-action:none';
    document.body.appendChild(host);
    const cases = [], observations = [];
    let app;
    const controller = createBoard(host, { manifest: manifest(), grid: grid(),
        label: 'Synthetic scene refresh', pieces: [],
        renderer: async ({ label, background }) => {
            app = new Application();
            await app.init({ resizeTo: host, width: 720, height: 520, background,
                resolution: 1, autoStart: false, preference: 'webgl', antialias: true });
            host.appendChild(app.canvas);
            return new PixiBoardRenderer(app, label);
        } }, () => {});
    window.disposeBoardSceneRefresh = () => { controller.destroy(); host.remove(); };
    await controller.ready;
    check(app.renderer.gl, 'test uses a real WebGL renderer');
    const canvas = app.canvas;
    function pixel(x, y) {
        app.render();
        const gl = app.renderer.gl, result = new Uint8Array(4);
        gl.readPixels(Math.round(x), app.canvas.height - Math.round(y) - 1,
            1, 1, gl.RGBA, gl.UNSIGNED_BYTE, result);
        return [...result];
    }
    function worldPixel(point) {
        const view = controller.viewport();
        return pixel(view.x + point.x * view.scale, view.y + point.y * view.scale);
    }
    async function waitFor(condition, message) {
        const deadline = performance.now() + 12_000;
        do {
            if (await condition()) return;
            await new Promise(resolve => setTimeout(resolve, 20));
        } while (performance.now() < deadline);
        throw Error(message);
    }
    const tilePoint = { x: 700, y: 650 };
    const rendered = color => matches(worldPixel(tilePoint), color);
    const requests = async name => (await (await fetch('/gate/status')).json())[name];
    const requested = async name => await requests(name) > 0;
    const release = name => fetch(`/gate/release/${name}`);
    function continuity(expectedView, color, label) {
        check(canvas === host.querySelector('canvas'), `${label}: canvas remains mounted`);
        check(equalView(controller.viewport(), expectedView), `${label}: current zoom and pan stay unchanged`);
        check(rendered(color), `${label}: map artwork remains visible`);
    }
    async function inspectFrames(expectedView, color, label, count = 6) {
        for (let i = 0; i < count; i++) {
            await frame();
            continuity(expectedView, color, `${label} frame ${i}`);
        }
        observations.push({ label, sampledFrames: count, viewport: controller.viewport() });
    }
    await waitFor(() => rendered(colors.original), 'initial synthetic map artwork loads');
    // Playwright sends real wheel and middle-button input before releasing this gate.
    await new Promise(resolve => { window.continueBoardSceneRefresh = resolve; });
    const currentView = controller.viewport();
    check(currentView.scale > .9 && currentView.x !== 100, 'real surface events changed zoom and pan');
    const tokenArt = document.createElement('canvas');
    tokenArt.width = tokenArt.height = 64;
    const context = tokenArt.getContext('2d');
    context.fillStyle = `rgb(${colors.token.join(',')})`;
    context.fillRect(0, 0, 64, 64);
    const piece = { key: 'hero', label: 'Synthetic token', x: 450, y: 450, size: 80,
        accent: '#5ad0e6', imageUrl: tokenArt.toDataURL('image/png') };
    await controller.update({ pieces: [piece] });
    check(matches(worldPixel(piece), colors.token), 'synthetic token artwork loads');
    const moved = { ...piece, x: 570, y: 440 };
    await controller.update({ manifest: manifest('map-a', 'original', 2), pieces: [moved] });
    await inspectFrames(currentView, colors.original, 'metadata refresh and teleported token');
    check(matches(worldPixel(moved), colors.token), 'token reaches its updated position');
    check(matches(worldPixel(piece), colors.original), 'old token position is cleared');
    cases.push('same-scene-metadata-and-token-update-preserve-camera-canvas-and-art');

    await controller.update({ manifest: manifest('map-a', 'revised', 3) });
    continuity(currentView, colors.original, 'immediately after raster revision');
    await waitFor(() => requested('revised'), 'replacement artwork is requested');
    await inspectFrames(currentView, colors.original, 'replacement artwork delayed');
    await release('revised');
    await waitFor(() => rendered(colors.revised), 'replacement artwork becomes visible');
    await inspectFrames(currentView, colors.revised, 'replacement artwork installed');
    cases.push('same-scene-raster-revision-keeps-old-art-until-replacement-is-ready');

    await controller.update({ manifest: manifest('map-a', 'revised', 4, 1400),
        grid: grid(true, 1400), initialView: { x: 0, y: 0, scale: .25 } });
    check(equalView(controller.viewport(), currentView), 'same-scene geometry update preserves camera');
    const gridX = currentView.x + 600 * currentView.scale;
    const gridY = currentView.y + 650 * currentView.scale;
    let lineVisible = false;
    for (let dx = -2; dx <= 2; dx++)
        lineVisible ||= pixel(gridX + dx, gridY).slice(0, 3).every(channel => channel > 125);
    check(lineVisible, 'updated grid geometry is rendered on the retained scene');
    cases.push('same-scene-geometry-update-refreshes-grid-without-resetting-camera');

    await controller.update({ manifest: manifest('map-a', 'superseded', 5, 1400), grid: grid() });
    await waitFor(() => requested('superseded'), 'older same-scene revision is pending');
    await controller.update({ manifest: manifest('map-a', 'latest', 6, 1400) });
    await waitFor(() => requested('latest'), 'newest same-scene revision is requested');
    await inspectFrames(currentView, colors.revised, 'two same-scene revisions pending');
    await release('superseded');
    await inspectFrames(currentView, colors.revised, 'superseded same-scene response finishes');
    await release('latest');
    await waitFor(() => rendered(colors.latest), 'only newest same-scene artwork becomes visible');
    await inspectFrames(currentView, colors.latest, 'newest same-scene revision installed');
    cases.push('newer-same-scene-revision-supersedes-a-delayed-response-without-flashing');

    await controller.update({ manifest: manifest('map-a', 'recovered', 7, 1400) });
    await waitFor(async () => (await (await fetch('/gate/failures')).json()).recovered === 1,
        'initial replacement request returns the synthetic HTTP 503');
    await inspectFrames(currentView, colors.latest, 'replacement failed before retry');
    // Wait for the board's bounded retry itself, without a second manifest update or a manual reload.
    await waitFor(async () => {
        continuity(currentView, colors.latest, 'while waiting for automatic retry');
        return await requests('recovered') === 2;
    }, 'the failed replacement is automatically retried');
    // A subsequent viewport sync must keep the successful old raster during the pending retry too.
    for (const deltaY of [-100, 100])
        host.dispatchEvent(new WheelEvent('wheel', { bubbles: true, cancelable: true,
            clientX: 360, clientY: 260, deltaY }));
    await inspectFrames(currentView, colors.latest, 'viewport refreshed during pending retry');
    await release('recovered');
    await waitFor(() => rendered(colors.recovered), 'automatic retry installs replacement artwork');
    await inspectFrames(currentView, colors.recovered, 'successful replacement after retry');
    check(await requests('recovered') === 2, 'one failed attempt and one bounded retry were sufficient');
    cases.push('failed-replacement-keeps-old-raster-across-viewport-sync-and-automatic-retry');

    await controller.update({ manifest: manifest('map-a', 'stale', 8, 1400), grid: grid() });
    await waitFor(() => requested('stale'), 'soon-stale artwork request is pending');
    await inspectFrames(currentView, colors.recovered, 'soon-stale artwork delayed');
    await controller.update({ manifest: manifest('map-b', 'other'), pieces: [],
        grid: grid(), initialView: undefined });
    const fit = { x: 100, y: 0, scale: 520 / 1024 };
    check(equalView(controller.viewport(), fit), 'different scene opens at its initial fitted viewport');
    await waitFor(() => requested('other'), 'new scene artwork is requested');
    check(!rendered(colors.recovered), 'different scene does not retain previous scene artwork');
    await release('other');
    await waitFor(() => rendered(colors.other), 'different scene artwork loads');
    await release('stale');
    await inspectFrames(fit, colors.other, 'after stale scene request finishes', 12);
    cases.push('scene-switch-resets-camera-clears-old-art-and-rejects-stale-loads');
    check(canvas === host.querySelector('canvas'), 'scene switch reuses the mounted canvas');
    return { cases, observations, colors, currentView, switchedView: controller.viewport() };
};
