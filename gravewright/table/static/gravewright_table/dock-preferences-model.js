/** Preferences contain only identities present in the recipient's rendered dock. */
export function dockStorageKey(profileId, tableId) {
    const component = value => encodeURIComponent(value).replaceAll('.', '%2E');
    return `gravewright.dock.${component(profileId)}.${component(tableId)}`;
}

export function normalizeDockPreferences(value, entries) {
    const saved = value?.version === 1 ? value : {};
    const order = {}, placement = {};
    for (const group of new Set(entries.map(entry => entry.group))) {
        const defaults = entries.filter(entry => entry.group === group).map(entry => entry.id);
        const known = new Set(defaults);
        const requested = Array.isArray(saved.order?.[group]) ? saved.order[group] : [];
        order[group] = [...new Set([...requested.filter(id => known.has(id)), ...defaults])];
    }
    for (const entry of entries) {
        const next = saved.placement?.[entry.id];
        placement[entry.id] = (entry.group === 'panels' ? ['dock', 'menu', 'hidden'] : ['dock', 'hidden']).includes(next)
            ? next : entry.defaultPlacement;
    }
    return { version: 1, order, placement };
}

/** Move between available peers while retaining unavailable entries for their next appearance. */
export function moveDockEntry(preferences, entries, id, direction, availableIds) {
    const next = normalizeDockPreferences(preferences, entries);
    const entry = entries.find(row => row.id === id);
    if (!entry || ![-1, 1].includes(direction)) return next;
    const order = next.order[entry.group], index = order.indexOf(id);
    const available = new Set(availableIds);
    if (!available.has(id)) return next;
    let target = index + direction;
    while (target >= 0 && target < order.length && !available.has(order[target])) target += direction;
    if (target >= 0 && target < order.length) [order[index], order[target]] = [order[target], order[index]];
    return next;
}
