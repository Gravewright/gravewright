// Pinned progress indicators keep per-member browser positions, never campaign state.
const STYLE_KEYS = ['position', 'left', 'top', 'right', 'bottom', 'width', 'maxWidth', 'maxHeight', 'overflowY'];
const MOVE_HELP = 'Drag to move. Use arrow keys; hold Shift for larger steps. Position is saved only in this browser.';
const coordinates = value => value && typeof value === 'object'
  && ['x', 'y'].every(key => Number.isFinite(value[key]) && Math.abs(value[key]) <= 1_000_000);

export function clampProgressPosition(point, size, viewport) {
  const margin = 8, width = Math.max(1, viewport.width), height = Math.max(1, viewport.height);
  const maxX = Math.max(margin, width - Math.min(size.width, width - 2 * margin) - margin);
  const maxY = Math.max(margin, height - Math.min(size.height, height - 2 * margin) - margin);
  const top = Math.min(maxY, Math.max(margin, viewport.top || margin));
  return { x: Math.max(margin, Math.min(point.x, maxX)), y: Math.max(top, Math.min(point.y, maxY)) };
}

export function mountProgressHudLayout(root, { profileId, campaignId, kind, t = key => key,
  signal: external, storage: suppliedStorage } = {}) {
  if (!['clock', 'clue'].includes(kind)) throw new TypeError('Invalid progress indicator kind.');
  const document = root.ownerDocument, view = document.defaultView;
  const own = new AbortController(), signal = external ? AbortSignal.any([own.signal, external]) : own.signal;
  const prefix = profileId && campaignId ? `gravewright.progress-hud.v1.${profileId}.${campaignId}.${kind}.` : null;
  const selector = `[data-${kind}-id]`, identity = `${kind}Id`;
  const desired = new Map(), originals = new WeakMap();
  let entries = new Map(), gesture, frame = 0, storage, lastDrag;
  try { storage = suppliedStorage === undefined ? view.localStorage : suppliedStorage; } catch { /* Browser storage may be disabled. */ }
  const viewport = () => ({ width: view.innerWidth, height: view.innerHeight,
    top: root.getBoundingClientRect().top });
  const preferenceId = id => view.innerWidth <= 480 ? `${id}.compact` : id;
  function remember(id, point) {
    desired.delete(id); desired.set(id, point);
    while (desired.size > 256) desired.delete(desired.keys().next().value);
  }
  function saved(id) {
    id = preferenceId(id);
    if (desired.has(id)) return desired.get(id);
    if (!prefix || !storage) return;
    try {
      const raw = storage.getItem(prefix + id);
      if (!raw || raw.length > 256) return;
      const value = JSON.parse(raw);
      if (coordinates(value)) { const point = { x: value.x, y: value.y }; remember(id, point); return point; }
    } catch { /* A damaged preference must not stop table interaction. */ }
  }
  function persist(id, point) {
    id = preferenceId(id);
    remember(id, point);
    if (prefix && storage) try { storage.setItem(prefix + id, JSON.stringify(point)); } catch { /* Keep the current view usable. */ }
  }
  function place(entry, point) {
    const value = clampProgressPosition(point, entry.size, viewport());
    entry.point = value;
    entry.card.style.left = `${value.x}px`; entry.card.style.top = `${value.y}px`;
    return value;
  }
  function finish(commit = false) {
    if (!gesture) return;
    const current = gesture; gesture = undefined;
    current.events.abort(); delete current.entry.card.dataset.progressMoving;
    if (current.handle.hasPointerCapture?.(current.pointerId)) {
      try { current.handle.releasePointerCapture(current.pointerId); } catch { /* The node may have been removed. */ }
    }
    if (commit && current.moved) persist(current.id, current.entry.point);
    else place(current.entry, current.origin);
  }
  function refresh() {
    if (signal.aborted) return;
    finish(false);
    const cards = [...root.querySelectorAll(selector)];
    // Restore every card before reading any geometry, so defaults still use CSS flow.
    for (const card of cards) {
      if (!originals.has(card)) originals.set(card, Object.fromEntries(STYLE_KEYS.map(key => [key, card.style[key] || ''])));
      Object.assign(card.style, originals.get(card));
    }
    const bounds = viewport(), next = new Map();
    let compactBottom = bounds.height - 80;
    if (kind === 'clock' && bounds.width <= 480) {
      const dock = document.querySelector?.('.game-dock')?.getBoundingClientRect();
      if (dock?.width && dock?.height && Number.isFinite(dock.top) && dock.top > bounds.top) {
        compactBottom = Math.min(compactBottom, dock.top - 8);
      }
    }
    const measured = cards.map(card => ({ card, box: card.getBoundingClientRect() }));
    for (const { card, box } of measured) {
      const id = card.dataset[identity], handle = card.querySelector('[data-progress-move-handle]');
      if (!id || !handle || !box.width || !box.height) continue;
      const size = { width: Math.min(box.width, Math.max(1, bounds.width - 16)),
        height: Math.min(box.height, Math.max(1, bounds.height - Math.max(8, bounds.top) - 8)) };
      const entry = { id, card, handle, size };
      Object.assign(card.style, { position: 'fixed', width: `${size.width}px`,
        maxWidth: `${Math.max(1, bounds.width - 16)}px`, maxHeight: `${Math.max(1, bounds.height - Math.max(8, bounds.top) - 8)}px`,
        overflowY: 'auto', right: 'auto', bottom: 'auto' });
      handle.tabIndex = 0;
      if (handle.dataset.progressDetailsTrigger === undefined) {
        handle.setAttribute('role', 'group');
        handle.setAttribute('aria-label', `${t('Move indicator')}: ${handle.textContent}`);
        handle.setAttribute('aria-keyshortcuts', 'ArrowLeft ArrowRight ArrowUp ArrowDown');
        handle.title = t(MOVE_HELP);
      } else {
        // The title also opens a role-specific modal. Keep that action's
        // semantics and keyboard hint when decorating it as a drag handle.
        handle.setAttribute('aria-keyshortcuts', 'Enter Space ArrowLeft ArrowRight ArrowUp ArrowDown');
        const moving = t(MOVE_HELP);
        if (!handle.title?.includes(moving)) handle.title = [handle.title, moving].filter(Boolean).join(' ');
      }
      const initial = { x: box.left, y: box.top };
      if (kind === 'clock' && bounds.width <= 480) {
        initial.y = Math.max(box.top, compactBottom - size.height);
        compactBottom = initial.y - 8;
      }
      place(entry, saved(id) || initial); next.set(id, entry);
    }
    entries = next;
  }
  function entryFor(event) {
    const handle = event.target.closest?.('[data-progress-move-handle]');
    if (!handle || !root.contains(handle)) return;
    const card = handle.closest(selector), entry = entries.get(card?.dataset[identity]);
    return entry?.handle === handle ? entry : undefined;
  }
  root.addEventListener('pointerdown', event => {
    if (gesture || event.button !== 0 || event.isPrimary === false) return;
    const entry = entryFor(event);
    if (!entry) return;
    const events = new AbortController(), dragSignal = AbortSignal.any([signal, events.signal]);
    const current = { id: entry.id, entry, handle: entry.handle, pointerId: event.pointerId,
      startX: event.clientX, startY: event.clientY, origin: { ...entry.point }, moved: false, events };
    gesture = current;
    entry.handle.focus({ preventScroll: true });
    document.addEventListener('pointermove', next => {
      if (gesture !== current || next.pointerId !== current.pointerId) return;
      const dx = next.clientX - current.startX, dy = next.clientY - current.startY;
      if (!current.moved && Math.hypot(dx, dy) < 4) return;
      if (!current.moved) {
        try { entry.handle.setPointerCapture?.(event.pointerId); } catch { /* Document listeners also handle uncaptured pointers. */ }
      }
      current.moved = true; current.entry.card.dataset.progressMoving = '';
      place(entry, { x: current.origin.x + dx, y: current.origin.y + dy });
      next.preventDefault(); next.stopPropagation();
    }, { signal: dragSignal });
    document.addEventListener('pointerup', next => {
      if (next.pointerId !== current.pointerId) return;
      if (current.moved) {
        lastDrag = { id: current.id, time: next.timeStamp };
        next.preventDefault(); next.stopPropagation();
      }
      finish(true);
    }, { signal: dragSignal });
    document.addEventListener('pointercancel', next => { if (next.pointerId === current.pointerId) finish(false); }, { signal: dragSignal });
    entry.handle.addEventListener('lostpointercapture', () => finish(false), { signal: dragSignal });
    document.addEventListener('keydown', next => {
      if (next.key === 'Escape') { next.preventDefault(); next.stopPropagation(); finish(false); }
    }, { signal: dragSignal });
    view.addEventListener('blur', () => finish(false), { signal: dragSignal });
    // Preserve native click/double-click generation until this becomes a drag.
    event.stopPropagation();
  }, { signal });
  const suppressDragClick = event => {
    if (lastDrag && event.timeStamp >= lastDrag.time && event.timeStamp - lastDrag.time < 350
        && entryFor(event)?.id === lastDrag.id) {
      event.preventDefault(); event.stopImmediatePropagation();
    }
  };
  for (const name of ['click', 'dblclick']) root.addEventListener(name, suppressDragClick, { capture: true, signal });
  root.addEventListener('keydown', event => {
    if (gesture || event.altKey || event.ctrlKey || event.metaKey) return;
    const delta = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[event.key];
    const entry = delta && entryFor(event);
    if (!entry) return;
    const amount = event.shiftKey ? 10 : 1;
    persist(entry.id, place(entry, { x: entry.point.x + delta[0] * amount, y: entry.point.y + delta[1] * amount }));
    event.preventDefault(); event.stopPropagation();
  }, { signal });
  const scheduleRefresh = () => {
    if (!frame) frame = view.requestAnimationFrame(() => { frame = 0; refresh(); });
  };
  view.addEventListener('resize', scheduleRefresh, { signal });
  view.addEventListener('gravewright:dock-resize', scheduleRefresh, { signal });
  function destroy() {
    if (own.signal.aborted) return;
    finish(false); own.abort(); if (frame) view.cancelAnimationFrame(frame);
    for (const { card } of entries.values()) Object.assign(card.style, originals.get(card));
    entries.clear(); desired.clear();
  }
  signal.addEventListener('abort', () => { if (!own.signal.aborted) destroy(); }, { once: true });
  refresh();
  return { refresh, destroy };
}
