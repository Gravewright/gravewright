import test from 'node:test';
import assert from 'node:assert/strict';
import { newMindmapDocument, addMindmapNode, removeMindmapNode, reparentMindmapNode, visibleMindmapNodes,
  createMindmapHistory, fitMindmap, zoomMindmap, createMindmapCommands } from '../../gravewright/table/static/gravewright_table/mindmap-model.js';

test('topic hierarchy supports roots, children and siblings without mutating the saved document', () => {
  const original = newMindmapDocument('Authored root', 'root');
  let value = addMindmapNode(original, 'root', 'Child', { id: 'child' });
  value = addMindmapNode(value, null, 'Sibling', { siblingId: 'child', id: 'sibling' });
  value = addMindmapNode(value, null, 'Another root', { id: 'another' });
  assert.deepEqual(value.nodes.map(node => [node.id, node.parentId]), [['root', null], ['child', 'root'], ['sibling', 'root'], ['another', null]]);
  assert.equal(original.nodes.length, 1); assert.equal(value.nodes[1].completed, false);
  assert.ok(value.nodes[2].y > value.nodes[1].y); assert.ok(value.nodes[1].x > value.nodes[0].x);
  for (const node of value.nodes) assert.equal(value.nodes.some(other => node.id !== other.id && node.x === other.x && node.y === other.y), false);
});

test('collapsed branches stay hidden and adding a child expands its parent', () => {
  let value = addMindmapNode(newMindmapDocument('Root', 'r'), 'r', 'Child', { id: 'c' });
  value.nodes[0].collapsed = true;
  assert.deepEqual(visibleMindmapNodes(value).map(node => node.id), ['r']);
  value = addMindmapNode(value, 'r', 'Next', { id: 'n' });
  assert.deepEqual(visibleMindmapNodes(value).map(node => node.id), ['r', 'c', 'n']);
});

test('subtree deletion removes crossing connections and reparenting rejects cycles', () => {
  let value = addMindmapNode(newMindmapDocument('Root', 'r'), 'r', 'Child', { id: 'c' });
  value = addMindmapNode(value, 'c', 'Grandchild', { id: 'g' });
  value.edges.push({ id: 'edge', from: 'r', to: 'g', label: 'Related' });
  assert.throws(() => reparentMindmapNode(value, 'r', 'g'), /descendant/);
  assert.throws(() => reparentMindmapNode(value, 'c', 'missing'), /existing/);
  assert.equal(reparentMindmapNode(value, 'g', null).nodes[2].parentId, null);
  assert.deepEqual(removeMindmapNode(value, 'c').nodes.map(node => node.id), ['r']);
  assert.deepEqual(removeMindmapNode(value, 'c').edges, []); assert.equal(value.nodes.length, 3);
});

test('bounded history restores data including opaque references and truncates redo after a new edit', () => {
  const initial = newMindmapDocument('Root', 'r'); initial.nodes[0].links = [{ unavailable: true, key: 'opaque' }];
  const history = createMindmapHistory(initial, 2);
  let candidate = history.value; candidate.nodes[0].label = 'One'; history.change(candidate);
  candidate.nodes[0].label = 'Two'; history.change(candidate); candidate.nodes[0].label = 'Three'; history.change(candidate);
  assert.equal(history.dirty, true); history.undo(); assert.equal(history.value.nodes[0].label, 'Two');
  history.undo(); assert.equal(history.value.nodes[0].label, 'One'); assert.equal(history.canUndo, false);
  assert.deepEqual(history.value.nodes[0].links, [{ unavailable: true, key: 'opaque' }]);
  candidate = history.value; candidate.nodes[0].notes = 'New branch'; history.change(candidate); assert.equal(history.canRedo, false);
  history.reset(initial); assert.equal(history.dirty, false); assert.equal(history.canUndo, false);
});

test('fitting and cursor-centered zoom remain bounded and preserve the world point beneath the cursor', () => {
  const nodes = newMindmapDocument('Root').nodes, view = fitMindmap(nodes, 800, 600);
  const point = { x: 200, y: 180 }, next = zoomMindmap(view, 1.4, point);
  assert.ok(Math.abs((point.x - view.x) / view.scale - (point.x - next.x) / next.scale) < .0001);
  assert.ok(Math.abs((point.y - view.y) / view.scale - (point.y - next.y) / next.scale) < .0001);
  assert.equal(zoomMindmap(view, 1e6, point).scale, 3); assert.equal(zoomMindmap(view, .000001, point).scale, .15);
  assert.ok(Number.isFinite(fitMindmap([], 320, 200).x));
});

test('uncertain save retries retain one UUID until canonical acknowledgement; changed candidates and conflicts get new UUIDs', async () => {
  const scope = new AbortController(), calls = []; let failure;
  const commands = createMindmapCommands({ signal: scope.signal, api: { mindmaps: { async update(payload, options) {
    calls.push([payload, options.requestId]); if (failure) throw failure; return { id: payload.id };
  } } } });
  const candidate = { id: 'map', version: 3, name: 'Draft' }; failure = Error('Lost response');
  await assert.rejects(commands.run('update', candidate)); failure = null;
  await commands.run('update', candidate); await commands.run('update', candidate);
  assert.equal(calls[0][1], calls[1][1]); assert.equal(calls[1][1], calls[2][1]);
  commands.acknowledge('map'); await commands.run('update', candidate); assert.notEqual(calls[2][1], calls[3][1]);
  failure = Object.assign(Error('Conflict'), { code: 'conflict' }); await assert.rejects(commands.run('update', candidate));
  failure = null; await commands.run('update', candidate); assert.notEqual(calls[4][1], calls[5][1]);
  await commands.run('update', { ...candidate, name: 'Another draft' }); assert.notEqual(calls[5][1], calls[6][1]);
  scope.abort(); await assert.rejects(commands.run('update', candidate)); assert.equal(calls.length, 7);
});
