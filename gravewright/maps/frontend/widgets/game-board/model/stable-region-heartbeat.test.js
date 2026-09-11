import assert from "node:assert/strict";
import test from "node:test";
import { StableRegionHeartbeat } from "./stable-region-heartbeat.js";
function clock() {
    let now = 0, nextId = 0;
    const pending = new Map();
    const scheduler = {
        after(milliseconds, callback) { const id = ++nextId; pending.set(id, { at: now + milliseconds, callback }); return id; },
        cancel(id) { pending.delete(id); },
    };
    return { scheduler, advance(milliseconds) { const end = now + milliseconds; while (true) {
            const due = [...pending].filter(([, task]) => task.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
            if (!due)
                break;
            now = due[1].at;
            pending.delete(due[0]);
            due[1].callback();
        } now = end; }, size: () => pending.size };
}
test("a settled viewport repeats so dwell and player leases remain observable", () => {
    const time = clock(), sent = [];
    const reporter = new StableRegionHeartbeat((left, right) => left === right, (value) => sent.push(value), time.scheduler);
    reporter.changed("region-a");
    time.advance(299);
    assert.deepEqual(sent, []);
    time.advance(1);
    assert.deepEqual(sent, ["region-a"]);
    time.advance(2000);
    assert.deepEqual(sent, ["region-a", "region-a", "region-a"]);
    reporter.stop();
    time.advance(5000);
    assert.equal(sent.length, 3);
    assert.equal(time.size(), 0);
});
test("movement replaces the pending region before any heartbeat starts", () => {
    const time = clock(), sent = [];
    const reporter = new StableRegionHeartbeat((left, right) => left === right, (value) => sent.push(value), time.scheduler);
    reporter.changed("crossed");
    time.advance(200);
    reporter.changed("destination");
    time.advance(300);
    assert.deepEqual(sent, ["destination"]);
    time.advance(1000);
    assert.deepEqual(sent, ["destination", "destination"]);
});
