import assert from 'node:assert/strict';
import { doorArt } from './door-art.js';

const wall = { kind: 'door', door_state: 'closed', asset_id: '7daaf194-d258-4d81-90ed-ef6905beb061',
    x1: 14, y1: 28, x2: 14, y2: 98, thickness: 12 };
const art = doorArt(wall);
assert.deepEqual([art.x, art.y, art.width, art.height, art.angle], [14, 28, 70, 12, 90]);
assert.equal(doorArt({ ...wall, door_state: 'open' }), undefined);
assert.deepEqual(doorArt({ ...wall, door_state: 'locked' }), art);
assert.equal(doorArt({ ...wall, kind: 'wall' }), undefined);
assert.equal(doorArt({ ...wall, asset_id: '../../foreign' }), undefined);
assert.equal(doorArt({ ...wall, x2: NaN }), undefined);
assert.equal(doorArt({ ...wall, thickness: Infinity }), undefined);
assert.equal(doorArt({ ...wall, x2: wall.x1, y2: wall.y1 }), undefined);

// The server derives the current appearance. The client never reads private
// blueprint definitions to decide which artwork other participants receive.
const alternate = '72f8c80b-a0af-4295-b141-ff834dfed41e';
const opened = doorArt({ ...wall, door_state: 'open',
    blueprintAppearance: { visible: true, assetId: alternate } });
assert.equal(opened.src, `/game/map-assets/${alternate}`);
assert.deepEqual([opened.x, opened.y, opened.width, opened.height, opened.angle],
    [art.x, art.y, art.width, art.height, art.angle]);
assert.equal(doorArt({ ...wall, blueprintAppearance: { visible: false, assetId: alternate } }), undefined);
assert.equal(doorArt({ ...wall, blueprintAppearance: { visible: true, assetId: null } }), undefined);
assert.equal(doorArt({ ...wall, blueprintAppearance: { visible: true, assetId: '../../foreign' } }), undefined);
assert.equal(doorArt({ ...wall, blueprintAppearance: { visible: 'true', assetId: alternate } }), undefined);
assert.equal(doorArt({ ...wall, blueprintAppearance: null }), undefined);
assert.equal(doorArt({ ...wall, blueprintAppearance: {}, blueprint: { assetId: alternate } }), undefined);
assert.equal(doorArt({ ...wall, kind: 'wall', blueprintAppearance: { visible: true, assetId: alternate } }), undefined);

for (const [rotationAnchor, position] of [['start', [14, 28]], ['center', [49, 63]], ['end', [84, 98]]]) {
    const data = { ...wall, rotationAnchor, door_state: 'open' }, before = structuredClone(data), opened = doorArt(data);
    assert.deepEqual([opened.x, opened.y, opened.angle], [...position, 180]);
    assert.deepEqual(data, before, 'opening rotates only the image, never the collision endpoints');
    assert.deepEqual(doorArt({ ...data, door_state: 'closed' }), art);
    assert.deepEqual(doorArt({ ...data, door_state: 'locked' }), art);
    assert.equal(doorArt({ ...data, blueprintAppearance: { visible: false, assetId: alternate } }), undefined);
    assert.equal(doorArt({ ...data, blueprintAppearance: { visible: true, assetId: alternate } }).angle, 180);
}
