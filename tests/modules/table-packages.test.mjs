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
test('compendium modules for another system are listed only while selected', () => {
  const book = { id: 'book', version: '1', content: { compendiums: ['book.json'], requiresSystem: { id: 'dnd' } } };
  const lore = { id: 'lore', version: '1', content: { compendiums: ['lore.json'] } };
  assert.deepEqual(tablePackages([book, lore], 'dnd', []), [book, lore]);
  assert.deepEqual(tablePackages([book, lore], 'savage', []), [lore]);
  assert.deepEqual(tablePackages([book, lore], 'savage', [book]), [book, lore]);
});
test('activation failures are explained in the interface language', async () => {
  const { activationMessage } = await import('../../gravewright/modules/static/gravewright_modules/table-packages.js');
  assert.match(activationMessage({ code: 'system_required' }, 'pt-BR'), /exige outro sistema/);
  assert.match(activationMessage({ code: 'incompatible_content' }, 'es'), /tipos de documento/);
  assert.match(activationMessage({ code: 'unexpected' }, 'en'), /could not be changed/);
});
