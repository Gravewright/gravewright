import { sourceKey, manualFieldKey, validManualField, MAX_MANUAL_FIELDS } from './manual-fields.js';
import { readCanonical } from './mapping.js';
import { fieldReference, fieldReferences } from './formulas.js';

const LISTS = ['manualFields', 'fieldActions', 'calculatedFields', 'fieldBindings'];

export function captureLayout(actor, source) {
    const key = sourceKey(source);
    const snapshot = { source: key, bars: structuredClone(actor.data.token.bars) };
    for (const list of LISTS) snapshot[list] = structuredClone((actor.data.pdf[list] || []).filter(row => row.source === key));
    return snapshot;
}

/** Restore definitions, leaving current values and other PDFs untouched. */
export function restoreLayout(actor, snapshot) {
    for (const list of LISTS)
        actor.data.pdf[list] = [...(actor.data.pdf[list] || []).filter(row => row.source !== snapshot.source), ...structuredClone(snapshot[list])];
    actor.data.token.bars = structuredClone(snapshot.bars);
}

export function copyLayout(actor, source, ids, fields) {
    const key = sourceKey(source), selected = new Set(ids);
    const definitions = (actor.data.pdf.manualFields || []).filter(field => field.source === key && selected.has(field.id));
    if (!definitions.length) return null;
    const keys = new Set(definitions.map(manualFieldKey));
    const values = Object.create(null);
    for (const field of definitions) values[manualFieldKey(field)] = readCanonical(actor, fields[manualFieldKey(field)]?.path || `sheet.fields.${manualFieldKey(field)}`);
    return { version: 1, source: key, fields: structuredClone(definitions), values,
        actions: structuredClone((actor.data.pdf.fieldActions || []).filter(row => row.source === key && keys.has(row.field))),
        calculations: structuredClone((actor.data.pdf.calculatedFields || []).filter(row => row.source === key && keys.has(row.field))) };
}

function remapFormula(formula, keys) {
    let result = formula;
    for (const key of fieldReferences(formula))
        if (keys.has(key)) result = result.split(fieldReference(key)).join(fieldReference(keys.get(key)));
    return result;
}

/** Paste uses new identities and remaps references inside a copied selection. */
export function pasteLayout(actor, source, clipboard, { page, pageCount, dx = .02, dy = .02, uuid = () => crypto.randomUUID() }) {
    const key = sourceKey(source);
    if (!clipboard || clipboard.version !== 1 || clipboard.source !== key || !Array.isArray(clipboard.fields)
        || !clipboard.fields.length || !clipboard.fields.every(validManualField)
        || ![dx, dy].every(Number.isFinite)) throw new Error('Copy fields from this PDF before pasting.');
    const all = actor.data.pdf.manualFields || [];
    if (all.length + clipboard.fields.length > MAX_MANUAL_FIELDS) throw new Error('Use at most 256 manual PDF fields.');
    const candidate = structuredClone(actor), keys = new Map();
    const firstPage = Math.min(...clipboard.fields.map(field => field.page));
    const minX = Math.min(...clipboard.fields.map(field => field.x)), minY = Math.min(...clipboard.fields.map(field => field.y));
    const maxX = Math.max(...clipboard.fields.map(field => field.x + field.width)), maxY = Math.max(...clipboard.fields.map(field => field.y + field.height));
    dx = Math.max(-minX, Math.min(1 - maxX, dx)); dy = Math.max(-minY, Math.min(1 - maxY, dy));
    const definitions = clipboard.fields.map(field => {
        const next = { ...field, id: uuid(), source: key, page: page + field.page - firstPage,
            x: Math.max(0, Math.min(1 - field.width, field.x + dx)), y: Math.max(0, Math.min(1 - field.height, field.y + dy)) };
        if (!validManualField(next) || next.page > pageCount) throw new Error('Choose a PDF page that can contain the copied fields.');
        keys.set(manualFieldKey(field), manualFieldKey(next));
        return next;
    });
    candidate.data.pdf.manualFields = [...all, ...definitions];
    for (const field of definitions) {
        const oldKey = [...keys].find(([, next]) => next === manualFieldKey(field))[0];
        const value = clipboard.values[oldKey];
        if (value !== undefined) candidate.data.fields[manualFieldKey(field)] = field.type === 'text' || field.type === 'multiline' ? String(value) : value;
    }
    for (const [list, rows] of [['fieldActions', clipboard.actions], ['calculatedFields', clipboard.calculations]]) {
        const copies = (rows || []).map(row => ({ ...row, source: key, field: keys.get(row.field),
            ...(list === 'fieldActions' ? { roll: { ...row.roll, formula: remapFormula(row.roll.formula, keys) } }
                : { formula: remapFormula(row.formula, keys) }) }));
        if (copies.length) candidate.data.pdf[list] = [...(candidate.data.pdf[list] || []), ...copies];
    }
    return { candidate, ids: definitions.map(field => field.id) };
}
