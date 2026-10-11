import { readReference, referenceMime, openReference } from '/static/gravewright_table/references.js';
import { openFormModal, modalText } from '/static/gravewright_table/form-modal.js';

export function journalPins(surface, board, map, gm, api) {
  const host = document.createElement('div'), status = document.createElement('p');
  host.className = 'journal-map-pins'; status.className = 'journal-map-pins__status';
  status.setAttribute('role', 'alert'); status.hidden = true;
  surface.append(host, status);
  let rows = [], byId = new Map(), closed = false, moving, modal;
  const deleting = new Set();
  const position = event => {
    const rect = surface.getBoundingClientRect(), view = board.viewport();
    return {x: (event.clientX - rect.left - view.x) / view.scale,
      y: (event.clientY - rect.top - view.y) / view.scale};
  };
  const fail = error => { if (!closed) { status.textContent = error.message; status.hidden = false; } };
  async function command(action, data) {
    await api.command('journalPins', action, data);
    if (!closed) await api.read();
  }
  function locate() {
    const view = board.viewport();
    if (!view) return;
    for (const button of host.children) {
      const pin = moving?.pin.id === button.dataset.pinId ? moving.preview : byId.get(button.dataset.pinId);
      if (pin) button.style.transform = `translate(${view.x + pin.x * view.scale}px, ${view.y + pin.y * view.scale}px) translate(-50%, -100%)`;
    }
  }
  function edit(pin) {
    if (!gm) return;
    modal = openFormModal(pin.label, [
      {name: 'public', type: 'checkbox', label: modalText('Show to players', 'Exibir aos jogadores'), value: pin.public},
    ], form => command('update', {id: pin.id, version: pin.version,
      public: form.elements.public.checked}), {key: 'journal-marker-options'});
    modal.classList.add('journal-marker-modal');
    const options = modal;
    const checkbox = options.querySelector('[name=public]');
    checkbox.parentElement.prepend(checkbox);
    const remove = document.createElement('button'); remove.type = 'button';
    remove.dataset.removeMarker = '';
    remove.textContent = modalText('Remove marker', 'Remover marcador');
    remove.onclick = async () => {
      remove.disabled = true;
      try { await command('delete', {id: pin.id, version: pin.version}); options.close(); }
      catch (error) {
        const alert = options.querySelector('[role=alert]');
        alert.textContent = error.message; alert.hidden = false; remove.disabled = false;
      }
    };
    options.querySelector('footer').prepend(remove);
  }
  function update(state) {
    if (closed) return;
    rows = state.journalPins || [];
    byId = new Map(rows.map(pin => [pin.id, pin]));
    const buttons = new Map([...host.children].map(button => [button.dataset.pinId, button]));
    const ids = new Set(rows.map(pin => pin.id));
    for (const button of [...host.children]) if (!ids.has(button.dataset.pinId)) button.remove();
    for (const pin of rows) {
      let button = buttons.get(pin.id);
      if (!button) {
        button = document.createElement('button'); button.type = 'button'; button.dataset.pinId = pin.id;
        host.append(button);
      }
      button.textContent = pin.public ? '◆' : '◇';
      button.className = 'journal-map-pin' + (pin.public ? '' : ' journal-map-pin--private');
      button.setAttribute('aria-label', pin.label);
      if (gm) button.setAttribute('aria-keyshortcuts', 'Delete Backspace');
      button.title = pin.label;
      button.onclick = event => {
        event.stopPropagation();
        if (button.dataset.dragged) { delete button.dataset.dragged; return; }
        void openReference({type: 'journal', id: pin.journalId, pageId: pin.pageId});
      };
      button.oncontextmenu = event => { event.preventDefault(); event.stopPropagation(); edit(pin); };
      button.onpointerdown = event => {
        event.stopPropagation();
        delete button.dataset.dragged;
        if (!gm || event.button !== 0) return;
        const start = position(event);
        moving = {pin, preview: pin, start, button, pointer: event.pointerId, moved: false};
        button.setPointerCapture(event.pointerId);
      };
      button.onpointermove = event => {
        if (!moving || moving.button !== button || event.pointerId !== moving.pointer) return;
        const point = position(event), dx = point.x - moving.start.x, dy = point.y - moving.start.y;
        if (Math.hypot(dx, dy) * board.viewport().scale < 4 && !moving.moved) return;
        moving.moved = true; button.dataset.dragged = 'true';
        moving.preview = {...pin, x: pin.x + dx, y: pin.y + dy}; locate();
      };
      button.onpointerup = event => {
        if (!moving || moving.button !== button) return;
        const gesture = moving; moving = undefined;
        if (button.hasPointerCapture(event.pointerId)) button.releasePointerCapture(event.pointerId);
        if (gesture.moved) void command('update', {id: pin.id, version: pin.version,
          x: gesture.preview.x, y: gesture.preview.y}).catch(error => { locate(); fail(error); });
      };
      button.onpointercancel = () => { moving = undefined; locate(); };
    }
    locate();
  }
  function dragover(event) {
    if (!gm || !event.dataTransfer.types.includes(referenceMime)) return;
    event.preventDefault(); event.dataTransfer.dropEffect = 'copy';
  }
  function drop(event) {
    const ref = readReference(event.dataTransfer);
    if (!ref || ref.type !== 'journal' || !gm) return;
    event.preventDefault(); event.stopImmediatePropagation();
    status.hidden = true;
    const point = position(event);
    void Promise.resolve(window.gravewrightJournals?.flush(ref.id)).then(saved => {
      if (saved === false) throw Error(modalText('Save the journal before creating its marker.', 'Salve o diário antes de criar seu marcador.'));
      if (!closed) return command('create', {journalId: ref.id, pageId: ref.pageId || '', ...point, public: false});
    }).catch(fail);
  }
  function keydown(event) {
    if (closed || event.altKey || event.ctrlKey || event.metaKey ||
        !['Delete', 'Backspace'].includes(event.key)) return;
    const button = event.target.closest?.('.journal-map-pin');
    if (!button || !host.contains(button) || host.closest('[inert]')) return;
    const pin = byId.get(button.dataset.pinId);
    if (!pin) return;
    event.preventDefault(); event.stopImmediatePropagation();
    if (!gm || moving || event.repeat || deleting.has(pin.id)) return;
    deleting.add(pin.id);
    button.setAttribute('aria-busy', 'true');
    void command('delete', {id: pin.id, version: pin.version}).catch(fail).finally(() => {
      deleting.delete(pin.id); button.removeAttribute('aria-busy');
    });
  }
  surface.addEventListener('dragover', dragover, true);
  surface.addEventListener('drop', drop, true);
  window.addEventListener('gravewright:map-viewport', locate);
  window.addEventListener('keydown', keydown, true);
  return {update, destroy() {
    closed = true; moving = undefined; modal?.close(); host.remove(); status.remove();
    surface.removeEventListener('dragover', dragover, true);
    surface.removeEventListener('drop', drop, true);
    window.removeEventListener('gravewright:map-viewport', locate);
    window.removeEventListener('keydown', keydown, true);
  }};
}
