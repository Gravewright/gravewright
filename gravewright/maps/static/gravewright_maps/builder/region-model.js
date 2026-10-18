/** Named presence rectangles in authored cell coordinates; occupancy belongs to the server. */
import { defaultBlueprint, eventGraph, connectNodes } from './blueprint-model.js';
import { normalizeRegionFilters } from '../region-filters.js';
export { normalizeRegionFilters, regionMatchesFilters, regionFilterDispositions, regionFilterVisibility } from '../region-filters.js';

const epsilon = 1e-7;
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function regionBounds(region) {
    return { x: region.x, y: region.y, width: region.width, height: region.height };
}
export function regionContainsPoint(region, point, elevation = 0) {
    if (!region || !point || ![point.x, point.y, elevation].every(Number.isFinite)) return false;
    return point.x >= region.x - epsilon && point.x <= region.x + region.width + epsilon
        && point.y >= region.y - epsilon && point.y <= region.y + region.height + epsilon
        && (region.vertical?.bottom == null || elevation >= region.vertical.bottom)
        && (region.vertical?.top == null || elevation <= region.vertical.top);
}
export function validateRegionGeometry(document, region) {
    if (!region || !['x', 'y', 'width', 'height'].every(key => Number.isFinite(region[key]))
        || region.width < .05 || region.height < .05 || region.x < 0 || region.y < 0
        || region.x + region.width > document.columns + epsilon || region.y + region.height > document.rows + epsilon) return false;
    if (region.vertical !== undefined) {
        const value = region.vertical;
        if (!value || Array.isArray(value) || Object.keys(value).length !== 2 || !Object.hasOwn(value, 'bottom') || !Object.hasOwn(value, 'top')
            || ![value.bottom, value.top].every(bound => bound === null || Number.isFinite(bound) && Math.abs(bound) <= 1000000)
            || value.bottom !== null && value.top !== null && value.bottom > value.top) return false;
    }
    if (region.filters !== undefined) {
        try { normalizeRegionFilters(region.filters); } catch { return false; }
    }
    return true;
}
/** Return a new rectangle without mutating the document, so the caller owns one undo step. */
export function createRegion(document, start, end = start, { id = crypto.randomUUID(), layerId, name = 'Region', enabled = true, snap = true, filters } = {}) {
    const layer = document.layers?.find(row => row.id === layerId);
    if (!layer || layer.locked || !layer.visible || !uuid.test(id) || typeof name !== 'string' || !name.trim()
        || Array.from(name).length > 120 || name.includes('\0') || typeof enabled !== 'boolean'
        || (document.regions?.length || 0) >= 128
        || ![start?.x, start?.y, end?.x, end?.y].every(Number.isFinite)) return null;
    const coordinate = (value, maximum) => Math.min(Math.max(snap ? Math.round(value) : Math.round(value * 1000) / 1000, 0), maximum);
    const left = coordinate(start.x, document.columns), right = coordinate(end.x, document.columns);
    const top = coordinate(start.y, document.rows), bottom = coordinate(end.y, document.rows);
    const minimum = snap ? 1 : .05;
    const x = Math.min(left, right, document.columns - minimum), y = Math.min(top, bottom, document.rows - minimum);
    const region = { id, layerId, x, y, width: Math.max(minimum, Math.abs(right - left)),
        height: Math.max(minimum, Math.abs(bottom - top)), name: name.trim(), enabled };
    if (filters !== undefined) {
        try { region.filters = normalizeRegionFilters(filters); } catch { return null; }
    }
    return validateRegionGeometry(document, region) ? region : null;
}
/** Occupancy is a transient editor preview, never an authored source property. */
export function regionInstance(region) { return { ...region, kind: 'region', state: 'empty' }; }

/** Replace the region's Blueprint with the standard first-in / last-out pressure plate. */
export function configurePressurePlate(region, targetId) {
    if (!region || !uuid.test(targetId ?? '')) return false;
    const blueprint = defaultBlueprint('region');
    for (const [event, occupancy, count, targetState] of [['presence:enter', 'occupied', 1, 'open'], ['presence:exit', 'empty', 0, 'closed']]) {
        const graph = eventGraph(event);
        graph.nodes.push({ id: 'target', type: 'reference', targetId, x: 60, y: 280 },
            { id: 'count', type: 'eventContext', property: 'count', x: 60, y: 520 },
            { id: 'compare', type: 'compareValue', valueType: 'number', operator: 'eq', expected: count, x: 380, y: 520 },
            { id: 'check', type: 'condition', state: occupancy, x: 380, y: 60 },
            { id: 'state', type: 'state', targetState, x: 700, y: 60 });
        connectNodes(graph, 'event', 'next', 'check', { version: 2 });
        connectNodes(graph, 'count', 'value', 'compare', { version: 2, input: 'value' });
        connectNodes(graph, 'compare', 'result', 'check', { version: 2, input: 'test' });
        connectNodes(graph, 'check', 'true', 'state', { version: 2 });
        connectNodes(graph, 'target', 'door', 'state', { version: 2, input: 'target' });
        blueprint.graphs[event] = graph;
    }
    region.blueprint = blueprint;
    return true;
}
