window.installTokenSavingProbe = ({ rows, scene, cell }) => {
    const copy = value => structuredClone(value);
    const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
    const board = gravewrightMaps.board;
    const original = { fetch: window.fetch, command: gravewrightRealtime.resourceCommand,
        layers: gravewrightRealtime.mapLayers, drag: gravewrightRealtime.tokenDrag,
        update: board.update };
    const status = document.querySelector('.token-workspace__status');
    const svg = document.querySelector('.token-workspace');
    const probe = window.__tokenSaving = { rows: copy(rows), scene, cell, commands: [], reads: [],
        refreshes: [], motions: [], presentations: [], mutations: { status: 0, svg: 0 },
        visible: [], pending: 0, next: {}, held: null, currentPieces: [], failures: [] };
    const observers = [];
    let wasSaving = false;
    for (const [kind, target] of [['status', status], ['svg', svg]]) {
        const observer = new MutationObserver(records => {
            probe.mutations[kind] += records.length;
            const saving = !status.hidden && status.textContent.includes('Saving');
            if (saving !== wasSaving) probe.visible.push({ saving, at: performance.now(), text: status.textContent });
            wasSaving = saving;
        });
        observer.observe(target, { attributes: true, childList: true, characterData: true, subtree: true });
        observers.push(observer);
    }
    probe.reset = () => {
        for (const observer of observers) observer.takeRecords();
        probe.commands = []; probe.reads = []; probe.refreshes = []; probe.motions = [];
        probe.presentations = []; probe.visible = []; probe.mutations = { status: 0, svg: 0 };
        wasSaving = !status.hidden && status.textContent.includes('Saving');
    };
    probe.stats = () => copy({ commands: probe.commands, reads: probe.reads, refreshes: probe.refreshes,
        mutations: probe.mutations, visible: probe.visible, pending: probe.pending,
        rows: probe.rows, currentPieces: probe.currentPieces, presentations: probe.presentations,
        status: { connected: status.isConnected, hidden: status.hidden,
            role: status.getAttribute('role'), text: status.textContent } });
    probe.configure = next => { probe.next = next; };
    probe.pushNewer = (id, changes) => {
        probe.rows = probe.rows.map(row => row.id === id ? { ...row, ...changes, version: row.version + 1 } : row);
        window.dispatchEvent(new CustomEvent('gravewright:tokens.state', {
            detail: { mapId: scene, tokens: copy(probe.rows) },
        }));
    };
    probe.release = () => { const release = probe.held; probe.held = null; release?.(); };
    window.fetch = function (input, ...args) {
        const url = String(input?.url || input);
        if (url.endsWith(`/maps/${scene}/tokens`)) {
            probe.reads.push({ at: performance.now(), rows: copy(probe.rows) });
            return Promise.resolve(new Response(JSON.stringify({ tokens: probe.rows }), {
                status: 200, headers: { 'Content-Type': 'application/json' },
            }));
        }
        return original.fetch.call(this, input, ...args);
    };
    gravewrightRealtime.mapLayers = id => { probe.refreshes.push({ id, at: performance.now() }); };
    gravewrightRealtime.tokenDrag = value => { probe.motions.push(copy(value)); };
    board.update = value => {
        if (value.pieces) {
            probe.currentPieces = copy(value.pieces);
            probe.presentations.push({ at: performance.now(), pieces: copy(value.pieces) });
        }
        return original.update.call(board, value);
    };
    gravewrightRealtime.resourceCommand = async (area, action, data) => {
        if (area !== 'tokens') return original.command(area, action, data);
        const options = probe.next;
        // A group failure applies to its named row after earlier rows were accepted.
        const target = options.failFor || options.holdFor;
        if (!target || target === data.id) probe.next = {};
        const call = { area, action, data: copy(data), at: performance.now() };
        probe.commands.push(call);
        probe.pending++;
        try {
            if (action !== 'move') throw Error(`Unexpected token action: ${action}`);
            const index = probe.rows.findIndex(row => row.id === data.id), before = probe.rows[index];
            if (!before || before.version !== data.expectedVersion) {
                probe.failures.push({ reason: 'stale-expected-version', data: copy(data), before: copy(before) });
                throw Object.assign(Error('Synthetic conflict'), { code: 'conflict' });
            }
            if (options.conflict || options.failFor === data.id) {
                probe.rows[index] = { ...before, gridX: before.gridX + .25, version: before.version + 1 };
                throw Object.assign(Error('Synthetic conflict'), { code: 'conflict' });
            }
            let after = { ...before, gridX: data.gridX, gridY: data.gridY, version: before.version + 1 };
            if (options.teleport) after = { ...after, ...options.teleport };
            probe.rows[index] = after;
            if (options.other) {
                probe.rows = probe.rows.map(row => row.id === options.other
                    ? { ...row, gridX: row.gridX + 1, version: row.version + 1 } : row);
            }
            const ack = { tokens: copy(probe.rows), createdIds: [],
                ...(options.teleport ? { teleports: [{ id: data.id, version: after.version }] } : {}) };
            call.ack = copy(ack);
            if (options.hold || options.holdFor === data.id) await new Promise(resolve => { probe.held = resolve; });
            else await pause(10);
            call.ackAt = performance.now();
            return ack;
        } finally {
            probe.pending--;
        }
    };
    probe.dispose = () => {
        probe.release();
        for (const observer of observers) observer.disconnect();
        window.fetch = original.fetch;
        gravewrightRealtime.resourceCommand = original.command;
        gravewrightRealtime.mapLayers = original.layers;
        gravewrightRealtime.tokenDrag = original.drag;
        board.update = original.update;
    };
};
