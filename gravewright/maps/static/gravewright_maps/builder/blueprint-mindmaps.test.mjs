import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultBlueprint, eventGraph, connectNodes, validateBlueprint, simulateGraph, blueprintContract, dataInputs, nodeOutputs } from './blueprint-model.js';
import { captureTemplate, resolveTemplate, validateTemplateDefinition } from './blueprint-templates.js';
import { sceneNetwork } from './network-model.js';
import { createRunFormatter } from './run-format.js';

const id = value => `00000000-0000-4000-8000-${String(value).padStart(12, '0')}`;
const catalog = { mindmaps: [{ id: id(1), name: 'Authored map', nodes: [{ id: id(2), name: 'Authored topic', completed: false }] },
    { id: id(3), name: 'Other map', nodes: [{ id: id(4), name: 'Other topic', completed: true }] }] };
const topic = (patch = {}) => ({ id: 'topic', type: 'mindMapNode', mindMapId: id(1), nodeId: id(2), action: 'complete', ...patch });
const open = (patch = {}) => ({ id: 'open', type: 'openMindMap', mindMapId: id(1), nodeId: null, audience: { scope: 'trigger' }, ...patch });
function fixture(...actions) {
    const blueprint = defaultBlueprint('lever'), graph = blueprint.graphs.interact = eventGraph('interact');
    graph.nodes.push(...actions.map((action, index) => ({ ...action, x: 320 + index * 300, y: 60 })));
    let previous = 'event';
    for (const action of actions) { connectNodes(graph, previous, 'next', action.id); previous = action.id; }
    return blueprint;
}

test('mind-map nodes have only execution ports and require exact version-two configuration', () => {
    for (const row of [topic(), open(), open({ nodeId: id(2) })]) {
        assert.deepEqual(dataInputs(row), []); assert.deepEqual(nodeOutputs(row), ['next']);
        assert.equal(blueprintContract.nodes[row.type].category, 'action');
        validateBlueprint(fixture(row), catalog);
        const old = fixture(row); old.version = 1;
        assert.throws(() => validateBlueprint(old, catalog), /version/);
    }
    for (const row of [topic({ action: 'set' }), topic({ nodeId: null }), topic({ mindMapId: 'invalid' }),
        open({ nodeId: false }), open({ audience: { scope: 'gm' } }), topic({ player: true })])
        assert.throws(() => validateBlueprint(fixture(row), catalog), /mind-map|audience|node/);
});

test('topic selections must belong to the selected map while portable missing bindings stay repairable', () => {
    validateBlueprint(fixture(topic({ nodeId: id(99) })));
    for (const row of [topic({ nodeId: id(4) }), open({ mindMapId: id(99) }), open({ nodeId: id(4) })])
        assert.throws(() => validateBlueprint(fixture(row), catalog), /Choose a mind map/);
});

test('mind-map previews preserve independent queued effects and authored catalogs', () => {
    const blueprint = fixture(open(), topic(), topic({ id: 'toggle', action: 'toggle' }));
    const before = structuredClone({ blueprint, catalog });
    const first = simulateGraph(blueprint, 'interact', 'off'), second = simulateGraph(blueprint, 'interact', 'off');
    assert.deepEqual(first.actions.map(row => row.type), ['openMindMap', 'mindMapNode', 'mindMapNode']);
    assert.deepEqual(first.trace, ['event', 'open', 'topic', 'toggle']);
    first.actions[1].action = 'reset';
    assert.equal(second.actions[1].action, 'complete');
    assert.deepEqual({ blueprint, catalog }, before);
});

test('templates bind maps and topics separately and reject cross-map topic combinations', () => {
    const blueprint = fixture(open(), topic());
    const template = captureTemplate(blueprint, { catalog });
    validateTemplateDefinition(template);
    assert.deepEqual(template.bindings.map(row => row.type), ['mindmap', 'mindmapTopic']);
    const [map, node] = template.bindings;
    const resolved = resolveTemplate(template, { catalog, bindings: { [map.id]: id(3), [node.id]: id(4) } });
    assert.equal(resolved.graphs.interact.nodes[1].nodeId, null);
    assert.equal(resolved.graphs.interact.nodes[2].mindMapId, id(3));
    assert.equal(resolved.graphs.interact.nodes[2].nodeId, id(4));
    assert.throws(() => resolveTemplate(template, { catalog, bindings: { [map.id]: id(3), [node.id]: id(2) } }), /Choose a mind map/);
});

test('network namespaces preserve map references independently of the owning element UUID', () => {
    const blueprint = fixture(open(), topic());
    const network = sceneNetwork({ ...catalog, elements: [{ id: id(1), kind: 'lever', blueprint }] });
    assert.equal(network.nodes.find(row => row.id === id(1)).editable, true);
    assert.equal(network.nodes.find(row => row.id === `mindmap:${id(1)}`).name, 'Authored map');
    assert.equal(network.edges.filter(row => row.kind === 'mindmap').length, 1);
    assert.deepEqual(network.edges[0].events, ['interact']);
});

test('run summaries describe completion without exposing mind-map notes or linked resources', () => {
    const formatter = createRunFormatter({ t: value => value, elements: () => [] });
    const text = formatter.stepText({ type: 'mindMapNode', action: 'complete', before: false, completed: true,
        mindMapId: id(1), nodeId: id(2), notes: 'PRIVATE SECRET', label: 'PRIVATE LABEL' });
    assert.match(text, /^Control mind-map topic: Complete topic/); assert.match(text, /Open → Completed/);
    assert.equal(text.includes('PRIVATE'), false);
    assert.equal(formatter.stepText({ type: 'openMindMap', mindMapId: id(1) }), 'Open mind map: Mind map');
});
