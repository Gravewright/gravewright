import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { combination, validCombination, reserved, conflicts, displayCombination } from './shortcuts-model.js';

/** Per-profile keyboard mappings for the table's existing executable controls. */
export function mountShortcuts(table) {
    const panel = table.querySelector('[data-shortcut-settings]');
    if (!panel) return () => {};
    // Static headings are rendered by Jinja; dynamic labels use the host adapter.
    panel.translate = false;
    const abort = new AbortController(), { signal } = abort;
    const t = createTranslator().t;
    const storageKey = `gravewright.shortcuts.${table.dataset.profileId}`;
    const error = panel.querySelector('[data-shortcut-error]'), list = panel.querySelector('[data-shortcut-list]');
    const entries = [], fields = new Map();
    let bindings = {};
    const visible = node => Boolean(node && node.getClientRects().length > 0 && !node.closest('[hidden],[inert]'));
    for (const button of table.querySelectorAll('.game-dock button[aria-keyshortcuts], .game-menubar [data-menubar-shortcut]')) {
        if (button.getAttribute('aria-disabled') === 'true') continue;
        const group = button.closest('[data-shortcut-layer]'), scope = group?.dataset.shortcutLayer;
        const action = button.dataset.menubarShortcut || button.dataset.dockTool || button.dataset.panel
            || (button.hasAttribute('data-open-command-palette') ? 'search' : 'settings');
        const id = scope ? `tool:${scope}:${action}` : `window:${action}`;
        entries.push({ id, scope, group: group?.dataset.shortcutLabel || (button.dataset.menubarShortcut ? 'Layers' : t('Windows')), button,
            label: button.getAttribute('aria-label'), defaultKey: button.getAttribute('aria-keyshortcuts') });
    }
    const node = (tag, text, attrs = {}) => {
        const result = document.createElement(tag);
        if (text) result.textContent = text;
        for (const [key, value] of Object.entries(attrs)) result.setAttribute(key, value);
        return result;
    };
    function apply() {
        for (const entry of entries) {
            const value = bindings[entry.id] ?? entry.defaultKey;
            entry.button.setAttribute('aria-keyshortcuts', value);
            if (entry.id === 'window:search') table.querySelector('[data-command-palette]')?.setAttribute('aria-keyshortcuts', value);
            if (entry.button.dataset.menubarShortcut) entry.button.title = `${entry.label}${value ? ' · ' + displayCombination(value) : ''}`;
            const tip = entry.button.querySelector('kbd');
            if (tip) { tip.textContent = displayCombination(value); tip.hidden = !value; }
            const field = fields.get(entry.id);
            if (field) { field.value = value ? displayCombination(value) : t('Unassigned'); field.dataset.recording = 'false'; }
        }
    }
    function read() {
        bindings = {};
        try {
            const stored = JSON.parse(localStorage.getItem(storageKey));
            if (stored && typeof stored === 'object' && !Array.isArray(stored)) {
                for (const [id, value] of Object.entries(stored)) if (/^(?:tool:[a-z-]+:[a-z-]+|window:[a-z-]+)$/.test(id)
                    && (value === '' || validCombination(value) && !reserved(value))) bindings[id] = value;
            }
        } catch {}
        apply();
    }
    function save(next) {
        error.hidden = true;
        try { localStorage.setItem(storageKey, JSON.stringify(next)); bindings = next; apply(); return true; }
        catch { error.textContent = t('Could not save the change.'); error.hidden = false; apply(); return false; }
    }
    const groups = new Map();
    for (const entry of entries) {
        if (!groups.has(entry.group)) {
            const group = node('section', '', { class: 'shortcut-group' });
            group.append(node('h3', t(entry.group))); list.append(group); groups.set(entry.group, group);
        }
        const row = node('div', '', { class: 'shortcut-row', 'data-shortcut-action': entry.id });
        const fieldId = `shortcut-${entry.id.replaceAll(':', '-')}`;
        const field = node('input', '', { id: fieldId, type: 'text', readonly: '', translate: 'no',
            'data-shortcut-record': entry.id, 'aria-describedby': 'shortcut-recording-hint' });
        fields.set(entry.id, field);
        field.addEventListener('focus', () => {
            field.dataset.recording = 'true'; field.value = t('Press a key combination…'); error.hidden = true;
        }, { signal });
        field.addEventListener('blur', apply, { signal });
        const clear = node('button', t('Unassign'), { type: 'button', 'data-shortcut-clear': entry.id,
            'aria-label': t('Unassign shortcut for {action}', { action: t(entry.label) }) });
        clear.addEventListener('click', () => save({ ...bindings, [entry.id]: '' }), { signal });
        row.append(node('label', t(entry.label), { for: fieldId }), field, clear);
        groups.get(entry.group).append(row);
    }
    panel.querySelector('header p').id = 'shortcut-recording-hint';
    panel.querySelector('[data-shortcut-reset]').addEventListener('click', () => save({}), { signal });
    read();
    window.addEventListener('storage', event => { if (event.key === storageKey || event.key === null) read(); }, { signal });
    window.addEventListener('keydown', event => {
        const recording = event.target.closest?.('[data-shortcut-record]');
        if (recording) {
            if (event.key === 'Tab') return;
            event.preventDefault(); event.stopImmediatePropagation();
            if (event.key === 'Escape') { apply(); recording.blur(); return; }
            const value = combination(event);
            if (!value) return;
            if (reserved(value)) { error.textContent = t('This combination is reserved for editing or the browser.'); error.hidden = false; return; }
            const id = recording.dataset.shortcutRecord;
            const conflict = conflicts(entries, id, value, bindings);
            if (conflict) {
                error.textContent = t('This shortcut is already assigned to {action}.', { action: t(conflict.label) });
                error.hidden = false; return;
            }
            const entry = entries.find(item => item.id === id), next = { ...bindings, [id]: value };
            if (value === entry.defaultKey) delete next[id];
            if (save(next)) recording.blur();
            return;
        }
        if (event.defaultPrevented || event.repeat || event.isComposing
            || event.target.closest?.('input,textarea,select,[contenteditable]:not([contenteditable=false])')) return;
        if ([...document.querySelectorAll('[aria-modal=true]')].some(visible)) return;
        const value = combination(event);
        if (!value) return;
        const available = button => visible(button) || (button.closest('[data-dock-overflow]')?.hidden
            && !button.hidden && !button.closest('[inert]') && visible(table.querySelector('[data-dock-menu-toggle]')));
        const entry = entries.find(item => available(item.button) && !item.button.disabled
            && item.button.getAttribute('aria-disabled') !== 'true'
            && (bindings[item.id] ?? item.defaultKey).split(' ').includes(value));
        if (!entry) return;
        event.preventDefault(); event.stopImmediatePropagation(); entry.button.click();
    }, { capture: true, signal });
    return () => abort.abort();
}
