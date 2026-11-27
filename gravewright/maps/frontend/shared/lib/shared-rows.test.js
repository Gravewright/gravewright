import test from 'node:test';
import assert from 'node:assert/strict';
import {applyRowChanges, changedRows, createSharedRows} from './shared-rows.js';

const row = (id, text = '', version = 1, canEdit = true) => ({id, text, version, canEdit});

test('gesture changes name only the rows they touched, for undo and redo', () => {
    const before = [row('a'), row('b'), row('gone')];
    const after = [row('a', 'moved'), row('b'), row('new')];
    const {undo, redo} = changedRows(before, after);
    assert.deepEqual(new Map(redo), new Map([['a', row('a', 'moved')], ['new', row('new')], ['gone', null]]));
    assert.deepEqual(new Map(undo), new Map([['a', row('a')], ['new', null], ['gone', row('gone')]]));
    assert.deepEqual(applyRowChanges([row('x'), row('a'), row('gone')], redo),
        [row('x'), row('a', 'moved'), row('new')]);
});

test('applied gestures keep peer rows that arrived after the gesture started', async () => {
    let displayed;
    const writes = [];
    const model = createSharedRows({initial: [row('mine'), row('peer', '', 1, false)], delay: 10000,
        save: async patch => {writes.push(patch); return {rows: [row('mine', 'moved', 2), row('peer', 'peer edit', 2, false), row('late', '', 1, false)], version: 3};},
        render: rows => {displayed = rows;}, error: assert.fail, refresh: assert.fail});
    // The gesture began from a snapshot that predates the peer's edit.
    const gesture = changedRows([row('mine'), row('peer', '', 1, false)], [row('mine', 'moved'), row('peer', '', 1, false)]);
    model.update([row('mine'), row('peer', 'peer edit', 2, false), row('late', '', 1, false)], 2);
    model.apply(gesture.redo);
    assert.equal(displayed.find(value => value.id === 'peer').text, 'peer edit');
    await model.flush();
    assert.deepEqual(writes, [{upserts: [{id: 'mine', text: 'moved', expected_version: 1}], removed: []}]);
    assert.deepEqual(displayed.map(value => value.id), ['mine', 'peer', 'late']);
    model.destroy();
});

test('undoing an addition removes it, and undoing a removal recreates it', async () => {
    const writes = [];
    let rows = [row('a')], version = 1;
    const model = createSharedRows({initial: rows, delay: 10000,
        save: async patch => {
            writes.push(patch);
            const removed = new Set(patch.removed.map(value => value.id));
            const upserts = new Map(patch.upserts.map(({expected_version, ...value}) => [value.id, value]));
            rows = [...rows.filter(value => !removed.has(value.id) && !upserts.has(value.id)),
                ...[...upserts.values()].map(value => ({...value, version: (rows.find(r => r.id === value.id)?.version ?? 0) + 1, canEdit: true}))];
            return {rows, version: ++version};
        },
        render: () => {}, error: assert.fail, refresh: assert.fail});
    const added = changedRows([row('a')], [row('a'), row('b')]);
    model.apply(added.redo); await model.flush();
    model.apply(added.undo); await model.flush();
    const removed = changedRows([row('a')], []);
    model.apply(removed.redo); await model.flush();
    model.apply(removed.undo); await model.flush();
    assert.deepEqual(writes, [
        {upserts: [{id: 'b', text: '', expected_version: null}], removed: []},
        {upserts: [], removed: [{id: 'b', expected_version: 1}]},
        {upserts: [], removed: [{id: 'a', expected_version: 1}]},
        {upserts: [{id: 'a', text: '', expected_version: null}], removed: []},
    ]);
    model.destroy();
});

test('a rejected gesture restores confirmed rows and reports once', async () => {
    let displayed;
    const failures = [];
    const model = createSharedRows({initial: [row('a')], delay: 10000,
        save: async () => {throw Error('forbidden');},
        refresh: async () => ({rows: [row('a', 'server', 2)], version: 4}),
        render: rows => {displayed = rows;}, error: reason => failures.push(reason.message)});
    model.apply([['a', row('a', 'local')]]);
    assert.equal(displayed[0].text, 'local');
    await model.flush();
    assert.deepEqual(failures, ['forbidden']);
    assert.equal(displayed[0].text, 'server');
    model.destroy();
});
