import { BAR_SLOTS, readCanonical, writeCanonical } from './mapping.js';
import { sourceKey } from './manual-fields.js';

/** Action identities follow PDF names or stable manual IDs within one source. */
export function actionsForSource(pdf, source) {
    const key = sourceKey(source), result = Object.create(null);
    const actions = Array.isArray(pdf?.fieldActions) ? pdf.fieldActions : [];
    for (const action of actions) {
        if (action?.source === key && typeof action.field === 'string' && action.roll)
            result[action.field] = action.roll;
    }
    return result;
}

export function numericFieldValue(value) {
    if (value === '' || value === undefined || value === null) return 0;
    if (typeof value === 'boolean') return value ? 1 : 0;
    if (typeof value === 'string') {
        const text = value.trim();
        if (!text) return 0;
        if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(text))
            throw new Error('This field needs a numeric value.');
        value = Number(text);
    }
    if (typeof value !== 'number' || !Number.isFinite(value) || Math.abs(value) > 1_000_000)
        throw new Error('This field needs a numeric value.');
    return value;
}

// The dice grammar accepts decimal literals, rather than exponent notation.
function decimal(value) {
    const text = String(value);
    if (!text.includes('e')) return text;
    const [mantissa, exponent] = text.split('e');
    const sign = mantissa.startsWith('-') ? '-' : '';
    const digits = mantissa.replace('-', '').replace('.', '');
    const point = mantissa.replace('-', '').split('.')[0].length + Number(exponent);
    if (point <= 0) return sign + '0.' + '0'.repeat(-point) + digits;
    return sign + digits.slice(0, point) + (point < digits.length ? '.' + digits.slice(point) : '0'.repeat(point - digits.length));
}

/** Expand the single supported reference without evaluating code or dice. */
export function fieldRollExpression(formula, value) {
    if (typeof formula !== 'string' || !formula.trim() || formula.length > 512)
        throw new Error('The expression must contain 1 to 512 characters.');
    let expression = formula.trim();
    if (/@value(?![A-Za-z0-9_.])/.test(expression)) {
        const literal = `(${decimal(numericFieldValue(value))})`;
        expression = expression.replace(/@value(?![A-Za-z0-9_.])/g, literal);
    }
    if (expression.includes('@')) throw new Error('Use @value to reference this field.');
    if (expression.length > 512) throw new Error('The resolved roll formula is too long.');
    return expression;
}

function storedValue(spec, value) {
    if (spec.type === 'number') return numericFieldValue(value);
    if (spec.type === 'boolean') return Boolean(value);
    return String(value ?? '');
}

/** Build an isolated save candidate; failed validation cannot poison autosave. */
export function fieldActionCandidate(actor, source, name, config, fields, originals) {
    const spec = fields[name], original = originals[name];
    if (!spec || !original || !config || typeof config !== 'object'
        || typeof config.bar !== 'string' || typeof config.formula !== 'string' || typeof config.label !== 'string')
        throw new Error('Invalid PDF field action.');
    const slot = BAR_SLOTS.find(slot => slot.key === config.bar);
    if (config.bar && !slot) throw new Error('Invalid token mapping.');
    if (slot && (original.type === 'boolean' || spec.multiline))
        throw new Error('Checkbox and multiline fields cannot be linked to a token bar.');
    const candidate = structuredClone(actor);
    const bars = candidate.data.token.bars;
    const current = readCanonical(actor, spec.path);
    // Restore values at their original address before changing the single write path.
    for (const previous of BAR_SLOTS) {
        if (bars[previous.key] === name) {
            writeCanonical(candidate, original.path, storedValue(original, current));
            bars[previous.key] = '';
        }
    }
    if (slot) {
        const displaced = bars[slot.key];
        if (displaced && fields[displaced] && originals[displaced])
            writeCanonical(candidate, originals[displaced].path,
                storedValue(originals[displaced], readCanonical(actor, fields[displaced].path)));
        bars[slot.key] = name;
        writeCanonical(candidate, slot.path, numericFieldValue(current));
    }
    const key = sourceKey(source);
    const actions = (candidate.data.pdf.fieldActions || []).filter(action => action.source !== key || action.field !== name);
    if (config.formula.trim()) actions.push({ source: key, field: name,
        roll: { formula: config.formula.trim(), label: config.label.trim() } });
    candidate.data.pdf.fieldActions = actions;
    return candidate;
}
