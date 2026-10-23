import test from 'node:test';
import assert from 'node:assert/strict';
import { createCanvasRenderer } from './canvas-renderer.js';
import { newDocument, objectKinds } from './model.js';

class SvgNode {
    constructor(tag) { this.tagName = tag; this.attributes = new Map(); this.children = []; this.dataset = {}; this.style = {}; }
    setAttribute(key, value) { this.attributes.set(key, String(value)); }
    getAttribute(key) { return this.attributes.get(key) ?? null; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    querySelector(selector) {
        if (selector === 'path') return this.children.find(child => child.tagName === 'path');
        if (selector === '#builder-grid') return this.children.find(child => child.getAttribute('id') === 'builder-grid');
        return null;
    }
    querySelectorAll() { return []; }
}
function fixture() {
    const document = newDocument(), nodes = new Map();
    const view = { preview: false, grid: true, layers: Object.fromEntries(objectKinds.map(kind => [kind, true])) };
    const root = { ownerDocument: { createElementNS: (_ns, tag) => new SvgNode(tag) },
        querySelector: selector => nodes.get(selector), querySelectorAll: selector => selector.includes('data-builder-paper')
            ? ['paper', 'grid', 'outline'].map(name => nodes.get(`[data-builder-${name}]`)) : [] };
    for (const name of ['defs', 'paper', 'grid', 'outline', 'background-image', 'background-name', 'background-remove', ...objectKinds])
        nodes.set(`[data-builder-${name}]`, new SvgNode('g'));
    const grid = new SvgNode('pattern'); grid.setAttribute('id', 'builder-grid'); grid.append(new SvgNode('path'));
    nodes.get('[data-builder-defs]').append(grid);
    const assets = new Map();
    const renderer = createCanvasRenderer({ root, getDocument: () => document, getView: () => view, assetById: id => assets.get(id) });
    return { document, view, nodes, assets, renderer, grid };
}

test('collision-only walls and doors are selectable guides in the editor and have no preview artwork', () => {
    const f = fixture();
    for (const kind of ['walls', 'doors']) {
        const source = { id: kind, layerId: f.document.layers[0].id, artwork: false, assetId: null,
            x1: 1.25, y1: 2.5, x2: 6.5, y2: 2.5, thickness: .18, state: 'closed' };
        const edit = f.renderer.objectNode(kind, source);
        assert.equal(edit.getAttribute('data-object-id'), kind);
        assert.equal(edit.children.length, 1); assert.equal(edit.children[0].tagName, 'line');
        assert.equal(edit.children[0].getAttribute('x1'), '1.25');
        assert.equal(edit.children[0].getAttribute('vector-effect'), 'non-scaling-stroke');
        f.view.preview = true;
        const preview = f.renderer.objectNode(kind, source);
        assert.equal(preview.children.length, 0, 'existing map artwork must not receive opaque wall or door paint');
        f.view.preview = false;
    }
    f.renderer.dispose();
});

test('an adopted background and grid use their original pixel geometry within the editor workspace', () => {
    const f = fixture(); f.document.cellSize = 70; f.document.columns = 15; f.document.rows = 12;
    f.document.sceneGeometry = { width: 1001, height: 801, gridSize: 35.5, gridOffsetX: 10.25, gridOffsetY: -5.5 };
    f.document.backgroundImage = { assetId: 'map' }; f.assets.set('map', { name: 'Native map', url: '/synthetic.png' });
    f.renderer.render();
    const image = f.nodes.get('[data-builder-background-image]').children[0];
    assert.equal(Number(image.getAttribute('width')) * 70, 1001);
    assert.equal(Number(image.getAttribute('height')) * 70, 801);
    assert.equal(Number(f.grid.getAttribute('width')) * 70, 35.5);
    assert.equal(Number(f.grid.getAttribute('x')) * 70, 10.25);
    assert.equal(Number(f.grid.getAttribute('y')) * 70, -5.5);
    assert.equal(f.nodes.get('[data-builder-outline]').getAttribute('width'), String(1001 / 70));
    f.document.sceneGeometry.imageScale = 2;
    f.renderer.render();
    assert.equal(Number(f.grid.getAttribute('width')) * 70, 71);
    assert.equal(Number(f.grid.getAttribute('x')) * 70, 20.5);
    assert.equal(Number(f.grid.getAttribute('y')) * 70, -11);
    assert.equal(Number(f.nodes.get('[data-builder-background-image]').children[0].getAttribute('width')) * 70, 1001);
    const light = { id: 'native-light', x: 2, y: 3, brightRadius: 2, dimRadius: 5, enabled: true, color: '#ffffff' };
    assert.equal(Number(f.renderer.objectNode('lights', light).children[0].getAttribute('r')) * 70, 355);
    delete f.document.sceneGeometry;
    f.renderer.render();
    assert.equal(image.getAttribute('width'), String(1001 / 70), 'the previous render is immutable');
    assert.equal(f.nodes.get('[data-builder-background-image]').children[0].getAttribute('width'), '15');
    assert.equal(f.grid.getAttribute('width'), '1'); assert.equal(f.grid.getAttribute('x'), '0');
    f.renderer.dispose();
});
