const aliases = new Map([
  ['Tradução', 'Translation'],
  ['Idiomas', 'Languages'],
  ['Dados', 'Dice'],
  ['Rolagens', 'Rolls'],
  ['Fichas', 'Sheets'],
  ['Automação', 'Automation'],
]);

/** Translate a display label while preserving its signed catalog identity. */
export function packageTagLabel(tag, translator) {
  return translator.t(aliases.get(tag) ?? tag);
}
