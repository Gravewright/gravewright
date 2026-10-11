// One Escape closes one surface through its existing close lifecycle.
const handlers = new WeakMap();
const documents = new WeakSet();
const surfaces = '[role="dialog"],[role="alertdialog"],[data-movable],.gw-window,.game-panel,[data-escape-surface]';
const visible = element => element.isConnected && !element.closest('[hidden],[inert]') && element.getClientRects().length > 0 && element.ownerDocument.defaultView.getComputedStyle(element).visibility !== 'hidden';

export function registerEscapeClose(element, close) {
  const marked = !element.matches(surfaces);
  if (marked) element.setAttribute('data-escape-surface', '');
  handlers.set(element, close);
  bindEscape(element.ownerDocument);
  return () => {
    if (handlers.get(element) !== close) return;
    handlers.delete(element);
    if (marked) element.removeAttribute('data-escape-surface');
  };
}

function closeButton(element) {
  const buttons = [...element.querySelectorAll('button,[role="button"]')]
    .filter(button => visible(button) && button.closest(surfaces) === element);
  return buttons.find(button => {
    return button.hasAttribute('data-close') || button.hasAttribute('data-modal-close') || button.hasAttribute('data-escape-close')
      || [...button.attributes].some(attr => attr.name.startsWith('data-') && ['close', 'close-browser'].includes(attr.value))
      || button.matches('.directory-dialog__close,.gw-table-modal__close')
      || /^(close|fechar|cerrar)\b/i.test(button.getAttribute('aria-label') || '');
  }) || buttons.find(button => button.hasAttribute('data-cancel') || /^(cancel|cancelar)$/i.test(button.textContent.trim()));
}

function layer(element) {
  const values = [];
  const view = element.ownerDocument.defaultView;
  for (let node = element; node; node = node.parentElement) {
    const style = view.getComputedStyle(node);
    // Ancestor stacking contexts matter more than the window's own z-index.
    if (style.zIndex !== 'auto') values.unshift(Number(style.zIndex) || 0);
  }
  return values;
}

export function bindEscape(doc = document) {
  if (documents.has(doc)) return;
  documents.add(doc);
  doc.defaultView.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || event.defaultPrevented || event.isComposing) return;
    if (event.repeat) { event.preventDefault(); event.stopImmediatePropagation(); return; }
    // Menus and editor suggestions handle Escape before their containing window.
    if ([...doc.querySelectorAll('[role="menu"],.directory-context-menu,.gw-folder-menu')].some(visible)) return;
    const candidates = [...doc.querySelectorAll(surfaces)].filter(visible).map(element => ({
      element, close: handlers.get(element), button: closeButton(element), layer: layer(element),
    })).filter(row => row.close || row.button);
    // A modal always owns the keyboard ahead of the windows behind it.
    const modals = candidates.filter(row => row.element.getAttribute('aria-modal') === 'true');
    const choices = modals.length ? modals : candidates;
    choices.sort((a, b) => {
      for (let index = 0; index < Math.max(a.layer.length, b.layer.length); index++) {
        const difference = (b.layer[index] || 0) - (a.layer[index] || 0);
        if (difference) return difference;
      }
      const focused = Number(b.element.contains(doc.activeElement)) - Number(a.element.contains(doc.activeElement));
      return focused || (a.element.compareDocumentPosition(b.element) & 4 ? 1 : -1);
    });
    const top = choices[0];
    if (!top) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (top.close) top.close();
    else top.button.click();
  }, true);
}

bindEscape();
