import assert from 'node:assert/strict';
import { createTokenSnapshots } from './token-snapshots.js';

const hero = { id: 'hero', version: 1, gridX: 0 }, other = { id: 'other', version: 1 };
const snapshots = createTokenSnapshots();
snapshots.accept([hero, other]);
const move = snapshots.begin();
const confirmed = { ...hero, version: 2, gridX: 1 };
assert.deepEqual(snapshots.confirm(move, [confirmed, other]), [confirmed, other]);
const stale = snapshots.begin();
const newer = { ...confirmed, version: 4, gridX: 6 }, added = { id: 'added', version: 1 };
snapshots.accept([newer, added]);
assert.deepEqual(snapshots.confirm(stale, [{ ...hero, version: 3, gridX: 2 }, other]), [newer, added],
    'a delayed ACK cannot roll back versions, resurrect a removed token, or discard a newly visible one');
const remove = snapshots.begin();
snapshots.accept([newer, added]);
assert.deepEqual(snapshots.confirm(remove, [newer]), [newer],
    'the full authorized ACK can still remove an unchanged token');
const concurrent = snapshots.begin();
const advanced = { ...newer, version: 5 };
snapshots.accept([advanced]);
assert.deepEqual(snapshots.confirm(concurrent, []), [advanced],
    'a newer confirmed token cannot disappear because an older ACK omitted it');
const failure = snapshots.begin();
snapshots.cancel(failure);
snapshots.clear();
const fresh = snapshots.begin();
assert.deepEqual(snapshots.confirm(fresh, [hero]), [hero]);
