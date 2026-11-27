import test from 'node:test';
import assert from 'node:assert/strict';
import { compendiumTree, folderKey, folderPath } from './compendium-tree.js';

const row = (id, folder, count = 1) => ({id, pack: {id, name: id, ...(folder === undefined ? {} : {folder})}, entries: Array.from({length: count}, (_, n) => ({id: id + n}))});

test('declared folders nest packs and count every entry beneath them', () => {
  const tree = compendiumTree([
    row('weapons-2014', ['SRD', '2014'], 3), row('monsters-2014', ['SRD', '2014'], 2),
    row('weapons-2024', ['SRD', '2024'], 4), row('table-pack', undefined, 1),
  ]);
  assert.equal(tree.count, 10);
  assert.deepEqual(tree.packs.map(entry => entry.id), ['table-pack']);
  assert.deepEqual([...tree.folders.keys()], ['SRD']);
  const srd = tree.folders.get('SRD');
  assert.equal(srd.count, 9);
  assert.equal(srd.packs.length, 0);
  assert.deepEqual([...srd.folders.values()].map(folder => [folder.id, folder.name, folder.count, folder.packs.map(entry => entry.id)]), [
    [folderKey(['SRD', '2014']), '2014', 5, ['weapons-2014', 'monsters-2014']],
    [folderKey(['SRD', '2024']), '2024', 4, ['weapons-2024']],
  ]);
});

test('filtered rows create only the folders that still contain a pack', () => {
  const tree = compendiumTree([row('spells-2024', ['SRD', '2024'], 0)]);
  assert.deepEqual([...tree.folders.get('SRD').folders.keys()], ['2024']);
  assert.equal(tree.folders.get('SRD').count, 0);
  assert.equal(compendiumTree([]).folders.size, 0);
});

test('folders take their permission key from any pack placed beneath them', () => {
  const withIds = (id, folder, folderIds) => ({...row(id, folder), pack: {...row(id, folder).pack, folderIds}});
  const tree = compendiumTree([
    withIds('legacy', ['SRD', '2014']),
    withIds('items-2014', ['SRD', '2014'], ['folder:srd', 'folder:2014']),
    withIds('items-2024', ['SRD', '2024'], ['folder:srd']),
  ]);
  const srd = tree.folders.get('SRD');
  assert.equal(srd.accessId, 'folder:srd');
  assert.equal(srd.folders.get('2014').accessId, 'folder:2014');
  assert.equal(srd.folders.get('2024').accessId, '', 'Mismatched key lists are ignored.');
});

test('malformed folder paths keep the pack at the top level', () => {
  for (const folder of ['SRD', [''], ['  '], [1], [['SRD']], null, {name: 'SRD'}]) {
    assert.deepEqual(folderPath({folder}), [], JSON.stringify(folder));
    assert.deepEqual(compendiumTree([row('pack', folder)]).packs.map(entry => entry.id), ['pack']);
  }
  assert.deepEqual(folderPath({folder: [' SRD ', '2014']}), ['SRD', '2014']);
  assert.notEqual(folderKey(['a', 'b']), folderKey(['a b']));
});
