/** Shared authored token filters for native regions and the Map Builder. */
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?![\s\S])/i;
export const regionFilterDispositions = Object.freeze(['friendly', 'neutral', 'hostile', 'unknown']);
export const regionFilterVisibility = Object.freeze(['any', 'visible', 'hidden']);
/** Missing criteria are unrestricted; normalizing an editor draft never mutates its source. */
export function normalizeRegionFilters(filters = {}) {
    const fields = ['tokenIds', 'actorIds', 'dispositions', 'visibility'];
    if (!filters || typeof filters !== 'object' || Array.isArray(filters) || Object.keys(filters).some(key => !fields.includes(key)))
        throw new TypeError('Invalid region filters.');
    const result = { tokenIds: [], actorIds: [], dispositions: [], visibility: 'any', ...structuredClone(filters) };
    for (const key of ['tokenIds', 'actorIds']) {
        const rows = result[key];
        if (!Array.isArray(rows) || rows.length > 64 || !Array.from(rows).every(id => typeof id === 'string' && uuid.test(id))
            || new Set(rows.map(id => id.toLowerCase())).size !== rows.length) throw new TypeError('Invalid region filters.');
        result[key] = rows.map(id => id.toLowerCase());
    }
    if (!Array.isArray(result.dispositions) || result.dispositions.length > 4
        || !Array.from(result.dispositions).every(value => regionFilterDispositions.includes(value))
        || new Set(result.dispositions).size !== result.dispositions.length || !regionFilterVisibility.includes(result.visibility))
        throw new TypeError('Invalid region filters.');
    return result;
}
/** Preview matching uses token metadata, independently of geometric containment or ownership. */
export function regionMatchesFilters(filters, token) {
    if (!token || typeof token !== 'object') return false;
    let value;
    try { value = normalizeRegionFilters(filters); } catch { return false; }
    const id = typeof token.id === 'string' ? token.id.toLowerCase() : '', actorId = typeof token.actorId === 'string' ? token.actorId.toLowerCase() : '';
    return (!value.tokenIds.length || value.tokenIds.includes(id)) && (!value.actorIds.length || value.actorIds.includes(actorId))
        && (!value.dispositions.length || value.dispositions.includes(token.disposition))
        && (value.visibility === 'any' || (value.visibility === 'hidden') === (token.hidden === true));
}
