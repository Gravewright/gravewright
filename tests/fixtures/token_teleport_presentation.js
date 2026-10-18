import 'pixi.js/unsafe-eval';
import { Application, Graphics, Sprite, Text } from 'pixi.js';
import { PixiBoardRenderer } from '../../gravewright/maps/frontend/widgets/game-board/lib/pixi-board-renderer.js';
import { BOARD_STACK } from '../../gravewright/maps/frontend/widgets/game-board/model/board-renderer.js';
import { tokenController } from '../../gravewright/maps/frontend/features/tokens/ui/controller.js';
import { renderingPreferences } from '../../gravewright/maps/frontend/shared/rendering/render-profile.js';
import { TOKEN_SETTLE_MS } from '../../gravewright/maps/frontend/features/tokens/model/token-motion.js';

const colors = { floor: [56, 112, 80], art: [232, 74, 96], final: [81, 111, 174], bar: [121, 195, 154] };
const cell = 64, viewport = { x: 23, y: 19, scale: 1.15 };
const frame = () => new Promise(resolve => requestAnimationFrame(resolve));
const check = (value, message) => { if (!value) throw Error(message); };
const matches = (actual, expected) => expected.every((value, channel) => Math.abs(actual[channel] - value) <= 4);
const center = token => ({ x: (token.gridX + .5) * cell, y: (token.gridY + .5) * cell });

window.runTokenTeleportPresentation = async () => {
    const report = window.__tokenTeleportPresentation = { cases: [], observations: [], floorSamples: 0, colors };
    const host = document.createElement('div');
    host.style.cssText = 'width:760px;height:450px;display:block';
    document.body.appendChild(host);
    const app = new Application();
    await app.init({ width: 760, height: 450, resizeTo: host, autoStart: false,
        resolution: 1, preference: 'webgl', antialias: true, background: '#0c1824' });
    host.appendChild(app.canvas);
    check(app.renderer.gl, 'the presentation fixture uses a real WebGL renderer');
    const board = new PixiBoardRenderer(app, 'Synthetic token teleport');
    const world = app.stage.children.find(child => child.children?.some(layer => layer.zIndex === BOARD_STACK.figures));
    const figures = world.children.find(child => child.zIndex === BOARD_STACK.figures);
    const floorLayer = board.createLayer('synthetic-floor', BOARD_STACK.tiles + 1);
    const floor = new Graphics().rect(0, 0, 640, 340).fill('#387050');
    floorLayer.native().container.addChild(floor);
    board.setViewport(viewport);
    renderingPreferences.select('quality');
    let row = { id: 'synthetic-token', actorId: 'synthetic-actor', mapId: 'synthetic-scene',
        name: 'Synthetic hero', version: 1, teleportVersion: 0, linkMode: 'linked',
        gridX: 1, gridY: 1, cells: 1, canControl: true, canOpenSheet: true,
        imageUrl: '/art/hero.png', accent: '#77ccbb',
        bars: { health: { value: 7, max: 10, color: '#79c39a' } },
        conditions: [{ label: 'Synthetic blessing', kind: 'positive' }] };
    const pending = new Set(), failures = [];
    let controller, disposed = false, previews = 0;
    function paint(rows = controller?.view.displayed ?? [row]) {
        if (disposed) return;
        const selected = controller?.view.selected ?? [row.id];
        const operation = board.setPieces(rows.map(token => ({ key: token.id,
            label: token.name, ...center(token), size: token.cells * cell,
            imageUrl: token.imageUrl, teleportVersion: token.teleportVersion,
            accent: token.accent, selected: selected.includes(token.id),
            bars: token.bars, conditions: token.conditions })));
        pending.add(operation);
        operation.catch(error => failures.push(String(error))).finally(() => pending.delete(operation));
    }
    controller = tokenController(host, {
        props: { tokens: [row], walls: [], cell, width: 640, height: 340,
            containerId: 'synthetic-table', blockId: 'synthetic-block', mapId: 'synthetic-scene',
            layer: 'game', tool: 'select', gm: true, viewport, grid: true },
        repaint: () => paint(),
        emit: (name, rows) => { if (name === 'preview') { previews++; paint(rows); } },
        read: async () => [row], command: async () => { throw Error('This fixture performs no server writes'); },
    });
    controller.call('select', [row.id]);
    controller.call('openSheet', row);
    paint();
    function pixel(x, y) {
        app.render();
        const gl = app.renderer.gl, value = new Uint8Array(4);
        const screenX = Math.round(viewport.x + x * viewport.scale);
        const screenY = Math.round(viewport.y + y * viewport.scale);
        gl.readPixels(screenX, app.canvas.height - screenY - 1, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, value);
        return [...value];
    }
    function stable(label) {
        check(!floor.destroyed && floor.parent === floorLayer.native().container, `${label}: floor object is preserved`);
        check(JSON.stringify(board.viewport()) === JSON.stringify(viewport), `${label}: camera and zoom are preserved`);
        const floorPixel = pixel(16, 16);
        report.floorSamples++;
        check(matches(floorPixel, colors.floor), `${label}: GPU floor remains visible (${floorPixel})`);
        check(!failures.length, `${label}: asynchronous presentation errors: ${failures.join(', ')}`);
    }
    function tokenRoot(label) {
        check(figures.children.length === 1, `${label}: exactly one token root exists (${figures.children.length})`);
        const root = figures.children[0], point = center(row);
        check(root.x === point.x && root.y === point.y, `${label}: token stands at the destination (${root.x}, ${root.y})`);
        return root;
    }
    function art(label, expected = colors.art) {
        const root = tokenRoot(label), sprite = root.children.find(child => child instanceof Sprite);
        const point = center(row), value = pixel(point.x, point.y);
        check(matches(value, expected), `${label}: GPU artwork has the expected color (${value})`);
        check(sprite?.mask && !sprite.mask.destroyed, `${label}: the fresh artwork has a live circular mask`);
        check(matches(pixel(point.x + 27, point.y - 27), colors.floor), `${label}: artwork corners are masked to the floor`);
        check(matches(pixel(point.x, point.y + 26), colors.bar), `${label}: health bar is preserved`);
        check(root.children.some(child => child instanceof Text && child.visible && child.text === row.name), `${label}: selection label is visible`);
        check(root.children.some(child => child.children?.some(icon => icon instanceof Text)), `${label}: condition icon is preserved`);
        check(controller.view.selected[0] === row.id && controller.view.selection[0]?.actorId === row.actorId,
            `${label}: selected token and actor keep their logical identities`);
        check(controller.view.sheet?.id === row.id && controller.view.sheet?.linkMode === row.linkMode,
            `${label}: the existing sheet remains attached to the same token`);
        stable(label);
        report.observations.push({ label, x: root.x, y: root.y, teleportVersion: row.teleportVersion, pixel: value });
        return root;
    }
    async function waitFor(condition, message) {
        const deadline = performance.now() + 12_000;
        while (performance.now() < deadline) {
            if (await condition()) return;
            stable(message);
            await frame();
        }
        throw Error(message);
    }
    async function settle() {
        const deadline = performance.now() + TOKEN_SETTLE_MS + 40;
        while (performance.now() < deadline) { await frame(); stable('movement frame'); }
        await Promise.all([...pending]);
    }
    function update(changes) {
        row = { ...row, ...changes, version: row.version + 1 };
        controller.update({ tokens: [row] });
    }
    async function ordinaryMove(gridX, label) {
        const previous = figures.children[0], oldX = controller.view.displayed[0].gridX;
        update({ gridX });
        check(controller.view.displayed[0].gridX === oldX, `${label}: ordinary motion starts at its displayed source`);
        await waitFor(() => {
            const x = controller.view.displayed[0].gridX;
            return x > oldX && x < gridX;
        }, `${label}: an intermediate frame interpolates ordinary movement`);
        check(figures.children[0] === previous && !previous.destroyed, `${label}: ordinary motion retains its root`);
        await settle();
        check(figures.children[0] === previous, `${label}: ordinary motion never remounts the token`);
        art(label);
        report.cases.push(label);
    }
    async function teleport(changes, label) {
        const oldRoot = figures.children[0], from = center(row);
        update(changes);
        const shown = controller.view.displayed[0];
        check(shown.gridX === row.gridX && shown.gridY === row.gridY,
            `${label}: changed teleport marker bypasses interpolation in the controller`);
        await frame();
        check(oldRoot.destroyed, `${label}: the old presentation root is destroyed before the first displayed frame`);
        const fresh = art(`${label}: first displayed frame`);
        check(fresh !== oldRoot, `${label}: the token is recreated as a fresh root`);
        if (from.x !== fresh.x || from.y !== fresh.y) {
            check(matches(pixel(from.x, from.y), colors.floor), `${label}: source no longer shows the token`);
        }
        for (let index = 0; index < 3; index++) {
            await frame();
            check(art(`${label}: frame ${index}`) === fresh, `${label}: following frames keep the new root`);
        }
        report.cases.push(label);
        return fresh;
    }
    try {
        await waitFor(() => figures.children.length === 1, 'initial synthetic token artwork loads');
        art('initial synthetic token');
        await ordinaryMove(3, 'normal-movement-interpolates-without-remounting');
        await teleport({ gridX: 7, gridY: 2, teleportVersion: 1 }, 'teleport-recreates-at-destination-without-sliding');
        const duplicateRoot = figures.children[0];
        update({});
        await frame();
        check(art('duplicate teleport receipt') === duplicateRoot, 'duplicate teleport marker does not recreate the token');
        report.cases.push('duplicate-teleport-marker-keeps-root');
        await ordinaryMove(8, 'normal-movement-after-teleport-keeps-root-and-marker');
        await teleport({ teleportVersion: 2 }, 'teleport-to-same-position-still-recreates');

        await fetch('/gate/slow/arm');
        const beforeDelayed = figures.children[0];
        update({ gridX: 1, gridY: 3, teleportVersion: 3, imageUrl: '/art/slow.png' });
        await waitFor(async () => (await (await fetch('/requests')).json()).slow > 0, 'delayed shared artwork request starts');
        // Multiple receipts can arrive before a shared artwork request resolves.
        update({ gridX: 4, teleportVersion: 4 });
        update({ gridX: 7, teleportVersion: 5 });
        check(beforeDelayed.destroyed, 'late artwork never leaves the old teleported root mounted');
        for (let index = 0; index < 3; index++) { await frame(); stable('rapid teleport with pending art'); }
        await fetch('/gate/slow/release');
        await waitFor(() => figures.children.length === 1, 'rapid teleport latest art loads');
        await Promise.all([...pending]);
        const delayedRoot = art('rapid teleport final marker');
        update({});
        await frame();
        check(art('duplicate final delayed marker') === delayedRoot, 'late art is associated with the latest teleport marker');
        report.cases.push('rapid-teleports-with-shared-delayed-art-create-one-latest-token');

        await fetch('/gate/stale/arm');
        update({ gridX: 1, teleportVersion: 6, imageUrl: '/art/stale.png' });
        await waitFor(async () => (await (await fetch('/requests')).json()).stale > 0, 'superseded artwork request starts');
        update({ gridX: 4, teleportVersion: 7, imageUrl: '/art/final.png' });
        await waitFor(() => figures.children.length === 1, 'latest replacement artwork loads');
        const finalRoot = art('new artwork before stale response', colors.final);
        await fetch('/gate/stale/release');
        await Promise.all([...pending]);
        await frame();
        check(art('late superseded artwork response', colors.final) === finalRoot,
            'superseded artwork cannot recreate or replace the final token');
        report.cases.push('late-superseded-art-does-not-orphan-roots-or-masks');

        await fetch('/gate/dispose/arm');
        update({ gridX: 7, teleportVersion: 8, imageUrl: '/art/dispose.png' });
        await waitFor(async () => (await (await fetch('/requests')).json()).dispose > 0, 'disposed artwork request starts');
        controller.destroy();
        const previewsAtClose = previews;
        disposed = true;
        board.destroy();
        board.destroy();
        await fetch('/gate/dispose/release');
        await Promise.all([...pending]);
        await frame();
        check(!host.querySelector('canvas') && !host.children.length, 'disposed board removes its canvas');
        check(previews === previewsAtClose, 'controller emits no previews after disposal');
        check(!failures.length, `disposal produces no late asynchronous errors: ${failures}`);
        report.cases.push('disposal-cancels-motion-and-pending-art-presentation');
        return report;
    } finally {
        if (!disposed) { controller.destroy(); disposed = true; board.destroy(); }
        for (const name of ['slow', 'stale', 'dispose']) await fetch(`/gate/${name}/release`);
        await Promise.all([...pending]);
        host.remove();
    }
};
