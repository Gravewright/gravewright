(() => {
    const p = window.__mapbuilderPerf = { active: false };
    const contexts = new Set(), bytes = value => new TextEncoder().encode(value).byteLength;
    const mark = (kind, data = {}) => { if (p.active) p.events.push({ kind, at: performance.now(), ...data }); };
    const context = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (kind, ...args) {
        const value = context.call(this, kind, ...args);
        if (value && /webgl/.test(kind)) contexts.add(value);
        return value;
    };
    const socket = window.WebSocket;
    window.WebSocket = class extends socket {
        constructor(...args) {
            super(...args);
            this.addEventListener('message', event => {
                if (!p.active || typeof event.data !== 'string') return;
                const value = JSON.parse(event.data);
                p.traffic.push({ direction: 'received', type: value.type, bytes: bytes(event.data), at: performance.now() });
            });
        }
    };
    const send = socket.prototype.send;
    socket.prototype.send = function (raw) {
        if (p.active && typeof raw === 'string') {
            const value = JSON.parse(raw);
            p.traffic.push({ direction: 'sent', type: value.type, bytes: bytes(raw), at: performance.now() });
            if (value.type === 'tokens.command') mark('command', { requestId: value.payload.requestId, action: value.payload.action });
        }
        return send.call(this, raw);
    };
    addEventListener('gravewright:api-event', event => {
        if (!p.active) return;
        const { type, payload } = event.detail;
        mark(type, { requestId: payload.requestId, domain: payload.domain || payload.area,
            module: payload.module, action: payload.action });
        if (type === 'tokens.error') p.errors.push(payload);
        const rows = type === 'tokens.ack' ? payload.result?.tokens : type === 'tokens.state' ? payload.tokens : null;
        const row = rows?.find(row => row.id === p.watch.token);
        if (row) p.lastToken = { gridX: row.gridX, gridY: row.gridY, version: row.version, type };
        if (row && row.gridX >= p.watch.minX && row.gridX <= p.watch.maxX && row.gridY >= p.watch.minY && row.gridY <= p.watch.maxY) {
            p.confirmedAt ??= performance.now();
            // A matching remote/local preview may already be on screen. A still
            // board needs no redraw; its default WebGL backbuffer is discardable.
            if (p.firstPixel) p.committedPixel ??= { ...p.firstPixel, reusedPreview: true };
        }
    });
    for (const name of ['pointerdown', 'pointerup']) addEventListener(name, () => mark(name), true);
    const fetchOriginal = window.fetch;
    window.fetch = function (input, ...args) {
        if (p.active) p.fetches.push({ url: String(input?.url || input), at: performance.now() });
        return fetchOriginal.call(this, input, ...args);
    };
    const bitmap = window.createImageBitmap;
    window.createImageBitmap = async function (...args) {
        const value = await bitmap.apply(this, args);
        if (p.active) { p.decodes++; p.decodedSizes.push({ width: value.width, height: value.height }); }
        return value;
    };
    for (const ctor of [window.WebGLRenderingContext, window.WebGL2RenderingContext].filter(Boolean)) {
        for (const name of ['clear', 'createTexture', 'deleteTexture', 'createFramebuffer', 'deleteFramebuffer', 'texImage2D']) {
            const original = ctor.prototype[name];
            ctor.prototype[name] = function (...args) {
                if (p.active) {
                    p.gpu[name]++;
                    if (name === 'texImage2D') {
                        const source = args[5];
                        p.uploads.push({ width: args.length >= 9 ? args[3] : source?.width,
                            height: args.length >= 9 ? args[4] : source?.height });
                    }
                }
                return original.apply(this, args);
            };
        }
    }
    let frame = 0, previous;
    function sampleGPU() {
        if (!p.active) return;
        const view = window.gravewrightMaps?.board?.viewport(), watch = p.watch;
        const surface = document.querySelector('.game-board__surface');
        if (view && surface && !p.committedPixel) {
            const rect = surface.getBoundingClientRect();
            const worldX = (watch.x + .5) * watch.cell, worldY = (watch.y + .5) * watch.cell;
            for (const gl of contexts) {
                const canvas = gl.canvas;
                if (!canvas.isConnected || !canvas.closest('.game-board') || gl.getParameter(gl.FRAMEBUFFER_BINDING) !== null) continue;
                const bounds = canvas.getBoundingClientRect();
                const x = Math.round((rect.x + view.x + worldX * view.scale - bounds.x) * canvas.width / bounds.width);
                const y = canvas.height - 1 - Math.round((rect.y + view.y + worldY * view.scale - bounds.y) * canvas.height / bounds.height);
                if (x < 0 || y < 0 || x >= canvas.width || y >= canvas.height) continue;
                const color = new Uint8Array(4);
                gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, color);
                p.lastPixel = { rgb: [...color], x, y, view };
                if (Math.abs(color[0] - 120) < 12 && Math.abs(color[1] - 181) < 12 && Math.abs(color[2] - 58) < 12) {
                    const point = { at: performance.now(), rgb: [...color], x, y };
                    p.firstPixel ??= point;
                    if (p.confirmedAt) p.committedPixel = point;
                }
            }
        }
    }
    const nativeFrame = window.requestAnimationFrame;
    window.requestAnimationFrame = callback => nativeFrame.call(window, time => {
        callback(time);
        sampleGPU();
    });
    function sample(time) {
        if (!p.active) return;
        if (previous !== undefined) p.gaps.push(time - previous);
        previous = time;
        frame = requestAnimationFrame(sample);
    }
    p.install = () => {
        const board = gravewrightMaps.board, update = board.update;
        board.update = function (value) {
            const started = performance.now(), active = p.active;
            const result = update.call(this, value);
            if (active) Promise.resolve(result).finally(() => {
                if (p.active) p.updates.push({ keys: Object.keys(value), ms: performance.now() - started });
            });
            return result;
        };
    };
    p.start = watch => {
        p.active = true; p.watch = watch; p.events = []; p.traffic = []; p.fetches = [];
        p.errors = []; p.gaps = []; p.decodes = 0; p.decodedSizes = []; p.uploads = []; p.updates = [];
        p.gpu = { clear: 0, createTexture: 0, deleteTexture: 0, createFramebuffer: 0, deleteFramebuffer: 0, texImage2D: 0 };
        p.confirmedAt = null; p.firstPixel = null; p.committedPixel = null;
        p.lastPixel = null; p.lastToken = null; previous = undefined;
        mark('armed'); cancelAnimationFrame(frame); frame = requestAnimationFrame(sample);
    };
    p.finish = () => {
        p.active = false; cancelAnimationFrame(frame);
        return { timeOrigin: performance.timeOrigin, visibility: document.visibilityState,
            events: p.events, traffic: p.traffic, fetches: p.fetches, errors: p.errors,
            gaps: p.gaps, gpu: p.gpu, decodes: p.decodes, updates: p.updates,
            decodedSizes: p.decodedSizes, uploads: p.uploads,
            firstPixel: p.firstPixel, committedPixel: p.committedPixel, confirmedAt: p.confirmedAt,
            lastPixel: p.lastPixel, lastToken: p.lastToken };
    };
})();
