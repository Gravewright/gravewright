import 'pixi.js/unsafe-eval';
import { Application } from 'pixi.js';
import { PixiBoardRenderer } from '../../gravewright/maps/frontend/widgets/game-board/lib/pixi-board-renderer.js';
import { SceneLayers } from '../../gravewright/maps/frontend/widgets/game-board/lib/scene-layers.js';
import { renderingPreferences } from '../../gravewright/maps/frontend/shared/rendering/render-profile.js';

const width = 3000, height = 2000, cell = 70, room = 300;
const frame = () => new Promise(resolve => requestAnimationFrame(resolve));
const check = (value, message) => { if (!value) throw Error(message); };
const median = values => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)] ?? 0;
const round = value => Math.round(value * 100) / 100;

/** Rooms of short wall segments; each shared side has one door. */
function walls() {
    const rows = [];
    let id = 0;
    for (let column = 1; column < width / room; column++)
        for (let y = 0; y < height; y += 100) {
            const doorway = y % room === 100;
            rows.push({ id: `v${id++}`, x1: column * room, y1: y, x2: column * room, y2: y + 100,
                kind: doorway ? 'door' : 'wall', door_state: doorway ? 'closed' : undefined });
        }
    for (let line = 1; line < height / room; line++)
        for (let x = 0; x < width; x += 100) {
            const doorway = x % room === 100;
            rows.push({ id: `h${id++}`, x1: x, y1: line * room, x2: x + 100, y2: line * room,
                kind: doorway ? 'door' : 'wall', door_state: doorway ? 'closed' : undefined });
        }
    return rows;
}
// Thirty torches in room centres. The second room stays dark, so only the
// first torch can light it, through the door between them.
const lights = Array.from({ length: 40 }, (_, index) => [index % 10, Math.floor(index / 10)])
    .filter(([column, row]) => column !== 1 || row !== 0).slice(0, 30)
    .map(([column, row], index) => ({ id: `torch-${index}`, enabled: true, x: column * room + 150, y: row * room + 150,
        color: '#ffb35c', intensity: 1, bright_radius: 2, dim_radius: 4, angle: 360, rotation: 0, animation: 'torch',
        elevation: 0 }));
const particles = Array.from({ length: 24 }, (_, index) => ({ id: `embers-${index}`, enabled: true, kind: 'ember',
    density: 1, scale: 1, x: (index % 8) * room + 200, y: Math.floor(index / 8) * room + 220, rotation: 0 }));
const shaders = [0, 1].map(index => ({ id: `orb-${index}`, enabled: true, source: 'gravewright-preset://orb-1/v1',
    x: 1050 + index * 900, y: 1050, radius: 2, color: '#8f6bff', intensity: .8, opacity: 1, scale: 1, speed: 1,
    rotation: 0, blend_mode: 'add' }));
const stroke = (id, x, y) => ({ id, kind: 'pen', color: '#f2d06b', width: 6, opacity: 1, fill: 'none',
    audience: 'campaign', rotation: 0, points: Array.from({ length: 50 }, (_, i) => ({ x: x + i * 4, y: y + Math.sin(i / 4) * 20 })) });
const card = (index, x = 2400 + index * 20) => ({ id: `card-${index}`, x, y: 1700, rotation: 0, scale: 1,
    z_index: index, card: {} });

window.runSceneLayerUpdates = async ({ assertions = true, repeat = 5, only } = {}) => {
    const host = document.createElement('div');
    host.style.cssText = 'width:960px;height:640px;display:block';
    document.body.appendChild(host);
    const app = new Application();
    await app.init({ width: 960, height: 640, resizeTo: host, resolution: 1, autoStart: false,
        preference: 'webgl', antialias: true, background: '#0c1824' });
    host.appendChild(app.canvas);
    check(app.renderer.gl, 'the fixture samples a real WebGL renderer');
    renderingPreferences.select('quality');
    const board = new PixiBoardRenderer(app, 'Synthetic scene layer updates');
    board.setViewport({ x: 0, y: 0, scale: .32 });
    let created = 0;
    const createLayer = board.createLayer.bind(board);
    board.createLayer = (...args) => { created++; return createLayer(...args); };
    const layers = new SceneLayers(board);
    window.disposeSceneLayerUpdates = () => { layers.dispose(); board.destroy(); host.remove(); };
    const longTasks = [];
    const observer = typeof PerformanceObserver === 'function' && PerformanceObserver.supportedEntryTypes?.includes('longtask')
        ? new PerformanceObserver(list => longTasks.push(...list.getEntries().map(entry => ({ start: entry.startTime, duration: entry.duration }))))
        : undefined;
    observer?.observe({ type: 'longtask' });
    const report = { cases: [], steps: {}, longTaskSupport: !!observer,
        scene: { walls: walls().length, lights: lights.length, particles: particles.length, shaders: shaders.length } };
    let state = { containerId: 'synthetic-table', blockId: 'synthetic-block', sceneId: 'synthetic-scene',
        images: [], walls: walls(), lights, particles, shaders, zones: [],
        cards: Array.from({ length: 10 }, (_, index) => card(index)),
        drawings: { rows: Array.from({ length: 40 }, (_, index) => stroke(`stroke-${index}`, 40 + (index % 10) * 290, 60 + Math.floor(index / 10) * 480)) },
        spatialSounds: [{ id: 'rain', x: 500, y: 500, radius: 400 }],
        lighting: { mode: 'dynamic', darkness: .7, lights_out: true }, fog: { enabled: false }, vision: [] };
    let gm = true;
    const render = () => layers.render(state, cell, width, height, gm);
    function pixel(point) {
        app.render();
        const view = board.viewport(), gl = app.renderer.gl, value = new Uint8Array(4);
        const x = Math.round(view.x + point.x * view.scale), y = Math.round(view.y + point.y * view.scale);
        gl.readPixels(x, app.canvas.height - y - 1, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, value);
        return [...value];
    }
    const brightness = value => value[0] + value[1] + value[2];
    function snapshot() {
        app.render();
        const gl = app.renderer.gl, value = new Uint8Array(app.canvas.width * app.canvas.height * 4);
        gl.readPixels(0, 0, app.canvas.width, app.canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, value);
        return value;
    }
    /**
     * The state reached through partial updates must draw exactly what a full mount of the
     * same content draws. Animation is frozen so both frames are deterministic.
     */
    async function equivalence(label) {
        state = { ...state, lights: state.lights.map(light => ({ ...light, animation: 'none' })), particles: [], shaders: [] };
        render();
        await settle(12);
        const partial = snapshot();
        const sceneId = state.sceneId;
        state = { ...state, sceneId: `${sceneId}-remounted` };
        render();
        await settle(12);
        const mounted = snapshot();
        let differing = 0, worst = 0;
        for (let i = 0; i < partial.length; i += 4) {
            const delta = Math.max(Math.abs(partial[i] - mounted[i]), Math.abs(partial[i + 1] - mounted[i + 1]),
                Math.abs(partial[i + 2] - mounted[i + 2]));
            worst = Math.max(worst, delta);
            if (delta > 4) differing++;
        }
        report.equivalence ??= {};
        report.equivalence[label] = { differingPixels: differing, worstChannelDelta: worst };
        if (assertions) check(differing === 0, `${label}: partial updates draw what a full mount draws (${differing} pixels, worst ${worst})`);
    }
    async function settle(frames = 10) { for (let i = 0; i < frames; i++) await frame(); }
    /** Time one update and the frames that follow it. */
    async function measure(label, mutate, frames = 30) {
        if (only && !only.includes(label)) return;
        const result = report.steps[label] ??= { render: [], layers: [], maxFrame: [], longTasks: [], longTaskTotal: [] };
        for (let index = 0; index < repeat; index++) {
            await settle(3);
            const before = created;
            state = mutate(state, index);
            const start = performance.now();
            render();
            result.render.push(performance.now() - start);
            result.layers.push(created - before);
            let previous = performance.now(), worst = previous - start;
            for (let i = 0; i < frames; i++) {
                await frame();
                const now = performance.now();
                worst = Math.max(worst, now - previous);
                previous = now;
            }
            result.maxFrame.push(worst);
            const tasks = longTasks.filter(task => task.start + task.duration >= start && task.start <= previous);
            result.longTasks.push(tasks.length);
            result.longTaskTotal.push(tasks.reduce((total, task) => total + task.duration, 0));
        }
        return result;
    }
    const nearDoor = state.walls.find(wall => wall.kind === 'door' && wall.x1 === room && wall.y1 === 100);
    const distant = lights.find(light => light.x === 9 * room + 150 && light.y === 150);
    const litPoint = { x: distant.x, y: distant.y }, behindDoor = { x: room + 40, y: 150 };
    const steps = {
        'add drawing': (value, index) => ({ ...value, drawings: { rows: [...value.drawings.rows,
            stroke(`new-${gm}-${index}`, 2300, 1300 + index * 30)] } }),
        'move card': (value, index) => ({ ...value, cards: value.cards.map(row => row.id === 'card-0'
            ? { ...row, x: 2300 + index * 37, rotation: index * 15 } : row) }),
        'toggle door': value => ({ ...value, walls: value.walls.map(wall => wall.id === nearDoor.id
            ? { ...wall, door_state: wall.door_state === 'open' ? 'closed' : 'open' } : wall) }),
        'move spatial sound': (value, index) => ({ ...value, spatialSounds: [{ ...value.spatialSounds[0], x: 500 + index * 50 }] }),
        'toggle light': value => ({ ...value, lights: value.lights.map(light => light.id === 'torch-5'
            ? { ...light, enabled: !light.enabled } : light) }),
    };

    render();
    await settle(20);
    check(brightness(pixel(litPoint)) > 60, `a torch lights the synthetic floor (${pixel(litPoint)})`);
    report.initial = { lit: pixel(litPoint), behindDoor: pixel(behindDoor) };
    for (const [label, mutate] of Object.entries(steps)) await measure(`gm: ${label}`, mutate);
    // The door toggled an odd number of times: it is now open, so the first torch reaches behind it.
    if (repeat % 2 && (!only || only.includes('gm: toggle door'))) {
        await settle(10);
        // Torches flicker: keep the brightest of several frames.
        report.doorOpened = pixel(behindDoor);
        for (let i = 0; i < 12; i++) {
            await frame();
            const value = pixel(behindDoor);
            if (brightness(value) > brightness(report.doorOpened)) report.doorOpened = value;
        }
        if (assertions) check(brightness(report.doorOpened) > brightness(report.initial.behindDoor) + 20,
            `an opened door lets the near torch reach the next room (${report.initial.behindDoor} -> ${report.doorOpened})`);
    }
    if (assertions) check(brightness(pixel(litPoint)) > 60, 'the distant torch stays lit after every update');
    const animated = { lights: state.lights, particles: state.particles, shaders: state.shaders, sceneId: state.sceneId };
    await equivalence('gm');
    state = { ...state, ...animated };
    // A player sees through token vision; the veil depends on walls but not on drawings or cards.
    gm = false;
    state = { ...state, vision: [{ sourceId: 'hero', x: 450, y: 450, radius: 0, elevation: 0, angle: 360, rotation: 0 }] };
    render();
    await settle(20);
    for (const label of ['add drawing', 'move card', 'toggle door']) await measure(`player: ${label}`, steps[label]);
    observer?.disconnect();
    await equivalence('player');
    for (const [label, values] of Object.entries(report.steps))
        report.steps[label] = { renderMedianMs: round(median(values.render)), renderMaxMs: round(Math.max(...values.render)),
            layersCreated: values.layers, maxFrameMedianMs: round(median(values.maxFrame)),
            longTasks: values.longTasks.reduce((a, b) => a + b, 0), longTaskMs: round(values.longTaskTotal.reduce((a, b) => a + b, 0)) };
    if (assertions) {
        for (const label of ['gm: add drawing', 'gm: move card', 'gm: move spatial sound', 'player: add drawing', 'player: move card'])
            if (report.steps[label]) check(report.steps[label].layersCreated.every(count => count === 0), `${label} mounts no layer`);
        for (const label of ['gm: toggle door', 'gm: toggle light', 'player: toggle door'])
            if (report.steps[label]) check(report.steps[label].layersCreated.every(count => count === 0), `${label} keeps the scene mounted`);
        report.cases.push('drawings-cards-and-sounds-update-without-remounting',
            'doors-and-lights-rebuild-only-effects', 'an-opened-door-reaches-the-gpu',
            'partial-updates-match-a-full-mount-for-gm-and-player');
    }
    return report;
};
