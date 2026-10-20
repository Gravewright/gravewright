import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { createAutosave } from './autosave.js';
import { sameDocument } from './asset-removal.js';

// Exercise the workspace's actual persistence callbacks without mounting its DOM,
// WebGL previews or a server. The transport and browser storage are the boundaries.
const source = readFileSync(new URL('./workspace.js', import.meta.url), 'utf8');
function section(start, end) {
    const first = source.indexOf(start), last = source.indexOf(end, first);
    assert.ok(first >= 0 && last > first, `Missing workspace section: ${start}`);
    return source.slice(first, last);
}
function fixture(t, respond = () => undefined) {
    const state = {
        id: '00000000-0000-4000-8000-000000000001', version: 1, folderId: null,
        document: { name: 'Saved map', decorations: [{ id: 'owner', blueprint: { value: 1 } }] },
        pending: new Map(), projects: [], assetRemovals: [],
    };
    state.saved = JSON.stringify(state.document);
    const values = new Map(), calls = [], receipts = new Map();
    const storage = {
        getItem: key => values.get(key) ?? null,
        setItem: (key, value) => values.set(key, value),
        removeItem: key => values.delete(key),
    };
    const noop = () => {};
    let version = state.version;
    const context = vm.createContext({
        state, crypto, TextEncoder, clone: structuredClone, sameDocument,
        sessionStorage: storage, draftPrefix: 'draft.', latestDraftKey: 'draft.latest', discardDraft: false,
        dirty: () => state.saved !== JSON.stringify(state.document),
        createAutosave: options => createAutosave({ ...options, delay: 0, retryDelays: [] }),
        autosave: undefined, autosaveEpoch: 0, projectWrite: undefined, disposed: false,
        ready: true, busy: false, saveBarrier: false, gesture: null, brushResize: null,
        floorPainter: null, terrainPainter: null, wallControls: null,
        form: { checkValidity: () => true }, selectionFieldsValid: () => true, applySettings: () => true,
        updateSaveState: noop, projectMetadata: noop, updateURL: noop, renderProjects: noop,
        notify: noop, hideNotice: noop, openProject: noop, saveCopy: noop, t: value => value,
        $: () => ({ dataset: { source: '' } }),
        target: { kind: 'decorations', id: 'owner' }, itemFor: () => state.document.decorations[0],
        editable: () => true, renderCanvas: noop, renderProperties: noop,
        commit: () => context.autosave.schedule(),
        api: async (path, payload) => {
            calls.push(structuredClone(payload));
            const result = await respond(payload, calls.length);
            if (result) return result;
            if (!receipts.has(payload.request_id)) receipts.set(payload.request_id, {
                project: { id: state.id, version: ++version, document: structuredClone(payload.document) },
            });
            return receipts.get(payload.request_id);
        },
    });
    const key = source.split('\n').find(line => line.includes('const projectKey ='));
    assert.ok(key);
    vm.runInContext([
        section('    function rememberDraft()', '    function updateSaveState()'), key,
        section('    function startAutosave()', '    function setBusy('),
        section('    async function operation(', '    async function loadFilterCatalog('),
        section('    async function saveCurrent(', '    function saveCopy()'),
    ].join('\n'), context);
    context.startAutosave();
    t.after(() => context.autosave.dispose());
    return { state, calls, values, context, saver: context.autosave,
        get draft() { return JSON.parse(storage.getItem('draft.' + state.id)); } };
}

test('Undo after a definitive project rejection removes its body and receipt before reload', async t => {
    const invalid = Object.assign(new Error('Invalid shader source.'), { status: 400 });
    const f = fixture(t, () => { throw invalid; });
    const baseline = structuredClone(f.state.document);
    f.state.document.name = 'Rejected draft';
    await assert.rejects(f.saver.flush(), /Invalid shader/);
    assert.equal(f.state.pending.size, 0);
    assert.equal(f.state.saveAttempt, null);
    assert.equal(f.draft.document.name, 'Rejected draft', 'the rejected authored document remains recoverable');

    f.state.document = baseline;
    f.saver.schedule(); await f.saver.flush();
    assert.equal(f.saver.state.status, 'saved');
    assert.equal(f.calls.length, 1, 'Undo to the acknowledged document needs no replacement write');
    assert.equal(f.draft, null, 'reload cannot replay the rejected body or infer an uncertain receipt');
});

test('repairing a rejected project saves normally and leaves no false recovery conflict', async t => {
    const f = fixture(t, (payload, attempt) => {
        if (attempt === 1) throw Object.assign(new Error('Invalid document.'), { status: 400 });
    });
    f.state.document.name = 'Rejected draft';
    await assert.rejects(f.saver.flush(), /Invalid document/);
    f.state.document.name = 'Corrected draft';
    f.saver.schedule(); await f.saver.flush();
    assert.equal(f.saver.state.status, 'saved');
    assert.equal(JSON.parse(f.state.saved).name, 'Corrected draft');
    assert.equal(f.state.pending.size, 0);
    assert.equal(f.state.saveAttempt, null);
    assert.equal(f.draft, null);
    assert.notEqual(f.calls[0].request_id, f.calls[1].request_id, 'the corrected document is a new logical operation');
});

for (const [name, error] of [
    ['transport failure', new Error('Offline')],
    ['server failure', Object.assign(new Error('Unavailable'), { status: 503 })],
    ['unreadable response', Object.assign(new Error('Invalid JSON'), { retryable: true })],
]) test(`${name} preserves its exact receipt and body before saving newer edits`, async t => {
    const f = fixture(t, (payload, attempt) => { if (attempt === 1) throw error; });
    f.state.document.name = 'Uncertain draft';
    await assert.rejects(f.saver.flush(), error);
    assert.equal(f.state.pending.size, 1);
    assert.equal(f.draft.saveAttempt.payload.document.name, 'Uncertain draft');
    f.state.document.name = 'Newer draft'; f.saver.schedule();
    f.saver.retry(); await f.saver.flush();
    assert.equal(f.calls.length, 3);
    assert.deepEqual(f.calls[0], f.calls[1], 'retry confirms the original operation without changing its UUID or revision');
    assert.notEqual(f.calls[1].request_id, f.calls[2].request_id);
    assert.equal(f.calls[2].expected_version, 2);
    assert.equal(f.calls[2].document.name, 'Newer draft');
    assert.equal(f.state.pending.size, 0); assert.equal(f.draft, null);
});

function behaviorSave(f, network) {
    const body = network
        ? section("    $('[data-builder-network]').addEventListener", '    function openBehavior(')
            .match(/save: async \(owner, blueprint\) => \{([\s\S]*?)\r?\n            \}, discard:/)
        : section('    function openBehavior(', '    async function refreshLibrary(')
            .match(/onSave: async blueprint => \{([\s\S]*?)\r?\n            \}, onDiscard:/);
    assert.ok(body, 'Missing Smart Object project callback');
    const callback = vm.runInContext(`async (${network ? 'owner, blueprint' : 'blueprint'}) => {${body[1]}}`, f.context);
    return network ? blueprint => callback({ sourceKind: 'decorations', id: 'owner' }, blueprint) : callback;
}

for (const network of [false, true]) {
    const label = network ? 'scene network' : 'direct Smart Object editor';
    test(`${label} retries the paused project write after the connection recovers`, async t => {
        let online = false;
        const f = fixture(t, () => { if (!online) throw new Error('Offline'); });
        const onSave = behaviorSave(f, network), blueprint = { value: 2 };
        const modal = createAutosave({ initialKey: JSON.stringify({ value: 1 }), delay: 0, retryDelays: [],
            read: () => ({ key: JSON.stringify(blueprint), payload: blueprint }),
            save: snapshot => onSave(structuredClone(snapshot.payload)),
        });
        t.after(() => modal.dispose());
        await assert.rejects(modal.flush(), /Offline/);
        assert.equal(f.saver.state.status, 'error');
        online = true;
        modal.retry(); await modal.flush();
        assert.equal(f.calls.length, 2);
        assert.deepEqual(f.calls[0], f.calls[1], 'retry retains the project operation receipt');
        assert.equal(modal.state.status, 'saved'); assert.equal(f.saver.state.status, 'saved');
        assert.equal(JSON.parse(f.state.saved).decorations[0].blueprint.value, 2);
    });

    test(`${label} keeps revision conflicts paused when the modal retries`, async t => {
        const conflict = Object.assign(new Error('Changed elsewhere'), { status: 409, conflict: true });
        const f = fixture(t, () => { throw conflict; });
        const onSave = behaviorSave(f, network);
        await assert.rejects(onSave({ value: 2 }), /Changed elsewhere/);
        await assert.rejects(onSave({ value: 2 }), /Changed elsewhere/);
        assert.equal(f.calls.length, 1);
        assert.equal(f.saver.state.status, 'conflict');
        assert.equal(f.state.pending.size, 0); assert.equal(f.state.saveAttempt, null);
        assert.equal(f.draft.document.decorations[0].blueprint.value, 2, 'the conflicted local graph remains recoverable');
    });
}
