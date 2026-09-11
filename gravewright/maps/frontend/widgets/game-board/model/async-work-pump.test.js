import assert from "node:assert/strict";
import test from "node:test";
import { AsyncWorkPump } from "./async-work-pump.js";
const deferred = () => {
    let resolve;
    const promise = new Promise((done) => { resolve = done; });
    return { promise, resolve };
};
test("work queued while a drain awaits starts a new pass when that drain finishes", async () => {
    let queued = 1;
    let passes = 0;
    const firstPass = deferred();
    const completed = deferred();
    const pump = new AsyncWorkPump(() => queued > 0, async () => {
        queued -= 1;
        passes += 1;
        if (passes === 1)
            await firstPass.promise;
        else
            completed.resolve();
    });
    pump.request();
    queued += 1;
    pump.request();
    assert.equal(passes, 1, "the second request must not drain concurrently");
    firstPass.resolve();
    await completed.promise;
    assert.equal(passes, 2);
    assert.equal(queued, 0);
});
