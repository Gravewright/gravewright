import assert from "node:assert/strict";
import test from "node:test";
import { classifyTile, PRIORITY, TileScheduler } from "./tile-scheduler.js";
function work(key, priority = PRIORITY.normal, extra = {}) {
    return { key, payload: key, priority, order: extra.order ?? 0, scene: extra.scene ?? "scene-1", generation: extra.generation ?? 1 };
}
test("the most urgent work leaves first", () => {
    const queue = new TileScheduler();
    queue.enqueue(work("far", PRIORITY.low), 0);
    queue.enqueue(work("edge", PRIORITY.normal), 0);
    queue.enqueue(work("eye", PRIORITY.high), 0);
    assert.deepEqual(queue.drain(0, { maxItems: 3 }), ["eye", "edge", "far"]);
    assert.equal(queue.size, 0, "drained work leaves the queue");
});
test("inside one priority, the nearer tile goes first", () => {
    const queue = new TileScheduler();
    queue.enqueue(work("d3", PRIORITY.normal, { order: 3 }), 0);
    queue.enqueue(work("d1", PRIORITY.normal, { order: 1 }), 0);
    queue.enqueue(work("d2", PRIORITY.normal, { order: 2 }), 0);
    assert.deepEqual(queue.drain(0, { maxItems: 3 }), ["d1", "d2", "d3"]);
});
test("a budget leaves the rest queued rather than dropping it", () => {
    const queue = new TileScheduler();
    for (const key of ["a", "b", "c"])
        queue.enqueue(work(key), 0);
    assert.equal(queue.drain(0, { maxItems: 2 }).length, 2);
    assert.equal(queue.size, 1);
});
test("re-queuing a key updates the work without resetting how long it has waited", () => {
    const queue = new TileScheduler();
    queue.enqueue(work("tile", PRIORITY.background), 0);
    queue.enqueue({ ...work("tile", PRIORITY.background), payload: "moved" }, 900);
    // Queued at 0, so by 1000ms it has waited two promotion windows whichever way it was re-queued.
    const [pending] = queue.pending(1000);
    assert.equal(pending?.priority, PRIORITY.normal, "the wait survives being asked for again");
    assert.deepEqual(queue.drain(1000, { maxItems: 1 }), ["moved"], "but the newest payload is what runs");
});
test("work that starves is promoted, one level per window, never to immediate", () => {
    const queue = new TileScheduler();
    queue.enqueue(work("starving", PRIORITY.background), 0);
    assert.equal(queue.pending(499)[0]?.priority, PRIORITY.background, "not yet");
    assert.equal(queue.pending(500)[0]?.priority, PRIORITY.low);
    assert.equal(queue.pending(1000)[0]?.priority, PRIORITY.normal);
    assert.equal(queue.pending(10_000)[0]?.priority, PRIORITY.high, "aging stops at high: waiting is not blocking");
});
test("aged background work overtakes fresher visible work", () => {
    const queue = new TileScheduler();
    queue.enqueue(work("old", PRIORITY.low), 0);
    queue.enqueue(work("fresh", PRIORITY.normal), 1400);
    assert.deepEqual(queue.drain(1500, { maxItems: 2 }), ["old", "fresh"]);
});
test("a scene change cancels the work the old scene queued", () => {
    const queue = new TileScheduler();
    queue.enqueue(work("old-scene", PRIORITY.high, { scene: "scene-1" }), 0);
    queue.enqueue(work("new-scene", PRIORITY.low, { scene: "scene-2" }), 0);
    assert.equal(queue.cancelScope({ sceneNot: "scene-2" }), 1);
    assert.deepEqual(queue.drain(0, { maxItems: 5 }), ["new-scene"]);
});
test("a moved viewport cancels what the previous one was still waiting for", () => {
    const queue = new TileScheduler();
    queue.enqueue(work("stale", PRIORITY.low, { generation: 4 }), 0);
    queue.enqueue(work("current", PRIORITY.low, { generation: 5 }), 0);
    assert.equal(queue.cancelScope({ olderThanGeneration: 5 }), 1);
    assert.deepEqual(queue.drain(0, { maxItems: 5 }), ["current"]);
});
test("a tile is ranked by where the eye is, not by where the range happens to be", () => {
    const visible = { firstColumn: 0, firstRow: 0, lastColumn: 10, lastRow: 10 };
    const focus = { column: 8, row: 8 };
    assert.equal(classifyTile({ column: 8, row: 8 }, visible, focus).ring, "visible-center");
    assert.equal(classifyTile({ column: 9, row: 8 }, visible, focus).priority, PRIORITY.high);
    assert.equal(classifyTile({ column: 2, row: 2 }, visible, focus).ring, "visible-edge", "on screen but far from the eye");
    assert.equal(classifyTile({ column: 2, row: 2 }, visible, focus).priority, PRIORITY.normal);
    const slack = classifyTile({ column: 11, row: 5 }, visible, focus);
    assert.equal(slack.ring, "prefetch");
    assert.equal(slack.priority, PRIORITY.low, "one pan away is worth fetching, but only after the screen is whole");
});
test("distance orders a ring from the eye outwards", () => {
    const visible = { firstColumn: 0, firstRow: 0, lastColumn: 10, lastRow: 10 };
    const focus = { column: 5, row: 5 };
    assert.equal(classifyTile({ column: 5, row: 5 }, visible, focus).distance, 0);
    assert.equal(classifyTile({ column: 8, row: 9 }, visible, focus).distance, 5);
});
