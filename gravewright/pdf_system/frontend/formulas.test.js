import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fieldReference, fieldReferences, expandFieldFormula, calculateFormula,
    captureFieldBindings, bindingsForSource, bindingPath, recalculateFields } from './formulas.js';

test('field references preserve exact names with punctuation, braces and backslashes', () => {
    const names = ['Score.with punctuation [0]', 'close}brace', 'back\\slash', '__proto__'];
    const formula = names.map(fieldReference).join(' + ') + ' + @value';
    assert.deepEqual(fieldReferences(formula), names);
    assert.equal(expandFieldFormula('1d20 + @{Score} + @value', () => '-3', { value: 2 }), '1d20 + (-3) + (2)');
    assert.equal(expandFieldFormula('@{Score}', () => 1e-7), '(0.0000001)');
    assert.equal(expandFieldFormula('@{Score}', () => false), '(0)');
    for (const formula of ['@{', '@{}', '@{ }', '@{bad\\q}', '@other', '@value.foo'])
        assert.throws(() => fieldReferences(formula));
    for (const value of ['1d20', '0x10', '1e3', {}, [], Infinity, NaN, 1000001])
        assert.throws(() => expandFieldFormula('@{Score}', () => value));
});

test('deterministic numeric semantics match native formula operations and bounds', () => {
    const cases = { 'floor(-1.2)': -2, 'ceil(-1.2)': -1, 'round(-1.5)': -1,
        'round(1.5)': 2, 'round(-0.5)': 0, 'abs(-3)': 3, 'min(2, 3)': 2,
        'max(2, 3)': 3, 'clamp(20, 0, 10)': 10, '1 < 2': 1,
        '2 == 3': 0, '-3 + 2 * 4 / 2': 1, '@{Score} * 2 + @{Score}': 9,
        'floor((@{Score} - 10) / 2)': -4 };
    for (const [formula, expected] of Object.entries(cases))
        assert.equal(calculateFormula(formula, () => 3), expected, formula);
    for (const formula of ['1 / 0', 'clamp(1, 3, 2)', '1000000 * 2', 'max(1 < 2, 3)',
        'unknown(2)', '1d6', 'd20', '4dF', '@value + 2', '1 < 2 < 3', 'constructor(1)',
        '1'.repeat(513), '('.repeat(33) + '1' + ')'.repeat(33)])
        assert.throws(() => calculateFormula(formula, () => 3), formula);
});

const binding = (field, extra = {}) => ({ source: 'template:generic', field,
    path: `sheet.fields.${field}`, type: 'number', name: field, ...extra });
const calculated = (field = 'Total', formula = '@{Score} + 2', extra = {}) => ({ source: 'template:generic', field, formula, ...extra });
const actor = () => ({ name: 'Hero', data: {
    pdf: { template: 'generic', fieldBindings: [binding('Score'), binding('Total'), binding('Double')],
        calculatedFields: [calculated()] }, fields: { Score: 3, Total: 999 },
    token: { bars: {} }, bars: { bar_1: { value: 0, max: 10 }, bar_2: { value: 0, max: 10 } },
} });

test('captured original bindings exclude private and protected addresses', () => {
    const originals = { Score: { path: 'sheet.fields.Score', type: 'number' },
        Name: { path: 'core.name', type: 'string' }, Private: { path: 'sheet.pdf.asset', type: 'string' },
        Proto: { path: 'sheet.fields.__proto__', type: 'number' },
        HP: { path: 'sheet.bars.bar_1.value', type: 'number' } };
    const rows = captureFieldBindings('template:generic', originals, new Map([['Score', { readOnly: true }]]));
    assert.deepEqual(rows.map(row => row.field), ['Score', 'HP']);
    assert.equal(rows[0].readOnly, true);
});

test('calculated targets ignore submitted values and chains use dependency order', () => {
    const value = actor();
    value.data.pdf.calculatedFields = [calculated('Double', '@{Total} * 2'), calculated()];
    const result = recalculateFields(value, 'template:generic');
    assert.equal(result.changed, true);
    assert.deepEqual(result.errors, []);
    assert.deepEqual([...result.fields], ['Double', 'Total']);
    assert.equal(value.data.fields.Total, 5);
    assert.equal(value.data.fields.Double, 10);
    assert.equal(recalculateFields(value, 'template:generic').changed, false);
});

test('missing references, self references, graph cycles and aliases never partially mutate fields', () => {
    const variants = [[calculated('Total', '@{Missing}')], [calculated('Total', '@{Total}')],
        [calculated('Total', '@{Double}'), calculated('Double', '@{Total}')]];
    for (const definitions of variants) {
        const value = actor(); value.data.pdf.calculatedFields = definitions;
        const before = structuredClone(value);
        assert.equal(recalculateFields(value, 'template:generic').errors.length, 1);
        assert.deepEqual(value, before);
    }
    const value = actor();
    value.data.pdf.fieldBindings.push(binding('Alias', { path: 'sheet.fields.Total' }));
    value.data.pdf.calculatedFields = [calculated('Total', '@{Alias}')];
    assert.match(recalculateFields(value, 'template:generic').errors[0].message, /circular/);
});

test('failed runtime inputs preserve last values and can restore a server candidate', () => {
    const previous = actor(); recalculateFields(previous, 'template:generic');
    const value = structuredClone(previous);
    value.data.fields.Score = 'Authored words';
    value.data.fields.Total = 999;
    const result = recalculateFields(value, 'template:generic', { previous });
    assert.equal(result.errors[0].field, 'Total');
    assert.equal(value.data.fields.Total, 5);
    value.data.fields.Total = 7;
    recalculateFields(value, 'template:generic');
    assert.equal(value.data.fields.Total, 7);
});

test('only the selected PDF source is recomputed and text targets retain string storage', () => {
    const value = actor();
    value.data.pdf.fieldBindings.push(binding('Score', { source: 'template:other' }), binding('Total', { source: 'template:other' }));
    value.data.pdf.calculatedFields.push(calculated('Total', '@{Score} * 100', { source: 'template:other' }));
    value.data.pdf.fieldBindings[1].type = 'string';
    recalculateFields(value, 'template:generic');
    assert.equal(value.data.fields.Total, '5');
    assert.equal(bindingsForSource(value.data.pdf, 'template:other').Total.type, 'number');
});

test('manual identities and current token bar overrides are resolved without PDF parsing', () => {
    const value = actor(), id = '11111111-1111-4111-8111-111111111111', key = 'manual_' + id.replaceAll('-', '');
    value.data.pdf.manualFields = [{ id, source: 'template:generic', name: 'Modifier', type: 'number', page: 1,
        x: 0.1, y: 0.1, width: 0.2, height: 0.05 }];
    value.data.pdf.calculatedFields = [calculated('Total', `@{${key}} + 2`)];
    value.data.token.bars = { bar1Value: key, bar2Value: 'Total' };
    value.data.bars.bar_1.value = 8;
    recalculateFields(value, 'template:generic');
    assert.equal(value.data.bars.bar_2.value, 10);
    assert.equal(bindingPath(value.data, bindingsForSource(value.data.pdf, 'template:generic')[key]), 'sheet.bars.bar_1.value');
});
