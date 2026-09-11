import { strict as assert } from 'node:assert';
import { test } from 'node:test';
import { pingShapes, PING_DURATION } from './map-ping.js';
test('legacy waves change to diamonds for focus, preserving size at any zoom', () => {
    assert.equal(PING_DURATION, 2000);
    const normal = pingShapes(.5, 1, false, '#123456'), focus = pingShapes(.5, 2, true, '#123456');
    assert.equal(normal.length, 5);
    assert.equal(focus.filter(s => s.kind === 'polygon').length, 3);
    const ring = normal[0], diamond = focus[0];
    if (ring.kind !== 'circle' || diamond.kind !== 'polygon')
        throw new Error('shape');
    assert.equal(diamond.points[2] * 2, ring.radius);
    assert.equal(diamond.stroke?.color, '#123456');
    assert.equal(pingShapes(.5, 1, false, 'invalid')[0]?.stroke?.color, '#f2c679');
});
