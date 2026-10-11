// Shared floating-window movement, focus and per-member layout preferences.
(() => {
const cleanups = new WeakMap(), windows = new Set(), mounted = new Set();
const restoredWindows = new WeakSet(), initialStyles = new WeakMap();
const table = document.querySelector('#table-workspace');
const scope = table?.dataset.profileId && table?.dataset.tableId
    ? `gravewright.windows.v1.${table.dataset.profileId}.${table.dataset.tableId}` : null;
let layouts = new Map();
try { if (scope) layouts = new Map(JSON.parse(localStorage.getItem(scope) || '[]')); } catch { }
const text = (en, pt) => document.documentElement.lang.toLowerCase().startsWith('pt') ? pt : en;
const visible = element => element.isConnected && !element.hidden && element.getClientRects().length > 0;
const minimized = element => element.hasAttribute('data-window-minimized') || [...element.classList].some(name => name.endsWith('--minimized'));
function mount(element) {
    const doc = element.ownerDocument, view = doc.defaultView;
    const originalZ = element.style.zIndex;
    const key = element.dataset.windowKey || element.id || [...element.classList].filter(name => !name.startsWith('gw-') && !name.includes('--')).join('.');
    const entry = { element, base: Number.parseInt(view.getComputedStyle(element).zIndex) || 7 };
    windows.add(entry);
    const initial = initialStyles.get(element) || Object.fromEntries(['position','width','height','left','top','right','bottom','transform'].map(name => [name, element.style[name]]));
    initialStyles.set(element, initial);
    let seen = restoredWindows.has(element), wasVisible = false, wasMinimized = minimized(element), resizing = false, saveTimer = 0;
    function raise() {
        if (!visible(element)) return;
        windows.delete(entry); windows.add(entry);
        const peers = [...windows].filter(row => row.element.ownerDocument === doc && row.base === entry.base && visible(row.element));
        for (const [index, peer] of peers.entries()) {
            peer.element.classList.toggle('gw-window--focused', peer === entry);
            peer.element.style.zIndex = String(peer.base + index);
        }
    }
    function place(value) {
        if (!value || !['x','y','width','height'].every(name => Number.isFinite(value[name])) || value.width < 80 || value.height < 30) return;
        const width = Math.min(value.width, view.innerWidth - 16), height = Math.min(value.height, view.innerHeight - 16);
        Object.assign(element.style, {position:'fixed',width:`${width}px`,height:`${height}px`,
            left:`${Math.max(8, Math.min(value.x, view.innerWidth - width - 8))}px`,
            top:`${Math.max(8, Math.min(value.y, view.innerHeight - height - 8))}px`,right:'auto',bottom:'auto',transform:'none'});
    }
    function save() {
        if (!scope || !key || element.ownerDocument !== document || !visible(element) || minimized(element)) return;
        const box = element.getBoundingClientRect();
        layouts.delete(key); layouts.set(key, {x:box.left,y:box.top,width:box.width,height:box.height});
        while (layouts.size > 100) layouts.delete(layouts.keys().next().value);
        try { localStorage.setItem(scope, JSON.stringify([...layouts])); } catch { }
    }
    function restore() {
        const isMinimized = minimized(element);
        if (wasMinimized && !isMinimized) save();
        wasMinimized = isMinimized;
        const button = element.querySelector('[data-window-action=minimize]');
        if (button) {
            const on = minimized(element), label = on ? text('Restore','Restaurar') : text('Minimize','Minimizar');
            const state = on ? 'minimized' : 'expanded';
            if (button.dataset.windowState !== state) { button.dataset.windowState = state; button.setAttribute('aria-label', label); button.title = label; button.textContent = on ? '□' : '−'; }
        }
        const on = visible(element);
        if (on && !wasVisible) {
            if (!seen && layouts.has(key)) place(layouts.get(key));
            seen = true; restoredWindows.add(element); raise();
        }
        wasVisible = on;
    }
    element.classList.add('gw-movable-resizable');
    const handle = element.querySelector('[data-move-handle]') ?? element.querySelector('header') ?? element;
    handle.classList.add('gw-move-handle');
    let stopDrag = () => {};
    const pointerDown = event => {
        if (event.button !== 0 || event.target.closest('button,input,select,textarea,a,[data-no-move]')) return;
        stopDrag();
        const bounds = element.getBoundingClientRect(), offsetX = event.clientX - bounds.left, offsetY = event.clientY - bounds.top;
        if (minimized(element)) Object.assign(element.style, {position:'fixed',left:`${bounds.left}px`,top:`${bounds.top}px`,right:'auto',bottom:'auto',transform:'none'});
        else place({x:bounds.left,y:bounds.top,width:bounds.width,height:bounds.height});
        const move = next => {
            if (next.pointerId !== event.pointerId) return;
            element.style.left = `${Math.min(view.innerWidth - 55, Math.max(55 - element.offsetWidth, next.clientX - offsetX))}px`;
            element.style.top = `${Math.min(view.innerHeight - 55, Math.max(0, next.clientY - offsetY))}px`;
        };
        const up = () => {
            doc.removeEventListener('pointermove', move); doc.removeEventListener('pointerup', up); doc.removeEventListener('pointercancel', up); view.removeEventListener('blur', up);
            handle.classList.remove('gw-move-handle--active'); stopDrag = () => {}; save();
        };
        handle.classList.add('gw-move-handle--active');
        doc.addEventListener('pointermove', move); doc.addEventListener('pointerup', up); doc.addEventListener('pointercancel', up); view.addEventListener('blur', up);
        stopDrag = up; event.preventDefault();
    };
    const resize = () => { if (visible(element) && !minimized(element)) { const box = element.getBoundingClientRect(); place({x:box.x,y:box.y,width:box.width,height:box.height}); } };
    const beginResize = event => { const box = element.getBoundingClientRect(); resizing = event.button === 0 && event.clientX >= box.right - 20 && event.clientY >= box.bottom - 20; };
    const endResize = () => { if (resizing) { resizing = false; clearTimeout(saveTimer); saveTimer = setTimeout(save, 0); } };
    const observer = new ResizeObserver(() => { if (resizing) { clearTimeout(saveTimer); saveTimer = setTimeout(save, 150); } restore(); });
    observer.observe(element);
    const visibility = new MutationObserver(restore);
    visibility.observe(element, {attributes:true,attributeFilter:['hidden','style','class','data-window-minimized']});
    const header = element.querySelector('header');
    const controls = [];
    if (header) {
        const host = header.querySelector('.gw-window__controls') || [...header.children].find(child => child.tagName === 'DIV') || header;
        function control(label, action, glyph) { const button = doc.createElement('button'); button.type='button'; button.className='gw-window__control'; button.setAttribute('aria-label',label); button.title=label; button.dataset.windowAction=action; button.textContent=glyph; host.append(button); controls.push(button); return button; }
        const reset = control(text('Reset window layout','Redefinir posição e tamanho'), 'reset', '↺');
        reset.onclick = () => { layouts.delete(key); try { if(scope) localStorage.setItem(scope,JSON.stringify([...layouts])); } catch {} Object.assign(element.style,initial); resize(); };
        const firstControl = [...host.children].find(child => child !== reset && child.tagName === 'BUTTON');
        if (firstControl) host.insertBefore(reset, firstControl);
        if (element.classList.contains('game-panel') && !header.querySelector('[data-map-panel=minimize],[data-actor-panel=minimize],[data-journal-directory=minimize],[data-visibility-action=minimize],[data-action=minimize],[data-window-action=minimize]')) {
            const button = control(text('Minimize','Minimizar'),'minimize','−');
            button.onclick = () => { const on = element.toggleAttribute('data-window-minimized'); button.setAttribute('aria-label',on?text('Restore','Restaurar'):text('Minimize','Minimizar')); button.title=button.getAttribute('aria-label'); button.textContent=on?'□':'−'; };
        }
    }
    element.addEventListener('pointerdown', raise, true); element.addEventListener('focusin', raise); element.addEventListener('pointerdown', beginResize);
    handle.addEventListener('pointerdown', pointerDown); doc.addEventListener('pointerup', endResize); view.addEventListener('resize', resize);
    restore();
    cleanups.set(element, () => {
        stopDrag(); clearTimeout(saveTimer); observer.disconnect(); visibility.disconnect(); controls.forEach(control => control.remove()); windows.delete(entry);
        element.style.zIndex=originalZ; element.classList.remove('gw-window--focused'); element.removeEventListener('pointerdown',raise,true); element.removeEventListener('focusin',raise); element.removeEventListener('pointerdown',beginResize);
        handle.removeEventListener('pointerdown',pointerDown); doc.removeEventListener('pointerup',endResize); view.removeEventListener('resize',resize);
    });
}
function syncWindows() {
    for (const element of mounted) if (!element.isConnected || element.ownerDocument !== document) { cleanups.get(element)?.(); cleanups.delete(element); mounted.delete(element); }
    document.querySelectorAll('[data-movable]').forEach(element => { if (!mounted.has(element)) { mount(element); mounted.add(element); } });
}
new MutationObserver(syncWindows).observe(document.documentElement,{childList:true,subtree:true});
syncWindows();
})();
