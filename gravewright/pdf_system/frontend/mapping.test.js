import { test } from 'node:test';
import assert from 'node:assert/strict';
import { autoMapFields, readCanonical, writeCanonical } from './mapping.js';
test('PDF choices write directly to canonical token values', () => {
    const fields = autoMapFields(['Health', 'HP'], { HP: { path: 'sheet.bars.bar_1.value', type: 'number' } }, () => 'Tx', { bar2Value: 'Health' });
    const actor = { name: 'Hero', data: {} };
    writeCanonical(actor, fields.Health.path, 17);
    assert.equal(readCanonical(actor, 'sheet.bars.bar_2.value'), 17);
    assert.equal(readCanonical(actor, 'sheet.fields.Health'), undefined);
});
test('PDF names cannot inject object prototypes and sanitized collisions stay distinct', () => {
    const fields = autoMapFields(['A B', 'A_B', 'A_B_2', '__proto__'], {}, () => 'Tx', {});
    assert.equal(new Set(Object.values(fields).map(f => f.path)).size, 4);
    const actor = { name: 'Hero', data: {} };
    writeCanonical(actor, 'sheet.__proto__.polluted', true);
    writeCanonical(actor, 'sheet.constructor.prototype.polluted', true);
    assert.equal({}.polluted, undefined);
    writeCanonical(actor, fields.__proto__.path, 'safe');
    assert.equal(readCanonical(actor, fields.__proto__.path), 'safe');
});
