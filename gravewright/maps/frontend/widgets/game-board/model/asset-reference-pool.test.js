import assert from "node:assert/strict";
import test from "node:test";
import { DOMAdapter, Loader, Texture, TextureSource } from "pixi.js";
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

test("reacquiring art during Pixi unloading never returns a destroyed texture", async () => {
    const previousAdapter = DOMAdapter.get();
    DOMAdapter.set({ ...previousAdapter, getBaseUrl: () => "https://example.test/" });
    const loader = new Loader();
    let loads = 0;
    loader.parsers.push({
        name: "reference-pool-fixture",
        test: () => true,
        async load() {
            loads++;
            return new Texture({ source: new TextureSource({ width: 1, height: 1 }) });
        },
        unload(texture) { texture.destroy(true); },
    });
    const pool = new AssetReferencePool(url => loader.load(url), url => loader.unload(url));
    const url = "https://example.test/actor.fixture";
    try {
        const first = await pool.acquire(url);
        pool.release(url);
        const second = await pool.acquire(url);
        assert.equal(first.destroyed, true);
        assert.equal(second.destroyed, false);
        assert.ok(second.source);
        assert.notEqual(second, first);
        assert.equal(loads, 2);
        pool.release(url);
        await new Promise(resolve => setImmediate(resolve));
        assert.equal(second.destroyed, true);
    }
    finally { DOMAdapter.set(previousAdapter); }
});

test("pending unloading blocks only matching art and preserves every new reservation", async () => {
    let finishUnload;
    const gate = new Promise(resolve => { finishUnload = resolve; });
    const cached = new Map(), loaded = [], unloaded = [];
    const pool = new AssetReferencePool(async url => {
        loaded.push(url);
        if (!cached.has(url)) cached.set(url, { alive: true });
        return cached.get(url);
    }, async url => {
        unloaded.push(url);
        if (url === "actor.webp" && unloaded.filter(value => value === url).length === 1) await gate;
        cached.get(url).alive = false;
        cached.delete(url);
    });
    const first = await pool.acquire("actor.webp");
    pool.release("actor.webp");
    const next = [pool.acquire("actor.webp"), pool.acquire("actor.webp")];
    const unrelated = await pool.acquire("other.webp");
    assert.equal(unrelated.alive, true);
    assert.deepEqual(loaded, ["actor.webp", "other.webp"]);
    finishUnload();
    const [second, shared] = await Promise.all(next);
    assert.equal(first.alive, false);
    assert.equal(second.alive, true);
    assert.equal(second, shared);
    pool.release("actor.webp");
    await Promise.resolve();
    assert.equal(second.alive, true);
    assert.deepEqual(unloaded, ["actor.webp"]);
    pool.release("actor.webp");
    pool.release("other.webp");
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(second.alive, false);
    assert.equal(unrelated.alive, false);
    assert.deepEqual(unloaded, ["actor.webp", "actor.webp", "other.webp"]);
});

test("failed unloading does not strand subsequent owners or failed load reservations", async () => {
    const texture = {};
    let unloads = 0, failLoad = false;
    const pool = new AssetReferencePool(async () => {
        if (failLoad) throw new Error("load failed");
        return texture;
    }, async () => { unloads++; throw new Error("unload failed"); });
    await pool.acquire("actor.webp");
    pool.release("actor.webp");
    failLoad = true;
    assert.equal(await pool.acquire("actor.webp"), undefined);
    failLoad = false;
    assert.equal(await pool.acquire("actor.webp"), texture);
    pool.release("actor.webp");
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(unloads, 3);
});
