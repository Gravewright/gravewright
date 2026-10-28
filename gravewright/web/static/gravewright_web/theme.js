// Apply before the page paints; only a palette identifier is stored locally.
(() => {
  const key = 'gravewright.interface-theme';
  const themes = new Set(['classic', 'ocean', 'forest', 'amethyst']);
  const root = document.documentElement;
  const scope = new AbortController();
  let saved = 'classic';
  try { saved = localStorage.getItem(key) || saved; } catch { /* Storage may be unavailable. */ }
  function sync(container = document) {
    if (container.matches?.('[data-theme-choice]')) container.checked = container.value === root.dataset.theme;
    container.querySelectorAll('[data-theme-choice]').forEach(input => {
      input.checked = input.value === root.dataset.theme;
    });
  }
  function apply(value) {
    root.dataset.theme = themes.has(value) ? value : 'classic';
    sync();
  }
  apply(saved);
  document.addEventListener('change', event => {
    if (!event.target.matches('[data-theme-choice]')) return;
    apply(event.target.value);
    let failed = false;
    try { localStorage.setItem(key, root.dataset.theme); } catch { failed = true; }
    document.querySelectorAll('[data-theme-storage-error]').forEach(node => { node.hidden = !failed; });
  }, { signal: scope.signal });
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) apply(event.newValue);
  }, { signal: scope.signal });
  // The Inside shell can be replaced by a Datastar navigation response.
  const observer = new MutationObserver(records => {
    for (const record of records) for (const node of record.addedNodes) {
      if (node.nodeType === Node.ELEMENT_NODE) sync(node);
    }
  });
  if (location.pathname === '/inside') observer.observe(root, { childList: true, subtree: true });
  window.addEventListener('pagehide', event => {
    if (!event.persisted) { observer.disconnect(); scope.abort(); }
  }, { signal: scope.signal });
})();
