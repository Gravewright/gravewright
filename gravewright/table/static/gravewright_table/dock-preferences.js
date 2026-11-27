import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { dockStorageKey, normalizeDockPreferences, moveDockEntry } from './dock-preferences-model.js';

/** Reorder existing controls; native visibility and permissions remain authoritative. */
export function mountDockPreferences(table) {
    const dock = table.querySelector('.game-dock'), settings = table.querySelector('[data-dock-settings]');
    if (!dock || !settings) return () => {};
    const abort = new AbortController(), { signal } = abort, t = createTranslator().t;
    const storageKey = dockStorageKey(table.dataset.profileId, table.dataset.tableId);
    const list = settings.querySelector('[data-dock-settings-list]'), error = settings.querySelector('[data-dock-settings-error]');
    const primary = dock.querySelector('[data-dock-primary]'), menu = dock.querySelector('[data-dock-panel-list]');
    const entries = [...dock.querySelectorAll('[data-dock-entry]')].map(button => {
        const layer = button.closest('[data-shortcut-layer]');
        return { id: button.dataset.dockEntry, group: layer ? `tools:${layer.dataset.shortcutLayer}` : 'panels',
            groupLabel: layer ? `${t('Tools')}: ${t(layer.dataset.shortcutLabel)}` : t('Panels'),
            label: button.getAttribute('aria-label'), button, parent: button.parentElement,
            defaultPlacement: layer || button.parentElement === primary ? 'dock' : 'menu' };
    });
    const byId = new Map(entries.map(entry => [entry.id, entry])), groups = new Map(), rows = new Map();
    const available = entry => !entry.button.hidden && !entry.button.disabled && entry.button.getAttribute('aria-disabled') !== 'true';
    const node = (tag, text, attrs = {}) => {
        const element = document.createElement(tag);
        if (text) element.textContent = text;
        for (const [name, value] of Object.entries(attrs)) element.setAttribute(name, value);
        return element;
    };
    let preferences = normalizeDockPreferences(null, entries);
    function render() {
        const focused = settings.contains(document.activeElement) ? document.activeElement : null;
        for (const [group, section] of groups) {
            const visible = preferences.order[group].filter(id => available(byId.get(id)));
            section.root.hidden = !visible.length;
            for (const id of preferences.order[group]) {
                const entry = byId.get(id), row = rows.get(id), placement = preferences.placement[id];
                row.root.hidden = !available(entry);
                row.choice.value = placement;
                const index = visible.indexOf(id);
                row.up.disabled = index <= 0;
                row.down.disabled = index < 0 || index === visible.length - 1;
                section.list.append(row.root);
                entry.button.toggleAttribute('data-dock-user-hidden', placement === 'hidden');
                // Hiding never changes a module's native `hidden` flag.
                const destination = group !== 'panels' ? entry.parent : placement === 'dock' ? primary : menu;
                destination.append(entry.button);
            }
        }
        for (const group of dock.querySelectorAll('[data-dock-secondary-group]')) {
            const empty = ![...group.children].some(button => !button.hidden && !button.hasAttribute('data-dock-user-hidden'));
            group.toggleAttribute('data-dock-empty', empty);
        }
        dock.querySelector('[data-dock-menu-empty]').hidden = !menu.hasAttribute('data-dock-empty');
        if (focused?.isConnected && !focused.disabled && focused.getClientRects().length) focused.focus({ preventScroll: true });
        else if (focused?.closest('[data-dock-preference-row]')) focused.closest('[data-dock-preference-row]').querySelector('select')?.focus({ preventScroll: true });
    }
    function save(value) {
        error.hidden = true;
        const next = normalizeDockPreferences(value, entries);
        try { localStorage.setItem(storageKey, JSON.stringify(next)); preferences = next; }
        catch { error.hidden = false; }
        render();
    }
    for (const entry of entries) {
        if (!groups.has(entry.group)) {
            const root = node('details', '', { class: 'dock-preference-group' });
            if (entry.group === 'panels') root.open = true;
            const ordered = node('ol');
            root.append(node('summary', entry.groupLabel), ordered);
            if (entry.group === 'panels') list.prepend(root); else list.append(root);
            groups.set(entry.group, { root, list: ordered });
        }
        const root = node('li', '', { class: 'dock-preference-row', 'data-dock-preference-row': entry.id });
        const id = `dock-preference-${entry.id.replaceAll(':', '-')}`;
        const choice = node('select', '', { id, 'data-dock-placement': entry.id });
        for (const [value, label] of entry.group === 'panels'
            ? [['dock', 'Dock'], ['menu', 'Panels menu'], ['hidden', 'Hidden']]
            : [['dock', 'Shown'], ['hidden', 'Hidden']]) choice.append(node('option', t(label), { value }));
        choice.addEventListener('change', () => save({ ...preferences, placement: { ...preferences.placement, [entry.id]: choice.value } }), { signal });
        const controls = node('span', '', { class: 'dock-preference-move' });
        const buttons = [-1, 1].map(direction => {
            const text = t(direction < 0 ? 'Move {action} up' : 'Move {action} down', { action: t(entry.label) });
            const button = node('button', direction < 0 ? '↑' : '↓', { type: 'button', title: text, 'aria-label': text,
                'data-dock-move': direction < 0 ? 'up' : 'down' });
            button.addEventListener('click', () => save(moveDockEntry(preferences, entries, entry.id, direction,
                entries.filter(available).map(row => row.id))), { signal });
            controls.append(button); return button;
        });
        root.append(node('label', t(entry.label), { for: id }), choice, controls);
        rows.set(entry.id, { root, choice, up: buttons[0], down: buttons[1] });
    }
    // Dynamic settings use translated strings directly, like the shortcut editor.
    list.translate = false;
    function read() {
        error.hidden = true;
        try { preferences = normalizeDockPreferences(JSON.parse(localStorage.getItem(storageKey)), entries); }
        catch { preferences = normalizeDockPreferences(null, entries); error.hidden = false; }
        render();
    }
    settings.querySelector('[data-dock-reset]').addEventListener('click', () => save(null), { signal });
    window.addEventListener('storage', event => { if (event.key === storageKey || event.key === null) read(); }, { signal });
    const observer = new MutationObserver(render);
    for (const entry of entries) observer.observe(entry.button, { attributes: true, attributeFilter: ['hidden', 'disabled', 'aria-disabled'] });
    const resize = new ResizeObserver(() => table.style.setProperty('--game-dock-height', `${Math.ceil(dock.getBoundingClientRect().height)}px`));
    resize.observe(dock);
    read();
    return () => { abort.abort(); observer.disconnect(); resize.disconnect(); };
}
