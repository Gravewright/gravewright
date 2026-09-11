import assert from "node:assert/strict";
import test from "node:test";
import { AssetReferencePool } from "./asset-reference-pool.js";
test("shared art unloads only after its last token releases it", async () => {
    const unloaded = [];
    const texture = {};
    const pool = new AssetReferencePool(async () => texture, async (url) => { unloaded.push(url); });
    await Promise.all([pool.acquire("actor.webp"), pool.acquire("actor.webp"), pool.acquire("actor.webp")]);
    pool.release("actor.webp");
    pool.release("actor.webp");
    assert.deepEqual(unloaded, []);
    pool.release("actor.webp");
    await Promise.resolve();
    assert.deepEqual(unloaded, ["actor.webp"]);
});
test("a failed load releases its reservation without unloading another token's art", async () => {
    const unloaded = [];
    let fails = false;
    const pool = new AssetReferencePool(async () => { if (fails)
        throw new Error("failed"); return {}; }, async (url) => { unloaded.push(url); });
    await pool.acquire("actor.webp");
    fails = true;
    assert.equal(await pool.acquire("actor.webp"), undefined);
    assert.deepEqual(unloaded, []);
    pool.release("actor.webp");
    await Promise.resolve();
    assert.deepEqual(unloaded, ["actor.webp"]);
});
