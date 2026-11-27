import test from 'node:test';
import assert from 'node:assert/strict';
import {createSharedMeasurements, measurementChanges} from './shared-measurements.js';

const row = (id, title = '', version = 1) => ({id, title, version, canEdit: true});
test('patches include only authored differences and preserve original revisions', () => {
    assert.deepEqual(measurementChanges([row('a'), row('b')], [row('a', 'new'), row('c')]), {
        upserts: [{id: 'a', title: 'new', expected_version: 1}, {id: 'c', title: '', expected_version: null}],
        removed: [{id: 'b', expected_version: 1}],
    });
    assert.deepEqual(measurementChanges([row('a')], [{...row('a', '', 9), canEdit: false}]), {upserts: [], removed: []});
    assert.deepEqual(measurementChanges([row('a')], [{title: '', id: 'a', version: 1}]), {upserts: [], removed: []});
});
test('edits during a save follow only the acknowledged revisions and retain peer rows', async () => {
    let resolve, displayed, writes = [];
    const model = createSharedMeasurements({initial: [row('a')], delay: 10000,
        save: patch => {writes.push(patch); return new Promise(done => {resolve = done;});},
        render: rows => {displayed = rows;}, error: assert.fail, refresh: assert.fail});
    model.edit([row('a', 'first')]); const first = model.flush();
    model.edit([row('a', 'second')]);
    model.update([row('a', 'first', 2), row('peer')], 3);
    resolve({markers: [row('a', 'first', 2)], version: 2}); await first;
    assert.equal(displayed.find(value => value.id === 'a').title, 'second');
    assert.equal(displayed.find(value => value.id === 'peer').title, '');
    const second = model.flush();
    assert.equal(writes[1].upserts[0].expected_version, 2);
    resolve({markers: [row('a', 'second', 3), row('peer')]}); await second;
    model.destroy();
});
test('conflicts discard pending changes, refresh, and never force a new write', async () => {
    let displayed, failures = [], count = 0;
    const model = createSharedMeasurements({initial: [row('a')], delay: 10000,
        save: async () => {count++; throw Error('conflict');},
        refresh: async () => ({markers: [row('a', 'peer edit', 2)]}),
        render: rows => {displayed = rows;}, error: e => failures.push(e.message)});
    model.edit([row('a', 'local')]); await model.flush(); await model.flush();
    assert.equal(count, 1); assert.deepEqual(failures, ['conflict']);
    assert.equal(displayed[0].title, 'peer edit'); model.destroy();
});
test('late acknowledgements cannot update a closed scene', async () => {
    let resolve, paints = 0;
    const model = createSharedMeasurements({save: () => new Promise(done => {resolve = done;}),
        render: () => {paints++;}, error: assert.fail, refresh: assert.fail});
    model.edit([row('new')]); const saving = model.flush(); model.destroy();
    resolve({markers: [row('new')]}); await saving; assert.equal(paints, 0);
});

test('a newer snapshot arriving before an old acknowledgement retains peer additions and removals', async () => {
    let resolve, displayed, writes = 0;
    const model = createSharedMeasurements({initial: [row('a'), row('removed')], delay: 10000,
        save: () => {writes++; return new Promise(done => {resolve = done;});},
        render: rows => {displayed = rows;}, error: assert.fail, refresh: assert.fail});
    model.edit([row('a', 'local'), row('removed')]); const saving = model.flush();
    model.update([row('a', 'newer remote', 3), row('added')], 12);
    model.update([row('a', 'local', 2), row('removed')], 11);
    resolve({markers: [row('a', 'local', 2), row('removed')], version: 11}); await saving;
    assert.deepEqual(displayed, [row('a', 'newer remote', 3), row('added')]);
    await model.flush(); assert.equal(writes, 1); model.destroy();
});

test('a snapshot older than the accepted operation cannot roll back its acknowledgement', async () => {
    let resolve, displayed;
    const model = createSharedMeasurements({initial: [row('a')], delay: 10000,
        save: () => new Promise(done => {resolve = done;}),
        render: rows => {displayed = rows;}, error: assert.fail, refresh: assert.fail});
    model.edit([row('a', 'local')]); const saving = model.flush();
    model.update([row('a')], 3);
    resolve({markers: [row('a', 'local', 2)], version: 4}); await saving;
    assert.deepEqual(displayed, [row('a', 'local', 2)]); model.destroy();
});

test('remote changes merge around unsaved edits without advancing their expected revisions', async () => {
    let displayed, patch;
    const model = createSharedMeasurements({initial: [row('a'), row('peer'), row('gone')], delay: 10000,
        save: async value => {patch = value; throw Error('conflict');},
        refresh: async () => ({markers: [row('a', 'remote', 2), row('peer', 'updated', 2), row('added')]}),
        render: rows => {displayed = rows;}, error: () => {}});
    model.edit([row('a', 'draft'), row('peer'), row('gone')]);
    model.update([row('a', 'remote', 2), row('peer', 'updated', 2), row('added')], 5);
    assert.deepEqual(new Map(displayed.map(value => [value.id, value])), new Map([
        ['a', row('a', 'draft')], ['peer', row('peer', 'updated', 2)], ['added', row('added')],
    ]));
    await model.flush();
    assert.deepEqual(patch, {upserts: [{id: 'a', title: 'draft', expected_version: 1}], removed: []});
    assert.equal(displayed.find(value => value.id === 'a').title, 'remote'); model.destroy();
});

test('edits made while conflict recovery reads the scene survive that refresh', async () => {
    let resolveRefresh, startedRefresh, displayed;
    const refreshing = new Promise(done => {startedRefresh = done;});
    const writes = [];
    const model = createSharedMeasurements({initial: [row('a'), row('b')], delay: 10000,
        save: async patch => {
            writes.push(patch);
            if (writes.length === 1) throw Error('conflict');
            return {markers: [row('a', 'remote', 2), row('b', 'new edit', 2), row('peer')], version: 4};
        },
        refresh: () => {startedRefresh(); return new Promise(done => {resolveRefresh = done;});},
        render: rows => {displayed = rows;}, error: () => {}});
    model.edit([row('a', 'conflicting'), row('b')]); const first = model.flush();
    await refreshing;
    model.edit([row('a'), row('b', 'new edit')]);
    resolveRefresh({markers: [row('a', 'remote', 2), row('b'), row('peer')], version: 3}); await first;
    assert.equal(displayed.find(value => value.id === 'a').title, 'remote');
    assert.equal(displayed.find(value => value.id === 'b').title, 'new edit');
    assert.ok(displayed.some(value => value.id === 'peer'));
    await model.flush();
    assert.deepEqual(writes[1], {upserts: [{id: 'b', title: 'new edit', expected_version: 1}], removed: []});
    model.destroy();
});

test('closing before the debounce fires saves the final edit without painting the closed scene', async () => {
    let resolve, paints = 0;
    const writes = [];
    const model = createSharedMeasurements({initial: [row('a')], delay: 10000,
        save: patch => {writes.push(patch); return new Promise(done => {resolve = done;});},
        render: () => {paints++;}, error: assert.fail, refresh: assert.fail});
    model.edit([row('a', 'final')]); model.destroy();
    assert.deepEqual(writes, [{upserts: [{id: 'a', title: 'final', expected_version: 1}], removed: []}]);
    model.edit([row('a', 'ignored')]); model.update([row('a', 'ignored')], 9);
    resolve({markers: [row('a', 'final', 2)], version: 2}); await Promise.resolve();
    await model.flush(); assert.equal(writes.length, 1); assert.equal(paints, 0);
});

test('closing during a save drains the queued edit using its accepted revision without painting', async () => {
    let paints = 0;
    const writes = [], replies = [];
    const model = createSharedMeasurements({initial: [row('a')], delay: 10000,
        save: patch => {writes.push(patch); return new Promise(done => {replies.push(done);});},
        render: () => {paints++;}, error: assert.fail, refresh: assert.fail});
    model.edit([row('a', 'first')]); const first = model.flush();
    model.edit([row('a', 'last')]); model.destroy();
    assert.equal(writes.length, 1);
    replies[0]({markers: [row('a', 'first', 2)], version: 2}); await first;
    assert.deepEqual(writes[1], {upserts: [{id: 'a', title: 'last', expected_version: 2}], removed: []});
    replies[1]({markers: [row('a', 'last', 3)], version: 3}); await Promise.resolve();
    await model.flush(); assert.equal(writes.length, 2); assert.equal(paints, 0);
});
