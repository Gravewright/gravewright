/**
 * Manual PDF fields use fractions of the displayed page, after PDF rotation.
 * Zoom and document coordinates never enter the persisted field definition.
 */
export const MANUAL_FIELD_TYPES = Object.freeze(["text", "number", "checkbox", "multiline"]);
export const MAX_MANUAL_FIELDS = 256;
export const MIN_MANUAL_SIZE = 0.001;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const TEMPLATE_PATTERN = /^[A-Za-z0-9_-]{1,120}$/;
const FIELD_KEYS = new Set(["id", "source", "page", "type", "name", "x", "y", "width", "height"]);
const finite = (value) => typeof value === "number" && Number.isFinite(value);
const clamp = (value, lower, upper) => Math.max(lower, Math.min(upper, value));

/** Return the persisted source identity, or an empty string for an invalid source. */
export function sourceKey(source) {
    if (source && typeof source === "object") {
        if (typeof source.kind !== "string" || typeof source.id !== "string")
            return "";
        return sourceKey(`${source.kind}:${source.id}`);
    }
    if (typeof source !== "string")
        return "";
    if (source.startsWith("asset:") && UUID_PATTERN.test(source.slice(6).toLowerCase()))
        return `asset:${source.slice(6).toLowerCase()}`;
    if (source.startsWith("template:") && TEMPLATE_PATTERN.test(source.slice(9)))
        return source;
    return "";
}

/** The stable value address depends on identity, so renaming cannot lose a value. */
export function manualFieldKey(fieldOrId) {
    const id = typeof fieldOrId === "string" ? fieldOrId : fieldOrId?.id;
    if (typeof id !== "string" || !UUID_PATTERN.test(id))
        return "";
    return `manual_${id.replaceAll("-", "")}`;
}

export function validManualField(field) {
    if (!field || typeof field !== "object" || Array.isArray(field)
        || Object.keys(field).some((key) => !FIELD_KEYS.has(key))
        || !manualFieldKey(field)
        || !field.source || sourceKey(field.source) !== field.source
        || !Number.isInteger(field.page) || field.page < 1 || field.page > 100000
        || !MANUAL_FIELD_TYPES.includes(field.type)
        || typeof field.name !== "string" || !field.name.trim() || field.name.length > 120)
        return false;
    const { x, y, width, height } = field;
    return [x, y, width, height].every(finite)
        && x >= 0 && y >= 0 && width >= MIN_MANUAL_SIZE && height >= MIN_MANUAL_SIZE
        && x <= 1 && y <= 1 && width <= 1 && height <= 1
        && x + width <= 1 && y + height <= 1;
}

export function validateManualFields(fields) {
    if (!Array.isArray(fields) || fields.length > MAX_MANUAL_FIELDS)
        return false;
    const ids = new Set();
    for (const field of fields) {
        if (!validManualField(field) || ids.has(field.id))
            return false;
        ids.add(field.id);
    }
    return true;
}

/** Invalid local data is omitted; the server still validates every saved definition. */
export function manualFieldsForSource(pdf, source) {
    const key = sourceKey(source);
    if (!key || !Array.isArray(pdf?.manualFields))
        return [];
    return pdf.manualFields.filter((field) => validManualField(field) && field.source === key);
}

export function manualFieldSpec(field) {
    const key = manualFieldKey(field);
    if (!key || !MANUAL_FIELD_TYPES.includes(field.type))
        return null;
    return {
        path: `sheet.fields.${key}`,
        type: field.type === "checkbox" ? "boolean" : field.type === "number" ? "number" : "string",
    };
}

/**
 * Convert two client points into a normalized rectangle within page bounds.
 * Default bounds accept already normalized points. Empty/invalid gestures return null.
 */
export function normalizedRect(start, end, bounds = { left: 0, top: 0, width: 1, height: 1 }) {
    if (!start || !end || !bounds)
        return null;
    const { left = 0, top = 0, width, height } = bounds;
    if (![start.x, start.y, end.x, end.y, left, top, width, height].every(finite)
        || width <= 0 || height <= 0)
        return null;
    const x1 = clamp((start.x - left) / width, 0, 1);
    const y1 = clamp((start.y - top) / height, 0, 1);
    const x2 = clamp((end.x - left) / width, 0, 1);
    const y2 = clamp((end.y - top) / height, 0, 1);
    const result = {
        x: Math.min(x1, x2), y: Math.min(y1, y2),
        width: Math.abs(x2 - x1), height: Math.abs(y2 - y1),
    };
    return result.width >= MIN_MANUAL_SIZE && result.height >= MIN_MANUAL_SIZE ? result : null;
}

/** Match native field bounds, using PDF.js's already rotated display viewport. */
export function manualFieldBounds(field, viewport, offsetTop = 0) {
    return {
        left: field.x * viewport.width, top: field.y * viewport.height + offsetTop,
        width: field.width * viewport.width, height: field.height * viewport.height,
        hidden: false,
    };
}

/** Move by normalized deltas and retain both field size and stable identity. */
export function moveManualField(field, dx, dy) {
    if (!validManualField(field) || !finite(dx) || !finite(dy))
        return null;
    return { ...field, x: clamp(field.x + dx, 0, 1 - field.width), y: clamp(field.y + dy, 0, 1 - field.height) };
}

/** Replace a normalized rectangle while retaining field identity and metadata. */
export function resizeManualField(field, rect) {
    if (!validManualField(field) || !rect || ![rect.x, rect.y, rect.width, rect.height].every(finite))
        return null;
    const width = clamp(rect.width, MIN_MANUAL_SIZE, 1);
    const height = clamp(rect.height, MIN_MANUAL_SIZE, 1);
    return { ...field, x: clamp(rect.x, 0, 1 - width), y: clamp(rect.y, 0, 1 - height), width, height };
}
