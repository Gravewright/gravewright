/** Read-only descriptions share the owner's authorized state and native modal. */
export function createProgressDetails({ root, kind, signal, text, load, refresh, state, sceneId }) {
  const document = root.ownerDocument, collection = `${kind}s`;
  let active, opening, sequence = 0, destroyed = false;
  const alive = () => !destroyed && !signal.aborted;
  const current = id => state()[collection].find(row => row.id === id);
  const node = (tag, className, value) => {
    const element = document.createElement(tag); if (className) element.className = className;
    if (value !== undefined) element.textContent = value; return element;
  };
  function paint(row) {
    if (!active) return;
    active.title.textContent = row.name;
    const description = kind === 'clock' ? row.description : row.content;
    active.description.textContent = typeof description === 'string' && description.trim() ? description : text('No description provided.');
    active.description.setAttribute('translate', typeof description === 'string' && description.trim() ? 'no' : 'yes');
  }
  function update() {
    if (!active) return;
    const row = current(active.id);
    if (!alive() || !row || active.sceneId !== sceneId()) active.modal.close?.(true);
    else paint(row);
  }
  async function open(id, { fresh = true } = {}) {
    if (!alive()) return;
    if (active?.id === id && active.modal.isConnected) { active.modal.focus(); return active.modal; }
    if (opening?.id === id) return opening.promise;
    active?.modal.close?.(true);
    const token = ++sequence, context = sceneId();
    const promise = (async () => {
      if (fresh) await refresh({ fresh: true });
      if (!alive() || token !== sequence || context !== sceneId() || !current(id)) return;
      const { mountModal } = await load('/static/gravewright_table/modal.js');
      if (!alive() || token !== sequence || context !== sceneId()) return;
      const row = current(id); if (!row) return;
      const modal = node('section', `table-form-modal progress-details ${kind}s-editor`);
      modal.dataset.progressDetails = kind; modal.dataset[`${kind}View`] = id;
      const header = node('header'), title = node('strong'), close = node('button', '', '×');
      title.id = `progress-details-${crypto.randomUUID()}`; title.dataset.progressDetailsTitle = ''; title.setAttribute('translate', 'no');
      modal.setAttribute('aria-labelledby', title.id); close.type = 'button'; close.setAttribute('aria-label', text('Close'));
      const body = node('div', 'table-form-modal__body'), description = node('p', 'progress-details__description');
      description.dataset.progressDescription = ''; description.dataset[kind === 'clock' ? 'clockDescription' : 'clueContent'] = '';
      header.append(title, close); body.append(description); modal.append(header, body);
      const controller = new AbortController();
      close.addEventListener('click', () => modal.close(), { signal: controller.signal });
      active = { id, modal, title, description, sceneId: context }; paint(row);
      modal.addEventListener('close', () => { controller.abort(); if (active?.modal === modal) active = undefined; }, { once: true });
      mountModal(modal, { nested: true });
      if (!alive()) modal.close?.(true);
      return modal;
    })().finally(() => { if (opening?.token === token) opening = undefined; });
    opening = { id, token, promise }; return promise;
  }
  function destroy() {
    if (destroyed) return;
    destroyed = true; ++sequence; opening = undefined; active?.modal.close?.(true); active = undefined;
  }
  signal.addEventListener('abort', destroy, { once: true });
  return { open, update, destroy };
}

export function bindProgressDetailsName(heading, { id, kind, text, open, report, signal }) {
  heading.dataset.progressDetailsTrigger = kind;
  heading.setAttribute('tabindex', '0'); heading.setAttribute('role', 'button'); heading.setAttribute('aria-keyshortcuts', 'Enter Space');
  const hint = text('Double-click the name or press Enter or Space to open details.');
  heading.setAttribute('aria-description', hint); heading.title = hint;
  const show = () => Promise.resolve(open(id)).catch(report);
  heading.addEventListener('dblclick', event => { event.preventDefault(); event.stopPropagation(); void show(); }, { signal });
  heading.addEventListener('keydown', event => {
    if (!['Enter', ' '].includes(event.key) || event.repeat || event.ctrlKey || event.metaKey || event.altKey) return;
    event.preventDefault(); event.stopPropagation(); void show();
  }, { signal });
}
