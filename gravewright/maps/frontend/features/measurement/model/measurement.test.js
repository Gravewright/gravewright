import assert from 'node:assert/strict';
import { area, dragMeasure, measurePath, summary, unitsPerPixel } from './measurement.js';
const m = { id: 'a', kind: 'line', origin: { x: 0, y: 0 }, length: 70, width: 35, direction: 0, angle: 60, color: '#ffffff' };
assert.equal(unitsPerPixel(70, 5) * 140, 10);
assert.equal(unitsPerPixel(140, 5) * 140, 5);
assert.equal(summary(m, 5 / 70, 'ft'), '5 ft');
assert.equal(dragMeasure(m, { x: 30, y: 40 }).length, 50);
assert.equal(dragMeasure(m, { x: 70, y: 20 }, true).direction, 0);
const rect = dragMeasure({ ...m, kind: 'rect', origin: { x: 100, y: 100 } }, { x: 20, y: 40 });
assert.deepEqual(rect.origin, { x: 20, y: 40 });
assert.equal(area(rect), 4800);
const square = dragMeasure({ ...m, kind: 'rect' }, { x: 80, y: 40 }, true);
assert.equal(square.length, square.width);
assert.ok(Math.abs(area({ ...m, kind: 'circle', length: 10 }) - Math.PI * 100) < 1e-8);
assert.ok(Math.abs(area({ ...m, kind: 'cone', length: 10, angle: 90 }) - 100) < 1e-8);
for (const kind of ['line', 'circle', 'rect', 'cone', 'wide-cone']) {
    const shape = { ...m, kind };
    assert.ok(!measurePath(shape).includes('NaN'));
    assert.ok(Number.isFinite(area(shape)));
}
const wide = { ...m, kind: 'wide-cone', length: 90, width: 30 };
assert.ok(measurePath(wide).includes('A15 15'));
assert.ok(area(wide) > Math.PI * 225);
assert.ok(area(wide) < 90 * 30);
