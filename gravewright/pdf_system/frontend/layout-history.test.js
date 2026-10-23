import { test } from 'node:test';
import assert from 'node:assert/strict';
import { captureLayout, restoreLayout, copyLayout, pasteLayout } from './layout-history.js';
import { manualFieldKey } from './manual-fields.js';

const source = 'template:generic', first = '11111111-1111-4111-8111-111111111111', second = '22222222-2222-4222-8222-222222222222';
const field = (id = first, changes = {}) => ({ id, source, page: 1, type: 'number', name: 'Score', x: .1, y: .2, width: .2, height: .05, ...changes });
function actor() {
    return { data: { pdf: { manualFields: [field()], fieldActions: [{ source, field: manualFieldKey(first), roll: { formula: '1d20+@value', label: 'Check' } }] },
        token: { bars: {} }, fields: { [manualFieldKey(first)]: 12 }, bars: { bar_1: { value: 4, max: 8 } } } };
}

test('layout restoration preserves current values and definitions belonging to another PDF', () => {
    const a = actor(), saved = captureLayout(a, source);
    a.data.pdf.manualFields[0].x = .4;
    a.data.pdf.manualFields.push(field(second, { source: 'template:other' }));
    a.data.fields[manualFieldKey(first)] = 19;
    a.data.bars.bar_1.value = 7;
    restoreLayout(a, saved);
    assert.equal(a.data.pdf.manualFields.find(row => row.id === first).x, .1);
    assert.equal(a.data.pdf.manualFields.find(row => row.id === second).source, 'template:other');
    assert.equal(a.data.fields[manualFieldKey(first)], 19);
    assert.equal(a.data.bars.bar_1.value, 7);
});

test('pasting allocates new identities, copies values and remaps internal formula references', () => {
    const a = actor(), key = manualFieldKey(first);
    a.data.pdf.fieldActions[0].roll.formula = `1d20+@{${key}}`;
    const clipboard = copyLayout(a, source, [first], { [key]: { path: `sheet.fields.${key}` } });
    const { candidate, ids } = pasteLayout(a, source, clipboard, { page: 2, pageCount: 2, uuid: () => second });
    assert.deepEqual(ids, [second]);
    assert.equal(candidate.data.pdf.manualFields[1].page, 2);
    assert.equal(candidate.data.fields[manualFieldKey(second)], 12);
    assert.equal(candidate.data.pdf.fieldActions[1].roll.formula, `1d20+@{${manualFieldKey(second)}}`);
    assert.equal(a.data.pdf.manualFields.length, 1);
    assert.throws(() => pasteLayout(a, source, clipboard, { page: 3, pageCount: 2, uuid: () => second }));
    assert.throws(() => pasteLayout(a, 'template:other', clipboard, { page: 1, pageCount: 2, uuid: () => second }));
});
