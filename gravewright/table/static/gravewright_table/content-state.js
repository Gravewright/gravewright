// This page snapshot is rendered for the authenticated member, never persisted in browser storage.
const seed = document.getElementById('table-initial-content');
export const contentStates = new Map(Object.entries(seed ? JSON.parse(seed.textContent) : {}));
export const initialContent = name => {
  const state = contentStates.get(name);
  return state ? structuredClone(state) : undefined;
};

// Initial rendering is ordered even when module downloads or socket replies arrive out of order.
const order = ['actors', 'journals', 'items'];
const panels = ['actors-panel', 'journals-panel', null];
const pending = new Map(), readyCallbacks = [];
let sceneComplete = !contentStates.has('maps'), index = 0;
export const contentReady = () => index === order.length;
function drain() {
  if (!sceneComplete) return;
  while (index < order.length) {
    if (panels[index] && !document.getElementById(panels[index])) { index++; continue; }
    const apply = pending.get(order[index]);
    if (!apply) return;
    pending.delete(order[index++]);
    apply();
  }
  for (const callback of readyCallbacks.splice(0)) callback();
}
export function restoreContent(name, apply) {
  if (order.indexOf(name) < index) { apply(); return; }
  pending.set(name, apply);
  drain();
}
export function sceneRestored() { sceneComplete = true; drain(); }
export function afterContentReady(callback) {
  if (contentReady()) callback();
  else readyCallbacks.push(callback);
}
export function clearContent() {
  contentStates.clear();
  pending.clear();
  readyCallbacks.length = 0;
  sceneComplete = true;
  index = order.length;
}
