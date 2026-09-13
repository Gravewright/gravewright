// Movable window behavior ported from the original Gravewright UI (Apache-2.0).
(() => {
const cleanups = new WeakMap();
const windows = new Set();
function mount(element) {
    const doc = element.ownerDocument, view = doc.defaultView;
    const originalZ = element.style.zIndex;
    const entry = { element, base: Number.parseInt(view.getComputedStyle(element).zIndex) || 7 };
    windows.add(entry);
    function raise() {
        const doc = element.ownerDocument;
        const peers = [...windows].filter(w => w.element.ownerDocument === doc && w.base === entry.base);
        windows.delete(entry);
        windows.add(entry);
        for (const peer of peers)
            peer.element.classList.toggle('gw-window--focused', peer === entry);
        [...windows].filter(w => w.element.ownerDocument === doc && w.base === entry.base).forEach((w, index) => { w.element.style.zIndex = String(w.base + index); });
    }
    element.classList.add('gw-movable-resizable');
    const handle = element.querySelector('[data-move-handle]') ?? element;
    handle.classList.add('gw-move-handle');
    let stopDrag = () => { };
    const pointerDown = (event) => {
        if (event.button !== 0 || event.target.closest('button,input,select,textarea,a,[data-no-move]'))
            return;
        stopDrag();
        const doc = element.ownerDocument, view = doc.defaultView;
        const bounds = element.getBoundingClientRect(), offsetX = event.clientX - bounds.left, offsetY = event.clientY - bounds.top;
        Object.assign(element.style, { position: 'fixed', width: `${bounds.width}px`, height: `${bounds.height}px`, left: `${bounds.left}px`, top: `${bounds.top}px`, right: 'auto', bottom: 'auto' });
        const move = (next) => {
            if (next.pointerId !== event.pointerId)
                return;
            element.style.left = `${Math.min(view.innerWidth - 55, Math.max(55 - element.offsetWidth, next.clientX - offsetX))}px`;
            element.style.top = `${Math.min(view.innerHeight - 55, Math.max(0, next.clientY - offsetY))}px`;
        };
        const up = () => { doc.removeEventListener('pointermove', move); doc.removeEventListener('pointerup', up); doc.removeEventListener('pointercancel', up); view.removeEventListener('blur', up); handle.classList.remove('gw-move-handle--active'); stopDrag = () => { }; };
        stopDrag = up;
        handle.classList.add('gw-move-handle--active');
        doc.addEventListener('pointermove', move);
        doc.addEventListener('pointerup', up);
        doc.addEventListener('pointercancel', up);
        view.addEventListener('blur', up);
        event.preventDefault();
    };
    const resize = () => { const box = element.getBoundingClientRect(); if (box.top > view.innerHeight - 55)
        element.style.top = `${Math.max(0, view.innerHeight - 55)}px`; if (box.left > view.innerWidth - 55) {
        element.style.left = `${Math.max(0, view.innerWidth - 55)}px`;
        element.style.right = 'auto';
    } };
    element.addEventListener('pointerdown', raise, true);
    element.addEventListener('focusin', raise);
    handle.addEventListener('pointerdown', pointerDown);
    view.addEventListener('resize', resize);
    raise();
    cleanups.set(element, () => { stopDrag(); windows.delete(entry); element.style.zIndex = originalZ; element.classList.remove('gw-window--focused'); element.removeEventListener('pointerdown', raise, true); element.removeEventListener('focusin', raise); handle.removeEventListener('pointerdown', pointerDown); view.removeEventListener('resize', resize); });
}

const mounted = new Set();
function syncWindows() {
  for (const el of mounted) if (!el.isConnected) { cleanups.get(el)?.(); cleanups.delete(el); mounted.delete(el); }
  document.querySelectorAll('[data-movable]').forEach(el => { if (!mounted.has(el)) { mount(el); mounted.add(el); } });
}
new MutationObserver(syncWindows).observe(document.documentElement,{childList:true,subtree:true});
syncWindows();

})();
// Browser-only helpers; Django and Datastar own the page and form workflows.
// Format before Datastar reads the input so its signal and the submitted value agree.
document.addEventListener('input', event => {
  const input = event.target;
  if (!input.matches('input[data-code-mask]') || event.isComposing) return;
  const start = input.selectionStart ?? input.value.length;
  const before = input.value.slice(0, start).replace(/[^a-z0-9]/gi, '').length;
  const code = input.value.replace(/[^a-z0-9]/gi, '').toUpperCase().slice(0, 8);
  const formatted = code.length > 4 ? `${code.slice(0, 4)}-${code.slice(4)}` : code;
  if (input.value === formatted) return;
  input.value = formatted;
  const caret = Math.min(formatted.length, before + (before > 4 ? 1 : 0));
  input.setSelectionRange(caret, caret);
}, true);

window.gravewrightInside = {
  location(target, search, system) {
    const url = new URL(target, window.location.origin);
    if (search) url.searchParams.set('search', search);
    if (system) url.searchParams.set('system', system);
    return url.pathname + url.search;
  },
  conditionLayout() {
    try { return localStorage.getItem('gravewright.conditions.anonymous') === 'classic' ? 'classic' : 'gravewright'; }
    catch { return 'gravewright'; }
  },
  selectConditions(mode) {
    try { localStorage.setItem('gravewright.conditions.anonymous', mode); } catch {}
  },
  cover(file, element) {
    if (!file) return;
    const target = element.closest('#campaign-dialog');
    const emit = detail => target?.dispatchEvent(new CustomEvent('cover-ready', {detail}));
    if (!['image/png','image/jpeg','image/webp'].includes(file.type) || file.size > 5000000) {
      emit({image:'',name:'',size:0,error:true}); return;
    }
    const reader = new FileReader();
    reader.onload = () => emit({image:reader.result,name:file.name,size:file.size,error:false});
    reader.onerror = () => emit({image:'',name:'',size:0,error:true});
    reader.readAsDataURL(file);
  }
};
