import test from 'node:test';
import assert from 'node:assert/strict';
import { createAutosave } from './autosave.js';

const microtasks = async () => { for (let index = 0; index < 12; index++) await Promise.resolve(); };
function deferred() {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
}
function clock() {
    let time = 0, ordinal = 0;
    const tasks = new Map();
    return { timers: { now: () => time,
        setTimeout: (run, delay) => { const id = ++ordinal; tasks.set(id, { run, at: time + delay }); return id; },
        clearTimeout: id => tasks.delete(id) },
        get pending() { return tasks.size; },
        async tick(milliseconds) {
            const target = time + milliseconds;
            for (let count = 0; count < 1000; count++) {
                const next = [...tasks.entries()].sort((a, b) => a[1].at - b[1].at)[0];
                if (!next || next[1].at > target) { time = target; await microtasks(); return; }
                time = next[1].at; tasks.delete(next[0]); next[1].run(); await microtasks();
            }
            throw new Error('Unexpected unbounded autosave timer loop.');
        } };
}
function fixture(t, options = {}) {
    const time = clock(), source = { value: 0 }, calls = [], states = [];
    let version = 1;
    const saver = createAutosave({ initialKey: '0', timers: time.timers,
        read: () => ({ key: String(source.value), payload: { document: source, version } }),
        save: async (snapshot, context) => { calls.push({ snapshot, context }); return { version: ++version }; },
        onState: state => states.push(state), ...options });
    t.after(() => saver.dispose());
    return { saver, time, source, calls, states };
}

test('opening a saved draft is idle and repeated edit notifications debounce to its latest content', async t => {
    const f = fixture(t);
    assert.equal(f.time.pending, 0);
    await f.time.tick(10000); assert.equal(f.calls.length, 0);
    f.source.value = 1; f.saver.schedule(); await f.time.tick(400);
    f.source.value = 2; f.saver.schedule(); await f.time.tick(699);
    assert.equal(f.calls.length, 0); assert.equal(f.saver.state.status, 'pending');
    await f.time.tick(1);
    assert.equal(f.calls.length, 1); assert.equal(f.calls[0].snapshot.payload.document.value, 2);
    assert.equal(f.saver.state.status, 'saved');
    f.saver.schedule(); await f.time.tick(700);
    assert.equal(f.calls.length, 1, 'the acknowledged key avoids duplicate content writes');
});

test('an unknown baseline permits a new empty project, while the constructor never starts a write', async t => {
    let reads = 0, saves = 0;
    const f = fixture(t, { initialKey: null, read: () => { reads++; return { key: 'empty', payload: {} }; },
        save: async () => { saves++; } });
    assert.equal(reads, 0); assert.equal(f.time.pending, 0);
    await f.time.tick(5000); assert.equal(saves, 0);
    await f.saver.flush(); assert.equal(saves, 1);
});

test('the next write captures the latest document after the previous acknowledgement updates its revision', async t => {
    const first = deferred(), calls = [];
    let revision = 1;
    const source = { value: 0 }, f = fixture(t, {
        read: () => ({ key: String(source.value), payload: { source, revision } }),
        save: async snapshot => {
            calls.push(snapshot);
            if (calls.length === 1) await first.promise;
            return { version: ++revision };
        } });
    source.value = 1; f.saver.schedule(); await f.time.tick(700);
    source.value = 2; f.saver.schedule(); source.value = 3; f.saver.schedule();
    await f.time.tick(2000); assert.equal(calls.length, 1, 'writes never overlap');
    assert.equal(calls[0].payload.source.value, 1, 'later mutable source edits cannot alter the operation snapshot');
    first.resolve(); await microtasks(); await f.time.tick(0);
    assert.equal(calls.length, 2); assert.equal(calls[1].payload.source.value, 3);
    assert.equal(calls[1].payload.revision, 2, 'the queued write uses the acknowledged revision');
});

test('flush skips debounce and waits for every newer edit without resolving after only the first write', async t => {
    const first = deferred(), second = deferred(), calls = [];
    const f = fixture(t, { save: snapshot => { calls.push(snapshot); return calls.length === 1 ? first.promise : second.promise; } });
    f.source.value = 1;
    let resolved = false;
    const pending = f.saver.flush().then(result => { resolved = true; return result; });
    f.source.value = 2; f.saver.schedule();
    first.resolve('first'); await microtasks(); await f.time.tick(0);
    assert.equal(calls.length, 2); assert.equal(resolved, false);
    second.resolve('latest'); await microtasks();
    assert.equal(await pending, 'latest'); assert.equal(f.saver.state.status, 'saved');
});

test('undoing to the previous saved content during a write still persists that undo after acknowledgement', async t => {
    const gate = deferred(), calls = [];
    const f = fixture(t, { save: async snapshot => { calls.push(snapshot); if (calls.length === 1) await gate.promise; } });
    f.source.value = 1; f.saver.schedule(); await f.time.tick(700);
    f.source.value = 0; f.saver.schedule(); gate.resolve(); await microtasks(); await f.time.tick(700);
    assert.deepEqual(calls.map(row => row.key), ['1', '0']);
});

test('gestures defer capture and network writes while a pending flush resumes once editing becomes safe', async t => {
    let allowed = false;
    const f = fixture(t, { canSave: () => allowed });
    f.source.value = 1;
    const pending = f.saver.flush();
    await f.time.tick(300); assert.equal(f.calls.length, 0); assert.equal(f.saver.state.status, 'pending');
    f.source.value = 2; allowed = true; await f.time.tick(100);
    await pending;
    assert.equal(f.calls.length, 1); assert.equal(f.calls[0].snapshot.key, '2');
});

test('network retries retain the original snapshot and abort signal, use bounded backoff, and reject a failed flush', async t => {
    const calls = [], offline = Object.assign(new Error('Offline'), { status: 503 });
    const f = fixture(t, { retryDelays: [10, 20], save: async (snapshot, context) => { calls.push({ snapshot, context }); throw offline; } });
    f.source.value = 1;
    const pending = assert.rejects(f.saver.flush(), /Offline/);
    await microtasks(); assert.equal(f.saver.state.retrying, true);
    await f.time.tick(9); assert.equal(calls.length, 1);
    await f.time.tick(1); assert.equal(calls.length, 2);
    await f.time.tick(20); await pending;
    assert.equal(calls.length, 3); assert.equal(f.saver.state.retrying, false);
    assert.deepEqual(calls.map(row => row.context.attempt), [1, 2, 3]);
    assert.equal(calls.every(row => row.snapshot === calls[0].snapshot), true);
    assert.equal(calls.every(row => row.context.signal === calls[0].context.signal), true);
    assert.equal(f.time.pending, 0);
});

test('a manual retry after an uncertain transport failure reuses its operation before saving newer content', async t => {
    const calls = [], offline = Object.assign(new Error('Offline'), { status: 0 });
    let recovered = false;
    const f = fixture(t, { retryDelays: [], save: async snapshot => { calls.push(snapshot); if (!recovered) throw offline; } });
    f.source.value = 1; await assert.rejects(f.saver.flush(), /Offline/);
    f.source.value = 2; f.saver.schedule(); recovered = true;
    f.saver.retry(); const pending = f.saver.flush(); await microtasks(); await f.time.tick(0); await pending;
    assert.equal(calls[0], calls[1]); assert.deepEqual(calls.map(row => row.key), ['1', '1', '2']);
});

test('version conflicts remain paused through new edits and flushes until the caller explicitly resolves and retries', async t => {
    const calls = [], conflict = Object.assign(new Error('Changed elsewhere'), { conflict: true, status: 409 });
    let recovered = false;
    const f = fixture(t, { save: async snapshot => { calls.push(snapshot); if (!recovered) throw conflict; } });
    f.source.value = 1; await assert.rejects(f.saver.flush(), /Changed elsewhere/);
    f.source.value = 2; f.saver.schedule(); await f.time.tick(10000);
    await assert.rejects(f.saver.flush(), /Changed elsewhere/); assert.equal(calls.length, 1);
    assert.equal(f.saver.state.status, 'conflict');
    recovered = true; f.saver.retry(); const pending = f.saver.flush(); await microtasks(); await pending;
    assert.deepEqual(calls.map(row => row.key), ['1', '2']); assert.notEqual(calls[0], calls[1]);
});

test('invalid payloads do not retry automatically, and a newly authored edit can repair the blocked draft', async t => {
    const invalid = Object.assign(new Error('Invalid document'), { status: 400 });
    let valid = false;
    const f = fixture(t, { save: async snapshot => { f.calls.push(snapshot); if (!valid) throw invalid; } });
    f.source.value = 1; await assert.rejects(f.saver.flush(), /Invalid document/);
    await f.time.tick(10000); assert.equal(f.calls.length, 1); assert.equal(f.saver.state.status, 'blocked');
    valid = true; f.source.value = 2; f.saver.schedule(); await f.time.tick(700);
    assert.deepEqual(f.calls.map(row => row.key), ['1', '2']); assert.equal(f.saver.state.status, 'saved');
});

test('client validation thrown while capturing a draft rejects flush without calling the server', async t => {
    let valid = false;
    const f = fixture(t, { initialKey: 'old', read: () => { if (!valid) throw new Error('Invalid blueprint.'); return { key: 'new', payload: {} }; } });
    await assert.rejects(f.saver.flush(), /Invalid blueprint/);
    assert.equal(f.calls.length, 0); assert.equal(f.saver.state.status, 'blocked');
    valid = true; f.saver.schedule(); await f.time.tick(700); assert.equal(f.calls.length, 1);
});

test('an edit already queued during a rejected payload can repair it, while another flush of unchanged content cannot retry validation', async t => {
    const gate = deferred(), calls = [], invalid = Object.assign(new Error('Invalid old document'), { status: 400 });
    const f = fixture(t, { save: async snapshot => { calls.push(snapshot); if (calls.length === 1) await gate.promise; return 'repaired'; } });
    f.source.value = 1;
    const pending = f.saver.flush();
    f.source.value = 2; f.saver.schedule();
    gate.reject(invalid); await microtasks(); await f.time.tick(0);
    assert.equal(await pending, 'repaired'); assert.deepEqual(calls.map(row => row.key), ['1', '2']);

    const unchangedGate = deferred(), failed = fixture(t, { save: () => unchangedGate.promise });
    failed.source.value = 1;
    const first = assert.rejects(failed.saver.flush(), /Invalid old document/);
    const second = assert.rejects(failed.saver.flush(), /Invalid old document/);
    unchangedGate.reject(invalid); await first; await second;
    assert.equal(failed.saver.state.status, 'blocked'); assert.equal(failed.time.pending, 0);
});

test('a validation error from the write gate rejects close barriers instead of leaving them unresolved', async t => {
    const f = fixture(t, { canSave: () => { throw new Error('Finish editing this field.'); } });
    await assert.rejects(f.saver.flush(), /Finish editing/);
    assert.equal(f.saver.state.status, 'blocked'); assert.equal(f.calls.length, 0);
});

test('a newer edit scheduled by an acknowledgement observer remains inside the flush barrier', async t => {
    let f;
    f = fixture(t, { onState: state => {
        if (state.status === 'saved' && f.source.value === 1) { f.source.value = 2; f.saver.schedule(); }
    } });
    f.source.value = 1;
    let resolved = false;
    const pending = f.saver.flush().then(() => { resolved = true; });
    await microtasks(); assert.equal(resolved, false);
    await f.time.tick(0); await pending;
    assert.deepEqual(f.calls.map(row => row.snapshot.key), ['1', '2']);
});

test('reload replays a lost acknowledgement with the same receipt before persisting an Undo to the previously saved content', async () => {
    const time = clock(), oldRequest = deferred(), pending = new Map(), receipts = new Map(), calls = [], reads = [];
    let ready = true, value = 'A', revision = 1, serverValue = 'A', serverRevision = 1, attemptSnapshot, nextId = 0;
    const read = () => { reads.push(revision); return { key: value, payload: { value, revision } }; };
    const save = async (snapshot, { signal }) => {
        attemptSnapshot = structuredClone(snapshot);
        const key = JSON.stringify(snapshot.payload);
        if (!pending.has(key)) pending.set(key, `operation-${++nextId}`);
        const requestId = pending.get(key);
        calls.push({ requestId, payload: structuredClone(snapshot.payload), signal });
        let result = receipts.get(requestId);
        if (!result) {
            assert.equal(snapshot.payload.revision, serverRevision, 'a new write uses the last acknowledged revision');
            serverValue = snapshot.payload.value; result = { revision: ++serverRevision };
            receipts.set(requestId, result);
        }
        if (calls.length === 1) await oldRequest.promise;
        revision = result.revision; pending.delete(key); attemptSnapshot = undefined;
        return result;
    };
    const original = createAutosave({ read, save, initialKey: 'A', timers: time.timers });
    value = 'B'; original.schedule(); await time.tick(700);
    assert.equal(serverValue, 'B'); assert.equal(revision, 1, 'the server committed before the browser received its acknowledgement');
    value = 'A'; original.schedule();
    const storedSnapshot = JSON.parse(JSON.stringify(attemptSnapshot));
    original.dispose(); oldRequest.reject(new DOMException('Navigation', 'AbortError')); await microtasks();

    ready = false;
    const recovered = createAutosave({ read, save, initialKey: 'A', pendingSnapshot: storedSnapshot,
        canSave: () => ready, timers: time.timers });
    storedSnapshot.payload.value = 'mutated outside controller';
    assert.equal(time.pending, 0, 'recovery construction does not write before the caller finishes loading');
    recovered.schedule(); await time.tick(800); assert.equal(calls.length, 1);
    ready = true; await time.tick(100); await time.tick(0);
    assert.deepEqual(calls.map(row => row.requestId), ['operation-1', 'operation-1', 'operation-2']);
    assert.deepEqual(calls.map(row => row.payload), [{ value: 'B', revision: 1 }, { value: 'B', revision: 1 }, { value: 'A', revision: 2 }]);
    assert.deepEqual(reads, [1, 2], 'the current document is captured only after its recovered predecessor is acknowledged');
    assert.equal(serverValue, 'A'); assert.equal(serverRevision, 3); assert.equal(revision, 3);
    assert.equal(recovered.state.status, 'saved'); assert.equal(pending.size, 0); recovered.dispose();
});

test('disposal cancels debounce and pending gate polls, aborts active work, and rejects close barriers', async () => {
    const time = clock(), gate = deferred(), calls = [], states = [];
    const saver = createAutosave({ initialKey: null, timers: time.timers, read: () => ({ key: 'new', payload: {} }),
        save: (snapshot, context) => { calls.push(context); return gate.promise; }, onState: state => states.push(state) });
    saver.schedule(); saver.dispose(); await time.tick(1000); assert.equal(calls.length, 0);
    const active = createAutosave({ initialKey: null, timers: time.timers, read: () => ({ key: 'new', payload: {} }),
        save: (snapshot, context) => { calls.push(context); return gate.promise; }, onState: state => states.push(state) });
    const closed = assert.rejects(active.flush(), error => error.name === 'AbortError');
    active.dispose(); await closed; assert.equal(calls[0].signal.aborted, true);
    const count = states.length; gate.resolve('late'); await microtasks(); assert.equal(states.length, count);
    await assert.rejects(active.flush(), error => error.name === 'AbortError'); assert.equal(time.pending, 0);
});
