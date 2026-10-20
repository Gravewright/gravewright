import test from 'node:test';
import assert from 'node:assert/strict';
import { createProjectApi, createProjectPersistence, recoverProjectDraft } from './project-persistence.js';
import { newDocument } from './model.js';

const campaignId = 'campaign';
const draftKey = id => `gravewright.map-builder.draft.${campaignId}.${id}`;
function memoryStorage() {
    const values = new Map();
    const storage = { values, getItem: key => values.get(key) ?? null,
        setItem: (key, value) => { values.set(key, value); storage[key] = value; },
        removeItem: key => { values.delete(key); delete storage[key]; },
        key: index => [...values.keys()][index] ?? null, get length() { return values.size; } };
    return storage;
}
function deferred() {
    let resolve;
    const promise = new Promise(yes => { resolve = yes; });
    return { promise, resolve };
}
function fixture(t, { respond = () => undefined, state, storage = memoryStorage(), server } = {}) {
    state ??= { id: crypto.randomUUID(), version: 1, folderId: null, document: newDocument('Saved map'),
        pending: new Map(), projects: [], assetRemovals: [] };
    state.saved ??= JSON.stringify(state.document);
    server ??= { version: state.version, document: structuredClone(JSON.parse(state.saved)), receipts: new Map() };
    const calls = [], acknowledgements = [];
    function commit(payload) {
        if (!server.receipts.has(payload.request_id)) {
            assert.equal(payload.expected_version, server.version, 'a new operation must use the acknowledged revision');
            server.document = structuredClone(payload.document);
            server.receipts.set(payload.request_id, { project: {
                id: state.id, version: ++server.version, document: structuredClone(payload.document),
            } });
        }
        return server.receipts.get(payload.request_id);
    }
    const saver = createProjectPersistence({ state, campaignId, storage, canSave: () => true,
        autosaveOptions: { delay: 0, retryDelays: [] }, onSaved: project => acknowledgements.push(project),
        api: async (path, payload) => {
            calls.push(structuredClone(payload));
            return await respond(payload, calls.length, commit) || commit(payload);
        },
    });
    saver.start(); t.after(() => saver.dispose());
    return { state, calls, storage, server, saver, acknowledgements,
        get draft() { return JSON.parse(storage.getItem(draftKey(state.id))); } };
}

test('Undo after a definitive rejection removes its body and receipt before reload', async t => {
    const invalid = Object.assign(new Error('Invalid shader source.'), { status: 400 });
    const f = fixture(t, { respond: () => { throw invalid; } });
    const baseline = structuredClone(f.state.document);
    f.state.document.name = 'Rejected draft';
    await assert.rejects(f.saver.flush(), /Invalid shader/);
    assert.equal(f.state.pending.size, 0); assert.equal(f.state.saveAttempt, null);
    assert.equal(f.draft.document.name, 'Rejected draft', 'the rejected authored document remains recoverable');
    f.state.document = baseline;
    f.saver.schedule(); await f.saver.flush();
    assert.equal(f.saver.state.status, 'saved'); assert.equal(f.calls.length, 1);
    assert.equal(f.draft, null, 'reload cannot replay the rejected body or infer an uncertain receipt');
});

test('repairing a rejected project leaves no false recovery conflict', async t => {
    const f = fixture(t, { respond: (payload, attempt) => {
        if (attempt === 1) throw Object.assign(new Error('Invalid document.'), { status: 400 });
    } });
    f.state.document.name = 'Rejected draft';
    await assert.rejects(f.saver.flush(), /Invalid document/);
    f.state.document.name = 'Corrected draft';
    f.saver.schedule(); await f.saver.flush();
    assert.equal(f.saver.state.status, 'saved');
    assert.equal(JSON.parse(f.state.saved).name, 'Corrected draft');
    assert.equal(f.state.pending.size, 0); assert.equal(f.state.saveAttempt, null); assert.equal(f.draft, null);
    assert.notEqual(f.calls[0].request_id, f.calls[1].request_id, 'the correction is a new logical operation');
});

for (const [name, error] of [
    ['transport failure', new Error('Offline')],
    ['server failure', Object.assign(new Error('Unavailable'), { status: 503 })],
    ['unreadable response', Object.assign(new Error('Invalid JSON'), { retryable: true })],
]) test(`${name} retains its receipt and body before saving newer edits`, async t => {
    const f = fixture(t, { respond: (payload, attempt) => { if (attempt === 1) throw error; } });
    f.state.document.name = 'Uncertain draft';
    await assert.rejects(f.saver.flush(), error);
    assert.equal(f.state.pending.size, 1);
    assert.equal(f.draft.saveAttempt.payload.document.name, 'Uncertain draft');
    f.state.document.name = 'Newer draft'; f.saver.schedule();
    f.saver.retry(); await f.saver.flush();
    assert.equal(f.calls.length, 3);
    assert.deepEqual(f.calls[0], f.calls[1], 'retry preserves the original UUID, revision and document');
    assert.notEqual(f.calls[1].request_id, f.calls[2].request_id);
    assert.equal(f.calls[2].expected_version, 2); assert.equal(f.calls[2].document.name, 'Newer draft');
    assert.equal(f.state.pending.size, 0); assert.equal(f.draft, null);
});

test('a revision conflict stays paused through edits without rebasing the local guard', async t => {
    const conflict = Object.assign(new Error('Changed elsewhere'), { status: 409, conflict: true });
    const f = fixture(t, { respond: () => { throw conflict; } });
    f.state.document.name = 'Local revision';
    await assert.rejects(f.saver.flush(), /Changed elsewhere/);
    f.state.document.name = 'Later local edit'; f.saver.rememberDraft(); f.saver.schedule();
    await assert.rejects(f.saver.flush(), /Changed elsewhere/);
    assert.equal(f.calls.length, 1); assert.equal(f.state.version, 1);
    assert.equal(f.saver.state.status, 'conflict');
    assert.equal(f.state.pending.size, 0); assert.equal(f.state.saveAttempt, null);
    assert.equal(f.draft.document.name, 'Later local edit');
});

test('an acknowledgement preserves newer document references and flush waits for their revision', async t => {
    const started = deferred(), response = deferred();
    const f = fixture(t, { respond: async (payload, attempt) => {
        if (attempt === 1) { started.resolve(); await response.promise; }
    } });
    f.state.document.name = 'First write';
    const flushed = f.saver.flush(); await started.promise;
    assert.ok(f.saver.pendingWrite);
    const authored = f.state.document;
    authored.name = 'Newer edit'; f.saver.schedule(); response.resolve(); await flushed;
    assert.equal(f.state.document, authored);
    assert.equal(f.state.document.name, 'Newer edit'); assert.equal(f.server.document.name, 'Newer edit');
    assert.deepEqual(f.calls.map(payload => payload.expected_version), [1, 2]);
    assert.deepEqual(f.acknowledgements.map(project => project.document.name), ['First write', 'Newer edit']);
    assert.equal(f.saver.pendingWrite, null); assert.equal(f.draft, null);
});

test('reload confirms a committed receipt before saving an Undo against its new revision', async t => {
    const started = deferred(), response = deferred();
    const f = fixture(t, { respond: async (payload, attempt, commit) => {
        const result = commit(payload); started.resolve(); await response.promise; return result;
    } });
    const baseline = structuredClone(f.state.document);
    f.state.document.name = 'Committed without reply';
    const stopped = assert.rejects(f.saver.flush(), error => error.name === 'AbortError');
    await started.promise;
    f.state.document = baseline; f.saver.schedule(); f.saver.rememberDraft();
    const { recovered } = recoverProjectDraft({ campaignId, projectId: f.state.id, folderId: null, storage: f.storage });
    f.saver.dispose(); await stopped;
    assert.equal(recovered.version, 1); assert.equal(f.server.version, 2);
    assert.equal(recovered.document.name, 'Saved map');
    const reopened = fixture(t, { state: recovered, storage: f.storage, server: f.server });
    await reopened.saver.flush();
    assert.equal(reopened.calls.length, 2);
    assert.deepEqual(reopened.calls[0], f.calls[0], 'reopening confirms the original body and receipt');
    assert.equal(reopened.calls[1].expected_version, 2);
    assert.equal(reopened.calls[1].document.name, 'Saved map'); assert.equal(f.server.version, 3);
    response.resolve(); await f.saver.pendingWrite;
    assert.equal(f.acknowledgements.length, 0, 'disposed clients ignore their late acknowledgement');
    assert.equal(reopened.draft, null);
});

test('legacy recovery retains unconfirmed revisions and rejects another folder', () => {
    const storage = memoryStorage(), id = crypto.randomUUID();
    const legacy = { id, version: 3, folderId: 'folder', document: newDocument('Private draft'),
        pending: [['/projects/' + id + ':unconfirmed', 'receipt-id']] };
    storage.setItem(`gravewright.map-builder.draft.${campaignId}`, JSON.stringify(legacy));
    const { recovered } = recoverProjectDraft({ campaignId, projectId: id, folderId: null, storage });
    assert.equal(recovered.version, 3); assert.equal(recovered.pending.get('/projects/' + id + ':unconfirmed'), 'receipt-id');
    assert.equal(recovered.saveAttempt, undefined, 'recovery must not invent the missing sent body');
    assert.equal(storage.getItem(`gravewright.map-builder.draft.${campaignId}`), null);
    assert.ok(storage.getItem(draftKey(id)));
    assert.equal(recoverProjectDraft({ campaignId, folderId: 'other-folder', storage }).recovered, undefined);
    assert.equal(recoverProjectDraft({ campaignId, folderId: 'folder', storage }).recovered.id, id);
});

test('invalid recovered content stays in storage for explicit recovery', () => {
    const storage = memoryStorage(), id = crypto.randomUUID(), document = newDocument('Recoverable');
    document.floors.push({ id: 'floor', name: '' });
    const original = JSON.stringify({ id, document }); storage.setItem(draftKey(id), original);
    const result = recoverProjectDraft({ campaignId, projectId: id, folderId: null, storage });
    assert.match(result.recoveryError, /name/); assert.equal(result.recovered, undefined);
    assert.equal(storage.getItem(draftKey(id)), original);
});

test('draft discard affects only this project and later authoring can retain another draft', t => {
    const f = fixture(t), otherId = crypto.randomUUID();
    f.storage.setItem(draftKey(otherId), 'Other project data');
    f.state.document.name = 'Unsaved'; f.saver.rememberDraft();
    assert.equal(f.draft.document.name, 'Unsaved');
    f.saver.discardDraft(); assert.equal(f.saver.discarded, true); assert.equal(f.draft, null);
    assert.equal(f.storage.getItem(draftKey(otherId)), 'Other project data');
    f.saver.keepDraft(); f.saver.rememberDraft();
    assert.equal(f.saver.discarded, false); assert.equal(f.draft.document.name, 'Unsaved');
});

test('asset reconciliation updates only readable campaign drafts and retains every revision guard', t => {
    const f = fixture(t), otherId = crypto.randomUUID();
    f.state.document.name = 'Local draft'; f.saver.rememberDraft();
    f.storage.setItem(draftKey(otherId), JSON.stringify({ version: 7, document: newDocument('Other draft') }));
    f.storage.setItem(draftKey('broken'), 'Unreadable draft');
    f.storage.setItem(draftKey('without-document'), '{"private":"preserve"}');
    const foreignKey = 'gravewright.map-builder.draft.another-campaign.project';
    const foreign = JSON.stringify({ document: newDocument('Another campaign') });
    f.storage.setItem(foreignKey, foreign);
    f.saver.updateDrafts(draft => { draft.document.name += ' reconciled'; });
    assert.equal(f.draft.document.name, 'Local draft reconciled'); assert.equal(f.draft.version, 1);
    const other = JSON.parse(f.storage.getItem(draftKey(otherId)));
    assert.equal(other.document.name, 'Other draft reconciled'); assert.equal(other.version, 7);
    assert.equal(f.storage.getItem(draftKey('broken')), 'Unreadable draft');
    assert.equal(f.storage.getItem(draftKey('without-document')), '{"private":"preserve"}');
    assert.equal(f.storage.getItem(foreignKey), foreign);
    assert.equal(f.storage.getItem(`gravewright.map-builder.draft.${campaignId}.latest`), f.state.id);
});

const translate = (key, params = {}) => key.replace('{status}', String(params.status));
test('the API keeps CSRF and cancellation local and preserves JSON and upload boundaries', async () => {
    const requests = [], controller = new AbortController();
    const api = createProjectApi({ base: '/api/containers/c/map-builder', signal: controller.signal, t: translate,
        fetch: async (url, options) => {
            requests.push({ url, options });
            return { ok: true, json: async () => url === '/__gravewright/csrf'
                ? { header: 'X-CSRF', token: 'private-token' } : { saved: true } };
        },
    });
    await api(); await api('/projects/p', { document: {} });
    const upload = new FormData(); upload.append('file', new Blob(['synthetic']));
    await api('/api/containers/c/library/upload', upload);
    assert.equal(requests.filter(request => request.url === '/__gravewright/csrf').length, 1);
    assert.equal(requests[0].options.headers['X-CSRF'], undefined);
    assert.equal(requests[2].options.headers['X-CSRF'], 'private-token');
    assert.equal(requests[2].options.headers['Content-Type'], 'application/json');
    assert.deepEqual(JSON.parse(requests[2].options.body), { document: {} });
    assert.equal(requests[3].options.body, upload); assert.equal(requests[3].options.headers['Content-Type'], undefined);
    assert.ok(requests.every(request => request.options.signal === controller.signal
        && request.options.credentials === 'same-origin' && request.options.cache === 'no-store'));
});

test('unreadable replies remain uncertain while a parsed rejection carries its conflict status', async () => {
    let readable = false;
    const api = createProjectApi({ base: '/api/map-builder', t: translate,
        fetch: async () => ({ ok: false, status: 409, json: async () => {
            if (!readable) throw new SyntaxError('Truncated response');
            return { error: 'Changed elsewhere' };
        } }),
    });
    await assert.rejects(api(), error => error.retryable === true && error.status === undefined && !error.conflict);
    readable = true;
    await assert.rejects(api(), error => error.status === 409 && error.conflict && error.message === 'Changed elsewhere');
});
