const gwText = (s, ...args) => typeof window !== 'undefined' && window.gravewright?.i18n
    ? window.gravewright.i18n.t(s, args) : s.replace(/\{(\d+)\}/g, (match, i) => args[Number(i)] === undefined ? match : String(args[Number(i)]));
const field = (key, label, min, max, initial) => ({ key, get label() { return gwText(label); }, min, max, initial });
const bonus = field('bonus', 'Modifier', -1000, 1000, 0);
const modifier = (v) => v ? ` ${v > 0 ? '+' : '-'} ${Math.abs(v)}` : '';
const one = (expression, label) => ({ expression, label, repeat: 1 });
export const dicePresets = [
    { id: 'pool-sum', get name() { return gwText('Dice sum'); }, get hint() { return gwText('Add all dice and apply the modifier.'); }, fields: [field('count', 'Dice', 1, 99, 3), field('faces', 'Faces', 2, 1000, 6), bonus], build: v => one(`${v.count}d${v.faces}` + modifier(v.bonus), gwText('Dice sum')) },
    // Historical IDs and field keys remain stable; their labels have no game meaning.
    { id: 'attributes', get name() { return gwText('4d6, drop lowest'); }, get hint() { return gwText('Roll 4d6 and drop the lowest die for each repetition.'); }, fields: [field('attributes', 'Repetitions', 1, 12, 1)], build: v => ({ expression: '4d6dl1', repeat: v.attributes, label: '4d6dl1' }) },
    { id: 'classic-attributes', name: '3d6', get hint() { return gwText('Add 3d6 for each repetition.'); }, fields: [field('attributes', 'Repetitions', 1, 12, 1)], build: v => ({ expression: '3d6', repeat: v.attributes, label: '3d6' }) },
    { id: 'd20', name: '1d20', get hint() { return gwText('One d20 with a modifier.'); }, fields: [bonus], build: v => one('1d20' + modifier(v.bonus), '1d20') },
    { id: 'advantage', get name() { return gwText('2d20, keep highest'); }, get hint() { return gwText('Roll 2d20 and keep the highest.'); }, fields: [bonus], build: v => one('2d20kh1' + modifier(v.bonus), '2d20kh1') },
    { id: 'disadvantage', get name() { return gwText('2d20, keep lowest'); }, get hint() { return gwText('Roll 2d20 and keep the lowest.'); }, fields: [bonus], build: v => one('2d20kl1' + modifier(v.bonus), '2d20kl1') },
    { id: 'pool', get name() { return gwText('Count dice ≥ target'); }, get hint() { return gwText('Count each die equal to or above the target.'); }, fields: [field('count', 'Dice', 1, 99, 5), field('faces', 'Faces', 2, 1000, 10), field('target', 'Target per die', 1, 1000, 8)], build: v => one(`${v.count}d${v.faces} >= ${v.target}`, gwText('Count dice ≥ target')) },
    { id: 'fudge', name: '4dF', get hint() { return gwText('Four dice with faces −1, 0, and +1, plus a modifier.'); }, fields: [bonus], build: v => one('4dF' + modifier(v.bonus), '4dF') },
    { id: '2d6', name: '2d6', get hint() { return gwText('Numeric result of 2d6 with a modifier.'); }, fields: [bonus], build: v => one('2d6' + modifier(v.bonus), '2d6') },
    { id: 'percentile', get name() { return gwText('1d100 ≤ target'); }, get hint() { return gwText('Compare 1d100 with the target (≤).'); }, fields: [field('target', 'Target (%)', 1, 100, 50)], build: v => one(`1d100 + 0 <= ${v.target}`, gwText('1d100 ≤ target')) },
    { id: 'exploding', get name() { return gwText('Exploding dice'); }, get hint() { return gwText('Each maximum result rolls another die; add the results.'); }, fields: [field('count', 'Dice', 1, 99, 3), field('faces', 'Faces', 2, 1000, 6), bonus], build: v => one(`${v.count}d${v.faces}!` + modifier(v.bonus), gwText('Exploding dice')) },
];
export function buildPreset(preset, values) { for (const f of preset.fields) {
    const v = values[f.key];
    if (typeof v !== 'number' || !Number.isInteger(v) || v < f.min || v > f.max)
        throw Error(gwText('Check the {0} field.', f.label));
} if (preset.id === 'pool' && values.target > values.faces)
    throw Error(gwText('The difficulty must fit within the die faces.')); return preset.build(values); }
