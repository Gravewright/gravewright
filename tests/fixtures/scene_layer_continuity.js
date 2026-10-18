import 'pixi.js/unsafe-eval';
import { Application } from 'pixi.js';
import { PixiBoardRenderer } from '../../gravewright/maps/frontend/widgets/game-board/lib/pixi-board-renderer.js';
import { SceneLayers } from '../../gravewright/maps/frontend/widgets/game-board/lib/scene-layers.js';

const background = [12, 24, 36], floorColor = [56, 112, 80], decorationColor = [81, 111, 174];
const frame = () => new Promise(resolve => requestAnimationFrame(resolve));
const check = (value, message) => { if (!value) throw Error(message); };
const matches = (actual, expected) => expected.every((value, channel) => Math.abs(actual[channel] - value) <= 4);
const surface = (mask, left, top) => ({ kind: 'floor', materialId: 'material', maskId: mask,
    cellSize: 70, left, top, rotation: 0 });
const placement = (id, x, y, width, height, extra = {}) => ({ id, x, y, natural_width: width,
    natural_height: height, src: `/art/${id}`, scale: 1, rotation: 0, layer: 'game', z_index: 0, ...extra });

window.runSceneLayerContinuity = async () => {
    const host = document.createElement('div');
    host.style.cssText = 'width:680px;height:480px;display:block';
    document.body.appendChild(host);
    const app = new Application();
    await app.init({ width: 680, height: 480, resizeTo: host, resolution: 1, autoStart: false,
        preference: 'webgl', antialias: true, background: '#0c1824' });
    host.appendChild(app.canvas);
    check(app.renderer.gl, 'the fixture samples a real WebGL renderer');
    const board = new PixiBoardRenderer(app, 'Synthetic region surface continuity');
    const layers = new SceneLayers(board);
    window.disposeSceneLayerContinuity = () => { layers.dispose(); board.destroy(); host.remove(); };
    const report = window.__sceneLayerContinuity = { cases: [], observations: [], colors: { background, floorColor } };
    let singleColor = floorColor;
    const single = placement('single', 130, 200, 200, 160, { surface: surface('single-mask', 30, 120) });
    const grouped = placement('grouped', 410, 200, 240, 200, {
        surface: surface('group-mask', 290, 100), surfacePlane: { group: 'floor-group', operation: 'paint', order: 0 } });
    const eraser = placement('eraser', 410, 200, 50, 50, {
        surfacePlane: { group: 'floor-group', operation: 'erase', order: 1 } });
    const decoration = placement('decoration', 150, 360, 80, 80);
    const privateSurface = placement('private', 600, 210, 80, 80, {
        layer: 'gm-image-layer', surface: surface('private-mask', 560, 170) });
    const region = { id: 'region', enabled: true,
        geometry: { shape: 'rect', x: 540, y: 60, width: 100, height: 80 },
        region: { state: 'empty', count: 0 } };
    const light = { id: 'effect-light', enabled: false, x: 590, y: 350, color: '#ffc36b',
        intensity: 1, bright_radius: .5, dim_radius: 1, angle: 360, rotation: 0, animation: 'none' };
    let state = { containerId: 'synthetic-table', blockId: 'synthetic-block', sceneId: 'synthetic-scene',
        images: [single, grouped, eraser, decoration, privateSurface], walls: [], lights: [light], particles: [], shaders: [],
        cards: [], zones: [region], drawings: { rows: [] }, spatialSounds: [],
        lighting: { mode: 'manual', darkness: 0 }, fog: { enabled: false }, vision: [] };
    const render = () => layers.render(state, 70, 680, 480, true);
    function pixel(x, y) {
        app.render();
        const gl = app.renderer.gl, value = new Uint8Array(4);
        gl.readPixels(x, app.canvas.height - y - 1, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, value);
        return [...value];
    }
    function samples() {
        return { single: pixel(120, 180), grouped: pixel(350, 150), erased: pixel(410, 200),
            decoration: pixel(150, 360), region: pixel(590, 100), light: pixel(590, 350) };
    }
    function continuity(label) {
        const pixels = samples();
        const shade = color => color.map(value => Math.round(value * (1 - (state.lighting.darkness || 0) * .5)));
        report.observations.push({ label, pixels, at: performance.now() });
        check(matches(pixels.single, shade(singleColor)), `${label}: standalone material remains visible (${pixels.single})`);
        check(matches(pixels.grouped, shade(floorColor)), `${label}: grouped floor remains visible (${pixels.grouped})`);
        check(matches(pixels.erased, shade(background)), `${label}: grouped eraser preserves the transparent hole`);
        check(matches(pixels.decoration, shade(decorationColor)), `${label}: ordinary image remains visible`);
        return pixels;
    }
    async function waitFor(condition, message) {
        const deadline = performance.now() + 12_000;
        while (performance.now() < deadline) {
            if (condition()) return;
            await frame();
        }
        throw Error(message);
    }
    async function update(label, mutate, validate, record = true) {
        await fetch('/gate/arm');
        try {
            const before = samples();
            state = mutate(state);
            render();
            continuity(`${label}: synchronous render`);
            for (let index = 0; index < 8; index++) {
                await frame();
                continuity(`${label}: delayed artwork frame ${index}`);
            }
            validate?.(before, samples());
            if (record) report.cases.push(label);
        } finally {
            await fetch('/gate/release');
        }
        await frame();
        await frame();
        continuity(`${label}: after delayed responses`);
    }
    render();
    await waitFor(() => {
        const value = samples();
        return matches(value.single, floorColor) && matches(value.grouped, floorColor)
            && matches(value.decoration, decorationColor);
    }, 'synthetic single and grouped floor materials load');
    continuity('initial artwork');
    report.cases.push('initial-materials-and-grouped-eraser-render-real-pixels');
    await update('region-entry', value => ({ ...value,
        zones: [{ ...region, region: { state: 'occupied', count: 1 } }] }), (before, after) => {
        check(after.region.some((channel, i) => Math.abs(channel - before.region[i]) > 10),
            'region entry visibly updates its occupied color');
    });
    await update('region-exit', value => ({ ...value, zones: [region] }), (before, after) => {
        check(after.region.some((channel, i) => Math.abs(channel - before.region[i]) > 10),
            'region exit visibly restores its empty color');
    });
    await update('standalone-surface-committed-transform', value => ({ ...value,
        images: value.images.map(row => row.id === single.id ? { ...row, x: row.x + 10 } : row) }), () => {
        check(matches(pixel(35, 180), background), 'the committed transform clears the old surface edge');
        check(matches(pixel(235, 180), floorColor), 'the committed transform moves material coverage to the new edge');
    });
    await update('native-light-enabled', value => ({ ...value, lights: [{ ...light, enabled: true }] }),
        (before, after) => check(after.light.some((channel, i) => channel - before.light[i] > 20),
            'native light update reaches the GPU'));
    await update('native-light-disabled', value => ({ ...value, lights: [light] }),
        (_before, after) => check(matches(after.light, background), 'native light switches off on the GPU'));
    await update('scene-darkness-changed', value => ({ ...value,
        lighting: { ...value.lighting, mode: 'dynamic', lights_out: true, darkness: .4 } }));
    await update('scene-darkness-restored', value => ({ ...value,
        lighting: { ...value.lighting, mode: 'manual', darkness: 0 } }), undefined, false);
    await fetch('/gate/arm');
    try {
        state = { ...state, images: state.images.map(row => row.id === single.id
            ? { ...row, surface: { ...row.surface, materialId: 'replacement-material' } } : row) };
        render();
        continuity('material replacement: synchronous render');
        for (let index = 0; index < 8; index++) {
            await frame();
            continuity(`material replacement: delayed frame ${index}`);
        }
    } finally { await fetch('/gate/release'); }
    singleColor = [180, 95, 60];
    await waitFor(() => matches(pixel(120, 180), singleColor), 'the new material replaces retained old art');
    continuity('material replacement: installed');
    state = { ...state, images: state.images.filter(row => row.id !== single.id) };
    render();
    await frame();
    check(matches(pixel(120, 180), background), 'removing a surface immediately removes its retained artwork');
    report.cases.push('delayed-material-replacement-and-explicit-surface-removal');
    check(!matches(pixel(600, 210), background), 'the GM can see the synthetic private surface');
    layers.render(state, 70, 680, 480, false);
    for (let index = 0; index < 3; index++) {
        await frame();
        check(matches(pixel(600, 210), background), 'changing role clears private retained surface art');
    }
    state = { ...state, sceneId: 'different-synthetic-scene', images: [], zones: [], lights: [], drawings: { rows: [] } };
    render();
    for (let index = 0; index < 3; index++) {
        await frame();
        check(matches(pixel(120, 180), background) && matches(pixel(350, 150), background),
            'a different scene never retains artwork from the previous scene');
    }
    report.cases.push('role-and-scene-switch-clear-private-or-previous-scene-artwork');
    return report;
};
