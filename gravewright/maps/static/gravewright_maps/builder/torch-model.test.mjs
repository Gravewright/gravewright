import test from 'node:test';
import assert from 'node:assert/strict';
import { newDocument, clone, translateSelection, rotateSelection, duplicateSelection, selectionBounds,
    removeObject, updateTorchGeometry, fitsBounds, history } from './model.js';
import { attachTorch, torchChildren, torchOwner, expandTorchSelection, torchComponentState, torchSourcePoint } from './torch-model.js';
import { moveSelectionToLayer, duplicateLayer, mergeLayerDown } from './layer-model.js';
import { detachDocumentAsset } from './asset-removal.js';
import { defaultBlueprint, elementInstanceNode, blueprintAppearance, eventGraph, connectNodes,
    validateBlueprint, simulateGraph } from './blueprint-model.js';
import { nativeEffectState } from './native-effects-model.js';

function fixture() {
    const document = newDocument(), layerId = document.layers[0].id;
    const parent = { id: crypto.randomUUID(), layerId, assetId: crypto.randomUUID(), x: 4, y: 4,
        width: 2, height: 2, rotation: 0, layer: 'over' };
    const light = { id: crypto.randomUUID(), layerId, x: 5, y: 4, brightRadius: 2, dimRadius: 5,
        intensity: 1, enabled: true, rotation: 25, color: '#ff9900', animation: 'torch', angle: 360 };
    const particle = { id: crypto.randomUUID(), layerId, x: 5, y: 4.5, enabled: true, kind: 'ember',
        density: .8, scale: .5, rotation: 0, light_emission: 1 };
    const shader = { id: crypto.randomUUID(), layerId, x: 5, y: 4, enabled: true,
        source: 'gravewright-preset://orb-1/v1', opacity: .6, intensity: .5, radius: 3, rotation: 10 };
    document.decorations.push(parent); document.lights.push(light); document.particles.push(particle); document.shaders.push(shader);
    const config = { lightId: light.id, particleId: particle.id, shaderId: shader.id };
    assert.equal(attachTorch(document, parent.id, config), true);
    return { document, parent, light, particle, shader, layerId, config, ref: { kind: 'decorations', id: parent.id } };
}

test('binding uses the real native components and rejects ownership, layer and type conflicts atomically', () => {
    const { document, parent, light, config } = fixture(), before = clone(document);
    assert.deepEqual(parent.torch, { state: 'off', lit: true, ...config });
    assert.equal(parent.blueprint.kind, 'torch');
    assert.equal(attachTorch(document, parent.id, config), false);
    for (const patch of [{ lit: 'true' }, { state: 'open' }, { lightId: 'missing' }, { surprise: true }]) {
        assert.equal(attachTorch(document, parent.id, { ...config, ...patch }), false);
        assert.deepEqual(document, before);
    }
    const another = { ...clone(parent), id: crypto.randomUUID() }; delete another.torch; delete another.blueprint;
    document.decorations.push(another);
    const staged = clone(document);
    assert.equal(attachTorch(document, another.id, config), false); assert.deepEqual(document, staged);
    light.layerId = crypto.randomUUID();
    assert.equal(attachTorch(document, parent.id, { ...config, lit: false }), false);
    light.layerId = parent.layerId; another.lever = { state: 'off' };
    assert.equal(attachTorch(document, another.id, config), false);
});

test('selection expands the composition once without taking away direct component editing', () => {
    const { document, parent, light, ref } = fixture(), children = torchChildren(document, parent);
    assert.equal(children.length, 3); assert.equal(torchOwner(document, 'lights', light.id), parent);
    assert.deepEqual(expandTorchSelection(document, [ref, ...children, ref]), [ref, ...children]);
    assert.deepEqual(expandTorchSelection(document, [children[0]]), [children[0]]);
    assert.equal(torchOwner(document, 'walls', parent.id), null);
});

test('mechanism and flame projections stay independent and never mutate authored native settings', () => {
    const { document, parent, light } = fixture(); parent.torch.state = 'on'; parent.torch.lit = false;
    const before = clone(document), projected = torchComponentState(document, 'lights', light);
    assert.deepEqual([projected.x, projected.y, projected.rotation, projected.enabled], [6, 5, 115, false]);
    assert.deepEqual(torchSourcePoint(document, 'lights', light.id, projected), { x: light.x, y: light.y });
    const state = nativeEffectState(document).state;
    assert.deepEqual([state.lights.length, state.particles.length, state.shaders.length], [0, 0, 0]);
    assert.deepEqual(document, before);
    parent.torch.lit = true; light.enabled = false;
    assert.equal(torchComponentState(document, 'lights', light).enabled, false);
    assert.equal(nativeEffectState(document).state.particles.length, 1);
    assert.equal(parent.torch.state, 'on'); assert.equal(light.enabled, false);
});

test('moving and rotating a selected torch includes each component exactly once', () => {
    const { document, parent, light, particle, ref } = fixture();
    assert.equal(translateSelection(document, [ref, { kind: 'lights', id: light.id }], 2, 3), true);
    assert.deepEqual([parent.x, parent.y, light.x, light.y, particle.x, particle.y], [6, 7, 7, 7, 7, 7.5]);
    assert.equal(rotateSelection(document, [ref, { kind: 'lights', id: light.id }]), true);
    assert.deepEqual([parent.rotation, light.x, light.y, light.rotation], [90, 8, 8, 115]);
    assert.equal(fitsBounds(document), true);
});

test('component gestures use displayed coordinates when the mechanism is turned', () => {
    const { document, parent, light } = fixture(); parent.torch.state = 'on';
    const parentBefore = clone(parent), ref = { kind: 'lights', id: light.id };
    assert.equal(translateSelection(document, [ref], 1, 2), true);
    assert.deepEqual([light.x, light.y], [7, 3]);
    assert.deepEqual(selectionBounds(document, [ref]), { x: 7, y: 7, width: 0, height: 0 });
    assert.deepEqual(parent, parentBefore);
});

test('effective parent orientation and child locations participate in bounds', () => {
    const { document, parent, light, ref } = fixture();
    parent.width = 4; parent.height = 1; parent.torch.state = 'on';
    light.x = 6; light.y = 4.5;
    const bounds = selectionBounds(document, [ref]);
    assert.equal(bounds.x, 5.5); assert.equal(bounds.y, 2.5);
    assert.equal(bounds.width, 1); assert.equal(bounds.height, 4);
    assert.equal(translateSelection(document, [ref], -100, -100), true);
    assert.equal(fitsBounds(document), true);
    assert.ok(Math.abs(selectionBounds(document, [ref]).y) < 1e-7);
});

test('parent geometry fields transform child offsets atomically while retaining native radii and scale', () => {
    const { document, parent, light, particle } = fixture();
    assert.equal(updateTorchGeometry(document, parent.id, { x: 9, y: 8, width: 4, rotation: 90 }), true);
    assert.deepEqual([parent.x, parent.y, parent.width, parent.rotation], [9, 8, 4, 90]);
    assert.deepEqual([light.x, light.y, light.rotation, light.brightRadius, light.dimRadius], [12, 9, 115, 2, 5]);
    assert.equal(particle.scale, .5);
    const before = clone(document);
    for (const patch of [{ x: -100 }, { width: 0 }, { rotation: NaN }, { layerId: 'other' }, { x: parent.x }]) {
        assert.equal(updateTorchGeometry(document, parent.id, patch), false); assert.deepEqual(document, before);
    }
});

test('duplication copies all native children and remaps internal Blueprint references independently', () => {
    const { document, parent, light, ref } = fixture(), graph = eventGraph('signal:FixtureEnterOn');
    graph.nodes.push({ id: 'self', type: 'reference', targetId: parent.id, x: 200, y: 0 },
        { id: 'lamp', type: 'light', targetId: light.id, enabled: true, x: 400, y: 0 },
        { id: 'external', type: 'reference', targetId: crypto.randomUUID(), x: 200, y: 300 });
    parent.blueprint.graphs['signal:FixtureEnterOn'] = graph;
    const before = clone(document), refs = duplicateSelection(document, [ref, { kind: 'lights', id: light.id }], 2, 3);
    assert.equal(refs.length, 1); assert.equal(refs[0].kind, 'decorations');
    const copy = document.decorations[1], children = torchChildren(document, copy);
    assert.equal(children.length, 3); assert.notEqual(copy.torch.lightId, parent.torch.lightId);
    assert.deepEqual(copy.blueprint.graphs['signal:FixtureEnterOn'].nodes.slice(1).map(node => node.targetId),
        [copy.id, copy.torch.lightId, graph.nodes[3].targetId]);
    assert.deepEqual(document.decorations[0], before.decorations[0]); assert.deepEqual(document.lights[0], before.lights[0]);
    assert.deepEqual([document.lights[1].x, document.lights[1].y], [7, 7]);
    copy.torch.lit = false; copy.blueprint.states.on.appearance = 'hidden';
    assert.deepEqual(document.decorations[0], before.decorations[0]);
});

test('layer transfer follows ownership and layer duplication keeps a self-contained copy', () => {
    const { document, parent, light, ref } = fixture(), layer = { id: crypto.randomUUID(), name: 'Upper', visible: true, locked: false };
    document.layers.push(layer);
    assert.equal(moveSelectionToLayer(document, [{ kind: 'lights', id: light.id }], layer.id), true);
    for (const { kind, id } of [ref, ...torchChildren(document, parent)]) assert.equal(document[kind].find(row => row.id === id).layerId, layer.id);
    const copy = duplicateLayer(document, layer.id, 'Copy'); assert.equal(copy.refs.length, 4);
    const copied = document.decorations.find(row => row.layerId === copy.layerId);
    assert.ok(copied); assert.notEqual(copied.torch.lightId, parent.torch.lightId);
    assert.equal(document.lights.find(row => row.id === copied.torch.lightId).layerId, copy.layerId);
    assert.ok(mergeLayerDown(document, copy.layerId));
    assert.equal(document.lights.find(row => row.id === copied.torch.lightId).layerId, layer.id);
});

test('protected layers reject composed geometry and transfers without partial mutations', () => {
    const { document, parent, ref } = fixture(); document.layers[0].locked = true;
    const before = clone(document);
    assert.equal(translateSelection(document, [ref], 1, 1), false);
    assert.equal(updateTorchGeometry(document, parent.id, { rotation: 90 }), false);
    assert.deepEqual(duplicateSelection(document, [ref]), []); assert.deepEqual(document, before);
});

test('deleting a parent cascades components and bridges other Blueprint light actions', () => {
    const { document, parent, light, ref } = fixture(), other = clone(parent);
    other.id = crypto.randomUUID(); delete other.torch; other.lever = { state: 'off' }; other.blueprint = defaultBlueprint('lever');
    const graph = eventGraph('signal:FixtureEnterOn');
    graph.nodes.push({ id: 'lamp', type: 'light', targetId: light.id, enabled: false, x: 200, y: 0 },
        { id: 'next', type: 'state', targetState: 'on', x: 400, y: 0 });
    connectNodes(graph, 'event', 'next', 'lamp', { version: 2 }); connectNodes(graph, 'lamp', 'next', 'next', { version: 2 });
    other.blueprint.graphs['signal:FixtureEnterOn'] = graph; document.decorations.push(other);
    removeObject(document, ref.kind, ref.id);
    assert.equal(document.decorations.length, 1);
    assert.deepEqual([document.lights.length, document.particles.length, document.shaders.length], [0, 0, 0]);
    assert.deepEqual(other.blueprint.graphs['signal:FixtureEnterOn'].nodes.map(row => row.id), ['event', 'next']);
    assert.deepEqual(other.blueprint.graphs['signal:FixtureEnterOn'].edges, [{ from: 'event', output: 'next', to: 'next', kind: 'execution' }]);
});

test('optional component deletion detaches only its reference while mandatory light deletion dissolves the torch', () => {
    const { document, parent, light, particle, shader } = fixture();
    removeObject(document, 'particles', particle.id); assert.equal(parent.torch.particleId, undefined);
    assert.equal(document.shaders.length, 1); assert.equal(parent.torch.lightId, light.id);
    const geometry = clone(parent); delete geometry.torch; delete geometry.blueprint;
    removeObject(document, 'lights', light.id);
    assert.deepEqual(parent, geometry); assert.equal(document.decorations.length, 1);
    assert.equal(document.shaders.some(row => row.id === shader.id), false);
});

test('permanent image removal dissolves the composition and history cannot resurrect its components', () => {
    const { document, parent, light, particle, shader } = fixture(), stack = history(document);
    translateSelection(document, [{ kind: 'decorations', id: parent.id }], 1, 0); stack.commit(document);
    const cleaned = detachDocumentAsset(document, parent.assetId);
    assert.equal(cleaned.decorations[0].assetId, null); assert.equal(cleaned.decorations[0].torch, undefined);
    assert.equal(cleaned.decorations[0].blueprint, undefined);
    for (const [kind, id] of [['lights', light.id], ['particles', particle.id], ['shaders', shader.id]]) {
        assert.equal(cleaned[kind].some(row => row.id === id), false);
    }
    stack.rebase(value => detachDocumentAsset(value, parent.assetId));
    assert.equal(stack.undo().decorations[0].torch, undefined);
    assert.equal(document.decorations[0].torch.lightId, light.id, 'reconciliation never changes another private draft');
});

test('torch Blueprint ports describe events and flame actions keep their independent meaning', () => {
    const { parent } = fixture(), before = clone(parent), instance = elementInstanceNode(parent);
    assert.equal(instance.type, 'torch'); assert.equal(instance.state, 'off');
    assert.deepEqual(instance.outputs.map(port => port.label), ['On interaction', 'On area enter', 'On area exit', 'On destroy']);
    const blueprint = defaultBlueprint('torch'), graph = eventGraph('signal:FixtureInteractOff');
    graph.nodes.push({ id: 'turn', type: 'state', targetState: 'on', x: 200, y: 0 },
        { id: 'flame', type: 'flame', enabled: false, x: 400, y: 0 });
    connectNodes(graph, 'event', 'next', 'turn', { version: 2 }); connectNodes(graph, 'turn', 'next', 'flame', { version: 2 });
    blueprint.graphs['signal:FixtureInteractOff'] = graph;
    assert.equal(validateBlueprint(blueprint), blueprint);
    assert.deepEqual(simulateGraph(blueprint, 'signal:FixtureInteractOff', 'off').actions.map(row => row.type), ['state', 'flame']);
    assert.deepEqual(parent, before);
    assert.deepEqual(blueprintAppearance({ ...parent, torch: { ...parent.torch, state: 'on', lit: false } }), { visible: true, assetId: parent.assetId });
    graph.nodes[2].enabled = 'false'; assert.throws(() => validateBlueprint(blueprint), /Invalid blueprint node/);
});

test('a typed flame target can reference a torch from a door graph without introducing another state store', () => {
    const { parent } = fixture(), blueprint = defaultBlueprint(); blueprint.version = 2;
    const graph = eventGraph('signal:FixtureEnterOpen');
    graph.nodes.push({ id: 'torch', type: 'reference', targetId: parent.id, x: 200, y: 200 },
        { id: 'flame', type: 'flame', enabled: false, x: 400, y: 0 });
    connectNodes(graph, 'event', 'next', 'flame', { version: 2 });
    connectNodes(graph, 'torch', 'door', 'flame', { version: 2, input: 'target' });
    blueprint.graphs['signal:FixtureEnterOpen'] = graph; validateBlueprint(blueprint);
    assert.equal(simulateGraph(blueprint, 'signal:FixtureEnterOpen', 'open').actions[0].target, parent.id);
    blueprint.version = 1; assert.throws(() => validateBlueprint(blueprint), /Unsupported/);
});

test('hidden state appearances suppress composed native emission without changing authored enabled flags', () => {
    const { document, parent, light } = fixture(); parent.blueprint.states.off.appearance = 'hidden';
    const before = clone(document), projected = nativeEffectState(document).state;
    assert.deepEqual([projected.lights.length, projected.particles.length, projected.shaders.length], [0, 0, 0]);
    assert.equal(light.enabled, true); assert.deepEqual(document, before);
});

test('dissolving a turned torch preserves its displayed orientation after light or image removal', () => {
    for (const operation of ['light', 'asset']) {
        const { document, parent, light } = fixture(); parent.rotation = 25; parent.torch.state = 'on';
        const result = operation === 'asset' ? detachDocumentAsset(document, parent.assetId)
            : (removeObject(document, 'lights', light.id), document);
        assert.equal(result.decorations[0].rotation, 115); assert.equal(result.decorations[0].torch, undefined);
    }
});

test('copying a component independently preserves its visible position and enabled state', () => {
    const { document, parent, light } = fixture(); parent.torch.state = 'on'; parent.torch.lit = false;
    const before = clone(light), refs = duplicateSelection(document, [{ kind: 'lights', id: light.id }], 1, 2);
    assert.equal(refs.length, 1);
    const copy = document.lights.find(row => row.id === refs[0].id);
    assert.deepEqual([copy.x, copy.y, copy.rotation, copy.enabled], [7, 7, 115, false]);
    assert.equal(torchOwner(document, 'lights', copy.id), null); assert.deepEqual(light, before);
});
