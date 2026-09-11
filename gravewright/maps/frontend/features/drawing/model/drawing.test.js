import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hit, translated, path, arrowHead } from './drawing.js';
const row = { id: 'a', kind: 'line', audience: 'campaign', points: [{ x: 0, y: 0 }, { x: 100, y: 100 }], color: '#ffffff', fill: 'none', width: 2, opacity: 1, fontSize: 21, text: '' };
test('selection hits the stroke, not the empty bounding box', () => { assert.equal(hit(row, { x: 50, y: 50 }, 3), true); assert.equal(hit(row, { x: 90, y: 10 }, 3), false); });
test('unfilled forms keep their interior selectable only after filling', () => { const rect = { ...row, kind: 'rect' }; assert.equal(hit(rect, { x: 50, y: 50 }, 3), false); assert.equal(hit({ ...rect, fill: '#ffffff' }, { x: 50, y: 50 }, 3), true); });
test('moving keeps source geometry immutable and preserves style', () => { const next = translated(row, 15, -10); assert.deepEqual(next.points, [{ x: 15, y: -10 }, { x: 115, y: 90 }]); assert.equal(row.points[0].x, 0); assert.equal(next.width, 2); });
test('arrowheads and reversed ellipses produce finite geometry', () => { assert.equal(arrowHead(row).length, 2); assert.ok(!path({ ...row, kind: 'ellipse', points: [{ x: 100, y: 100 }, { x: 0, y: 0 }] }).includes('NaN')); });
