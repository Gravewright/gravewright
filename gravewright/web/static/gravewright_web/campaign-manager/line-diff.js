/** Longest-common-subsequence line diff; inputs are bounded by journal limits. */
export function lineDiff(before, after) {
  const a = before.slice(0, 2000), b = after.slice(0, 2000);
  const table = Array.from({ length: a.length + 1 }, () => new Uint16Array(b.length + 1));
  for (let i = a.length - 1; i >= 0; i--) for (let j = b.length - 1; j >= 0; j--)
    table[i][j] = a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1]);
  const out = [];
  let i = 0, j = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) { out.push([' ', a[i]]); i++; j++; }
    else if (table[i + 1][j] >= table[i][j + 1]) out.push(['-', a[i++]]);
    else out.push(['+', b[j++]]);
  }
  while (i < a.length) out.push(['-', a[i++]]);
  while (j < b.length) out.push(['+', b[j++]]);
  return out;
}
