import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultBlueprint, upgradeBlueprint, eventGraph, connectNodes } from './blueprint-model.js';
import { captureTemplate, resolveTemplate, validateTemplateDefinition, templateParameterOptions } from './blueprint-templates.js';

const id = number => `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`;
const event = 'signal:FixtureInteractClosed';
const catalog = { assets: [{ id: id(10) }, { id: id(11) }], elements: [{ id: id(2) }, { id: id(3) }],
    lights: [{ id: id(20) }, { id: id(21) }], sounds: [{ id: id(30) }, { id: id(31) }], users: [{ id: id(40) }], handouts: [{ id: id(50) }] };
function fixture() {
    const blueprint = upgradeBlueprint(defaultBlueprint()), graph = eventGraph(event);
    blueprint.graphs[event] = graph;
    graph.nodes.push(...[
        { id: 'ref', type: 'reference', targetId: id(1) },
        { id: 'group', type: 'elementGroup', name: id(1), memberType: 'element', targetIds: [id(1), id(2)] },
        { id: 'light', type: 'light', targetId: id(20), enabled: false },
        { id: 'delay', type: 'delay', seconds: 3 },
        { id: 'variable', type: 'setVariable', scope: 'element', name: 'value', valueType: 'text', value: id(1) },
        { id: 'message', type: 'showMessage', text: id(2), audience: { scope: 'users', userIds: [id(40)] } },
        { id: 'handout', type: 'showHandout', journalId: id(50), audience: { scope: 'trigger' } },
        { id: 'teleport', type: 'teleport', destinationId: id(3) },
        { id: 'sprite', type: 'setAppearance', assetId: id(10) },
    ].map((row, index) => ({ x: 200 + index * 300, y: 50, ...row })));
    connectNodes(graph, 'event', 'next', 'light', { version: 2 });
    connectNodes(graph, 'light', 'next', 'delay', { version: 2 });
    return blueprint;
}
const bindingsFor = (definition, light = id(20)) => Object.fromEntries(definition.bindings.filter(row => !row.self).map(row => [row.id,
    row.type === 'light' ? light : row.type === 'user' ? id(40) : row.type === 'handout' ? id(50) : row.type === 'asset' ? id(10)
        : row.id === definition.bindings.find(binding => !binding.self && binding.type === 'element').id ? id(2) : id(3)]));

test('capture replaces every typed resource, reuses shared slots and preserves authored UUID-like strings', () => {
    const blueprint = fixture(), original = structuredClone(blueprint), definition = captureTemplate(blueprint, { ownerId: id(1), catalog });
    const nodes = definition.blueprint.graphs[event].nodes;
    assert.equal(definition.bindings[0].self, true);
    assert.deepEqual(nodes[1].targetId, nodes[2].targetIds[0]);
    assert.equal(nodes[2].name, id(1)); assert.equal(nodes[5].value, id(1)); assert.equal(nodes[6].text, id(2));
    assert.deepEqual(nodes[6].audience.userIds, [{ binding: definition.bindings.find(row => row.type === 'user').id }]);
    assert.equal(definition.bindings.some(row => Object.hasOwn(row, 'targetId')), false);
    assert.deepEqual(blueprint, original);
    assert.deepEqual(validateTemplateDefinition(definition), definition);
});

test('two independent instances bind their own Self, lights and scalar parameters', () => {
    const blueprint = fixture(), options = templateParameterOptions(blueprint), expose = options.filter(row => row.path.at(-1) === 'seconds');
    const definition = captureTemplate(blueprint, { ownerId: id(1), catalog, expose }), original = structuredClone(definition);
    const first = resolveTemplate(definition, { ownerId: id(100), catalog, bindings: bindingsFor(definition), parameters: { [definition.parameters[0].id]: 9 } });
    const second = resolveTemplate(definition, { ownerId: id(101), catalog, bindings: bindingsFor(definition, id(21)) });
    assert.equal(first.graphs[event].nodes[1].targetId, id(100)); assert.equal(second.graphs[event].nodes[1].targetId, id(101));
    assert.equal(first.graphs[event].nodes[3].targetId, id(20)); assert.equal(second.graphs[event].nodes[3].targetId, id(21));
    assert.equal(first.graphs[event].nodes[4].seconds, 9); assert.equal(second.graphs[event].nodes[4].seconds, 3);
    first.graphs[event].nodes[2].targetIds.reverse(); first.graphs[event].nodes[6].audience.userIds.reverse();
    assert.deepEqual(definition, original);
    assert.deepEqual(second.graphs[event].nodes[2].targetIds, [id(101), id(2)]);
});

test('missing, stale, extra or incorrectly typed bindings cannot become implicit Self', () => {
    const definition = captureTemplate(fixture(), { ownerId: id(1), catalog }), bindings = bindingsFor(definition);
    const light = definition.bindings.find(row => row.type === 'light').id;
    for (const values of [{}, { ...bindings, extra: id(9) }, { ...bindings, [light]: id(999) }, { ...bindings, [light]: 1 }])
        assert.throws(() => resolveTemplate(definition, { ownerId: id(100), catalog, bindings: values }), /binding|resource/);
    assert.throws(() => resolveTemplate(definition, { catalog, bindings }), /binding/);
});

test('definitions reject literal IDs, unused bindings and injected scalar topology paths', () => {
    const original = captureTemplate(fixture(), { ownerId: id(1), catalog });
    const edits = [row => { row.blueprint.graphs[event].nodes[1].targetId = id(1); },
        row => { row.bindings[0].type = 'light'; }, row => { row.bindings[0].self = false; },
        row => row.bindings.push({ id: 'extra', type: 'asset', label: 'Unused' }),
        row => row.parameters.push({ id: 'parameter', label: 'Bad', path: ['graphs', event, 'nodes', 1, 'targetId'], type: 'text', default: id(1) })];
    for (const edit of edits) { const definition = structuredClone(original); edit(definition); assert.throws(() => validateTemplateDefinition(definition), /template/); }
});

test('parameters are opt-in typed scalars and whole-graph constraints still apply', () => {
    const blueprint = fixture(), options = templateParameterOptions(blueprint), duration = options.find(row => row.path.at(-1) === 'seconds');
    assert.equal(options.some(row => ['id', 'type', 'x', 'scope', 'targetId', 'name'].includes(row.path.at(-1))), false);
    assert.deepEqual(captureTemplate(blueprint, { ownerId: id(1), catalog }).parameters, []);
    const definition = captureTemplate(blueprint, { ownerId: id(1), catalog, expose: [duration] }), bindings = bindingsFor(definition);
    for (const value of [true, '1', 0, 86401, NaN]) assert.throws(() => resolveTemplate(definition, { ownerId: id(100), catalog, bindings,
        parameters: { [definition.parameters[0].id]: value } }), /parameter|control/);
    const wrong = structuredClone(definition); wrong.parameters[0].default = 7;
    assert.throws(() => validateTemplateDefinition(wrong), /parameter/);
});

test('new templates use the current format and all-zero configured Random weights are rejected', () => {
    const empty = captureTemplate(defaultBlueprint(), { ownerId: id(1) });
    assert.equal(resolveTemplate(empty, { ownerId: id(2) }).version, 2);
    const blueprint = upgradeBlueprint(defaultBlueprint()), graph = eventGraph(event); blueprint.graphs[event] = graph;
    graph.nodes.push({ id: 'choice', type: 'random', weights: [1, 0], x: 100, y: 100 });
    const definition = captureTemplate(blueprint, { expose: templateParameterOptions(blueprint) });
    assert.throws(() => resolveTemplate(definition, { ownerId: id(2), parameters: { parameter1: 0, parameter2: 0 } }), /weights/);
});
