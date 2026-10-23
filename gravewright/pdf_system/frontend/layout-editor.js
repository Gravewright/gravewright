/** Geometry-only operations for a selection of authored PDF fields. */
const finite = value => typeof value === 'number' && Number.isFinite(value);
const clamp = (value, lower, upper) => Math.max(lower, Math.min(upper, value));
const valid = field => field && typeof field.id === 'string'
    && [field.x, field.y, field.width, field.height].every(finite)
    && field.x >= 0 && field.y >= 0 && field.width >= .001 && field.height >= .001
    && field.x + field.width <= 1 && field.y + field.height <= 1;
const nearest = (value, step) => finite(step) && step > 0 ? Math.round(value / step) * step : value;

function groups(fields) {
    const pages = new Map(), seen = new Set();
    for (const field of fields || []) {
        if (!valid(field) || seen.has(field.id)) continue;
        seen.add(field.id);
        const key = JSON.stringify([field.source || '', field.page || 1]);
        if (!pages.has(key)) pages.set(key, []);
        pages.get(key).push(field);
    }
    return [...pages.values()];
}

function changed(field, changes) {
    return Object.keys(changes).some(key => Math.abs(field[key] - changes[key]) > 1e-12)
        ? { id: field.id, changes } : null;
}

/** Return the normalized bounding rectangle, without changing authored fields. */
export function layoutBounds(fields) {
    const rows = (fields || []).filter(valid);
    if (!rows.length) return null;
    const x = Math.min(...rows.map(field => field.x));
    const y = Math.min(...rows.map(field => field.y));
    return { x, y, width: Math.max(...rows.map(field => field.x + field.width)) - x,
        height: Math.max(...rows.map(field => field.y + field.height)) - y };
}

/** Move each page's whole selection, clamping once so internal gaps stay exact. */
export function moveLayoutFields(fields, dx, dy, grid = {}) {
    if (!finite(dx) || !finite(dy)) return [];
    return groups(fields).flatMap(rows => {
        const bounds = layoutBounds(rows);
        const x = clamp(nearest(bounds.x + dx, grid.x), 0, 1 - bounds.width);
        const y = clamp(nearest(bounds.y + dy, grid.y), 0, 1 - bounds.height);
        return rows.map(field => changed(field, {
            x: clamp(field.x + x - bounds.x, 0, 1 - field.width),
            y: clamp(field.y + y - bounds.y, 0, 1 - field.height),
        })).filter(Boolean);
    });
}

/** Align within a page; a spread never moves fields from one page to another. */
export function alignLayoutFields(fields, alignment) {
    if (!['left', 'right', 'top', 'bottom', 'center-x', 'center-y'].includes(alignment)) return [];
    return groups(fields).flatMap(rows => {
        if (rows.length < 2) return [];
        const bounds = layoutBounds(rows);
        return rows.map(field => {
            const changes = alignment === 'left' ? { x: bounds.x }
                : alignment === 'right' ? { x: bounds.x + bounds.width - field.width }
                : alignment === 'top' ? { y: bounds.y }
                : alignment === 'bottom' ? { y: bounds.y + bounds.height - field.height }
                : alignment === 'center-x' ? { x: bounds.x + (bounds.width - field.width) / 2 }
                : { y: bounds.y + (bounds.height - field.height) / 2 };
            if (changes.x !== undefined) changes.x = clamp(changes.x, 0, 1 - field.width);
            if (changes.y !== undefined) changes.y = clamp(changes.y, 0, 1 - field.height);
            return changed(field, changes);
        }).filter(Boolean);
    });
}

/** Equalize nonnegative gaps, keeping the first and last edges fixed. */
export function distributeLayoutFields(fields, axis) {
    if (!['horizontal', 'vertical'].includes(axis)) return [];
    const coordinate = axis === 'horizontal' ? 'x' : 'y';
    const size = axis === 'horizontal' ? 'width' : 'height';
    return groups(fields).flatMap(rows => {
        if (rows.length < 3) return [];
        const ordered = [...rows].sort((a, b) => a[coordinate] - b[coordinate] || a.id.localeCompare(b.id));
        const first = ordered[0][coordinate];
        const last = ordered.at(-1)[coordinate] + ordered.at(-1)[size];
        const gap = (last - first - ordered.reduce((sum, field) => sum + field[size], 0)) / (ordered.length - 1);
        if (gap < -1e-12) return [];
        let cursor = first;
        const updates = new Map();
        for (const field of ordered) {
            const update = changed(field, { [coordinate]: clamp(cursor, 0, 1 - field[size]) });
            if (update) updates.set(field.id, update);
            cursor += field[size] + Math.max(0, gap);
        }
        return rows.map(field => updates.get(field.id)).filter(Boolean);
    });
}

/** Snap both rectangle edges to a page-local grid and retain valid page bounds. */
export function snapLayoutRect(rect, grid = {}) {
    if (!rect || ![rect.x, rect.y, rect.width, rect.height].every(finite)
        || rect.width < 0 || rect.height < 0) return null;
    const x = clamp(nearest(rect.x, grid.x), 0, .999);
    const y = clamp(nearest(rect.y, grid.y), 0, .999);
    const right = clamp(nearest(rect.x + rect.width, grid.x), x + .001, 1);
    const bottom = clamp(nearest(rect.y + rect.height, grid.y), y + .001, 1);
    return { x, y, width: right - x, height: bottom - y };
}
