import test from 'node:test';
import assert from 'node:assert/strict';
import { newDocument, clone, normalizeDocument, setDynamicSurface, duplicateSelection, history } from './model.js';

const id = n => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
function fixture() {
    const doc = newDocument();
    doc.floors.push({ id: id(1), layerId: doc.layers[0].id, assetId: null, x: 2, y: 2, width: 2, height: 2, rotation: 0 });
    doc.walls.push({ id: id(2), layerId: doc.layers[0].id, assetId: null, x1: 2, y1: 2, x2: 4, y2: 2, thickness: .2 });
    return doc;
}
test('promotion is optional, reversible in one history step and preserves legacy omission', () => {
    const doc = fixture(), before = clone(doc), stack = history(doc);
    assert.deepEqual(normalizeDocument(doc), before);
    const changed = clone(doc); setDynamicSurface(changed, 'floors', id(1), true); stack.commit(changed);
    assert.equal(changed.floors[0].dynamic, true);
    assert.deepEqual(stack.undo(), before);
    assert.equal(setDynamicSurface(doc, 'walls', id(2), true), true);
    assert.equal(setDynamicSurface(doc, 'walls', id(2), false), true);
    assert.deepEqual(doc, before);
});
test('promotion rejects erasers, unrelated objects and malformed flags', () => {
    const doc = fixture();
    doc.floors[0].brush = { operation: 'erase' };
    assert.equal(setDynamicSurface(doc, 'floors', id(1), true), false);
    assert.equal(setDynamicSurface(doc, 'doors', id(2), true), false);
    for (const dynamic of [null, 1, 'true', []]) {
        const value = fixture(); value.walls[0].dynamic = dynamic;
        assert.throws(() => normalizeDocument(value), /dynamic surface/);
    }
});
test('duplicating promoted targets remaps copied references without changing external targets', () => {
    const doc = fixture(); setDynamicSurface(doc, 'floors', id(1), true);
    doc.doors.push({ id: id(3), layerId: doc.layers[0].id, assetId: null, x1: 8, y1: 8, x2: 9, y2: 8, thickness: .2, state: 'closed',
        blueprint: { graphs: { 'signal:FixtureEnterOpen': { nodes: [{ id: 'target', type: 'reference', targetId: id(1) },
            { id: 'others', type: 'elementGroup', memberType: 'element', targetIds: [id(1), id(2)] }], edges: [] } } } });
    const refs = duplicateSelection(doc, [{ kind: 'floors', id: id(1) }, { kind: 'doors', id: id(3) }], 1, 1);
    const copy = doc.floors.find(row => row.id === refs[0].id), door = doc.doors.find(row => row.id === refs[1].id);
    assert.equal(copy.dynamic, true);
    const nodes = door.blueprint.graphs['signal:FixtureEnterOpen'].nodes;
    assert.equal(nodes[0].targetId, copy.id); assert.deepEqual(nodes[1].targetIds, [copy.id, id(2)]);
});
