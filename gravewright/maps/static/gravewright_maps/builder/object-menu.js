/** A disposable object menu with a keyboard-accessible preset list. */
export function createObjectMenu({ t, signal, onError = () => {} }) {
    if (!document.querySelector('link[data-builder-object-menu-css]')) {
        const link = document.createElement('link'); link.rel = 'stylesheet'; link.dataset.builderObjectMenuCss = '';
        link.href = new URL('./object-menu.css', import.meta.url).href; document.head.append(link);
    }
    let menu, local, pageScope, origin, position, pages;
    function close(restoreFocus = true) {
        if (!menu) return;
        pageScope.abort(); local.abort(); menu.remove(); menu = null;
        if (restoreFocus && origin?.isConnected) origin.focus({ preventScroll: true });
    }
    const controls = () => [...menu.querySelectorAll('[role=menuitem]:not(:disabled)')];
    function place() {
        const box = menu.getBoundingClientRect();
        menu.style.left = `${Math.max(8, Math.min(position.x, innerWidth - box.width - 8))}px`;
        menu.style.top = `${Math.max(8, Math.min(position.y, innerHeight - box.height - 8))}px`;
    }
    function render(focusId) {
        pageScope?.abort(); pageScope = new AbortController();
        const page = pages.at(-1); menu.replaceChildren();
        const heading = document.createElement('strong'); heading.textContent = page.label;
        heading.className = 'map-builder-object-menu__title'; heading.translate = false; menu.append(heading);
        const rows = pages.length > 1 ? [{ id: 'back', label: t('Back'), action: () => { const previous = pages.pop(); render(previous.parentId); } }, ...page.entries] : page.entries;
        for (const entry of rows) {
            const button = document.createElement('button'); button.type = 'button'; button.setAttribute('role', 'menuitem');
            button.dataset.builderObjectAction = entry.id; button.disabled = Boolean(entry.disabled);
            button.classList.toggle('gw-folder-menu__danger', Boolean(entry.danger));
            const name = document.createElement('span'); name.textContent = entry.label; button.append(name);
            if (entry.children) {
                button.setAttribute('aria-haspopup', 'menu');
                const arrow = document.createElement('span'); arrow.textContent = '›'; arrow.setAttribute('aria-hidden', 'true'); button.append(arrow);
            }
            const choose = () => {
                if (entry.children) {
                    pages.push({ label: entry.label, entries: entry.children, parentId: entry.id }); render(); return;
                }
                if (entry.id === 'back') { entry.action(); return; }
                close();
                try { Promise.resolve(entry.action()).catch(onError); } catch (error) { onError(error); }
            };
            button.addEventListener('click', choose, { signal: pageScope.signal });
            button.addEventListener('keydown', event => {
                if (event.key === 'ArrowRight' && entry.children) { event.preventDefault(); event.stopPropagation(); choose(); }
            }, { signal: pageScope.signal }); menu.append(button);
        }
        place();
        (controls().find(button => button.dataset.builderObjectAction === focusId) || controls()[0] || menu).focus({ preventScroll: true });
    }
    function open({ x, y, entries, label, returnTo }) {
        close(false); if (signal.aborted || !entries.length) return;
        origin = returnTo || document.activeElement; position = { x, y }; local = new AbortController();
        pages = [{ label, entries }];
        menu = document.createElement('menu'); menu.className = 'gw-folder-menu map-builder-object-menu';
        menu.dataset.builderObjectMenu = ''; menu.setAttribute('role', 'menu'); menu.setAttribute('aria-label', t('Object options')); menu.tabIndex = -1;
        document.body.append(menu); render();
        const outside = event => { if (!menu.contains(event.target)) close(false); };
        document.addEventListener('pointerdown', outside, { signal: local.signal, capture: true });
        document.addEventListener('contextmenu', outside, { signal: local.signal, capture: true });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' || event.key === 'Tab') {
                event.preventDefault(); event.stopImmediatePropagation(); close(); return;
            }
            if (event.key === 'ArrowLeft' && pages.length > 1) {
                event.preventDefault(); event.stopImmediatePropagation(); const previous = pages.pop(); render(previous.parentId); return;
            }
            if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault(); event.stopImmediatePropagation();
            const items = controls(), index = items.indexOf(document.activeElement);
            const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1
                : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
            items[next]?.focus();
        }, { signal: local.signal, capture: true });
        window.addEventListener('resize', () => close(), { signal: local.signal });
        window.addEventListener('blur', () => close(false), { signal: local.signal });
        document.addEventListener('wheel', event => { if (!menu.contains(event.target)) close(false); }, { signal: local.signal, capture: true, passive: true });
    }
    signal.addEventListener('abort', () => close(false), { once: true });
    return { open, close, get isOpen() { return Boolean(menu); } };
}
