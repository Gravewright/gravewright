import test from 'node:test';
import assert from 'node:assert/strict';
import { SceneImageArt } from './scene-image-art.js';

const row = (id, src) => ({ id, src });
const settle = () => new Promise(resolve => setImmediate(resolve));
function fixture(options = {}) {
    const loads = [], applied = [], removed = [], released = [], pending = new Map();
    const art = new SceneImageArt({
        load: (url, signal) => {
            loads.push({ url, signal });
            return new Promise(resolve => pending.set(url, resolve));
        },
        apply: (id, resource) => applied.push([id, resource.url]),
        remove: id => removed.push(id),
        release: resource => released.push(resource.url),
        ...options,
    });
    return { art, loads, applied, removed, released, pending,
        async resolve(url, bytes = 4) {
            await settle();
            pending.get(url)({ url, bytes });
            await settle();
        },
    };
}

test('shared art loads once; unchanged updates and decoded swaps need no extra load', async () => {
    const f = fixture();
    f.art.sync([row('one', '/a'), row('two', '/a')]);
    await f.resolve('/a');
    assert.deepEqual(f.loads.map(load => load.url), ['/a']);
    assert.deepEqual(f.applied, [['one', '/a'], ['two', '/a']]);
    f.art.sync([row('one', '/b'), row('two', '/a')]);
    assert.deepEqual(f.released, []);
    assert.deepEqual(f.applied.at(-1), ['two', '/a']);
    await f.resolve('/b');
    f.art.sync([row('one', '/a'), row('two', '/a')]);
    assert.deepEqual(f.applied.at(-1), ['one', '/a']);
    f.art.sync([row('one', '/a'), row('two', '/a')]);
    assert.equal(f.applied.length, 4);
    assert.deepEqual(f.loads.map(load => load.url), ['/a', '/b']);
});

test('late art cannot overwrite a newer request or reappear after removal', async () => {
    const f = fixture();
    f.art.sync([row('one', '/a')]);
    await f.resolve('/a');
    f.art.sync([row('one', '/b')]);
    await settle();
    f.art.sync([row('one', '/c')]);
    assert.equal(f.loads.find(load => load.url === '/b').signal.aborted, true);
    await f.resolve('/c');
    await f.resolve('/b');
    assert.deepEqual(f.applied, [['one', '/a'], ['one', '/c']]);
    assert.ok(f.released.includes('/b'));
    f.art.sync([row('one', '/d')]);
    await settle();
    f.art.sync([]);
    await f.resolve('/d');
    assert.deepEqual(f.removed, ['one']);
    assert.equal(f.applied.length, 2);
    assert.ok(f.released.includes('/d'));
});

test('old visible art is retained until replacement is decoded, even with no idle allowance', async () => {
    const f = fixture({ idleLimit: 0 });
    f.art.sync([row('one', '/a')]);
    await f.resolve('/a');
    f.art.sync([row('one', '/b')]);
    await settle();
    assert.deepEqual(f.applied, [['one', '/a']]);
    assert.deepEqual(f.released, []);
    await f.resolve('/b');
    assert.deepEqual(f.applied.at(-1), ['one', '/b']);
    assert.deepEqual(f.released, ['/a']);
});

test('idle count and decoded-byte budgets release least recently used art but never active art', async () => {
    for (const options of [{ idleLimit: 1 }, { idleLimit: 8, idleBytes: 4 }]) {
        const f = fixture(options);
        f.art.sync([row('one', '/a')]);
        await f.resolve('/a');
        f.art.sync([row('one', '/b')]);
        await f.resolve('/b');
        f.art.sync([row('one', '/c')]);
        await f.resolve('/c');
        assert.deepEqual(f.released, ['/a']);
        f.art.sync([row('one', '/b')]);
        assert.deepEqual(f.applied.at(-1), ['one', '/b']);
        assert.equal(f.loads.length, 3);
        assert.ok(!f.released.includes('/b'));
    }
});

test('a static rebuild reuses current resources and pending loads without old callbacks', async () => {
    const f = fixture({ idleLimit: 0 });
    f.art.sync([row('one', '/a'), row('two', '/b')]);
    await f.resolve('/a');
    f.art.reset(true);
    f.art.sync([row('one', '/a'), row('two', '/b')]);
    assert.deepEqual(f.applied, [['one', '/a'], ['one', '/a']]);
    await f.resolve('/b');
    assert.deepEqual(f.applied.at(-1), ['two', '/b']);
    assert.equal(f.applied.length, 3);
    assert.equal(f.loads.length, 2);
    assert.deepEqual(f.released, []);
});

test('scene/role disposal frees decoded art, aborts pending work and cannot publish late results', async () => {
    const f = fixture();
    f.art.sync([row('one', '/a'), row('two', '/b')]);
    await f.resolve('/a');
    f.art.reset();
    assert.deepEqual(f.released, ['/a']);
    assert.equal(f.loads.find(load => load.url === '/b').signal.aborted, true);
    await f.resolve('/b');
    assert.deepEqual(f.released, ['/a', '/b']);
    assert.deepEqual(f.applied, [['one', '/a']]);
    assert.deepEqual(f.removed, ['one', 'two']);
});

test('a light rebuild retains previous art while its replacement is still loading', async () => {
    const f = fixture({ idleLimit: 0 });
    f.art.sync([row('one', '/a')]);
    await f.resolve('/a');
    f.art.sync([row('one', '/b')]);
    await settle();
    f.art.reset(true);
    f.art.sync([row('one', '/b')]);
    assert.deepEqual(f.applied, [['one', '/a'], ['one', '/a']]);
    assert.deepEqual(f.released, []);
    await f.resolve('/b');
    assert.deepEqual(f.applied.at(-1), ['one', '/b']);
    assert.deepEqual(f.released, ['/a']);
});

test('failed replacement preserves previous art and can retry on the next authoritative update', async () => {
    const f = fixture();
    f.art.sync([row('one', '/a')]);
    await f.resolve('/a');
    f.art.sync([row('one', '/b')]);
    await settle();
    f.pending.get('/b')(undefined);
    await settle();
    assert.deepEqual(f.applied, [['one', '/a']]);
    f.art.sync([row('one', '/b')]);
    await f.resolve('/b');
    assert.deepEqual(f.applied.at(-1), ['one', '/b']);
    assert.equal(f.loads.length, 3);
});
