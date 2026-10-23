import test from 'node:test';
import assert from 'node:assert/strict';
import { mountManagedScenes, sceneUpdatePayload, builderProjectUrl } from '../../gravewright/web/static/gravewright_web/campaign-manager/scenes.js';
import { createSceneBuilder } from '../../gravewright/maps/static/gravewright_maps/scene-builder.js';

class Element extends EventTarget {
  constructor(tag, document) {
    super(); this.tagName = tag; this.ownerDocument = document; this.children = []; this.dataset = {};
    this.attributes = new Map(); this.isConnected = true; this.disabled = false;
  }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  focus() { this.focused = true; }
  close() { this.isConnected = false; this.dispatchEvent(new Event('close')); }
  querySelector(selector) { return this.controls?.[selector]; }
}

function fixture({ loadHook } = {}) {
  const navigated = [], calls = [], errors = [], dialogs = [], interchanges = [], loads = [];
  const document = { createElement: tag => new Element(tag, document), defaultView: { location: { assign: url => navigated.push(url) } } };
  const host = document.createElement('div'), importButton = document.createElement('button');
  const root = { ownerDocument: document, dataset: { tableId: 'campaign' }, querySelector: key => key === '[data-manager-maps]' ? host : importButton };
  const abort = new AbortController();
  let selected = null;
  const api = { context: { tableId: 'campaign' }, maps: {
    async update(payload, options) { calls.push(['update', structuredClone(payload), options]); return {}; },
    navigate() { assert.fail('local selection must not navigate the table'); },
    activate() { assert.fail('management must not broadcast a scene'); },
  } };
  const state = { is_gm: true, maps: [{ id: 'scene', name: '<script>authored name</script>', visibility: 'gm', version: 8, gridSize: 70, width: 1200, height: 900 }] };
  const transport = {
    signal: abort.signal,
    async check() { calls.push(['check']); },
    async read(domain) { calls.push(['read', domain]); return state; },
    async resourceCommand(domain, action, payload, options) {
      assert.equal(domain, 'maps'); assert.equal(action, 'update');
      const result = await api.maps.update(payload, options); await this.read(domain); return result;
    },
  };
  const http = { async post(path, payload, options) { calls.push(['post', path, payload, options]); return { project: { id: 'adopted' } }; } };
  const modal = () => {
    const node = document.createElement('section');
    node.controls = { '[name="name"]': document.createElement('input'), '[name="gridSize"]': document.createElement('input') };
    return node;
  };
  const load = async path => {
    loads.push(path);
    await loadHook?.(path);
    if (path.endsWith('scene-builder.js')) return { createSceneBuilder };
    if (path.endsWith('form-modal.js')) return { openFormModal(title, fields, save, options) {
      const node = modal(); dialogs.push({ title, fields, save, options, node }); return node;
    } };
    if (path.endsWith('permissions.js')) return { async openPermissions(kind, id, options) {
      calls.push(['permissions', kind, id, options]); return modal();
    } };
    if (path.endsWith('universal-vtt.js')) return { openUniversalVtt(options) { interchanges.push(options); return modal(); } };
    assert.fail('Unexpected native import: ' + path);
  };
  const component = mountManagedScenes({ root, api, transport, http, t: key => `translated:${key}`,
    report: error => errors.push(error), selectedScene: () => selected,
    onSelect: id => { selected = id; }, load });
  component.render(state);
  const actions = (row = 0) => host.children[row].children[1].children;
  const find = label => actions().find(node => node.textContent === `translated:${label}`);
  const click = async node => { node.dispatchEvent(new Event('click')); await new Promise(setImmediate); };
  return { component, state, api, transport, http, host, importButton, calls, errors, dialogs,
    interchanges, loads, navigated, abort, actions, find, click, get selected() { return selected; } };
}

test('selection and authored labels remain local, with native tools loaded only on demand', async () => {
  const f = fixture();
  assert.equal(f.host.children[0].children[0].children[0].textContent, '<script>authored name</script>');
  assert.deepEqual(f.loads, []);
  await f.click(f.find('Select scene'));
  assert.equal(f.selected, 'scene');
  assert.equal(f.find('Selected').attributes.get('aria-pressed'), 'true');
  assert.deepEqual(f.calls, []);
  assert.deepEqual(f.navigated, []);
  f.component.destroy();
});

test('scene edits keep the opening revision, numeric settings and logical retry identity', async () => {
  const f = fixture();
  await f.click(f.find('Edit scene'));
  const dialog = f.dialogs[0];
  assert.equal(dialog.title, 'translated:Edit scene');
  assert.equal(dialog.node.controls['[name="name"]'].maxLength, 120);
  const form = { elements: { name: { value: '  New name  ' }, visibility: { value: 'players' }, gridSize: { value: '80.5' } } };
  let requests = 0;
  f.api.maps.update = async (payload, options) => {
    f.calls.push(['update', structuredClone(payload), options]);
    if (++requests <= 2) throw new Error('Synthetic lost response');
    return {};
  };
  await assert.rejects(dialog.save(form), /Synthetic lost response/);
  await assert.rejects(dialog.save(form), /Synthetic lost response/);
  form.elements.name.value = 'A different logical change';
  await dialog.save(form);
  const updates = f.calls.filter(call => call[0] === 'update');
  assert.deepEqual(updates[0][1], { mapId: 'scene', version: 8, settings: { name: 'New name', visibility: 'players', gridSize: 80.5 } });
  assert.equal(updates[0][2].requestId, updates[1][2].requestId);
  assert.notEqual(updates[1][2].requestId, updates[2][2].requestId);
  f.state.maps[0].version = 12;
  f.component.render(f.state);
  f.api.maps.update = async payload => {
    assert.equal(payload.version, 8);
    throw Object.assign(new Error('Changed elsewhere'), { code: 'conflict' });
  };
  await assert.rejects(dialog.save(form), /translated:The scene changed. Reopen its settings and try again./);
  assert.equal(form.elements.name.value, 'A different logical change');
  f.component.destroy();
  assert.equal(dialog.node.isConnected, false);
});

test('native permissions and UVTT import/export keep scene and campaign ownership', async () => {
  const f = fixture();
  await f.click(f.find('Permissions'));
  const permission = f.calls.find(call => call[0] === 'permissions');
  assert.deepEqual(permission.slice(0, 3), ['permissions', 'scenes', 'scene']);
  await permission[3].onSave();
  f.component.destroy();

  const importing = fixture();
  await importing.click(importing.importButton);
  assert.equal(importing.interchanges[0].campaignId, 'campaign');
  assert.equal(importing.interchanges[0].builderEditable, true);
  assert.equal(importing.interchanges[0].sceneId, undefined);
  await importing.interchanges[0].onImported({ scene: { id: 'new' } });
  assert.ok(importing.calls.some(call => call[0] === 'read' && call[1] === 'maps'));
  importing.component.destroy();

  const exporting = fixture();
  await exporting.click(exporting.find('Export Universal VTT'));
  assert.equal(exporting.interchanges[0].sceneId, 'scene');
  assert.equal(exporting.interchanges[0].campaignId, 'campaign');
  exporting.component.destroy();
});

test('Builder reuses linked projects and concurrent adoption never creates duplicate operations', async () => {
  const linked = fixture();
  linked.state.maps[0].builderProjectId = 'linked/project'; linked.component.render(linked.state);
  await linked.click(linked.find('Edit map with MapBuilder'));
  assert.deepEqual(linked.navigated, ['/game/campaign/map-builder?project=linked%2Fproject']);
  assert.equal(linked.calls.some(call => call[0] === 'post'), false);
  linked.component.destroy();

  const f = fixture();
  let finish;
  f.http.post = async (path, payload) => { f.calls.push(['post', path, payload]); return new Promise(resolve => { finish = resolve; }); };
  await f.click(f.find('Edit map with MapBuilder'));
  f.component.render(f.state);
  await f.click(f.find('Edit map with MapBuilder'));
  assert.equal(f.calls.filter(call => call[0] === 'post').length, 1);
  assert.equal(f.calls.find(call => call[0] === 'post')[2].expected_scene_version, 8);
  f.component.destroy();
  finish({ project: { id: 'late-adoption' } }); await new Promise(setImmediate);
  assert.deepEqual(f.navigated, []);
});

test('destroying during a lazy editor import prevents late modal creation and further actions', async () => {
  let finish;
  const f = fixture({ loadHook: () => new Promise(resolve => { finish = resolve; }) });
  await f.click(f.find('Edit scene'));
  assert.equal(f.loads.length, 1);
  f.abort.abort(); finish(); await new Promise(setImmediate);
  assert.equal(f.dialogs.length, 0);
  await f.click(f.find('Edit scene'));
  assert.equal(f.loads.length, 1);
  f.component.render({ maps: [] });
  assert.equal(f.host.children.length, 1);
  f.component.destroy();
});

test('public payload and project URL helpers retain native names and escape only URL segments', () => {
  assert.deepEqual(sceneUpdatePayload({ id: 'scene', version: 3 }, { name: ' Name ', visibility: 'gm', gridSize: '70' }), {
    mapId: 'scene', version: 3, settings: { name: 'Name', visibility: 'gm', gridSize: 70 },
  });
  assert.equal(builderProjectUrl('campaign/slash', 'project?one'), '/game/campaign%2Fslash/map-builder?project=project%3Fone');
});
