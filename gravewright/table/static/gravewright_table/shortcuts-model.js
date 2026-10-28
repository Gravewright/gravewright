/** Normalized key combinations and context-aware conflicts for table commands. */
export function combination(event) {
    if (event.isComposing || event.key === 'Dead') return null;
    const key = /^Digit[0-9]$/.test(event.code || '') ? event.code.slice(-1) : event.key?.toUpperCase();
    if (!/^(?:[\p{L}\p{N}]|F(?:[1-9]|1[0-2]))$/u.test(key || '')) return null;
    return [event.ctrlKey && 'Control', event.altKey && 'Alt', event.shiftKey && 'Shift', event.metaKey && 'Meta', key].filter(Boolean).join('+');
}
export function validCombination(value) {
    return typeof value === 'string' && /^(?:Control\+)?(?:Alt\+)?(?:Shift\+)?(?:Meta\+)?(?:[\p{Lu}\p{N}]|F(?:[1-9]|1[0-2]))$/u.test(value);
}
export function reserved(value) {
    const parts = value.split('+'), key = parts.at(-1);
    return (['F5', 'F11', 'F12'].includes(key) && value !== 'F5') || value === 'Alt+F4'
        || parts.some(part => part === 'Control' || part === 'Meta') && 'ACFLNPRTVWXYZ'.includes(key) && key.length === 1;
}
export function conflicts(entries, id, value, bindings) {
    const current = entries.find(entry => entry.id === id);
    return entries.find(entry => entry.id !== id && (!current.scope || !entry.scope || current.scope === entry.scope)
        && (bindings[entry.id] ?? entry.defaultKey).split(' ').includes(value));
}
export function displayCombination(value) {
    return value ? value.replaceAll('Control+', 'Ctrl+').replaceAll('Meta+', '⌘+').replaceAll(' ', ' / ') : 'Unassigned';
}
