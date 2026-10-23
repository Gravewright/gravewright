const clone = value => structuredClone(value);

export function newMindmapDocument(label, id = crypto.randomUUID()) {
  return { nodes: [{ id, parentId: null, label, notes: '', color: '#c9a44c', x: 0, y: 0,
    collapsed: false, completed: false, links: [] }], edges: [] };
}

export function visibleMindmapNodes(document) {
  const byId = new Map(document.nodes.map(node => [node.id, node]));
  return document.nodes.filter(node => {
    const seen = new Set([node.id]); let parent = byId.get(node.parentId);
    while (parent) {
      if (parent.collapsed || seen.has(parent.id)) return false;
      seen.add(parent.id); parent = byId.get(parent.parentId);
    }
    return true;
  });
}

export function addMindmapNode(document, parentId, label, { siblingId, id = crypto.randomUUID() } = {}) {
  const next = clone(document), sibling = next.nodes.find(node => node.id === siblingId);
  const parent = next.nodes.find(node => node.id === (sibling ? sibling.parentId : parentId));
  const peers = next.nodes.filter(node => node.parentId === (parent?.id || null));
  let x = sibling ? sibling.x : parent ? parent.x + 260 : next.nodes.length ? Math.max(...next.nodes.map(node => node.x)) + 260 : 0;
  let y = sibling ? sibling.y + 110 : parent ? parent.y + peers.length * 110 : 0;
  if (x > 100000) { x = 0; y = Math.max(0, ...next.nodes.map(node => node.y)) + 110; }
  x = Math.max(-100000, Math.min(100000, x)); y = Math.max(-100000, Math.min(100000, y));
  for (let attempts = 0; attempts < 501 && next.nodes.some(node => Math.abs(node.x - x) < 230 && Math.abs(node.y - y) < 96); attempts++) {
    y += 110; if (y > 100000) { y = -100000; x = Math.max(-100000, x - 260); }
  }
  next.nodes.push({ id, parentId: parent?.id || null, label, notes: '', color: parent?.color || '#c9a44c', x, y,
    collapsed: false, completed: false, links: [] });
  if (parent) parent.collapsed = false;
  return next;
}

export function removeMindmapNode(document, id) {
  const removed = new Set([id]);
  for (let changed = true; changed;) {
    changed = false;
    for (const node of document.nodes) if (removed.has(node.parentId) && !removed.has(node.id)) { removed.add(node.id); changed = true; }
  }
  return { nodes: document.nodes.filter(node => !removed.has(node.id)).map(clone),
    edges: document.edges.filter(edge => !removed.has(edge.from) && !removed.has(edge.to)).map(clone) };
}

export function reparentMindmapNode(document, id, parentId) {
  const byId = new Map(document.nodes.map(node => [node.id, node]));
  if (!byId.has(id) || parentId !== null && !byId.has(parentId)) throw Error('Choose an existing topic.');
  const seen = new Set([id]); let parent = byId.get(parentId);
  while (parent) {
    if (seen.has(parent.id)) throw Error('A topic cannot become its own descendant.');
    seen.add(parent.id); parent = byId.get(parent.parentId);
  }
  const next = clone(document); next.nodes.find(node => node.id === id).parentId = parentId; return next;
}

export function createMindmapHistory(initial, limit = 50) {
  let entries = [clone(initial)], index = 0, saved = JSON.stringify(initial);
  return {
    get value() { return clone(entries[index]); },
    get dirty() { return JSON.stringify(entries[index]) !== saved; },
    get canUndo() { return index > 0; }, get canRedo() { return index + 1 < entries.length; },
    change(value) {
      if (JSON.stringify(value) === JSON.stringify(entries[index])) return false;
      entries = entries.slice(0, index + 1); entries.push(clone(value));
      if (entries.length > limit + 1) entries.shift(); index = entries.length - 1; return true;
    },
    undo() { if (index) index--; return this.value; },
    redo() { if (index + 1 < entries.length) index++; return this.value; },
    reset(value) { entries = [clone(value)]; index = 0; saved = JSON.stringify(value); },
  };
}

export function fitMindmap(nodes, width, height) {
  if (!nodes.length) return { x: width / 2, y: height / 2, scale: 1 };
  const left = Math.min(...nodes.map(node => node.x)), top = Math.min(...nodes.map(node => node.y));
  const right = Math.max(...nodes.map(node => node.x + 210)), bottom = Math.max(...nodes.map(node => node.y + 76));
  const scale = Math.min(1.4, Math.max(.15, Math.min((width - 64) / Math.max(1, right - left), (height - 64) / Math.max(1, bottom - top))));
  return { x: width / 2 - (left + right) / 2 * scale, y: height / 2 - (top + bottom) / 2 * scale, scale };
}

export function zoomMindmap(view, factor, point) {
  const scale = Math.max(.15, Math.min(3, view.scale * factor)), ratio = scale / view.scale;
  return { x: point.x - (point.x - view.x) * ratio, y: point.y - (point.y - view.y) * ratio, scale };
}

/** Keep uncertain retries tied to one candidate, never to a later edit. */
export function createMindmapCommands({ api, signal }) {
  const attempts = new Map();
  return { async run(method, payload) {
    signal.throwIfAborted();
    const key = payload.id || 'create', fingerprint = JSON.stringify([method, payload]);
    let attempt = attempts.get(key);
    if (attempt?.fingerprint !== fingerprint) { attempt = { fingerprint, requestId: crypto.randomUUID() }; attempts.set(key, attempt); }
    try {
      const result = await api.mindmaps[method](payload, { signal, requestId: attempt.requestId });
      signal.throwIfAborted();
      return result;
    } catch (error) {
      if (error?.status >= 400 && error.status < 500 && ![408, 429].includes(error.status)
        || ['conflict', 'permission_denied', 'invalid_data', 'not_found'].includes(error?.code)) attempts.delete(key);
      throw error;
    }
  }, acknowledge(id) { attempts.delete(id || 'create'); }, destroy() { attempts.clear(); } };
}
