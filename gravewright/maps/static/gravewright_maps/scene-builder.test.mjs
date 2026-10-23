import test from 'node:test';
import assert from 'node:assert/strict';
import { createSceneBuilder } from './scene-builder.js';

test('linked scenes open their project without adopting a second source', async () => {
    const opened = [], open = createSceneBuilder({ campaignId: 'campaign',
        post: () => assert.fail('linked scenes need no mutation'), navigate: id => opened.push(id) });
    await open({ id: 'scene', version: 3, builderProjectId: 'existing' });
    assert.deepEqual(opened, ['existing']);
});

test('lost adoption replies retain the UUID and revision while later revisions start a new operation', async () => {
    const requests = [], opened = [];
    const open = createSceneBuilder({ campaignId: 'campaign', post: async (url, payload) => {
        requests.push({ url, payload: structuredClone(payload) });
        if (requests.length < 3) throw new Error('Offline');
        return { project: { id: 'adopted' } };
    }, navigate: id => opened.push(id) });
    const map = { id: 'scene', version: 3 };
    await assert.rejects(open(map), /Offline/);
    await assert.rejects(open(map), /Offline/);
    assert.deepEqual(requests[0], requests[1]);
    await open({ ...map, version: 4 });
    assert.notEqual(requests[2].payload.request_id, requests[0].payload.request_id);
    assert.equal(requests[2].payload.expected_scene_version, 4);
    assert.equal(requests[2].url, '/api/containers/campaign/map-builder/scenes/scene/adopt');
    assert.deepEqual(opened, ['adopted']);
});

test('concurrent actions do not duplicate adoption and a disposed page never navigates late', async () => {
    let finish, calls = 0;
    const abort = new AbortController(), open = createSceneBuilder({ campaignId: 'campaign', signal: abort.signal,
        post: async (_url, _payload, options) => {
            calls++; assert.equal(options.signal, abort.signal);
            return new Promise(resolve => { finish = resolve; });
        }, navigate: () => assert.fail('disposed directory must not navigate') });
    const first = open({ id: 'scene', version: 3 });
    assert.equal(await open({ id: 'scene', version: 3 }), false);
    abort.abort(); finish({ project: { id: 'adopted' } });
    assert.equal(await first, false); assert.equal(calls, 1);
    assert.equal(await open({ id: 'other', version: 1 }), false);
});

test('definitive conflicts retain the error and retry with a new operation identity', async () => {
    const requests = [], cause = Object.assign(new Error('Scene changed'), { status: 409 });
    const open = createSceneBuilder({ campaignId: 'campaign', post: async (_url, payload) => {
        requests.push(structuredClone(payload)); throw cause;
    }, navigate: () => assert.fail('conflicting adoption must not navigate') });
    const map = { id: 'scene', version: 3 };
    await assert.rejects(open(map), error => error === cause);
    await assert.rejects(open(map), error => error === cause);
    assert.notEqual(requests[0].request_id, requests[1].request_id);
});
