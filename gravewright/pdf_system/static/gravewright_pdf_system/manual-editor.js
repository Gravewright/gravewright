import { moveLayoutFields, alignLayoutFields,
  distributeLayoutFields, snapLayoutRect } from './controller.js';

/** Manual mapping gestures stay local until one field operation is committed. */
export function createManualEditor({ root, controller, t, onConfigure }) {
  const document = root.ownerDocument;
  const overlay = root.querySelector(".pdf-sheet__mapping");
  const tools = root.querySelector("[data-pdf-mapping-tools]");
  const tool = root.querySelector("[data-pdf-map-tool]");
  const properties = root.querySelector("[data-pdf-map-properties]");
  const nameInput = root.querySelector("[data-pdf-map-name]");
  const error = root.querySelector("[data-pdf-map-error]");
  const listeners = new AbortController();
  const boxes = new Map();
  const selectedIds = new Set();
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const show = (element, visible) => element?.toggleAttribute("hidden", !visible);
  let view, selectedId = "", drag = null, preview = null, lastClick = null, destroyed = false,
    selecting = false, clipboard, clipboardSource = '', actionPending = false, snap = false;
  const toolbar = document.createElement('div');
  toolbar.className = 'pdf-sheet__layout-tools';
  toolbar.dataset.pdfLayoutTools = '';
  toolbar.setAttribute('role', 'group');
  toolbar.setAttribute('aria-label', t('Layout tools'));
  const selectionCount = document.createElement('span');
  selectionCount.dataset.pdfMapSelection = '';
  selectionCount.setAttribute('aria-live', 'polite');
  const disclosure = document.createElement('details');
  disclosure.className = 'pdf-sheet__layout-disclosure';
  disclosure.dataset.pdfLayoutDisclosure = '';
  const sheetWidth = (root.closest('.gw-window') || root).getBoundingClientRect().width
    || document.documentElement.clientWidth;
  disclosure.open = sheetWidth >= 640;
  const summary = document.createElement('summary');
  summary.append(document.createTextNode(t('Layout tools') + ' '), selectionCount);
  disclosure.append(summary, toolbar);
  const buttons = new Map();
  for (const [action, label] of [['copy', 'Copy fields'], ['paste', 'Paste fields'],
    ['duplicate', 'Duplicate fields'], ['undo', 'Undo layout'], ['redo', 'Redo layout']]) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.pdfLayoutAction = action;
    button.textContent = t(label);
    button.addEventListener('click', () => void runLayoutAction(action), { signal: listeners.signal });
    toolbar.append(button);
    buttons.set(action, button);
  }
  for (const [attribute, label, options] of [
    ['align', 'Align fields', [['left', 'Align left'], ['right', 'Align right'], ['top', 'Align top'],
      ['bottom', 'Align bottom'], ['center-x', 'Center horizontally'], ['center-y', 'Center vertically']]],
    ['distribute', 'Distribute fields', [['horizontal', 'Distribute horizontally'], ['vertical', 'Distribute vertically']]],
  ]) {
    const select = document.createElement('select');
    select.dataset[attribute === 'align' ? 'pdfLayoutAlign' : 'pdfLayoutDistribute'] = '';
    select.setAttribute('aria-label', t(label));
    select.append(new Option(t(label), ''));
    for (const [value, text] of options) select.append(new Option(t(text), value));
    select.addEventListener('change', () => {
      const action = select.value;
      select.value = '';
      const rows = selectedRows();
      applyEdits(attribute === 'align' ? alignLayoutFields(rows, action) : distributeLayoutFields(rows, action));
    }, { signal: listeners.signal });
    toolbar.append(select);
  }
  const snapLabel = document.createElement('label');
  const snapInput = document.createElement('input');
  snapInput.type = 'checkbox';
  snapInput.dataset.pdfLayoutSnap = '';
  snapInput.addEventListener('change', () => { snap = snapInput.checked; }, { signal: listeners.signal });
  snapLabel.append(snapInput, document.createTextNode(t('Snap to grid')));
  toolbar.append(snapLabel);
  tools?.insertBefore(disclosure, root.querySelector('[data-pdf-map-help]'));
  if (!document.querySelector('link[data-pdf-layout-editor-style]')) {
    const stylesheet = document.createElement('link');
    stylesheet.rel = 'stylesheet';
    stylesheet.href = new URL('./layout-editor.css', import.meta.url).href;
    stylesheet.dataset.pdfLayoutEditorStyle = '';
    document.head.append(stylesheet);
  }

  function showError(message = "") {
    if (!error) return;
    error.textContent = message;
    show(error, !!message);
  }
  function selected() {
    return view?.manualFields?.find((field) => field.id === selectedId);
  }
  function selectedRows() {
    return (view?.manualFields || []).filter(field => selectedIds.has(field.id) && frameFor(field.page));
  }
  function frameFor(page) {
    return view?.pageFrames?.find((frame) => frame.page === page);
  }
  function pageCanvas(frame) {
    return root.querySelector(`[data-pdf-page="${frame.page}"]`);
  }
  function pageAtPoint(x, y) {
    for (const frame of view?.pageFrames || []) {
      const canvas = pageCanvas(frame);
      const bounds = canvas?.getBoundingClientRect();
      if (bounds?.width > 0 && bounds.height > 0 && x >= bounds.left && x <= bounds.right && y >= bounds.top && y <= bounds.bottom)
        return { frame, bounds };
    }
    return null;
  }
  function point(event, bounds) {
    return { x: clamp((event.clientX - bounds.left) / bounds.width, 0, 1), y: clamp((event.clientY - bounds.top) / bounds.height, 0, 1) };
  }
  function boundsStyle(element, rect, frame) {
    element.style.left = `${rect.x * frame.viewport.width}px`;
    element.style.top = `${frame.top + rect.y * frame.viewport.height}px`;
    element.style.width = `${rect.width * frame.viewport.width}px`;
    element.style.height = `${rect.height * frame.viewport.height}px`;
  }
  function select(id, focus = false, { toggle = false, preserve = false, ids } = {}) {
    const stage = root.querySelector('.pdf-sheet__stage');
    const before = stage?.getBoundingClientRect().top;
    const field = view?.manualFields?.find(field => field.id === id);
    if (ids) {
      selectedIds.clear();
      for (const value of ids) selectedIds.add(value);
    } else if (toggle && field) {
      if (selectedRows().some(row => row.page !== field.page)) selectedIds.clear();
      if (selectedIds.has(id)) selectedIds.delete(id);
      else selectedIds.add(id);
    } else if (!preserve || !selectedIds.has(id)) {
      selectedIds.clear();
      if (id) selectedIds.add(id);
    }
    selectedId = selectedIds.has(id) ? id : selectedIds.values().next().value || '';
    showError();
    paint(view);
    if (stage) stage.scrollTop += stage.getBoundingClientRect().top - before;
    if (focus) {
      selecting = true;
      boxes.get(id)?.focus({ preventScroll: true });
      selecting = false;
    }
  }
  function commit(method, ...args) {
    try {
      const result = controller.call(method, ...args);
      if (result === false) {
        showError(t("Could not update this mapped field. Check its name and bounds."));
        return false;
      }
      showError();
      return result;
    } catch {
      showError(t("Could not update this mapped field. Check its name and bounds."));
      return false;
    }
  }
  function removeSelected() {
    if (!selectedRows().length || !view.mappingEditing || !view.canMap) return;
    if (applyEdits(selectedRows().map(field => ({ id: field.id, remove: true }))) !== false) {
      selectedId = "";
      selectedIds.clear();
      paint(controller.view);
      root.querySelector("[data-pdf-map-add]")?.focus({ preventScroll: true });
    }
  }
  function applyEdits(edits) {
    if (!edits?.length || !view?.mappingEditing || !view.canMap) return false;
    const result = commit('editManualFields', edits);
    paint(controller.view);
    return result;
  }
  function gridFor(frame) {
    if (!snap) return {};
    const zoom = view?.actor?.data?.pdf?.zoom || 1;
    return { x: 5 * zoom / frame.viewport.width, y: 5 * zoom / frame.viewport.height };
  }
  async function runLayoutAction(action) {
    if (!view?.mappingEditing || !view.canMap || actionPending) return;
    const source = JSON.stringify(view.currentSource);
    actionPending = true;
    try {
      if (action === 'copy' || action === 'duplicate') {
        if (!selectedRows().length) return;
        clipboard = await controller.call('copyManualFields', selectedRows().map(field => field.id));
        clipboardSource = source;
      }
      if (action === 'paste' || action === 'duplicate') {
        if (!clipboard || clipboardSource !== source) return;
        const result = await controller.call('pasteManualFields', clipboard, { dx: .02, dy: .02 });
        if (destroyed || source !== JSON.stringify(controller.view.currentSource)) return;
        const ids = Array.isArray(result) ? result : result?.ids;
        if (ids?.length) select(ids[0], true, { ids });
      }
      if (action === 'undo' || action === 'redo')
        await controller.call(action === 'undo' ? 'undoManualLayout' : 'redoManualLayout');
      showError();
    } catch (failure) {
      if (!destroyed) showError(t(failure.message || 'Could not update this mapped field. Check its name and bounds.'));
    } finally {
      actionPending = false;
      if (!destroyed) paint(controller.view);
    }
  }
  function makeBox(field) {
    const box = document.createElement("button");
    box.type = "button";
    box.className = "pdf-sheet__map-box";
    box.dataset.pdfMapField = field.id;
    box.setAttribute("translate", "no");
    const label = document.createElement("span");
    label.className = "pdf-sheet__map-label";
    label.setAttribute("translate", "no");
    const handle = document.createElement("span");
    handle.className = "pdf-sheet__map-resize";
    handle.dataset.pdfMapResize = "";
    handle.setAttribute("aria-hidden", "true");
    box.append(label, handle);
    overlay.append(box);
    boxes.set(field.id, box);
    return box;
  }
  function paint(nextView) {
    if (destroyed || !nextView || !overlay) return;
    if (view && JSON.stringify(view.currentSource) !== JSON.stringify(nextView.currentSource)) {
      selectedIds.clear(); selectedId = ''; lastClick = null;
    }
    view = nextView;
    const editing = !!view.mappingEditing && !!view.canMap;
    if (drag) {
      const frame = frameFor(drag.frame.page);
      if (!editing || JSON.stringify(view.currentSource) !== drag.source
          || !frame || frame.viewport.width !== drag.frame.viewport.width
          || frame.viewport.height !== drag.frame.viewport.height || frame.top !== drag.frame.top
          || drag.fields?.some(row => !view.manualFields?.some(field => field.id === row.id)))
        cancelDrag();
    }
    show(tools, editing);
    show(overlay, editing);
    overlay.dataset.editing = String(editing);
    overlay.dataset.tool = tool?.value || "select";
    root.querySelector(".pdf-sheet__stage")?.setAttribute("data-mapping-editing", String(editing));
    const toggle = root.querySelector("[data-pdf=toggleMapping]");
    show(toggle, !!view.canMap);
    toggle?.setAttribute("aria-pressed", String(editing));
    toggle?.classList.toggle("pdf-sheet__btn--active", editing);
    for (const id of selectedIds) {
      const field = view.manualFields?.find(field => field.id === id);
      if (!field || view.canMap && !frameFor(field.page)) selectedIds.delete(id);
    }
    if (!selectedIds.has(selectedId)) selectedId = selectedIds.values().next().value || '';
    const count = selectedRows().length;
    const countLabel = t('{0} fields selected', [count]);
    if (selectionCount.textContent !== countLabel) selectionCount.textContent = countLabel;
    overlay.dataset.multiple = String(count > 1);
    for (const action of ['copy', 'duplicate']) buttons.get(action).disabled = !count || actionPending;
    buttons.get('paste').disabled = !clipboard || clipboardSource !== JSON.stringify(view.currentSource) || actionPending;
    buttons.get('undo').disabled = !view.canUndoManualLayout || actionPending;
    buttons.get('redo').disabled = !view.canRedoManualLayout || actionPending;
    toolbar.querySelector('[data-pdf-layout-align]').disabled = count < 2 || actionPending;
    toolbar.querySelector('[data-pdf-layout-distribute]').disabled = count < 3 || actionPending;
    const visible = new Set();
    for (const field of view.manualFields || []) {
      const frame = frameFor(field.page);
      if (!frame) continue;
      visible.add(field.id);
      const box = boxes.get(field.id) || makeBox(field);
      box.firstElementChild.textContent = field.name;
      box.setAttribute("aria-label", field.name);
      box.setAttribute("aria-pressed", String(selectedIds.has(field.id)));
      box.classList.toggle("pdf-sheet__map-box--selected", selectedIds.has(field.id));
      box.dataset.type = field.type;
      if (!drag || !drag.fields?.some(row => row.id === field.id)) boundsStyle(box, field, frame);
    }
    for (const [id, box] of boxes) {
      if (visible.has(id)) continue;
      box.remove();
      boxes.delete(id);
    }
    const field = selected();
    show(properties, editing && !!field);
    if (field) {
      if (nameInput) nameInput.disabled = count > 1;
      if (nameInput && root.ownerDocument.activeElement !== nameInput) nameInput.value = field.name;
      for (const input of root.querySelectorAll("[data-pdf-map-property]")) {
        input.disabled = count > 1;
        if (root.ownerDocument.activeElement !== input) input.value = String(Math.round(field[input.dataset.pdfMapProperty] * 100000) / 1000);
      }
    }
  }
  function endCapture(pointerId) {
    if (overlay.hasPointerCapture?.(pointerId)) overlay.releasePointerCapture(pointerId);
  }
  function cancelDrag() {
    const previous = drag;
    drag = null;
    preview?.remove();
    preview = null;
    if (previous) endCapture(previous.pointerId);
    if (view) paint(view);
  }
  function onPointerDown(event) {
    if (event.button !== 0 || !view?.mappingEditing || !view.canMap || drag) return;
    const modifier = event.shiftKey || event.ctrlKey || event.metaKey;
    const repeatedClick = !modifier && onConfigure && lastClick && event.timeStamp - lastClick.time <= 500
        && Math.hypot(event.clientX - lastClick.x, event.clientY - lastClick.y) <= 5
        && lastClick.source === JSON.stringify(view.currentSource)
        && view.manualFields.some(field => field.id === lastClick.id);
    const target = event.target.closest("[data-pdf-map-field]");
    const field = view.manualFields.find(field => field.id === (repeatedClick ? lastClick.id : target?.dataset.pdfMapField));
    lastClick = null;
    if (field && modifier) {
      event.preventDefault();
      select(field.id, true, { toggle: true });
      return;
    }
    const page = field ? (() => {
      const frame = frameFor(field.page);
      const bounds = frame && pageCanvas(frame)?.getBoundingClientRect();
      return bounds?.width > 0 && bounds.height > 0 ? { frame, bounds } : null;
    })() : pageAtPoint(event.clientX, event.clientY);
    if (!page) return;
    const mode = field ? event.target.closest("[data-pdf-map-resize]") ? "resize" : "move"
      : !tool || tool.value === 'select' ? 'marquee' : 'draw';
    event.preventDefault();
    if (field) select(field.id, true, { preserve: true });
    // Keep the inspector's height stable while drawing a new rectangle.
    // Its selection changes only when the new field is committed.
    const bounds = pageCanvas(page.frame)?.getBoundingClientRect() || page.bounds;
    drag = {
      pointerId: event.pointerId, mode, field, frame: page.frame, bounds, repeatedClick,
      source: JSON.stringify(view.currentSource),
      start: point(event, bounds), clientX: event.clientX, clientY: event.clientY,
      rect: field && { x: field.x, y: field.y, width: field.width, height: field.height },
      fields: field ? mode === 'resize' ? [field] : selectedRows() : [],
      additive: modifier,
    };
    overlay.setPointerCapture?.(event.pointerId);
    if (mode === "draw" || mode === 'marquee') {
      preview = document.createElement("div");
      preview.className = "pdf-sheet__map-preview";
      preview.setAttribute("aria-hidden", "true");
      overlay.append(preview);
    }
  }
  function onPointerMove(event) {
    if (!drag || event.pointerId !== drag.pointerId) return;
    event.preventDefault();
    const end = point(event, drag.bounds);
    const dx = (event.clientX - drag.clientX) / drag.bounds.width;
    const dy = (event.clientY - drag.clientY) / drag.bounds.height;
    if (drag.mode === "draw" || drag.mode === 'marquee') {
      drag.rect = { x: Math.min(drag.start.x, end.x), y: Math.min(drag.start.y, end.y), width: Math.abs(end.x - drag.start.x), height: Math.abs(end.y - drag.start.y) };
      if (drag.mode === 'draw' && snap) drag.rect = snapLayoutRect(drag.rect, gridFor(drag.frame));
      boundsStyle(preview, drag.rect, drag.frame);
    } else if (drag.mode === 'move') {
      drag.edits = moveLayoutFields(drag.fields, dx, dy, gridFor(drag.frame));
      const changes = new Map(drag.edits.map(edit => [edit.id, edit.changes]));
      for (const field of drag.fields) {
        const rect = { ...field, ...(changes.get(field.id) || {}) };
        boundsStyle(boxes.get(field.id), rect, frameFor(field.page));
      }
    } else {
      const field = drag.field;
      drag.rect = { x: field.x, y: field.y, width: clamp(field.width + dx, 0.001, 1 - field.x), height: clamp(field.height + dy, 0.001, 1 - field.y) };
      if (snap) {
        const snapped = snapLayoutRect(drag.rect, gridFor(drag.frame));
        drag.rect.width = clamp(snapped.x + snapped.width - field.x, .001, 1 - field.x);
        drag.rect.height = clamp(snapped.y + snapped.height - field.y, .001, 1 - field.y);
      }
      boundsStyle(boxes.get(field.id), drag.rect, drag.frame);
    }
  }
  function onPointerUp(event) {
    if (!drag || event.pointerId !== drag.pointerId) return;
    onPointerMove(event);
    const gesture = drag;
    drag = null;
    preview?.remove();
    preview = null;
    endCapture(event.pointerId);
    if (gesture.mode === 'move' && Math.hypot(event.clientX - gesture.clientX, event.clientY - gesture.clientY) <= 3) {
      if (gesture.repeatedClick) {
        paint(controller.view);
        onConfigure(gesture.field.id);
        return;
      }
      lastClick = { id: gesture.field.id, x: event.clientX, y: event.clientY,
        time: event.timeStamp, source: gesture.source };
      gesture.edits = [];
    }
    if (gesture.mode === "draw") {
      const rect = gesture.rect;
      if (rect && rect.width >= 0.001 && rect.height >= 0.001 && rect.width * gesture.bounds.width >= 4 && rect.height * gesture.bounds.height >= 4) {
        const id = commit("addManualField", tool.value, t("New field"), gesture.frame.page, rect);
        if (typeof id === "string") { selectedId = id; selectedIds.clear(); selectedIds.add(id); }
      }
    } else if (gesture.mode === 'marquee') {
      const rect = gesture.rect;
      const ids = gesture.additive ? [...selectedIds] : [];
      if (rect && rect.width * gesture.bounds.width >= 3 && rect.height * gesture.bounds.height >= 3)
        for (const field of view.manualFields) {
          if (field.page === gesture.frame.page && field.x < rect.x + rect.width
              && field.x + field.width > rect.x && field.y < rect.y + rect.height
              && field.y + field.height > rect.y) ids.push(field.id);
        }
      select(ids[0] || '', false, { ids: [...new Set(ids)] });
    } else if (gesture.mode === 'move') {
      applyEdits(gesture.edits);
    } else if (["x", "y", "width", "height"].some((key) => gesture.field[key] !== gesture.rect[key])) {
      applyEdits([{ id: gesture.field.id, changes: gesture.rect }]);
    }
    paint(controller.view);
    if (selectedId) boxes.get(selectedId)?.focus({ preventScroll: true });
  }
  overlay?.addEventListener("pointerdown", onPointerDown, { signal: listeners.signal });
  overlay?.addEventListener("pointermove", onPointerMove, { signal: listeners.signal });
  overlay?.addEventListener("pointerup", onPointerUp, { signal: listeners.signal });
  overlay?.addEventListener("pointercancel", (event) => {
    if (drag?.pointerId === event.pointerId) cancelDrag();
  }, { signal: listeners.signal });
  overlay?.addEventListener("lostpointercapture", (event) => {
    if (drag?.pointerId === event.pointerId) cancelDrag();
  }, { signal: listeners.signal });
  overlay?.addEventListener("focusin", (event) => {
    const target = event.target.closest("[data-pdf-map-field]");
    if (!selecting && target && !selectedIds.has(target.dataset.pdfMapField)) select(target.dataset.pdfMapField);
  }, { signal: listeners.signal });
  overlay?.addEventListener("click", (event) => {
    const target = event.target.closest("[data-pdf-map-field]");
    if (event.detail === 0 && target && !selectedIds.has(target.dataset.pdfMapField)) select(target.dataset.pdfMapField);
  }, { signal: listeners.signal });
  root.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && drag) {
      event.preventDefault();
      event.stopPropagation();
      cancelDrag();
      return;
    }
    if (!view?.mappingEditing || !view.canMap) return;
    const editable = event.target.closest('input,textarea,select,[contenteditable=true]');
    const command = event.ctrlKey || event.metaKey;
    if (command && !editable) {
      const key = event.key.toLowerCase();
      const action = key === 'c' ? 'copy' : key === 'v' ? 'paste' : key === 'd' ? 'duplicate'
        : key === 'z' ? event.shiftKey ? 'redo' : 'undo' : key === 'y' ? 'redo' : '';
      if (action) {
        event.preventDefault(); event.stopPropagation();
        cancelDrag(); void runLayoutAction(action); return;
      }
      if (key === 'a') {
        event.preventDefault(); event.stopPropagation();
        const page = selected()?.page || view.pageFrames?.[0]?.page;
        const ids = view.manualFields.filter(field => field.page === page).map(field => field.id);
        select(ids[0] || '', true, { ids }); return;
      }
    }
    if (editable || !event.target.closest("[data-pdf-map-field]")) return;
    const field = selected();
    if (!field) return;
    if (event.key === "Delete" || event.key === "Backspace") {
      event.preventDefault();
      event.stopPropagation();
      removeSelected();
      return;
    }
    const delta = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[event.key];
    const frame = frameFor(field.page);
    if (!delta || !frame) return;
    event.preventDefault();
    event.stopPropagation();
    const step = event.shiftKey ? 10 : 1;
    const grid = gridFor(frame);
    applyEdits(moveLayoutFields(selectedRows(), delta[0] * step * (grid.x || 1 / frame.viewport.width),
      delta[1] * step * (grid.y || 1 / frame.viewport.height), grid));
    paint(controller.view);
  }, { signal: listeners.signal });
  tool?.addEventListener("change", () => {
    cancelDrag();
    overlay.dataset.tool = tool.value;
    showError();
  }, { signal: listeners.signal });
  root.querySelector("[data-pdf-map-add]")?.addEventListener("click", () => {
    if (!view?.mappingEditing || !view.canMap) return;
    const stage = root.querySelector(".pdf-sheet__stage")?.getBoundingClientRect();
    const frames = view.pageFrames || [];
    const frame = frames.find((frame) => {
      const bounds = pageCanvas(frame)?.getBoundingClientRect();
      return bounds && (!stage || bounds.bottom > stage.top && bounds.top < stage.bottom);
    }) || frames[0];
    if (!frame) return;
    const type = tool?.value && tool.value !== "select" ? tool.value : "text";
    const rect = { x: 0.1, y: 0.1, width: type === "checkbox" ? 0.04 : 0.3, height: type === "multiline" ? 0.12 : type === "checkbox" ? 0.04 : 0.04 };
    const id = commit("addManualField", type, t("New field"), frame.page, rect);
    if (typeof id === "string") {
      selectedId = id; selectedIds.clear(); selectedIds.add(id);
      paint(controller.view);
      nameInput?.focus();
      nameInput?.select();
    }
  }, { signal: listeners.signal });
  nameInput?.addEventListener("change", () => {
    if (!selected() || !view.mappingEditing || !view.canMap) return;
    const result = commit("updateManualField", selectedId, { name: nameInput.value });
    nameInput.setAttribute("aria-invalid", String(result === false));
    paint(controller.view);
  }, { signal: listeners.signal });
  for (const input of root.querySelectorAll("[data-pdf-map-property]")) {
    input.addEventListener("change", () => {
      if (!selected() || !view.mappingEditing || !view.canMap) return;
      const value = input.value === "" ? NaN : Number(input.value) / 100;
      const result = commit("updateManualField", selectedId, { [input.dataset.pdfMapProperty]: value });
      input.setAttribute("aria-invalid", String(result === false));
      paint(controller.view);
    }, { signal: listeners.signal });
  }
  root.querySelector("[data-pdf-map-delete]")?.addEventListener("click", removeSelected, { signal: listeners.signal });
  return {
    paint,
    cancelGesture() {
      if (!drag) return false;
      cancelDrag();
      return true;
    },
    destroy() {
      destroyed = true;
      listeners.abort();
      cancelDrag();
      boxes.clear();
    },
  };
}
