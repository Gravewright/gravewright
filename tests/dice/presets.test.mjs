import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {dicePresets, buildPreset} from '../../gravewright/dice/static/gravewright_dice/presets.js';

const initial = preset => Object.fromEntries(preset.fields.map(field => [field.key, field.initial]));
const byId = id => dicePresets.find(preset => preset.id === id);

test('the default is a configurable sum and all historical preset identifiers remain valid', () => {
  assert.equal(dicePresets[0].id, 'pool-sum');
  assert.deepEqual(buildPreset(dicePresets[0], initial(dicePresets[0])), {expression:'3d6', label:'Dice sum', repeat:1});
  assert.equal(buildPreset(dicePresets[0], {count:4, faces:8, bonus:-2}).expression, '4d8 - 2');
  assert.deepEqual(dicePresets.map(preset => preset.id).sort(), [
    'attributes', 'classic-attributes', 'd20', 'advantage', 'disadvantage',
    'pool', 'pool-sum', 'fudge', '2d6', 'percentile', 'exploding',
  ].sort());
  for (const preset of dicePresets) {
    const result = buildPreset(preset, initial(preset));
    assert.equal(result.repeat, 1);
    assert.doesNotMatch(preset.name, /attributes|advantage|fate|fudge|check/i);
    assert.throws(() => buildPreset(preset, {...initial(preset), [preset.fields[0].key]:NaN}));
  }
});

test('retained arithmetic presets use formula labels and explicit independent repetitions', () => {
  assert.deepEqual(buildPreset(byId('attributes'), {attributes:4}), {expression:'4d6dl1', label:'4d6dl1', repeat:4});
  assert.deepEqual(buildPreset(byId('classic-attributes'), {attributes:2}), {expression:'3d6', label:'3d6', repeat:2});
  assert.equal(byId('attributes').fields[0].label, 'Repetitions');
  assert.equal(buildPreset(byId('advantage'), {bonus:3}).expression, '2d20kh1 + 3');
  assert.equal(buildPreset(byId('disadvantage'), {bonus:0}).expression, '2d20kl1');
  assert.equal(buildPreset(byId('fudge'), {bonus:-1}).label, '4dF');
  assert.throws(() => buildPreset(byId('pool'), {count:2, faces:6, target:7}));
});

test('new formula names, hints and repetition labels are localized in Portuguese and Spanish', async () => {
  const added = ['Dice sum','4d6, drop lowest','Roll 4d6 and drop the lowest die for each repetition.',
    'Repetitions','Add 3d6 for each repetition.','2d20, keep highest','2d20, keep lowest',
    'Count dice ≥ target','Count each die equal to or above the target.','Target per die',
    '1d100 ≤ target','Compare 1d100 with the target (≤).','Formula presets'];
  try {
    for (const locale of ['pt-BR','es']) {
      const catalog = JSON.parse(await readFile(new URL(`../../gravewright/modules/locale_overrides/${locale}.json`, import.meta.url), 'utf8'));
      for (const key of added) {
        assert.equal(typeof catalog[key], 'string', `${locale}: ${key}`);
        assert.notEqual(catalog[key], key, `${locale}: ${key}`);
      }
      globalThis.window = {gravewright:{i18n:{t:key => catalog[key] ?? key}}};
      assert.equal(byId('attributes').fields[0].label, catalog.Repetitions);
      assert.equal(byId('pool-sum').name, catalog['Dice sum']);
      assert.equal(buildPreset(byId('pool-sum'), initial(byId('pool-sum'))).label, catalog['Dice sum']);
      assert.equal(byId('advantage').name, catalog['2d20, keep highest']);
    }
  } finally {
    delete globalThis.window;
  }
});
