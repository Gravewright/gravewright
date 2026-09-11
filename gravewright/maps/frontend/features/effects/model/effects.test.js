import { test } from 'node:test';
import assert from 'node:assert/strict';
import { defaults, hitEffect, inMarquee, translatedCopies } from './effects.js';
const a = { key: 'particle:a', id: 'a', kind: 'particle', x: 10, y: 20, data: { ...defaults(), x: 10, y: 20 } };
const b = { key: 'shader:b', id: 'b', kind: 'shader', x: 30, y: 40, data: { ...defaults(), x: 30, y: 40 } };
test('marquee selects origins in either direction, including empty selections', () => { assert.deepEqual(inMarquee([a, b], { x: 40, y: 50 }, { x: 0, y: 0 }), [a.key, b.key]); assert.deepEqual(inMarquee([a, b], { x: 100, y: 100 }, { x: 101, y: 101 }), []); });
test('hit targets remain the same size on screen as zoom changes', () => { assert.equal(hitEffect([a], { x: 16, y: 20 }, 2)?.id, 'a'); assert.equal(hitEffect([a], { x: 17, y: 20 }, 2), undefined); });
test('mixed copies preserve relative origins and never send source identities', () => { const pasted = translatedCopies([a, b], { x: 100, y: 100 }); assert.equal(pasted[0].data.x, 90); assert.equal(pasted[1].data.x, 110); assert.equal(pasted[1].data.y, 110); assert.equal('id' in pasted[0].data, false); });
