import { openFormModal, modalText } from './form-modal.js';
import { afterContentReady } from './content-state.js';

export const referenceMime = 'application/x-gravewright-reference';
const kinds = new Set(['actor', 'item', 'journal']);
const uuid = /^[a-f\d]{8}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{12}$/i;
export function readReference(transfer) {
  try {
    const ref = JSON.parse(transfer.getData(referenceMime));
    if (kinds.has(ref.type) && uuid.test(ref.id) && typeof ref.title === 'string' &&
        (!ref.pageId || typeof ref.pageId === 'string' && ref.pageId.length <= 120) &&
        ref.tableId === document.getElementById('table-workspace').dataset.tableId) return ref;
  } catch { /* Other drags belong to their own tools. */ }
  return null;
}
export function writeReference(transfer, ref) {
  transfer.setData(referenceMime, JSON.stringify({...ref,
    tableId: document.getElementById('table-workspace').dataset.tableId}));
}
export function referenceHref(ref) {
  const tableId = document.getElementById('table-workspace').dataset.tableId;
  return `/game/${tableId}?document=${ref.type}:${ref.id}` + (ref.pageId ? '&page=' + encodeURIComponent(ref.pageId) : '');
}
export function openReference(ref) {
  if (ref.type === 'journal') return window.gravewrightJournals?.open(ref.id, ref.pageId);
  if (ref.type === 'actor') return window.gravewrightActors?.open(ref.id);
  if (ref.type === 'item') return window.gravewrightItems?.open(ref.id);
}
export function followReference(event) {
  const link = event.target.closest('a[href]');
  if (!link) return false;
  const url = new URL(link.href, location.href);
  const ref = fromURL(url);
  if (!ref) return false;
  event.preventDefault(); event.stopPropagation();
  void openReference(ref);
  return true;
}
function fromURL(url) {
  const tableId = document.getElementById('table-workspace')?.dataset.tableId;
  const [type, id] = (url.searchParams.get('document') || '').split(':');
  if (url.origin !== location.origin || url.pathname !== '/game/' + tableId || !kinds.has(type) || !uuid.test(id || '')) return null;
  return {type, id, pageId: url.searchParams.get('page') || ''};
}
let openedInitial = false;
function initialReference() {
  if (openedInitial) return;
  const ref = fromURL(new URL(location.href));
  if (!ref) return;
  const ready = ref.type === 'journal' ? window.gravewrightJournals : ref.type === 'actor' ? window.gravewrightActors : window.gravewrightItems;
  if (ready) { openedInitial = true; void openReference(ref); }
}
for (const event of ['gravewright:connected', 'gravewright:journals', 'gravewright:actors', 'gravewright:items']) window.addEventListener(event, initialReference);
afterContentReady(() => queueMicrotask(initialReference));

export function pickReference(insert) {
  let selected, timer, requestId;
  const modal = openFormModal(modalText('Insert reference', 'Inserir referência'), [
    {name: 'query', label: modalText('Search sheets, items and journals', 'Buscar fichas, itens e diários'), type: 'search'},
  ], () => {
    if (!selected) throw Error(modalText('Choose a document.', 'Selecione um documento.'));
    insert(selected);
  }, {key: 'reference-picker', submitLabel: modalText('Insert', 'Inserir')});
  const input = modal.querySelector('input'), results = document.createElement('div');
  results.className = 'document-reference-results';
  results.setAttribute('aria-live', 'polite');
  modal.querySelector('[data-fields]').append(results);
  modal.querySelector('[type=submit]').disabled = true;
  input.oninput = () => {
    clearTimeout(timer); selected = undefined; requestId = undefined;
    modal.querySelector('[type=submit]').disabled = true;
    results.textContent = modalText('Type at least two characters.', 'Digite pelo menos dois caracteres.');
    if (input.value.trim().length < 2) return;
    timer = setTimeout(() => {
      requestId = crypto.randomUUID();
      results.textContent = modalText('Searching…', 'Buscando…');
      if (!window.gravewrightRealtime.tableTool('table.search', {query: input.value.slice(0, 200), requestId}))
        results.textContent = modalText('Connect to the table to search.', 'Conecte-se à mesa para buscar.');
    }, 180);
  };
  const receive = ({detail}) => {
    if (detail.requestId !== requestId) return;
    results.replaceChildren();
    for (const row of detail.results.filter(row => kinds.has(row.type))) {
      const button = document.createElement('button'); button.type = 'button';
      button.textContent = row.title; button.setAttribute('aria-pressed', 'false');
      button.onclick = () => {
        selected = row;
        for (const choice of results.children) choice.setAttribute('aria-pressed', String(choice === button));
        modal.querySelector('[type=submit]').disabled = false;
      };
      results.append(button);
    }
    if (!results.children.length) results.textContent = modalText('No results.', 'Nenhum resultado.');
  };
  const failed = ({detail}) => { if (detail.requestId === requestId) results.textContent = detail.message; };
  window.addEventListener('gravewright:table.search', receive);
  window.addEventListener('gravewright:table.tool_error', failed);
  modal.addEventListener('close', () => {
    clearTimeout(timer);
    window.removeEventListener('gravewright:table.search', receive);
    window.removeEventListener('gravewright:table.tool_error', failed);
  }, {once: true});
  input.oninput();
  return modal;
}
