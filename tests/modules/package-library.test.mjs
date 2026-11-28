import test from 'node:test';
import assert from 'node:assert/strict';
import { compareVersions, currentReleases, packageBadges } from '../../gravewright/web/static/gravewright_web/inside/package-library.js';

test('versions compare numerically by component', () => {
  assert.equal(compareVersions('1.10.0', '1.9.9'), 1);
  assert.equal(compareVersions('0.2.0', '0.2.0'), 0);
  assert.equal(compareVersions('0.1.9', '0.2.0'), -1);
});

test('the library keeps one release per package, preferring the newest usable one', () => {
  const old = { id: 'book', version: '1.9.0' }, newest = { id: 'book', version: '1.10.0' };
  const revoked = { id: 'book', version: '2.0.0', revoked: true };
  const other = { id: 'lore', version: '0.1.0' };
  assert.deepEqual(currentReleases([old, other, newest, revoked]), [other, newest]);
  const onlyRevoked = [{ id: 'gone', version: '1.0.0', revoked: true }, { id: 'gone', version: '1.1.0', revoked: true }];
  assert.deepEqual(currentReleases(onlyRevoked), [onlyRevoked[1]]);
});

test('badges describe server code, compendiums and the required system', () => {
  const system = { id: 'gravewright.5e-srd', version: '0.2.2', name: 'SRD 5e', system: {} };
  const book = { id: 'book', version: '1.0.0', content: { compendiums: ['book.json'], requiresSystem: { id: system.id } } };
  assert.deepEqual(packageBadges(book, [system]), [
    { kind: 'compendiums' }, { kind: 'system', id: system.id, name: 'SRD 5e' },
  ]);
  assert.deepEqual(packageBadges(book, []).at(-1).name, system.id, 'An absent system is named by its ID.');
  assert.deepEqual(packageBadges({ id: 'srv', type: 'django' }), [{ kind: 'django' }]);
  assert.deepEqual(packageBadges({ id: 'srv', django: { apps: ['x'] } }), [{ kind: 'django' }]);
  assert.deepEqual(packageBadges({ id: 'plain', version: '1.0.0' }), []);
});
