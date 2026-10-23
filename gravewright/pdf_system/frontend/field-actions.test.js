import { test } from 'node:test';
import assert from 'node:assert/strict';
import { actionsForSource, numericFieldValue, fieldRollExpression, fieldActionCandidate } from './field-actions.js';

test('roll actions stay source-bound and do not interpret PDF names as prototypes', () => {
    const pdf = { fieldActions: [
        { source: 'template:first', field: '__proto__', roll: { formula: '1d6' } },
        { source: 'template:second', field: 'Score', roll: { formula: '1d20' } },
    ] };
    const actions = actionsForSource(pdf, 'template:first');
    assert.equal(Object.getPrototypeOf(actions), null);
    assert.equal(actions.__proto__.formula, '1d6');
    assert.equal(actions.Score, undefined);
});

test('roll references accept only bounded numeric values, preserving signs and tiny decimals', () => {
    assert.equal(fieldRollExpression('2d20kh1 + @value', '-3.5'), '2d20kh1 + (-3.5)');
    assert.equal(fieldRollExpression('max(@value, @value + 1d6)', true), 'max((1), (1) + 1d6)');
    assert.equal(fieldRollExpression('1d6 + @value', 1e-7), '1d6 + (0.0000001)');
    assert.equal(fieldRollExpression('1d6 + @value', -1e-20), '1d6 + (-0.00000000000000000001)');
    assert.equal(fieldRollExpression('1d6', 'Authored text'), '1d6');
    assert.equal(fieldRollExpression('1d6 + @value', ''), '1d6 + (0)');
    for (const value of ['1d6', '0x10', '1e3', {}, NaN, Infinity, 1000001])
        assert.throws(() => numericFieldValue(value));
    for (const formula of ['1d6+@other', '1d6+@value.foo', '', '1'.repeat(513)])
        assert.throws(() => fieldRollExpression(formula, 1));
});

const actor = () => ({ name: 'Hero', data: {
    pdf: {}, fields: { Score: '12', Other: 9 },
    token: { bars: { bar1Value: '', bar1Max: '', bar2Value: '', bar2Max: '', initiative: '', defense: '' } },
    bars: { bar_1: { value: 3, max: 20 }, bar_2: { value: 5, max: 10 } },
} });
const originals = { Score: { path: 'sheet.fields.Score', type: 'string' },
    Other: { path: 'sheet.fields.Other', type: 'number' } };

test('binding, moving and removing a token bar preserves the displayed field value', () => {
    const before = actor();
    let saved = fieldActionCandidate(before, 'template:first', 'Score', { bar: 'bar1Value', formula: '1d20+@value', label: 'Check' }, originals, originals);
    assert.equal(saved.data.bars.bar_1.value, 12);
    assert.equal(before.data.bars.bar_1.value, 3);
    assert.equal(saved.data.token.bars.bar1Value, 'Score');
    assert.equal(saved.data.pdf.fieldActions[0].roll.formula, '1d20+@value');
    saved.data.bars.bar_1.value = 17;
    const resolved = { ...originals, Score: { path: 'sheet.bars.bar_1.value', type: 'number' } };
    const unbound = fieldActionCandidate(saved, 'template:first', 'Score', { bar: '', formula: '', label: '' }, resolved, originals);
    assert.equal(unbound.data.fields.Score, '17');
    assert.equal(unbound.data.token.bars.bar1Value, '');
    assert.deepEqual(unbound.data.pdf.fieldActions, []);
});

test('replacing a bar field archives its last value without changing the actor or other source actions', () => {
    const before = actor();
    before.data.token.bars.bar1Value = 'Other';
    before.data.pdf.fieldActions = [{ source: 'template:second', field: 'Score', roll: { formula: '1d6', label: '' } }];
    const resolved = { ...originals, Other: { path: 'sheet.bars.bar_1.value', type: 'number' } };
    const saved = fieldActionCandidate(before, 'template:first', 'Score', { bar: 'bar1Value', formula: '', label: '' }, resolved, originals);
    assert.equal(saved.data.fields.Other, 3);
    assert.equal(before.data.fields.Other, 9);
    assert.equal(saved.data.bars.bar_1.value, 12);
    assert.deepEqual(saved.data.pdf.fieldActions, before.data.pdf.fieldActions);
    before.data.fields.Score = 'Name';
    assert.throws(() => fieldActionCandidate(before, 'template:first', 'Score', { bar: 'bar1Value', formula: '', label: '' }, resolved, originals));
    assert.equal(before.data.token.bars.bar1Value, 'Other');
});
