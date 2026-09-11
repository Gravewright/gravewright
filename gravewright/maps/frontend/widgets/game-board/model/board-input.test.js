import assert from "node:assert/strict";
import test from "node:test";
import { MAX_SCALE, MIN_SCALE, movedBeyondThreshold, zoomAround } from "./board-input.js";
test("a press only becomes a drag once it leaves the threshold", () => {
    const origin = { x: 100, y: 100 };
    assert.equal(movedBeyondThreshold(origin, { x: 100, y: 100 }), false);
    assert.equal(movedBeyondThreshold(origin, { x: 106, y: 108 }), false, "exactly 10px still counts as held still");
    assert.equal(movedBeyondThreshold(origin, { x: 111, y: 100 }), true);
    assert.equal(movedBeyondThreshold(origin, { x: 105, y: 100 }, 4), true, "callers may tighten the threshold");
});
test("zooming keeps the point under the pointer anchored", () => {
    const pointer = { x: 400, y: 300 };
    const before = { x: 50, y: 20 };
    const scale = 1;
    const world = { x: (pointer.x - before.x) / scale, y: (pointer.y - before.y) / scale };
    const zoomedIn = zoomAround(pointer, before, scale, -100);
    assert.ok(zoomedIn.scale > scale);
    assert.equal(Math.round(zoomedIn.position.x + world.x * zoomedIn.scale), pointer.x);
    assert.equal(Math.round(zoomedIn.position.y + world.y * zoomedIn.scale), pointer.y);
    const zoomedOut = zoomAround(pointer, before, scale, 100);
    assert.ok(zoomedOut.scale < scale);
    assert.equal(Math.round(zoomedOut.position.x + world.x * zoomedOut.scale), pointer.x);
});
test("zoom stays inside the scale range however hard the wheel is spun", () => {
    let viewport = { scale: 1, position: { x: 0, y: 0 } };
    for (let step = 0; step < 40; step += 1)
        viewport = zoomAround({ x: 0, y: 0 }, viewport.position, viewport.scale, -1);
    assert.equal(viewport.scale, MAX_SCALE);
    viewport = { scale: 1, position: { x: 0, y: 0 } };
    for (let step = 0; step < 40; step += 1)
        viewport = zoomAround({ x: 0, y: 0 }, viewport.position, viewport.scale, 1);
    assert.equal(viewport.scale, MIN_SCALE);
});
