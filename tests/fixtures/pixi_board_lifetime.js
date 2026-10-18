import 'pixi.js/unsafe-eval';
import { Application } from 'pixi.js';
import { PixiBoardRenderer } from '../../gravewright/maps/frontend/widgets/game-board/lib/pixi-board-renderer.js';

const color = [232, 74, 96];
const background = [12, 24, 36];
const nextFrame = () => new Promise(resolve => requestAnimationFrame(resolve));
const check = (value, message) => { if (!value) throw Error(message); };

function artwork() {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 96;
    const context = canvas.getContext('2d');
    context.fillStyle = `rgb(${color.join(',')})`;
    context.fillRect(0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/png');
}

function pixel(app, x, y) {
    app.render();
    const gl = app.renderer.gl;
    const result = new Uint8Array(4);
    gl.readPixels(x, app.canvas.height - y - 1, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, result);
    return [...result];
}

function matches(actual, expected) {
    return expected.every((value, channel) => Math.abs(actual[channel] - value) <= 3);
}

window.runBoardLifetime = async () => {
    const art = artwork(), cases = [], mounted = new Set();
    async function mount(name) {
        const host = document.createElement('div');
        host.style.cssText = 'width:440px;height:320px;display:inline-block;vertical-align:top';
        document.body.appendChild(host);
        const app = new Application();
        await app.init({ width: 440, height: 320, resizeTo: host, autoStart: false,
            resolution: 1, preference: 'webgl', background: '#0c1824' });
        host.appendChild(app.canvas);
        const board = new PixiBoardRenderer(app, name);
        const piece = { key: 'hero', label: name, x: 100, y: 110, size: 80,
            accent: '#77ccbb', selected: true, imageUrl: art };
        await board.setPieces([piece]);
        app.render();
        const value = { app, board, host, piece };
        mounted.add(value);
        return value;
    }
    function assertArt(value, x, y, label) {
        check(matches(pixel(value.app, x, y), color), `${label}: token artwork is still rendered`);
        check(matches(pixel(value.app, x + 30, y - 30), background), `${label}: circular mask is intact`);
    }
    function destroy(value) {
        value.board.destroy();
        value.board.destroy();
        check(!value.host.querySelector('canvas'), 'destroy removes its own canvas');
        value.host.remove();
        mounted.delete(value);
    }
    try {
        const main = await mount('Main token');
        assertArt(main, main.piece.x, main.piece.y, 'initial main');
        for (let i = 0; i < 6; i++) {
            const clearing = main.board.setPieces([]);
            const reentering = main.board.setPieces([{ ...main.piece, x: 110 + i * 40 }]);
            await Promise.all([clearing, reentering]);
            main.piece = { ...main.piece, x: 110 + i * 40 };
            await nextFrame();
            assertArt(main, main.piece.x, main.piece.y, `after immediately remounting art ${i}`);
            cases.push('cleared-token-reacquires-live-masked-art');
        }
        for (let i = 0; i < 4; i++) {
            const preview = await mount('Preview token');
            assertArt(preview, preview.piece.x, preview.piece.y, 'preview');
            destroy(preview);
            const piece = { ...main.piece, label: `Main token ${i}`, x: 110 + i * 60,
                y: 110 + i * 8, hovered: i % 2 === 0, selected: true,
                conditions: [{ label: `Synthetic condition ${i}`, kind: 'positive' }] };
            await main.board.setPieces([piece]);
            main.piece = piece;
            main.host.style.width = `${440 + i * 12}px`;
            main.board.resize();
            await nextFrame();
            assertArt(main, piece.x, piece.y, `after closing preview ${i}`);
            cases.push('closing-preview-preserves-main-art-mask-text-resize');
        }
        const remaining = await mount('Surviving preview');
        assertArt(remaining, remaining.piece.x, remaining.piece.y, 'second board before main close');
        destroy(main);
        remaining.piece = { ...remaining.piece, label: 'Surviving board after closing main', x: 260,
            selected: true, hovered: true };
        await remaining.board.setPieces([remaining.piece]);
        remaining.board.resize();
        await nextFrame();
        assertArt(remaining, remaining.piece.x, remaining.piece.y, 'preview after main close');
        cases.push('closing-main-preserves-other-board');
        window.__lifetimeCanvas = remaining.app.canvas;
        destroy(remaining);
        cases.push('each-board-disposes-idempotently');
        return { cases, color };
    } finally {
        for (const value of mounted) destroy(value);
    }
};
