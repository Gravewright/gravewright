import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createTranslator } from '../../gravewright/modules/static/gravewright_modules/i18n.js';
import { packageTagLabel } from '../../gravewright/web/static/gravewright_web/inside/package-tags.js';

const reviewed = Object.fromEntries(['pt-BR', 'es'].map(locale => [locale,
  JSON.parse(readFileSync(new URL(`../../gravewright/modules/locale_overrides/${locale}.json`, import.meta.url), 'utf8')),
]));
const tags = Object.freeze([
  'Tradução', 'Idiomas', 'Interface', 'Dados', '3D', 'Rolagens',
  'D&D', '5e', 'SRD', '2014', '2024', 'Savage Worlds', 'SWADE', 'Fichas', 'Automação',
]);
const expected = {
  en: ['Translation', 'Languages', 'Interface', 'Dice', '3D', 'Rolls',
    'D&D', '5e', 'SRD', '2014', '2024', 'Savage Worlds', 'SWADE', 'Sheets', 'Automation'],
  'pt-BR': ['Tradução', 'Idiomas', 'Interface', 'Dados', '3D', 'Rolagens',
    'D&D', '5e', 'SRD', '2014', '2024', 'Savage Worlds', 'SWADE', 'Fichas', 'Automação'],
  es: ['Traducción', 'Idiomas', 'Interfaz', 'Dados', '3D', 'Tiradas',
    'D&D', '5e', 'SRD', '2014', '2024', 'Savage Worlds', 'SWADE', 'Fichas', 'Automatización'],
};

function locale(id, messages = reviewed[id] ?? {}) {
  globalThis.window = new EventTarget();
  window.gravewrightLocale = { id, messages };
}

for (const id of ['en', 'pt-BR', 'es']) {
  test(`official host catalogs label current marketplace tags in ${id} without changing their identities`, () => {
    locale(id);
    const translator = createTranslator(), before = JSON.stringify(tags);
    assert.deepEqual(tags.map(tag => packageTagLabel(tag, translator)), expected[id]);
    assert.equal(JSON.stringify(tags), before);
  });
}

test('English defaults work with no installed Translator language package or browser locale', () => {
  delete globalThis.window;
  const translator = createTranslator();
  assert.equal(translator.locale, 'en');
  assert.deepEqual(tags.map(tag => packageTagLabel(tag, translator)), expected.en);
});

test('English catalog tags use the same official translations as their legacy Portuguese aliases', () => {
  const english = ['Translation', 'Languages', 'Interface', 'Dice', 'Rolls', 'Sheets', 'Automation'];
  for (const id of ['pt-BR', 'es']) {
    locale(id);
    const translator = createTranslator();
    const indices = [0, 1, 2, 3, 5, 13, 14];
    assert.deepEqual(english.map(tag => packageTagLabel(tag, translator)), indices.map(index => expected[id][index]));
  }
});

test('unknown tags, brands and acronyms retain the official adapter fallback and aliases are exact', () => {
  const unchanged = ['Custom campaign tools', 'Técnicas próprias', 'constructor', '__proto__',
    'dados', 'TRADUÇÃO', 'Fichas especiais', '3D', 'D&D', '5e', 'SRD', '2014', '2024', 'Savage Worlds', 'SWADE'];
  for (const id of ['en', 'pt-BR', 'es']) {
    locale(id);
    const translator = createTranslator();
    assert.deepEqual(unchanged.map(tag => packageTagLabel(tag, translator)), unchanged);
  }
});

test('new language catalogs and their disposal work through the real adapter without helper changes', () => {
  locale('fr-CA');
  const translator = createTranslator();
  assert.equal(packageTagLabel('Tradução', translator), 'Translation');
  const dispose = translator.register({
    en: { Translation: 'Translation', Languages: 'Languages', Dice: 'Dice', Rolls: 'Rolls',
      Sheets: 'Sheets', Automation: 'Automation', Interface: 'Interface', 'New category': 'New category' },
    fr: { Translation: 'Traduction', Languages: 'Langues', Dice: 'Dés', Rolls: 'Jets',
      Sheets: 'Fiches', Automation: 'Automatisation', Interface: 'Interface', 'New category': 'Nouvelle catégorie' },
  });
  try {
    assert.deepEqual(['Tradução', 'Idiomas', 'Dados', 'Rolagens', 'Fichas', 'Automação', 'New category']
      .map(tag => packageTagLabel(tag, translator)),
    ['Traduction', 'Langues', 'Dés', 'Jets', 'Fiches', 'Automatisation', 'Nouvelle catégorie']);
  } finally {
    dispose();
  }
  assert.equal(packageTagLabel('Tradução', translator), 'Translation');
  assert.equal(packageTagLabel('New category', translator), 'New category');
});

test('the same translator follows the selected locale instead of caching a display language', () => {
  locale('pt-BR');
  const translator = createTranslator();
  assert.equal(packageTagLabel('Rolagens', translator), 'Rolagens');
  window.gravewrightLocale = { id: 'es', messages: reviewed.es };
  assert.equal(packageTagLabel('Rolagens', translator), 'Tiradas');
  window.gravewrightLocale = { id: 'en', messages: {} };
  assert.equal(packageTagLabel('Rolagens', translator), 'Rolls');
});
