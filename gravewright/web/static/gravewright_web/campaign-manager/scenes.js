/** Build a native scene edit without changing the revision captured by its editor. */
export function sceneUpdatePayload(scene, values) {
  return { mapId: scene.id, version: scene.version, settings: {
    name: values.name.trim(), visibility: values.visibility, gridSize: Number(values.gridSize),
  } };
}

/** Project navigation is an explicit page change, independent of scene broadcast. */
export function builderProjectUrl(campaignId, projectId) {
  return `/game/${encodeURIComponent(campaignId)}/map-builder?project=${encodeURIComponent(projectId)}`;
}

/**
 * Mount the GM's scene directory without importing the board or its transport.
 * Selection is a local editing context. Native editors are loaded only on use;
 * their requests retain permissions, revisions and the management lifetime.
 */
export function mountManagedScenes({ root, api, transport, http, t, report,
  selectedScene, onSelect, load = path => import(path) }) {
  const document = root.ownerDocument, scope = new AbortController();
  const signal = transport.signal ? AbortSignal.any([scope.signal, transport.signal]) : scope.signal;
  const campaignId = api.context?.tableId || root.dataset.tableId;
  const host = root.querySelector('[data-manager-maps]');
  const importButton = root.querySelector('[data-manager-uvtt]');
  const modals = new Set();
  let state = { maps: [] }, localSelection = typeof selectedScene === 'function' ? selectedScene() : selectedScene;
  let builder, opening = false, rows = new AbortController();
  const chosen = () => typeof selectedScene === 'function' ? selectedScene() : localSelection;
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const alive = () => !signal.aborted;
  function remember(modal) {
    if (!modal) return;
    if (!alive()) { modal.close?.(true); return; }
    modals.add(modal);
    modal.addEventListener('close', () => modals.delete(modal), { once: true });
    return modal;
  }
  function existingEditor() {
    for (const modal of modals) if (modal.isConnected) { modal.focus(); return true; }
    return false;
  }
  async function refresh() {
    const next = await transport.read('maps');
    if (alive()) render(next);
    return next;
  }
  function button(label, action) {
    const node = element('button', '', t(label)); node.type = 'button';
    node.addEventListener('click', async () => {
      if (!alive() || node.disabled) return;
      node.disabled = true;
      try { await action(); }
      catch (error) { if (alive() && error.name !== 'AbortError') report(error); }
      finally { if (alive()) node.disabled = false; }
    }, { signal: rows.signal });
    return node;
  }
  async function editScene(scene) {
    if (opening || existingEditor()) return;
    opening = true;
    try {
      await transport.check();
      const { openFormModal } = await load('/static/gravewright_table/form-modal.js');
      if (!alive()) return;
      const snapshot = { ...scene };
      let attempt;
      const modal = openFormModal(t('Edit scene'), [
        { name: 'name', label: t('Scene name'), value: snapshot.name, required: true },
        { name: 'visibility', label: t('Visibility'), value: snapshot.visibility, options: [
          { value: 'gm', label: t('GM only') }, { value: 'players', label: t('Players') },
        ] },
        { name: 'gridSize', label: t('Grid size'), type: 'number', value: snapshot.gridSize ?? 70, required: true },
      ], async form => {
        await transport.check();
        const payload = sceneUpdatePayload(snapshot, {
          name: form.elements.name.value, visibility: form.elements.visibility.value,
          gridSize: form.elements.gridSize.value,
        });
        const fingerprint = JSON.stringify(payload);
        if (attempt?.fingerprint !== fingerprint) attempt = { fingerprint, requestId: crypto.randomUUID() };
        try {
          await transport.resourceCommand('maps', 'update', payload, { signal, requestId: attempt.requestId });
        } catch (error) {
          if (error.code === 'conflict' || error.status === 409) {
            await refresh().catch(cause => { if (alive()) report(cause); });
            throw new Error(t('The scene changed. Reopen its settings and try again.'));
          }
          throw Object.assign(new Error(t(error.message || 'Could not update scene.')), {
            code: error.code, status: error.status,
          });
        }
      }, { key: `managed-scene:${scene.id}`, submitLabel: t('Save changes') });
      const name = modal.querySelector('[name="name"]'), grid = modal.querySelector('[name="gridSize"]');
      name.maxLength = 120; name.setAttribute('translate', 'no');
      grid.min = '1'; grid.max = '10000'; grid.step = 'any';
      remember(modal);
    } finally { opening = false; }
  }
  async function permissions(scene) {
    if (opening || existingEditor()) return;
    opening = true;
    try {
      await transport.check();
      const { openPermissions } = await load('/static/gravewright_table/permissions.js');
      if (alive()) remember(await openPermissions('scenes', scene.id, { onSave: refresh }));
    } finally { opening = false; }
  }
  async function interchange(scene) {
    if (opening || existingEditor()) return;
    opening = true;
    try {
      await transport.check();
      const { openUniversalVtt } = await load('/static/gravewright_maps/universal-vtt.js');
      if (!alive()) return;
      remember(openUniversalVtt({ campaignId, ...(scene ? { sceneId: scene.id } : { builderEditable: true }), t,
        onImported: refresh }));
    } finally { opening = false; }
  }
  async function editBuilder(scene) {
    if (existingEditor()) return;
    await transport.check();
    if (!builder) {
      builder = load('/static/gravewright_maps/scene-builder.js').then(({ createSceneBuilder }) => createSceneBuilder({
        campaignId, signal, post: (...args) => http.post(...args),
        navigate: projectId => { if (alive()) document.defaultView.location.assign(builderProjectUrl(campaignId, projectId)); },
      })).catch(error => { builder = undefined; throw error; });
    }
    const open = await builder;
    if (alive()) await open(scene);
  }
  function render(next) {
    if (!alive() || !host) return;
    rows.abort(); rows = new AbortController();
    state = next || { maps: [] };
    if (importButton) importButton.disabled = state.is_gm === false;
    host.replaceChildren();
    if (!state.maps?.length) {
      host.append(element('p', 'campaign-manager__empty', t('No scenes yet.')));
      return;
    }
    for (const scene of state.maps) {
      const row = element('article', 'campaign-manager__row'); row.dataset.sceneId = scene.id;
      const info = element('div', 'campaign-manager__row-info');
      const name = element('strong', '', scene.name); name.setAttribute('translate', 'no');
      info.append(name, element('small', '', `${t(scene.visibility === 'gm' ? 'GM only' : 'Players')} · ${scene.width} × ${scene.height}`));
      const actions = element('footer', 'campaign-manager__section-actions');
      const select = button(chosen() === scene.id ? 'Selected' : 'Select scene', async () => {
        localSelection = scene.id;
        await onSelect?.(scene.id);
        render(state);
      });
      select.dataset.managerMapSelect = scene.id; select.setAttribute('aria-pressed', String(chosen() === scene.id));
      actions.append(select);
      if (state.is_gm !== false) actions.append(
        button('Edit scene', () => editScene(scene)), button('Permissions', () => permissions(scene)),
        button('Edit map with MapBuilder', () => editBuilder(scene)),
        button('Export Universal VTT', () => interchange(scene)),
      );
      row.append(info, actions); host.append(row);
    }
  }
  importButton?.addEventListener('click', () => {
    if (!alive() || importButton.disabled) return;
    void interchange().catch(error => { if (alive()) report(error); });
  }, { signal });
  signal.addEventListener('abort', () => { rows.abort(); for (const modal of modals) modal.close?.(true); modals.clear(); }, { once: true });
  return { render, destroy() { scope.abort(); } };
}
