import assert from 'node:assert/strict';
import { createTokenTeleports } from './token-teleports.js';

const token = { id: 'hero', version: 3, gridX: 5, gridY: 6 };
const marks = createTokenTeleports();
assert.equal(marks.apply([token])[0].teleportVersion, 0);
const landed = marks.apply([token], [{ id: token.id, version: token.version }]);
assert.equal(landed[0].teleportVersion, 3);
assert.equal(landed[0].id, token.id);
assert.equal(token.teleportVersion, undefined, 'projection is not mutated');
assert.deepEqual(marks.apply([token], [{ id: token.id, version: token.version }]), landed,
    'command acknowledgement and snapshot share one presentation marker');
const moved = { ...token, version: 4, gridX: 7 };
assert.equal(marks.apply([moved])[0].teleportVersion, 3,
    'ordinary snapshots keep the same rendered token incarnation');
assert.equal(marks.apply([moved], [{ id: token.id, version: 3 }])[0].teleportVersion, 3,
    'a delayed teleport marker cannot apply to a newer token position');
const stale = createTokenTeleports();
stale.apply([moved]);
assert.equal(stale.apply([token], [{ id: token.id, version: 3 }])[0].teleportVersion, 0,
    'an older snapshot cannot start a superseded teleport');
const invalid = [null, {}, { id: 'other', version: 4 }, { id: token.id, version: 5 },
    { id: token.id, version: '4' }, { id: token.id, version: -1 }];
assert.equal(marks.apply([moved], invalid)[0].teleportVersion, 3);
assert.equal(marks.apply([moved], null)[0].teleportVersion, 3);
assert.equal(marks.apply([{ ...moved, version: 5 }], [{ id: token.id, version: 5 }])[0].teleportVersion, 5,
    'a later teleport creates a new incarnation');
marks.apply([]);
assert.equal(marks.apply([token])[0].teleportVersion, 0, 'removing a token forgets its marker');
marks.apply([token], [{ id: token.id, version: 3 }]);
marks.clear();
assert.equal(marks.apply([token])[0].teleportVersion, 0, 'destroying the workspace forgets markers');
assert.equal(createTokenTeleports().apply([token])[0].teleportVersion, 0,
    'another scene has an independent marker ledger');
