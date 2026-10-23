import { BAR_SLOTS, readCanonical, writeCanonical } from './mapping.js';
import { manualFieldKey, manualFieldSpec, manualFieldsForSource, sourceKey } from './manual-fields.js';

const fail = message => { throw new Error(message); };
const finite = value => {
    if (!Number.isFinite(value)) fail('Could not calculate this PDF field. Check its formula and numeric values.');
    return value;
};
const numeric = value => {
    if (value === undefined || value === null || value === '') return 0;
    if (typeof value === 'boolean') return value ? 1 : 0;
    if (typeof value === 'string') {
        value = value.trim();
        if (!value) return 0;
        if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(value)) fail('This field needs a numeric value.');
        value = Number(value);
    }
    if (typeof value !== 'number' || !Number.isFinite(value) || Math.abs(value) > 1_000_000)
        fail('This field needs a numeric value.');
    return value === 0 ? 0 : value;
};
function decimal(value) {
    const text = String(numeric(value));
    if (!text.includes('e')) return text;
    const [mantissa, exponent] = text.split('e');
    const sign = mantissa.startsWith('-') ? '-' : '';
    const unsigned = mantissa.replace('-', ''), digits = unsigned.replace('.', '');
    const point = unsigned.split('.')[0].length + Number(exponent);
    return point <= 0 ? sign + '0.' + '0'.repeat(-point) + digits
        : sign + digits.slice(0, point) + (point < digits.length ? '.' + digits.slice(point) : '0'.repeat(point - digits.length));
}

export function fieldReference(field) {
    if (typeof field !== 'string' || !field.trim() || field.includes('\0')) fail('Invalid PDF field reference.');
    return '@{' + field.replaceAll('\\', '\\\\').replaceAll('}', '\\}') + '}';
}

function parts(formula, allowValue = true) {
    if (typeof formula !== 'string' || !formula.trim() || formula.length > 512)
        fail('Use a PDF field formula with 1 to 512 characters.');
    const result = [];
    let offset = 0;
    while (offset < formula.length) {
        const start = formula.indexOf('@', offset);
        if (start < 0) { result.push(formula.slice(offset)); break; }
        result.push(formula.slice(offset, start));
        const value = /^@value(?![A-Za-z0-9_.])/.exec(formula.slice(start));
        if (value) {
            if (!allowValue) fail('Calculated fields must reference other fields instead of @value.');
            result.push({ field: null }); offset = start + value[0].length; continue;
        }
        if (!formula.startsWith('@{', start)) fail('Use @value or @{field} to reference PDF fields.');
        offset = start + 2;
        let name = '';
        while (offset < formula.length && formula[offset] !== '}') {
            let character = formula[offset++];
            if (character === '\\') {
                character = formula[offset++];
                if (character !== '\\' && character !== '}') fail('Invalid PDF field reference.');
            }
            name += character;
        }
        if (offset >= formula.length || !name.trim() || name.includes('\0')) fail('Invalid PDF field reference.');
        result.push({ field: name }); offset += 1;
    }
    return result;
}

export function fieldReferences(formula, { allowValue = true } = {}) {
    return [...new Set(parts(formula, allowValue).filter(part => typeof part !== 'string' && part.field !== null).map(part => part.field))];
}

export function expandFieldFormula(formula, resolve, { value, allowValue = true, maxLength = 512 } = {}) {
    const expression = parts(formula, allowValue).map(part => typeof part === 'string' ? part
        : `(${decimal(part.field === null ? value : resolve(part.field))})`).join('').trim();
    if (expression.length > maxLength) fail('The resolved roll formula is too long.');
    return expression;
}

// This deterministic subset mirrors native numeric grammar. Dice execution
// always stays in the server's native roll service; no eval or Function is used.
function calculationPlan(formula) {
    const tokens = [];
    for (const part of parts(formula, false)) {
        if (typeof part !== 'string') { tokens.push({ kind: 'reference', field: part.field }); continue; }
        let text = part;
        while (text) {
            const whitespace = /^[\s\uFEFF]+/.exec(text);
            if (whitespace) { text = text.slice(whitespace[0].length); continue; }
            const number = /^(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)/.exec(text);
            const identifier = /^[A-Za-z_][A-Za-z0-9_]*/.exec(text);
            const operator = /^(?:>=|<=|==|!=|[+*/<>()!,\-])/.exec(text);
            if (number) { tokens.push({ kind: 'number', value: finite(Number(number[0])) }); text = text.slice(number[0].length); }
            else if (identifier) { tokens.push({ kind: 'identifier', name: identifier[0] }); text = text.slice(identifier[0].length); }
            else if (operator) { tokens.push({ kind: operator[0] }); text = text.slice(operator[0].length); }
            else fail('Invalid PDF field formula.');
        }
    }
    let position = 0, nesting = 0;
    const peek = () => tokens[position]?.kind;
    const consume = kind => peek() === kind ? tokens[position++] : null;
    const required = kind => consume(kind) || fail('Invalid PDF field formula.');
    const nested = read => {
        if (++nesting > 32) fail('Invalid PDF field formula.');
        try { return read(); } finally { nesting--; }
    };
    function primary() {
        const number = consume('number') || consume('reference');
        if (number) return number;
        if (consume('(')) { const node = nested(comparison); required(')'); return node; }
        const identifier = consume('identifier');
        if (!identifier) fail('Invalid PDF field formula.');
        if (/^d(?:[0-9]|[Ff])/.test(identifier.name)) fail('Calculated fields cannot roll dice.');
        required('(');
        const args = [];
        if (!consume(')')) {
            do { args.push(nested(comparison)); } while (consume(','));
            required(')');
        }
        return { kind: 'call', name: identifier.name, args };
    }
    function unary() {
        const operator = consume('+') || consume('-');
        return operator ? { kind: 'unary', operator: operator.kind, operand: nested(unary) } : primary();
    }
    function binary(read, choices) {
        let left = read();
        while (choices.includes(peek())) { const operator = tokens[position++].kind; left = { kind: 'binary', operator, left, right: read() }; }
        return left;
    }
    const multiplicative = () => binary(unary, ['*', '/']);
    const additive = () => binary(multiplicative, ['+', '-']);
    function comparison() {
        const left = additive();
        if (!['>=', '<=', '==', '!=', '>', '<'].includes(peek())) return left;
        const operator = tokens[position++].kind;
        return { kind: 'comparison', operator, left, right: additive() };
    }
    const root = comparison();
    if (position !== tokens.length) fail('Invalid PDF field formula.');
    let nodes = 0;
    function check(node, depth = 1) {
        if (++nodes > 1000 || depth > 128) fail('Invalid PDF field formula.');
        const children = node.args || (node.operand ? [node.operand] : node.left ? [node.left, node.right] : []);
        if (children.some(child => check(child, depth + 1) !== 'number')) fail('Invalid PDF field formula.');
        if (node.kind === 'call') {
            const ranges = { floor: [1, 1], ceil: [1, 1], round: [1, 1], abs: [1, 1], min: [2, 100], max: [2, 100], clamp: [3, 3] };
            const range = Object.hasOwn(ranges, node.name) && ranges[node.name];
            if (!range || children.length < range[0] || children.length > range[1]) fail('Invalid PDF field formula.');
        }
        return node.kind === 'comparison' ? 'boolean' : 'number';
    }
    check(root);
    return root;
}

export function calculateFormula(formula, resolve) {
    const root = calculationPlan(formula);
    function execute(node) {
        if (node.kind === 'reference') return numeric(resolve(node.field));
        if (node.kind === 'number') return node.value;
        if (node.kind === 'unary') return finite((node.operator === '-' ? -1 : 1) * execute(node.operand));
        if (node.kind === 'call') {
            const args = node.args.map(execute);
            if (node.name === 'clamp') {
                if (args[1] > args[2]) fail('Could not calculate this PDF field. Check its formula and numeric values.');
                return finite(Math.min(Math.max(args[0], args[1]), args[2]));
            }
            return finite(Math[node.name](...args));
        }
        const left = execute(node.left), right = execute(node.right);
        if (node.kind === 'comparison') return { '>=': left >= right, '<=': left <= right, '==': left === right, '!=': left !== right, '>': left > right, '<': left < right }[node.operator];
        if (node.operator === '/' && right === 0) fail('Could not calculate this PDF field. Check its formula and numeric values.');
        return finite(node.operator === '+' ? left + right : node.operator === '-' ? left - right : node.operator === '*' ? left * right : left / right);
    }
    return numeric(execute(root));
}

const validPath = path => typeof path === 'string' && (BAR_SLOTS.some(slot => slot.path === path)
    || /^sheet\.fields\.[A-Za-z0-9_-]{1,512}$/.test(path) && !['__proto__', 'prototype', 'constructor'].includes(path.slice(13)));

export function captureFieldBindings(source, originals, fieldIndex) {
    const key = sourceKey(source), result = [];
    if (!key) return result;
    for (const [field, spec] of Object.entries(originals)) {
        if (!validPath(spec.path) || !['string', 'number', 'boolean'].includes(spec.type) || field.length > 512 || !field.trim()) continue;
        const info = fieldIndex?.get(field);
        result.push({ source: key, field, path: spec.path, type: spec.type,
            name: String(info?.manual?.name || spec.label || field).slice(0, 512), readOnly: !!info?.readOnly });
    }
    return result;
}

export function bindingsForSource(pdf, source) {
    const key = sourceKey(source), result = Object.create(null);
    for (const binding of pdf?.fieldBindings || []) {
        if (binding.source === key && validPath(binding.path)) result[binding.field] = binding;
    }
    for (const field of manualFieldsForSource(pdf, key)) {
        const name = manualFieldKey(field), spec = manualFieldSpec(field);
        result[name] = { source: key, field: name, ...spec, name: field.name,
            readOnly: false, multiline: field.type === 'multiline', manual: true };
    }
    return result;
}

export function bindingPath(data, binding) {
    const matches = BAR_SLOTS.filter(slot => data.token?.bars?.[slot.key] === binding.field);
    return matches.length ? (binding.manual ? matches[0] : matches.at(-1)).path : binding.path;
}

export function recalculateFields(actor, source, { previous } = {}) {
    const key = sourceKey(source), pdf = actor.data.pdf;
    const definitions = (pdf.calculatedFields || []).filter(entry => entry.source === key);
    const bindings = bindingsForSource(pdf, key), targets = new Map(definitions.map(entry => [entry.field, entry]));
    const fields = new Set(targets.keys()), errors = [], paths = new Map(), order = [];
    const visiting = new Set(), visited = new Set();
    let changed = false;
    try {
        for (const field of fields) {
            const binding = bindings[field];
            if (!binding) fail('A calculated PDF field is not available.');
            if (binding.type === 'boolean' || binding.multiline || binding.readOnly) fail('This PDF field cannot be calculated.');
            const path = bindingPath(actor.data, binding);
            if (paths.has(path)) fail('Calculated PDF fields must use different value addresses.');
            paths.set(path, field);
        }
        function visit(field) {
            if (visiting.has(field)) fail('Calculated PDF fields cannot contain circular references.');
            if (visited.has(field)) return;
            visiting.add(field);
            calculationPlan(targets.get(field).formula);
            for (const reference of fieldReferences(targets.get(field).formula, { allowValue: false })) {
                if (!bindings[reference]) fail('A referenced PDF field is not available.');
                const dependency = paths.get(bindingPath(actor.data, bindings[reference]));
                if (dependency) visit(dependency);
            }
            visiting.delete(field); visited.add(field); order.push(targets.get(field));
        }
        for (const field of fields) visit(field);
    } catch (error) {
        return { changed, errors: [{ field: '', message: error.message }], fields };
    }
    for (const entry of order) {
        const binding = bindings[entry.field], path = bindingPath(actor.data, binding);
        const type = BAR_SLOTS.some(slot => slot.path === path) ? 'number' : binding.type;
        let value;
        try {
            value = calculateFormula(entry.formula, field => readCanonical(actor, bindingPath(actor.data, bindings[field])));
            if (type === 'string') value = decimal(value);
        } catch (error) {
            errors.push({ field: entry.field, message: error.message });
            if (!previous) continue;
            const old = bindingsForSource(previous.data.pdf, key)[entry.field] || binding;
            value = readCanonical(previous, bindingPath(previous.data, old));
            try { value = type === 'string' ? String(value ?? '0') : numeric(value); } catch { value = 0; }
        }
        if (readCanonical(actor, path) !== value) { writeCanonical(actor, path, value); changed = true; }
    }
    return { changed, errors, fields };
}
