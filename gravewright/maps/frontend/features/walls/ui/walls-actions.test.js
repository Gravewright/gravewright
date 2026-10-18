import test from 'node:test';
import assert from 'node:assert/strict';
import { wallController } from './walls.js';

const settle = () => new Promise(resolve => setImmediate(resolve));
function fixture(t, state = 'closed', failure = null) {
    const priorWindow = globalThis.window;
    globalThis.window = new EventTarget();
    const wall = { id: 'door', version: 7, kind: 'door', door_state: state,
        blueprint: { version: 2, graphs: { interact: { nodes: [{ id: 'event', type: 'event', event: 'interact' },
            { id: 'message', type: 'showMessage' }], edges: [{ from: 'event', output: 'next', to: 'message', kind: 'execution' }] } } } };
    const calls = [], refreshes = [], changes = [], element = new EventTarget();
    const controller = wallController(element, { props: { state: { walls: [wall] }, containerId: 'campaign', blockId: 'scene' },
        command: async (...args) => { calls.push(args); if (failure) throw failure; return {}; },
        read: async (...args) => { refreshes.push(args); return { walls: [wall] }; },
        emit: (...args) => changes.push(args), repaint() {} });
    t.after(() => { controller.destroy(); globalThis.window = priorWindow; });
    return { wall, calls, refreshes, changes, controller };
}

test('ordinary door gestures remain interaction commands even with a custom generic handler', async t => {
    const f = fixture(t), before = structuredClone(f.wall);
    f.controller.call('operate', f.wall);
    await settle();
    assert.deepEqual(f.calls, [['walls', 'door', { wall_id: 'door', door_state: 'open' }]]);
    assert.deepEqual(f.refreshes, [[]]);
    assert.deepEqual(f.wall, before, 'the server chooses whether the authored interaction changes state');
});

test('explicit GM states use the update CAS contract instead of replaying the custom interaction', async t => {
    const f = fixture(t), before = structuredClone(f.wall);
    for (const state of ['open', 'closed', 'locked']) {
        f.calls.length = 0;
        f.controller.call('setDoorState', f.wall, state);
        await settle();
        assert.deepEqual(f.calls, [['walls', 'update', { wall_id: 'door', version: 7, door_state: state }]]);
        assert.deepEqual(f.wall, before);
    }
});

test('the quick lock shortcut is an explicit GM update while normal clicks retain the gesture channel', async t => {
    const f = fixture(t);
    for (const [current, target] of [['closed', 'locked'], ['locked', 'closed']]) {
        f.wall.door_state = current; f.calls.length = 0;
        f.controller.call('operate', f.wall, true);
        await settle();
        assert.deepEqual(f.calls, [['walls', 'update', { wall_id: 'door', version: 7, door_state: target }]]);
    }
});

test('a conflicting explicit state refreshes once and retains its diagnostic without retrying the write or adopting a newer version', async t => {
    const conflict = Object.assign(new Error('This object changed. Reopen it and try again.'), { code: 'conflict', status: 409 });
    const f = fixture(t, 'closed', conflict);
    f.controller.call('setDoorState', f.wall, 'locked');
    await settle();
    assert.deepEqual(f.calls, [['walls', 'update', { wall_id: 'door', version: 7, door_state: 'locked' }]]);
    assert.deepEqual(f.refreshes, [[]], 'one authoritative read follows the failed command');
    assert.equal(f.changes.length, 1); assert.equal(f.changes[0][0], 'changed');
    assert.equal(f.controller.view.error, conflict.message);
    assert.equal(f.controller.view.busy, false);
    assert.equal(f.wall.version, 7);
    assert.equal(f.wall.door_state, 'closed');
});
