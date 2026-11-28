// Package library helpers: one card per package and its descriptive badges.

/** Compare stable `major.minor.patch` releases numerically. */
export function compareVersions(a, b) {
  const left = String(a).split('.').map(Number), right = String(b).split('.').map(Number);
  for (let index = 0; index < 3; index++) {
    const difference = (left[index] || 0) - (right[index] || 0);
    if (difference) return Math.sign(difference);
  }
  return 0;
}

/**
 * Keep one installed release per package ID: the newest usable release, or the
 * newest revoked one when none is usable. Older revoked releases stay recorded
 * on the server so their bytes cannot be installed again, but get no card.
 */
export function currentReleases(rows) {
  const current = new Map();
  for (const row of rows) {
    const kept = current.get(row.id);
    if (!kept || (kept.revoked && !row.revoked)
        || (!!kept.revoked === !!row.revoked && compareVersions(row.version, kept.version) > 0)) current.set(row.id, row);
  }
  return rows.filter(row => current.get(row.id) === row);
}

/**
 * Describe what a package provides, independently of signed catalog
 * categories: trusted server code, compendiums and the system a
 * compendium module requires (named after the installed system when known).
 */
export function packageBadges(pkg, installed = []) {
  const badges = [];
  if (pkg.django || pkg.type === 'django') badges.push({ kind: 'django' });
  if (pkg.content?.compendiums?.length) badges.push({ kind: 'compendiums' });
  const required = pkg.content?.requiresSystem?.id;
  if (required) {
    const system = currentReleases(installed.filter(row => row.id === required && row.system))[0];
    badges.push({ kind: 'system', id: required, name: system?.name ?? required });
  }
  return badges;
}
