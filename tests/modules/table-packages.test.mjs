import test from 'node:test';
import assert from 'node:assert/strict';
import { tablePackages } from '../../gravewright/modules/static/gravewright_modules/table-packages.js';

const dice = { id: 'dice', version: '1' };
const translator = { id: 'translator', version: '1', locales: {} };
const savage = { id: 'savage', version: '2', system: {} };
const older = { ...savage, version: '1' };
const dnd = { id: 'dnd', version: '1', system: {} };
const packages = [dice, dnd, older, savage, translator];

test('table keeps only its active system version, with inactive ordinary modules', () => {
  assert.deepEqual(tablePackages(packages, 'savage', [savage]), [dice, savage, translator]);
});
test('stale module selections cannot expose a different system', () => {
  assert.deepEqual(tablePackages(packages, 'savage', [savage, dnd]), [dice, savage, translator]);
});
test('no active system exposes only ordinary extensions', () => {
  assert.deepEqual(tablePackages(packages, 'savage'), [dice, translator]);
  assert.deepEqual(tablePackages(packages, '', [savage]), [dice, translator]);
});
test('revocation remains visible for the selected system', () => {
  const revoked = { ...savage, revoked: true };
  assert.deepEqual(tablePackages([revoked, dnd], 'savage', [savage]), [revoked]);
});
