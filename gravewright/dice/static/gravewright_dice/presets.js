const gwText = (s, ...args) => s.replace(/\{(\d+)\}/g, (_, i) => args[Number(i)]);
const field = (key, label, min, max, initial) => ({ key, get label() { return gwText(label); }, min, max, initial });
const bonus = field('bonus', 'Modifier', -1000, 1000, 0);
const modifier = (v) => v ? ` ${v > 0 ? '+' : '-'} ${Math.abs(v)}` : '';
const one = (expression, label) => ({ expression, label, repeat: 1 });
export const dicePresets = [
    { id: 'attributes', get name() { return gwText('d20 attributes'); }, get hint() { return gwText('4d6 per attribute; drop the lowest. Each value is independent.'); }, fields: [field('attributes', 'Number of attributes', 1, 12, 6)], build: v => ({ expression: '4d6dl1', repeat: v.attributes, get label() { return gwText('d20 attributes'); } }) },
    { id: 'classic-attributes', get name() { return gwText('3d6 attributes'); }, get hint() { return gwText('Sum 3d6 per attribute, without dropping dice.'); }, fields: [field('attributes', 'Number of attributes', 1, 12, 6)], build: v => ({ expression: '3d6', repeat: v.attributes, get label() { return gwText('3d6 attributes'); } }) },
    { id: 'd20', get name() { return gwText('d20 check'); }, get hint() { return gwText('One d20 with a modifier.'); }, fields: [bonus], build: v => one('1d20' + modifier(v.bonus), gwText('d20 check')) },
    { id: 'advantage', get name() { return gwText('Advantage'); }, get hint() { return gwText('Roll 2d20 and keep the highest.'); }, fields: [bonus], build: v => one('2d20kh1' + modifier(v.bonus), gwText('Advantage')) },
    { id: 'disadvantage', get name() { return gwText('Disadvantage'); }, get hint() { return gwText('Roll 2d20 and keep the lowest.'); }, fields: [bonus], build: v => one('2d20kl1' + modifier(v.bonus), gwText('Disadvantage')) },
    { id: 'pool', get name() { return gwText('Success pool'); }, get hint() { return gwText('Each die equal to or above the difficulty counts as a success.'); }, fields: [field('count', 'Dice', 1, 99, 5), field('faces', 'Faces', 2, 1000, 10), field('target', 'Difficulty per die', 1, 1000, 8)], build: v => one(`${v.count}d${v.faces} >= ${v.target}`, gwText('Success pool')) },
    { id: 'pool-sum', get name() { return gwText('Sum pool'); }, get hint() { return gwText('Add all dice and apply the modifier.'); }, fields: [field('count', 'Dice', 1, 99, 3), field('faces', 'Faces', 2, 1000, 6), bonus], build: v => one(`${v.count}d${v.faces}` + modifier(v.bonus), gwText('Sum pool')) },
    { id: 'fudge', name: 'Fudge / Fate', get hint() { return gwText('Four dice with faces −1, 0, and +1, plus a modifier.'); }, fields: [bonus], build: v => one('4dF' + modifier(v.bonus), 'Fudge / Fate') },
    { id: '2d6', get name() { return gwText('2d6 check'); }, get hint() { return gwText('Numeric result of 2d6 with a modifier.'); }, fields: [bonus], build: v => one('2d6' + modifier(v.bonus), gwText('2d6 check')) },
    { id: 'percentile', get name() { return gwText('Percentile check'); }, get hint() { return gwText('Success when d100 is equal to or below the target.'); }, fields: [field('target', 'Target (%)', 1, 100, 50)], build: v => one(`1d100 + 0 <= ${v.target}`, gwText('Percentile check')) },
    { id: 'exploding', get name() { return gwText('Exploding dice'); }, get hint() { return gwText('Each maximum result rolls another die; add the results.'); }, fields: [field('count', 'Dice', 1, 99, 3), field('faces', 'Faces', 2, 1000, 6), bonus], build: v => one(`${v.count}d${v.faces}!` + modifier(v.bonus), gwText('Exploding dice')) },
];
export function buildPreset(preset, values) { for (const f of preset.fields) {
    const v = values[f.key];
    if (typeof v !== 'number' || !Number.isInteger(v) || v < f.min || v > f.max)
        throw Error(gwText('Check the {0} field.', f.label));
} if (preset.id === 'pool' && values.target > values.faces)
    throw Error(gwText('The difficulty must fit within the die faces.')); return preset.build(values); }
