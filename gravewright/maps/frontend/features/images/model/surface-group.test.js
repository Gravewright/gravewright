import test from 'node:test';
import assert from 'node:assert/strict';
import { surfaceGroupBounds, surfaceGroupsLayout } from './surface-group.js';

const row = (extra = {}) => ({ x: 100, y: 100, natural_width: 40, natural_height: 20, scale: 1, rotation: 0, ...extra });
test('surface layer bounds retain transformed paint and erasers while clipping to scene pixels', () => {
    assert.deepEqual(surfaceGroupBounds([row(), row({ x: 20, rotation: 90 })], 200, 200),
        { left: 10, top: 80, width: 110, height: 40 });
    assert.deepEqual(surfaceGroupBounds([row({ x: 0, y: 0 })], 200, 200), { left: 0, top: 0, width: 20, height: 10 });
    assert.equal(surfaceGroupBounds([row({ x: -1000 })], 200, 200), null);
});
test('group buffers reject oversized or nonfinite geometry before canvas allocation', () => {
    assert.throws(() => surfaceGroupBounds([row({ natural_width: 5000, natural_height: 5000, x: 2500, y: 2500 })], 5000, 5000), /surface group/);
    assert.throws(() => surfaceGroupBounds([row({ x: NaN })], 200, 200), /surface group/);
});
test('all group buffers are budgeted before asynchronous image loads or canvas allocation', () => {
    assert.throws(() => surfaceGroupsLayout(Array.from({ length: 1000 }, () => [row()]), 4096, 4096), /Too many/);
    const full = row({ x: 2048, y: 2048, natural_width: 4096, natural_height: 4096 });
    assert.equal(surfaceGroupsLayout([[full], [full], [full], [full]], 4096, 4096).length, 4);
    assert.throws(() => surfaceGroupsLayout([[full], [full], [full], [full], [full]], 4096, 4096), /pixel limit/);
});
